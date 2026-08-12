#!/usr/bin/env python3
"""Byte-verify a deterministic DeepSeek V4 REAP132 noMTP checkpoint."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mmap
import os
import re
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCHEMA = "heretic-v2-reap132-post-prune-v1"
EXPERT_RE = re.compile(
    r"^layers\.(?P<layer>\d+)\.ffn\.experts\.(?P<expert>\d+)\."
    r"(?P<projection>w[123])\.(?P<payload>weight|scale)$"
)
ROUTER_RE = re.compile(r"^layers\.(?P<layer>\d+)\.ffn\.gate\.weight$")
ROUTER_BIAS_RE = re.compile(r"^layers\.(?P<layer>\d+)\.ffn\.gate\.bias$")
TID_RE = re.compile(r"^layers\.(?P<layer>\d+)\.ffn\.gate\.tid2eid$")
MTP_PREFIX = "mtp."
PLAN_SHA = "b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04"
PLAN_LOGICAL_SHA = "082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17"
EXPECTED_CONFIG = {
    "model_type": "deepseek_v4",
    "n_routed_experts": 132,
    "num_hidden_layers": 43,
    "num_hash_layers": 3,
    "num_experts_per_tok": 6,
    "num_nextn_predict_layers": 0,
}
DIRECT_ALIGN = 4096


@dataclass(frozen=True)
class TensorRef:
    path: Path
    dtype: str
    shape: tuple[int, ...]
    start: int
    end: int

    @property
    def nbytes(self) -> int:
        return self.end - self.start

    def chunks(self, size: int = 8 * 1024 * 1024) -> Iterable[bytes]:
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECT)
        try:
            position = self.start
            remaining = self.nbytes
            while remaining:
                wanted = min(size, remaining)
                aligned_position = position - position % DIRECT_ALIGN
                leading = position - aligned_position
                aligned_size = ((leading + wanted + DIRECT_ALIGN - 1) // DIRECT_ALIGN) * DIRECT_ALIGN
                buffer = mmap.mmap(-1, aligned_size)
                try:
                    view = memoryview(buffer)
                    read = os.preadv(fd, [view], aligned_position)
                    if read < leading + wanted:
                        view.release()
                        raise ValueError(f"short O_DIRECT tensor payload: {self.path}")
                    block = bytes(view[leading:leading + wanted])
                    view.release()
                finally:
                    buffer.close()
                position += len(block)
                remaining -= len(block)
                yield block
        finally:
            os.close(fd)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    try:
        size = os.fstat(fd).st_size
        position = 0
        while position < size:
            wanted = min(8 * 1024 * 1024, size - position)
            aligned_size = ((wanted + DIRECT_ALIGN - 1) // DIRECT_ALIGN) * DIRECT_ALIGN
            buffer = mmap.mmap(-1, aligned_size)
            try:
                view = memoryview(buffer)
                read = os.preadv(fd, [view], position)
                if read < wanted:
                    view.release()
                    raise ValueError(f"short O_DIRECT file payload: {path}")
                digest.update(view[:wanted])
                view.release()
            finally:
                buffer.close()
            position += wanted
    finally:
        os.close(fd)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    claimed = payload.get("manifest_sha256")
    unsigned = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if claimed != actual:
        raise ValueError(f"manifest self-hash mismatch: {path}")
    return payload


def load_headers(checkpoint: Path, index: dict) -> dict[str, TensorRef]:
    refs: dict[str, TensorRef] = {}
    for filename in sorted(set(index["weight_map"].values())):
        path = checkpoint / filename
        if not path.is_file():
            raise ValueError(f"missing shard: {path}")
        with path.open("rb") as handle:
            raw_length = handle.read(8)
            if len(raw_length) != 8:
                raise ValueError(f"truncated safetensors header: {path}")
            header_length = struct.unpack("<Q", raw_length)[0]
            header = json.loads(handle.read(header_length))
        data_start = 8 + header_length
        for name, spec in header.items():
            if name == "__metadata__":
                continue
            # Overlay checkpoints may retain the pre-overlay tensor in its base
            # shard. The index-selected shard is the sole semantic owner.
            indexed_shard = index["weight_map"].get(name)
            if indexed_shard is None:
                raise ValueError(f"orphan tensor absent from index: {name}")
            if indexed_shard != filename:
                continue
            if name in refs:
                raise ValueError(f"duplicate tensor: {name}")
            start, end = spec["data_offsets"]
            ref = TensorRef(path, spec["dtype"], tuple(spec["shape"]), data_start + start, data_start + end)
            if ref.end < ref.start:
                raise ValueError(f"invalid offsets for {name}")
            refs[name] = ref
    index_names = set(index["weight_map"])
    if set(refs) != index_names:
        raise ValueError(
            f"index/header namespace mismatch: index={len(index_names)} header={len(refs)}"
        )
    return refs


def equal_bytes(left: TensorRef, right: TensorRef) -> bool:
    if left.dtype != right.dtype or left.shape != right.shape or left.nbytes != right.nbytes:
        return False
    return all(a == b for a, b in zip(left.chunks(), right.chunks()))


def equal_rows(source: TensorRef, output: TensorRef, rows: list[int]) -> bool:
    if len(source.shape) < 1 or len(output.shape) != len(source.shape):
        return False
    if output.shape[0] != len(rows) or source.shape[1:] != output.shape[1:]:
        return False
    if source.dtype != output.dtype or source.nbytes % source.shape[0]:
        return False
    row_bytes = source.nbytes // source.shape[0]
    with source.path.open("rb") as source_handle, output.path.open("rb") as output_handle:
        for new_id, old_id in enumerate(rows):
            source_handle.seek(source.start + old_id * row_bytes)
            output_handle.seek(output.start + new_id * row_bytes)
            if source_handle.read(row_bytes) != output_handle.read(row_bytes):
                return False
    return True


def plan_tid_bytes(plan: dict, layer: int) -> tuple[bytes, tuple[int, ...]]:
    item = plan["hash_routing"][str(layer)]
    raw = zlib.decompress(base64.b64decode(item["data"]))
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"plan tid2eid hash mismatch for layer {layer}")
    return raw, tuple(item["shape"])


def config_failures(output: Path) -> list[str]:
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    failures = [
        f"config {key}={config.get(key)!r}, expected {expected!r}"
        for key, expected in EXPECTED_CONFIG.items()
        if config.get(key) != expected
    ]
    args = config.get("moe_compress_args") or {}
    if args.get("drop_mtp") is not True:
        failures.append("config moe_compress_args.drop_mtp is not true")
    return failures


def verify(
    source: Path, output: Path, plan_path: Path, source_manifest_path: Path, output_manifest_path: Path
) -> dict:
    source = source.resolve()
    output = output.resolve()
    plan_path = plan_path.resolve()
    source_manifest = load_manifest(source_manifest_path.resolve())
    output_manifest = load_manifest(output_manifest_path.resolve())
    plan_bytes = plan_path.read_bytes()
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    plan = json.loads(plan_bytes)
    failures: list[str] = []
    if plan_sha != PLAN_SHA:
        failures.append(f"plan SHA mismatch: {plan_sha}")
    if plan.get("logical_sha256") != PLAN_LOGICAL_SHA:
        failures.append("plan logical SHA mismatch")
    failures.extend(config_failures(output))

    source_index = json.loads((source / "model.safetensors.index.json").read_text())
    output_index = json.loads((output / "model.safetensors.index.json").read_text())
    source_refs = load_headers(source, source_index)
    output_refs = load_headers(output, output_index)
    source_names = set(source_refs)
    output_names = set(output_refs)
    source_experts = {name for name in source_names if EXPERT_RE.fullmatch(name)}
    source_mtp = {name for name in source_names if name.startswith(MTP_PREFIX)}
    expected_names: set[str] = source_names - source_mtp - source_experts
    mapping: dict[tuple[int, int], int] = {}
    layer_results: list[dict] = []
    for layer_key, layer_plan in sorted(plan["layers"].items(), key=lambda item: int(item[0])):
        layer = int(layer_key)
        keep = layer_plan["kept_experts"]
        mapping.update({(layer, new_id): old_id for new_id, old_id in enumerate(keep)})
        for new_id in range(len(keep)):
            for projection in ("w1", "w2", "w3"):
                for payload in ("weight", "scale"):
                    expected_names.add(f"layers.{layer}.ffn.experts.{new_id}.{projection}.{payload}")
        layer_failures = []
        checked = 0
        for new_id, old_id in enumerate(keep):
            for projection in ("w1", "w2", "w3"):
                for payload in ("weight", "scale"):
                    out_name = f"layers.{layer}.ffn.experts.{new_id}.{projection}.{payload}"
                    src_name = f"layers.{layer}.ffn.experts.{old_id}.{projection}.{payload}"
                    if out_name not in output_refs or src_name not in source_refs:
                        layer_failures.append(f"missing expert provenance {out_name} <- {src_name}")
                    elif not equal_bytes(source_refs[src_name], output_refs[out_name]):
                        layer_failures.append(f"expert bytes mismatch {out_name} <- {src_name}")
                    checked += 1
        layer_results.append({"layer": layer, "kept_experts": len(keep), "expert_tensors": checked, "failures": layer_failures})
        failures.extend(layer_failures)

    expected_names.update(name for name in source_names if name not in source_experts and name not in source_mtp)
    if output_names != expected_names:
        failures.append(f"namespace mismatch: unexpected={len(output_names - expected_names)} missing={len(expected_names - output_names)}")
    if any(name.startswith(MTP_PREFIX) for name in output_names):
        failures.append("MTP/DSpark tensors remain in output")

    router_failures = []
    for name, out_ref in output_refs.items():
        match = ROUTER_RE.fullmatch(name) or ROUTER_BIAS_RE.fullmatch(name)
        if match:
            layer = int(match.group("layer"))
            keep = plan["layers"][str(layer)]["kept_experts"]
            source_name = name
            if source_name not in source_refs or not equal_rows(source_refs[source_name], out_ref, keep):
                router_failures.append(f"router mismatch {name}")
    failures.extend(router_failures)

    tid_failures = []
    dangling = 0
    for layer in range(3):
        name = f"layers.{layer}.ffn.gate.tid2eid"
        expected, shape = plan_tid_bytes(plan, layer)
        ref = output_refs.get(name)
        if ref is None or ref.dtype != "I64" or ref.shape != shape or ref.nbytes != len(expected):
            tid_failures.append(f"tid2eid shape/dtype mismatch {name}")
            continue
        actual = b"".join(ref.chunks())
        if actual != expected:
            tid_failures.append(f"tid2eid bytes mismatch {name}")
        values = struct.unpack("<" + "q" * (len(actual) // 8), actual)
        dangling += sum(value < 0 or value >= 132 for value in values)
    if dangling:
        tid_failures.append(f"dangling expert IDs: {dangling}")
    failures.extend(tid_failures)

    untouched_failures = []
    expert_output_names = {name for name in output_names if EXPERT_RE.fullmatch(name)}
    for name in sorted(output_names - expert_output_names - {f"layers.{i}.ffn.gate.tid2eid" for i in range(3)}):
        if ROUTER_RE.fullmatch(name) or ROUTER_BIAS_RE.fullmatch(name):
            continue
        if name not in source_refs or not equal_bytes(source_refs[name], output_refs[name]):
            untouched_failures.append(f"untouched tensor mismatch {name}")
    failures.extend(untouched_failures)

    summary = {
        "layers": "PASS" if len(layer_results) == 43 and not any(r["failures"] for r in layer_results) else "FAIL",
        "router": "PASS" if not router_failures else "FAIL",
        "experts": "PASS" if not any(r["failures"] for r in layer_results) else "FAIL",
        "scales": "PASS" if not any(".scale" in failure for failure in failures) else "FAIL",
        "shared_experts": "PASS" if not any("shared_experts" in failure for failure in untouched_failures) else "FAIL",
        "tid2eid": "PASS" if not tid_failures else "FAIL",
        "heretic_overlay": "PASS" if not any("attn.wo_b" in failure for failure in untouched_failures) else "FAIL",
        "mtp_dspark_absent": "PASS" if not (source_mtp & output_names) else "FAIL",
        "dangling_expert_ids": "PASS" if not dangling else "FAIL",
    }
    return {
        "schema": SCHEMA,
        "plan": {"file_sha256": plan_sha, "logical_sha256": plan.get("logical_sha256")},
        "source_manifest_sha256": source_manifest["manifest_sha256"],
        "output_manifest_sha256": output_manifest["manifest_sha256"],
        "source_tensor_count": len(source_names),
        "output_tensor_count": len(output_names),
        "expected_output_tensor_count": len(expected_names),
        "summary": summary,
        "layer_results": layer_results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(args.source, args.output, args.plan, args.source_manifest, args.output_manifest)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "failures": len(report["failures"]), "report": str(args.report.resolve())}, indent=2))
    return 0 if not report["failures"] and all(value == "PASS" for value in report["summary"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
