#!/usr/bin/env python3
"""Build a reviewable K96 plan and regenerate hash-layer routing."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mmap
import os
import struct
import zlib
from pathlib import Path
from typing import Any

import numpy as np

DIRECT_ALIGN = 4096
HASH_LAYERS = range(3)
TOP_K = 6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_ref(checkpoint: Path, name: str) -> tuple[Path, str, tuple[int, ...], int, int]:
    index = json.loads((checkpoint / "model.safetensors.index.json").read_text(encoding="utf-8"))
    filename = index["weight_map"][name]
    path = checkpoint / filename
    with path.open("rb") as handle:
        raw_length = handle.read(8)
        header_length = struct.unpack("<Q", raw_length)[0]
        header = json.loads(handle.read(header_length))
    spec = header[name]
    start, end = spec["data_offsets"]
    data_start = 8 + header_length
    return path, spec["dtype"], tuple(spec["shape"]), data_start + start, data_start + end


def direct_read(path: Path, start: int, end: int) -> bytes:
    length = end - start
    aligned_start = start - start % DIRECT_ALIGN
    leading = start - aligned_start
    aligned_length = ((leading + length + DIRECT_ALIGN - 1) // DIRECT_ALIGN) * DIRECT_ALIGN
    fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    try:
        buffer = mmap.mmap(-1, aligned_length)
        try:
            view = memoryview(buffer)
            received = os.preadv(fd, [view], aligned_start)
            if received < leading + length:
                view.release()
                raise ValueError(f"short O_DIRECT tensor read: {path}")
            raw = bytes(view[leading:leading + length])
            view.release()
            return raw
        finally:
            buffer.close()
    finally:
        os.close(fd)


def decode_matrix(raw: bytes, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    if dtype == "BF16":
        words = np.frombuffer(raw, dtype="<u2").astype(np.uint32)
        values = (words << 16).view(np.float32)
    elif dtype == "F32":
        values = np.frombuffer(raw, dtype="<f4")
    elif dtype == "F16":
        values = np.frombuffer(raw, dtype="<f2").astype(np.float32)
    else:
        raise ValueError(f"unsupported router dtype: {dtype}")
    return values.reshape(shape).astype(np.float32, copy=False)


def decode_tid(item: dict[str, Any]) -> np.ndarray:
    raw = zlib.decompress(base64.b64decode(item["data"]))
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError("K132 tid2eid blob checksum mismatch")
    table = np.frombuffer(raw, dtype="<i8").reshape(item["shape"])
    if table.shape[1] != TOP_K or np.any(table < 0) or np.any(table >= 132):
        raise ValueError("K132 tid2eid geometry/range mismatch")
    if np.any(np.diff(np.sort(table, axis=1), axis=1) == 0):
        raise ValueError("K132 tid2eid contains duplicate row IDs")
    return table


def candidate_order(router: np.ndarray, selected_old_ids: list[int]) -> dict[int, list[int]]:
    selected = router[selected_old_ids]
    orders = {}
    for old_id in range(router.shape[0]):
        distances = np.sum((selected - router[old_id]) ** 2, axis=1, dtype=np.float64)
        orders[old_id] = [selected_old_ids[index] for index in np.lexsort((selected_old_ids, distances))]
    return orders


def remap_tid(table: np.ndarray, router: np.ndarray, selected_old_ids: list[int]) -> tuple[np.ndarray, dict[str, int]]:
    selected_set = set(selected_old_ids)
    new_id = {old_id: compact for compact, old_id in enumerate(selected_old_ids)}
    orders = candidate_order(router, selected_old_ids)
    output = np.empty_like(table)
    direct = replacements = collision_avoids = 0
    for row_index, row in enumerate(table):
        assigned: dict[int, int] = {}
        used: set[int] = set()
        # Preserve surviving direct assignments before replacing deleted IDs.
        for position, old_value in enumerate(row.tolist()):
            if old_value in selected_set:
                assigned[position] = old_value
                used.add(old_value)
                direct += 1
        for position, old_value in enumerate(row.tolist()):
            if position in assigned:
                continue
            replacements += 1
            for candidate_index, candidate in enumerate(orders[old_value]):
                if candidate not in used:
                    assigned[position] = candidate
                    used.add(candidate)
                    collision_avoids += int(candidate_index > 0)
                    break
            else:
                raise ValueError(f"row {row_index}: no collision-free replacement")
        output[row_index] = [new_id[assigned[position]] for position in range(TOP_K)]
    if np.any(output < 0) or np.any(output >= 96):
        raise ValueError("K96 tid2eid outside compact range")
    if np.any(np.diff(np.sort(output, axis=1), axis=1) == 0):
        raise ValueError("K96 tid2eid contains duplicate row IDs")
    return output, {"direct_assignments": direct, "replacements": replacements, "collision_avoids": collision_avoids}


def compressed_blob(table: np.ndarray) -> dict[str, Any]:
    raw = table.astype("<i8", copy=False).tobytes(order="C")
    compressed = zlib.compress(raw, level=9)
    return {
        "dtype": "int64",
        "shape": list(table.shape),
        "encoding": "zlib+base64",
        "raw_nbytes": len(raw),
        "compressed_nbytes": len(compressed),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(compressed).decode("ascii"),
    }


def build_plan(k132_path: Path, score_path: Path, checkpoint: Path) -> dict[str, Any]:
    k132 = json.loads(k132_path.read_text(encoding="utf-8"))
    score = json.loads(score_path.read_text(encoding="utf-8"))
    if score.get("schema") != "heretic-reap96-consensus-score-report-v1":
        raise ValueError("unsupported score report")
    layers = {}
    for layer in map(str, range(43)):
        selected = score["layers"][layer]["selected_experts"]
        universe = k132["layers"][layer]["kept_experts"]
        if len(selected) != 96 or selected != sorted(selected) or not set(selected) <= set(universe):
            raise ValueError(f"layer {layer}: invalid selected K96 subset")
        layers[layer] = {"kept_experts": selected}

    hash_routing = {}
    for layer in HASH_LAYERS:
        k132_original = k132["layers"][str(layer)]["kept_experts"]
        selected_original = layers[str(layer)]["kept_experts"]
        old_compact = {original: compact for compact, original in enumerate(k132_original)}
        selected_old_ids = [old_compact[original] for original in selected_original]
        tensor_name = f"layers.{layer}.ffn.gate.weight"
        path, dtype, shape, start, end = tensor_ref(checkpoint, tensor_name)
        router = decode_matrix(direct_read(path, start, end), dtype, shape)
        if router.shape[0] != 132:
            raise ValueError(f"layer {layer}: expected 132 router rows, got {router.shape}")
        table = decode_tid(k132["hash_routing"][str(layer)])
        remapped, stats = remap_tid(table, router, selected_old_ids)
        hash_routing[str(layer)] = {
            "tensor_name": f"layers.{layer}.ffn.gate.tid2eid",
            "source_router_tensor": tensor_name,
            "source_router_dtype": dtype,
            "replacement": "squared-L2 nearest K96 router row; preserve direct survivors; exclude row-local duplicates",
            "stats": stats,
            **compressed_blob(remapped),
        }

    plan = {
        "schema": "heretic-reap96-consensus-v1",
        "model": "DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP",
        "base_num_routed_experts": 256,
        "candidate_num_routed_experts": 132,
        "kept_num_routed_experts": 96,
        "num_hidden_layers": 43,
        "num_hash_layers": 3,
        "top_k": TOP_K,
        "k132_plan": {"path": str(k132_path), "sha256": sha256_file(k132_path), "logical_sha256": k132["logical_sha256"]},
        "score_report": {"path": str(score_path), "sha256": sha256_file(score_path)},
        "layers": layers,
        "hash_routing": hash_routing,
    }
    logical = {key: plan[key] for key in ("k132_plan", "score_report", "layers", "hash_routing")}
    plan["logical_sha256"] = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k132-plan", type=Path, required=True)
    parser.add_argument("--score-report", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_plan(args.k132_plan.resolve(), args.score_report.resolve(), args.checkpoint.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "logical_sha256": plan["logical_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
