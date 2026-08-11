#!/usr/bin/env python3
"""Build REAP132 noMTP by slicing source safetensors payloads directly."""

from __future__ import annotations

import argparse
import base64
import json
import mmap
import os
import re
import shutil
import struct
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

EXPERT_RE = re.compile(r"^layers\.(\d+)\.ffn\.experts\.(\d+)\.(w[123])\.(weight|scale)$")
ROUTER_RE = re.compile(r"^layers\.(\d+)\.ffn\.gate\.(weight|bias)$")
MTP_PREFIX = "mtp."
SHARD_BYTES = 4_000_000_000


@dataclass(frozen=True)
class Ref:
    path: Path
    dtype: str
    shape: tuple[int, ...]
    start: int
    end: int

    @property
    def nbytes(self):
        return self.end - self.start


@dataclass(frozen=True)
class Slice:
    ref: Ref
    row_start: int = 0
    row_count: int | None = None

    @property
    def nbytes(self):
        if self.row_count is None:
            return self.ref.nbytes
        return self.ref.nbytes // self.ref.shape[0] * self.row_count

    @property
    def shape(self):
        return self.ref.shape if self.row_count is None else (self.row_count, *self.ref.shape[1:])


def headers(root: Path, index: dict) -> dict[str, Ref]:
    refs = {}
    for filename in sorted(set(index["weight_map"].values())):
        path = root / filename
        with path.open("rb") as f:
            nraw = f.read(8)
            n = struct.unpack("<Q", nraw)[0]
            header = json.loads(f.read(n))
        for name, spec in header.items():
            if name == "__metadata__" or index["weight_map"].get(name) != filename:
                continue
            if name in refs:
                raise ValueError(f"duplicate indexed tensor: {name}")
            start, end = spec["data_offsets"]
            refs[name] = Ref(path, spec["dtype"], tuple(spec["shape"]), 8 + n + start, 8 + n + end)
    if set(refs) != set(index["weight_map"]):
        raise ValueError("source index/header namespace mismatch")
    return refs


def plan_tid(plan: dict, layer: int) -> tuple[bytes, tuple[int, ...]]:
    item = plan["hash_routing"][str(layer)]
    raw = zlib.decompress(base64.b64decode(item["data"]))
    if __import__("hashlib").sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError(f"plan tid2eid hash mismatch: {layer}")
    return raw, tuple(item["shape"])


BLOCK = 8 * 1024 * 1024


def _direct_write(fd: int, data: bytes) -> None:
    """Write bytes through O_DIRECT using a page-aligned anonymous buffer."""
    offset = 0
    while offset < len(data):
        size = min(BLOCK, len(data) - offset)
        aligned = mmap.mmap(-1, BLOCK)
        try:
            aligned[:size] = data[offset:offset + size]
            view = memoryview(aligned)[:size]
            written = os.write(fd, view)
            if written != size:
                raise OSError(f"short O_DIRECT write: {written}/{size}")
            view.release()
        finally:
            aligned.close()
        offset += size


def copy_bytes(item: Slice, out_fd: int):
    row_bytes = item.ref.nbytes // item.ref.shape[0] if item.row_count is not None else item.ref.nbytes
    start = item.ref.start + item.row_start * row_bytes if item.row_count is not None else item.ref.start
    remaining = item.nbytes
    fd = os.open(item.ref.path, os.O_RDONLY)
    try:
        position = start
        while remaining:
            block = os.pread(fd, min(BLOCK, remaining), position)
            if not block:
                raise ValueError("short source payload")
            _direct_write(out_fd, block)
            position += len(block)
            remaining -= len(block)
            try:
                os.posix_fadvise(fd, position - len(block), len(block), os.POSIX_FADV_DONTNEED)
            except AttributeError:
                pass
    finally:
        os.close(fd)


def build(source: Path, output: Path, plan_path: Path, max_shard: int = SHARD_BYTES):
    source_index = json.loads((source / "model.safetensors.index.json").read_text())
    source_refs = headers(source, source_index)
    plan = json.loads(plan_path.read_text())
    output_items: dict[str, tuple[str, Slice | bytes, str, tuple[int, ...]]] = {}
    expert_names = set()

    for name, ref in source_refs.items():
        if name.startswith(MTP_PREFIX):
            continue
        match = EXPERT_RE.fullmatch(name)
        if match:
            expert_names.add(name)
            continue
        router = ROUTER_RE.fullmatch(name)
        if router:
            layer, kind = int(router.group(1)), router.group(2)
            keep = plan["layers"][str(layer)]["kept_experts"]
            if kind == "weight" or kind == "bias":
                output_items[name] = (name, Slice(ref, 0, len(keep)), ref.dtype, (len(keep), *ref.shape[1:]))
            continue
        if name.endswith("tid2eid") and name.startswith("layers."):
            layer = int(name.split(".")[1])
            raw, shape = plan_tid(plan, layer)
            output_items[name] = (name, raw, "I64", shape)
        else:
            output_items[name] = (name, Slice(ref), ref.dtype, ref.shape)

    for layer_key, layer_plan in plan["layers"].items():
        layer = int(layer_key)
        for new_id, old_id in enumerate(layer_plan["kept_experts"]):
            for projection in ("w1", "w2", "w3"):
                for payload in ("weight", "scale"):
                    old = f"layers.{layer}.ffn.experts.{old_id}.{projection}.{payload}"
                    new = f"layers.{layer}.ffn.experts.{new_id}.{projection}.{payload}"
                    if old not in source_refs:
                        raise ValueError(f"missing source expert: {old}")
                    ref = source_refs[old]
                    output_items[new] = (old, Slice(ref), ref.dtype, ref.shape)

    output.mkdir(parents=True, exist_ok=False)
    shard_no = 0
    pending = []
    pending_bytes = 0
    weight_map = {}

    def flush(items):
        nonlocal shard_no
        shard_no += 1
        filename = f"model-{shard_no:05d}-of-00000.safetensors"
        payload_path = output / (filename + ".payload")
        offsets = {}
        cursor = 0
        # Keep the temporary payload bounded and discard source pages after
        # each chunk. O_DIRECT is intentionally opt-in because safetensors
        # tensor lengths are not block-aligned; unaligned direct writes would
        # require padding gaps in every data offset.
        payload_fd = os.open(payload_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            for name, source_item, dtype, shape in items:
                offsets[name] = {"dtype": dtype, "shape": list(shape), "data_offsets": [cursor, cursor + (len(source_item) if isinstance(source_item, bytes) else source_item.nbytes)]}
                if isinstance(source_item, bytes):
                    _direct_write(payload_fd, source_item)
                else:
                    copy_bytes(source_item, payload_fd)
                cursor = offsets[name]["data_offsets"][1]
        finally:
            os.close(payload_fd)
        header = {"__metadata__": {"format": "pt"}}
        header.update(offsets)
        encoded = json.dumps(header, separators=(",", ":")).encode()
        final = output / filename
        try:
            with final.open("wb") as out, payload_path.open("rb") as payload:
                out.write(struct.pack("<Q", len(encoded)))
                out.write(encoded)
                shutil.copyfileobj(payload, out, BLOCK)
                out.flush()
                os.fsync(out.fileno())
            payload_path.unlink()
        except Exception:
            # Leave the completed payload for an explicit resume/inspection;
            # never publish a shard whose header and payload are incomplete.
            if final.exists():
                final.unlink()
            raise
        for name in offsets:
            weight_map[name] = filename

    for name in sorted(output_items):
        item = output_items[name]
        size = len(item[1]) if isinstance(item[1], bytes) else item[1].nbytes
        if pending and pending_bytes + size > max_shard:
            flush(pending)
            pending, pending_bytes = [], 0
        pending.append(item)
        pending_bytes += size
    if pending:
        flush(pending)

    total = shard_no
    for path in output.glob("model-*-of-00000.safetensors"):
        final = path.with_name(path.name.replace("of-00000", f"of-{total:05d}"))
        path.rename(final)
        for name, shard in list(weight_map.items()):
            if shard == path.name:
                weight_map[name] = final.name
    (output / "model.safetensors.index.json").write_text(json.dumps({"metadata": {"total_size": sum((output / s).stat().st_size for s in set(weight_map.values()))}, "weight_map": weight_map}, indent=2))
    config = json.loads((source / "config.json").read_text())
    config["n_routed_experts"] = 132
    config["moe_compress_args"] = {"plan": str(plan_path), "drop_mtp": True, "raw_safetensors_slice": True}
    (output / "config.json").write_text(json.dumps(config, indent=2))
    for name in ("generation_config.json", "tokenizer.json", "tokenizer_config.json"):
        if (source / name).exists():
            shutil.copy2(source / name, output / name)
    print(f"wrote {len(weight_map)} tensors in {total} shards")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("plan", type=Path)
    args = p.parse_args()
    build(args.source, args.output, args.plan)


if __name__ == "__main__":
    main()
