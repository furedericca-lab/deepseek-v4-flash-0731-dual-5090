#!/usr/bin/env python3
"""Verify a K96 IQ4_XS GGUF against its immutable K96 MXFP4 Golden."""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path


ALIGNMENT = 4096
CHUNK = 16 * 1024 * 1024
GGUF_MAGIC = 0x46554747
GGUF_MXFP4 = 39
GGUF_IQ4_XS = 23
GGUF_Q5_K = 13
GGUF_Q6_K = 14
EXPERT_PATTERN = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight$")
ROUTING_PATTERN = re.compile(r"^blk\.(\d+)\.(ffn_gate_inp|ffn_gate_tid2eid)\.weight$")


@dataclass(frozen=True)
class Tensor:
    shape: tuple[int, ...]
    tensor_type: int
    offset: int
    size: int


@dataclass(frozen=True)
class GGUF:
    path: Path
    metadata: dict[str, object]
    tensors: dict[str, Tensor]


def read_u32(handle) -> int:
    return struct.unpack("<I", handle.read(4))[0]


def read_u64(handle) -> int:
    return struct.unpack("<Q", handle.read(8))[0]


def read_string(handle) -> str:
    return handle.read(read_u64(handle)).decode("utf-8")


def read_value(handle, value_type: int) -> object:
    formats = {
        0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
        6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
    }
    if value_type in formats:
        fmt = formats[value_type]
        return struct.unpack(fmt, handle.read(struct.calcsize(fmt)))[0]
    if value_type == 8:
        return read_string(handle)
    if value_type == 9:
        element_type = read_u32(handle)
        count = read_u64(handle)
        if count > 1_000_000:
            for _ in range(count):
                skip_value(handle, element_type)
            return {"array_type": element_type, "count": count}
        return [read_value(handle, element_type) for _ in range(count)]
    raise ValueError(f"unsupported GGUF metadata value type {value_type}")


def skip_value(handle, value_type: int) -> None:
    primitive_sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
    if value_type in primitive_sizes:
        handle.seek(primitive_sizes[value_type], os.SEEK_CUR)
    elif value_type == 8:
        handle.seek(read_u64(handle), os.SEEK_CUR)
    elif value_type == 9:
        element_type = read_u32(handle)
        count = read_u64(handle)
        for _ in range(count):
            skip_value(handle, element_type)
    else:
        raise ValueError(f"unsupported GGUF metadata value type {value_type}")


def parse_gguf(path: Path) -> GGUF:
    with path.open("rb") as handle:
        if read_u32(handle) != GGUF_MAGIC:
            raise ValueError(f"not a GGUF file: {path}")
        version = read_u32(handle)
        if version not in (2, 3):
            raise ValueError(f"unsupported GGUF version {version}")
        tensor_count, kv_count = struct.unpack("<QQ", handle.read(16))
        metadata: dict[str, object] = {}
        alignment = 32
        keep_keys = {
            "general.architecture", "general.file_type", "general.name",
            "deepseek4.block_count", "deepseek4.expert_count",
            "deepseek4.expert_used_count", "deepseek4.hash_layer_count",
        }
        for _ in range(kv_count):
            key = read_string(handle)
            value_type = read_u32(handle)
            if key in keep_keys or key == "general.alignment":
                value = read_value(handle, value_type)
                metadata[key] = value
                if key == "general.alignment":
                    alignment = int(value)
            else:
                skip_value(handle, value_type)

        infos = []
        for _ in range(tensor_count):
            name = read_string(handle)
            dims = read_u32(handle)
            shape = struct.unpack("<" + "Q" * dims, handle.read(8 * dims))
            tensor_type = read_u32(handle)
            offset = read_u64(handle)
            infos.append((name, shape, tensor_type, offset))
        data_start = (handle.tell() + alignment - 1) // alignment * alignment

    sorted_offsets = sorted(offset for _, _, _, offset in infos)
    file_size = path.stat().st_size
    next_offset = {
        offset: sorted_offsets[index + 1] if index + 1 < len(sorted_offsets) else file_size - data_start
        for index, offset in enumerate(sorted_offsets)
    }
    tensors = {
        name: Tensor(tuple(shape), tensor_type, data_start + offset, next_offset[offset] - offset)
        for name, shape, tensor_type, offset in infos
    }
    metadata["tensor_count"] = tensor_count
    return GGUF(path, metadata, tensors)


def direct_read_stable(fd: int, offset: int, size: int) -> tuple[bytes, int]:
    base = offset - offset % ALIGNMENT
    lead = offset - base
    read_size = (lead + size + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
    previous: bytes | None = None
    unstable_reads = 0
    for _ in range(5):
        buffer = mmap.mmap(-1, read_size)
        try:
            view = memoryview(buffer)
            read = os.preadv(fd, [view], base)
            if read < lead + size:
                raise OSError("short O_DIRECT read")
            data = bytes(view[lead:lead + size])
            view.release()
        finally:
            buffer.close()
        if previous == data:
            return data, unstable_reads
        if previous is not None:
            unstable_reads += 1
        previous = data
    raise OSError(f"O_DIRECT read did not stabilize at offset {offset}")


def direct_compare(left: GGUF, right: GGUF, name: str) -> tuple[bool, str, int, int]:
    lhs = left.tensors[name]
    rhs = right.tensors[name]
    if lhs.size != rhs.size:
        return False, "size mismatch", 0, 0
    left_fd = os.open(left.path, os.O_RDONLY | os.O_DIRECT)
    right_fd = os.open(right.path, os.O_RDONLY | os.O_DIRECT)
    digest = hashlib.sha256()
    compared = 0
    unstable_reads = 0
    try:
        while compared < lhs.size:
            left_offset = lhs.offset + compared
            right_offset = rhs.offset + compared
            logical = min(CHUNK, lhs.size - compared)
            left_data, left_unstable = direct_read_stable(left_fd, left_offset, logical)
            right_data, right_unstable = direct_read_stable(right_fd, right_offset, logical)
            unstable_reads += left_unstable + right_unstable
            if left_data != right_data:
                return False, "payload mismatch", compared, unstable_reads
            digest.update(left_data)
            compared += logical
    finally:
        os.close(left_fd)
        os.close(right_fd)
    return True, digest.hexdigest(), compared, unstable_reads


def verify(golden_path: Path, candidate_path: Path) -> dict:
    golden = parse_gguf(golden_path)
    candidate = parse_gguf(candidate_path)
    failures: list[str] = []

    required_metadata = {
        "general.architecture": "deepseek4",
        "deepseek4.block_count": 43,
        "deepseek4.expert_count": 96,
        "deepseek4.expert_used_count": 6,
        "deepseek4.hash_layer_count": 3,
        "tensor_count": 1328,
    }
    for key, expected in required_metadata.items():
        if candidate.metadata.get(key) != expected:
            failures.append(f"candidate metadata {key}: {candidate.metadata.get(key)!r} != {expected!r}")
    for key in required_metadata:
        if key != "tensor_count" and candidate.metadata.get(key) != golden.metadata.get(key):
            failures.append(f"critical metadata drift: {key}")

    if set(golden.tensors) != set(candidate.tensors):
        failures.append("tensor namespace mismatch")

    experts = sorted(name for name in candidate.tensors if EXPERT_PATTERN.match(name))
    routing = sorted(name for name in candidate.tensors if ROUTING_PATTERN.match(name))
    if len(experts) != 129:
        failures.append(f"expected 129 routed-expert tensors, found {len(experts)}")
    expected_routing = {f"blk.{layer}.ffn_gate_inp.weight" for layer in range(43)}
    expected_routing.update(f"blk.{layer}.ffn_gate_tid2eid.weight" for layer in range(3))
    if set(routing) != expected_routing:
        failures.append(f"expected 46 router/tid2eid tensors, found {len(routing)}")

    comparisons = []
    for category, names in (("routed_expert", experts), ("routing", routing)):
        for name in names:
            source = golden.tensors[name]
            target = candidate.tensors[name]
            if source.shape != target.shape:
                failures.append(f"shape drift: {name}")
                continue
            if source.tensor_type != target.tensor_type:
                failures.append(f"type drift: {name}")
                continue
            if category == "routed_expert" and target.tensor_type != GGUF_MXFP4:
                failures.append(f"routed expert is not MXFP4: {name}")
                continue
            matched, detail, size, unstable_reads = direct_compare(golden, candidate, name)
            comparisons.append({"category": category, "name": name, "bytes": size, "sha256": detail if matched else None, "status": "PASS" if matched else "FAIL", "unstable_reads": unstable_reads})
            if not matched:
                failures.append(f"{category} payload drift: {name}: {detail}")

    type_counts: dict[str, int] = {}
    for tensor in candidate.tensors.values():
        key = str(tensor.tensor_type)
        type_counts[key] = type_counts.get(key, 0) + 1

    return {
        "schema": "heretic-reap96-iq4xs-acceptance-v1",
        "status": "PASS" if not failures else "FAIL",
        "golden": {"path": str(golden.path), "size_bytes": golden.path.stat().st_size},
        "candidate": {"path": str(candidate.path), "size_bytes": candidate.path.stat().st_size},
        "metadata": candidate.metadata,
        "tensor_type_counts": type_counts,
        "routed_expert_tensors": len(experts),
        "routing_tensors": len(routing),
        "comparison_count": len(comparisons),
        "comparison_bytes": sum(item["bytes"] for item in comparisons),
        "unstable_reads": sum(item["unstable_reads"] for item in comparisons),
        "comparisons": comparisons,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.golden, args.candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "routed_expert_tensors", "routing_tensors", "comparison_count", "comparison_bytes", "failures")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
