#!/usr/bin/env python3
"""Verify sampled DeepSeek-V4 expert MXFP4 blocks against a GGUF payload.

This intentionally does not use ``GGUFReader`` or safetensors tensor loaders:
both can mmap large files.  It parses only headers through buffered reads and
uses aligned O_DIRECT reads for every payload comparison.
"""

from __future__ import annotations

import argparse
import json
import mmap
import os
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ALIGNMENT = 4096
GGUF_MAGIC = 0x46554747
GGUF_MXFP4 = 39
GGUF_Q8_0 = 8
PROJECTIONS = {
    "w1": "ffn_gate_exps",
    "w2": "ffn_down_exps",
    "w3": "ffn_up_exps",
}


@dataclass(frozen=True)
class Range:
    path: Path
    offset: int
    size: int


@dataclass(frozen=True)
class SourceTensor:
    shape: tuple[int, int]
    data: Range


@dataclass(frozen=True)
class GGUFExpertTensor:
    shape: tuple[int, int, int]
    data: Range


@dataclass(frozen=True)
class GGUFTensor:
    shape: tuple[int, ...]
    tensor_type: int
    data: Range


def direct_read(data: Range, relative: int, size: int) -> bytes:
    if relative < 0 or size < 0 or relative + size > data.size:
        raise ValueError(f"range outside payload: offset={relative}, size={size}, total={data.size}")
    offset = data.offset + relative
    aligned_offset = offset - offset % ALIGNMENT
    leading = offset - aligned_offset
    aligned_size = (leading + size + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
    fd = os.open(data.path, os.O_RDONLY | os.O_DIRECT)
    try:
        buffer = mmap.mmap(-1, aligned_size)
        try:
            view = memoryview(buffer)
            received = os.preadv(fd, [view], aligned_offset)
            if received < leading + size:
                raise OSError(f"short O_DIRECT read from {data.path}: {received} < {leading + size}")
            result = bytes(view[leading:leading + size])
            view.release()
            return result
        finally:
            buffer.close()
    finally:
        os.close(fd)


def source_tensors(root: Path) -> dict[str, SourceTensor]:
    index = json.loads((root / "model.safetensors.index.json").read_text(encoding="utf-8"))
    result: dict[str, SourceTensor] = {}
    for shard in sorted(set(index["weight_map"].values())):
        path = root / shard
        with path.open("rb") as handle:
            header_length = struct.unpack("<Q", handle.read(8))[0]
            header = json.loads(handle.read(header_length))
        base = 8 + header_length
        for name, item in header.items():
            if name == "__metadata__" or index["weight_map"].get(name) != shard:
                continue
            is_weight = item["dtype"] == "I8" and name.endswith(".weight")
            is_scale = item["dtype"] == "F8_E8M0" and name.endswith(".scale")
            is_fp8_pair = item["dtype"] in {"F8_E4M3", "F8_E8M0"} and name.endswith((".weight", ".scale"))
            is_nonexpert = name in {"embed.weight", "norm.weight", "head.weight"}
            if not (is_weight or is_scale or is_fp8_pair or is_nonexpert):
                continue
            shape = tuple(item["shape"])
            if len(shape) not in (1, 2):
                continue
            start, end = item["data_offsets"]
            result[name] = SourceTensor(shape, Range(path, base + start, end - start))
    return result


def read_u32(handle) -> int:
    return struct.unpack("<I", handle.read(4))[0]


def read_u64(handle) -> int:
    return struct.unpack("<Q", handle.read(8))[0]


def read_string(handle) -> str:
    return handle.read(read_u64(handle)).decode("utf-8")


def skip_value(handle, value_type: int) -> None:
    # GGUF primitive value type sizes.  Arrays recurse using their element type.
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


def gguf_tensors(path: Path) -> dict[str, GGUFTensor]:
    with path.open("rb") as handle:
        if read_u32(handle) != GGUF_MAGIC:
            raise ValueError("not a GGUF file")
        version = read_u32(handle)
        if version not in (2, 3):
            raise ValueError(f"unsupported GGUF version {version}")
        tensor_count, kv_count = struct.unpack("<QQ", handle.read(16))
        alignment = 32
        for _ in range(kv_count):
            key = read_string(handle)
            value_type = read_u32(handle)
            if key == "general.alignment" and value_type == 4:
                alignment = read_u32(handle)
            else:
                skip_value(handle, value_type)
        infos: list[tuple[str, tuple[int, ...], int, int]] = []
        for _ in range(tensor_count):
            name = read_string(handle)
            dims = struct.unpack("<I", handle.read(4))[0]
            shape = struct.unpack("<" + "Q" * dims, handle.read(8 * dims))
            tensor_type = read_u32(handle)
            offset = read_u64(handle)
            infos.append((name, shape, tensor_type, offset))
        data_start = (handle.tell() + alignment - 1) // alignment * alignment
    # Tensor offsets are relative to the data section.  Most checks only need a
    # small prefix, so use the next declared offset as a conservative payload
    # bound rather than materializing tensors or maintaining a full type table.
    file_size = path.stat().st_size
    sorted_offsets = sorted(offset for _, _, _, offset in infos)
    next_offsets = {
        offset: (sorted_offsets[index + 1] if index + 1 < len(sorted_offsets) else file_size - data_start)
        for index, offset in enumerate(sorted_offsets)
    }
    result: dict[str, GGUFTensor] = {}
    for name, shape, tensor_type, offset in infos:
        payload_end = next_offsets[offset]
        if payload_end < offset:
            raise ValueError(f"invalid GGUF tensor offset for {name}: {offset} > {payload_end}")
        result[name] = GGUFTensor(shape, tensor_type, Range(path, data_start + offset, payload_end - offset))
    return result


def gguf_expert_tensors(path: Path) -> dict[str, GGUFExpertTensor]:
    all_tensors = gguf_tensors(path)
    result: dict[str, GGUFExpertTensor] = {}
    for name, tensor in all_tensors.items():
        shape = tensor.shape
        tensor_type = tensor.tensor_type
        if tensor_type != GGUF_MXFP4 or ".ffn_" not in name or "_exps.weight" not in name:
            continue
        if len(shape) != 3:
            raise ValueError(f"unexpected expert shape for {name}: {shape}")
        logical_cols, rows, experts = shape
        if logical_cols % 32:
            raise ValueError(f"unexpected MXFP4 logical cols for {name}: {logical_cols}")
        size = experts * rows * (logical_cols // 32) * 17
        result[name] = GGUFExpertTensor((experts, rows, logical_cols), Range(path, tensor.data.offset, size))
    return result


def repack_source_row(source: bytes, scales: bytes) -> bytes:
    if len(source) * 2 != len(scales) * 32:
        raise ValueError("source packed row and scale row disagree")
    output = bytearray()
    for block, exponent in enumerate(scales):
        packed = source[block * 16:(block + 1) * 16]
        values = []
        for value in packed:
            values.extend((value & 0x0F, value >> 4))
        output.append(exponent)
        output.extend(values[index] | values[index + 16] << 4 for index in range(16))
    return bytes(output)


def verify(source_root: Path, gguf_path: Path, layers: list[int], experts: list[int], rows: int) -> dict:
    source = source_tensors(source_root)
    gguf = gguf_expert_tensors(gguf_path)
    comparisons = []
    failures = []
    for layer in layers:
        for expert in experts:
            for projection, gguf_projection in PROJECTIONS.items():
                weight_name = f"layers.{layer}.ffn.experts.{expert}.{projection}.weight"
                scale_name = f"layers.{layer}.ffn.experts.{expert}.{projection}.scale"
                gguf_name = f"blk.{layer}.{gguf_projection}.weight"
                weight = source.get(weight_name)
                scale = source.get(scale_name)
                target = gguf.get(gguf_name)
                if weight is None or scale is None or target is None:
                    failures.append(f"missing input for {weight_name}")
                    continue
                out_features, packed_cols = weight.shape
                scale_rows, blocks = scale.shape
                if scale_rows != out_features or blocks != packed_cols // 16:
                    failures.append(f"invalid source shapes for {weight_name}: {weight.shape}, {scale.shape}")
                    continue
                if target.shape != (132, out_features, packed_cols * 2):
                    failures.append(f"unexpected GGUF shape for {gguf_name}: {target.shape}")
                    continue
                sampled_rows = min(rows, out_features)
                row_bytes = packed_cols
                scale_bytes = blocks
                target_row_bytes = blocks * 17
                for row in range(sampled_rows):
                    source_weight = direct_read(weight.data, row * row_bytes, row_bytes)
                    source_scale = direct_read(scale.data, row * scale_bytes, scale_bytes)
                    expected = repack_source_row(source_weight, source_scale)
                    target_offset = (expert * out_features + row) * target_row_bytes
                    actual = direct_read(target.data, target_offset, target_row_bytes)
                    record = {"layer": layer, "expert": expert, "projection": projection, "row": row}
                    comparisons.append(record)
                    if actual != expected:
                        failures.append(f"payload mismatch: {record}")
    return {
        "source": str(source_root),
        "gguf": str(gguf_path),
        "comparison_count": len(comparisons),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def verify_nonexpert(source_root: Path, gguf_path: Path, sample_bytes: int) -> dict:
    source = source_tensors(source_root)
    gguf = gguf_tensors(gguf_path)
    mapping = {
        "embed.weight": "token_embd.weight",
        "norm.weight": "output_norm.weight",
        "head.weight": "output.weight",
    }
    comparisons = []
    failures = []
    for source_name, gguf_name in mapping.items():
        item = source.get(source_name)
        target = gguf.get(gguf_name)
        if item is None or target is None:
            failures.append(f"missing input for {source_name}")
            continue
        expected_type = 0 if source_name == "norm.weight" else 30
        if target.tensor_type != expected_type:
            failures.append(f"unexpected GGUF type for {gguf_name}: {target.tensor_type}")
            continue
        expected_shape = tuple(reversed(item.shape))
        if target.shape != expected_shape:
            failures.append(f"unexpected GGUF shape for {gguf_name}: {target.shape} != {expected_shape}")
            continue
        offsets = sorted({0, max(0, item.data.size // 2 - sample_bytes // 2), max(0, item.data.size - sample_bytes)})
        for offset in offsets:
            size = min(sample_bytes, item.data.size - offset)
            expected = direct_read(item.data, offset, size)
            if source_name == "norm.weight":
                if size % 2:
                    raise ValueError("BF16 sample must contain whole elements")
                bits = struct.unpack("<" + "H" * (size // 2), expected)
                expected = struct.pack("<" + "f" * len(bits), *(struct.unpack("<f", struct.pack("<I", value << 16))[0] for value in bits))
                target_offset = offset * 2
            else:
                target_offset = offset
            actual = direct_read(Range(target.data.path, target.data.offset, item.data.size * (2 if source_name == "norm.weight" else 1)), target_offset, len(expected))
            record = {"source": source_name, "gguf": gguf_name, "offset": offset, "size": size}
            comparisons.append(record)
            if actual != expected:
                failures.append(f"payload mismatch: {record}")
    return {
        "source": str(source_root),
        "gguf": str(gguf_path),
        "comparison_count": len(comparisons),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


FP8_TARGETS = {
    "attn.wkv.weight": "attn_kv.weight",
    "attn.wo_a.weight": "attn_output_a.weight",
    "attn.wo_b.weight": "attn_output_b.weight",
    "attn.wq_a.weight": "attn_q_a.weight",
    "attn.wq_b.weight": "attn_q_b.weight",
    "attn.indexer.wq_b.weight": "indexer.attn_q_b.weight",
    "ffn.shared_experts.w1.weight": "ffn_gate_shexp.weight",
    "ffn.shared_experts.w2.weight": "ffn_down_shexp.weight",
    "ffn.shared_experts.w3.weight": "ffn_up_shexp.weight",
}


def fp8_e4m3_to_float(data: bytes) -> list[float]:
    """Decode torch.float8_e4m3fn source bytes without loading safetensors."""
    result = []
    for value in data:
        sign = -1.0 if value & 0x80 else 1.0
        exponent = (value >> 3) & 0x0F
        mantissa = value & 0x07
        if exponent == 0:
            result.append(sign * (mantissa / 8.0) * 2.0 ** -6)
        elif exponent == 0x0F and mantissa == 0x07:
            result.append(sign * 448.0)
        else:
            result.append(sign * (1.0 + mantissa / 8.0) * 2.0 ** (exponent - 7))
    return result


def q8_0_block(values: list[float]) -> bytes:
    if len(values) != 32:
        raise ValueError("Q8_0 expects exactly 32 values")
    # Match gguf.quants.Q8_0 exactly: dequantization is float32, the scale is
    # rounded to float16 only after quantizing, and ties round away from zero.
    block = np.asarray(values, dtype=np.float32).reshape(1, 32)
    scale = np.abs(block).max(axis=1, keepdims=True) / np.float32(127.0)
    inverse = np.where(scale == 0, np.float32(0.0), np.float32(1.0) / scale)
    magnitude = np.abs(block * inverse)
    rounded = np.sign(block * inverse) * (np.floor(magnitude) + np.floor(2 * (magnitude - np.floor(magnitude))))
    return scale.astype(np.float16).view(np.uint8).tobytes() + rounded.astype(np.int8).view(np.uint8).tobytes()


def verify_fp8(source_root: Path, gguf_path: Path, layers: list[int], rows: int) -> dict:
    source = source_tensors(source_root)
    gguf = gguf_tensors(gguf_path)
    comparisons = []
    failures = []
    for layer in layers:
        for suffix, target_suffix in FP8_TARGETS.items():
            weight_name = f"layers.{layer}.{suffix}"
            scale_name = weight_name.removesuffix(".weight") + ".scale"
            gguf_name = f"blk.{layer}.{target_suffix}"
            weight = source.get(weight_name)
            scale = source.get(scale_name)
            target = gguf.get(gguf_name)
            # The first sliding-attention layer has no CSA indexer tensors.
            # Absence on both sides is architectural, not a conversion failure.
            if weight is None and scale is None and target is None:
                continue
            if weight is None or scale is None or target is None:
                failures.append(f"missing input for {weight_name}")
                continue
            if target.tensor_type != GGUF_Q8_0:
                failures.append(f"unexpected GGUF type for {gguf_name}: {target.tensor_type}")
                continue
            out_features, in_features = weight.shape
            scale_rows, scale_cols = scale.shape
            if scale_rows * 128 < out_features or scale_cols * 128 < in_features:
                failures.append(f"invalid FP8 scale shape for {weight_name}: {scale.shape}")
                continue
            if target.shape != (in_features, out_features):
                failures.append(f"unexpected GGUF shape for {gguf_name}: {target.shape}")
                continue
            row_count = min(rows, out_features)
            q8_row_bytes = (in_features // 32) * 34
            for row in range(row_count):
                source_bytes = direct_read(weight.data, row * in_features, in_features)
                scale_bytes = direct_read(scale.data, (row // 128) * scale_cols, scale_cols)
                source_values = fp8_e4m3_to_float(source_bytes)
                dequantized = [
                    value * 2.0 ** (scale_bytes[column // 128] - 127)
                    for column, value in enumerate(source_values)
                ]
                expected = b"".join(
                    q8_0_block(dequantized[offset:offset + 32])
                    for offset in range(0, in_features, 32)
                )
                actual = direct_read(target.data, row * q8_row_bytes, q8_row_bytes)
                record = {"layer": layer, "source": weight_name, "gguf": gguf_name, "row": row}
                comparisons.append(record)
                if actual != expected:
                    failures.append(f"payload mismatch: {record}")
    return {
        "source": str(source_root),
        "gguf": str(gguf_path),
        "comparison_count": len(comparisons),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--layers", default="0,1,2")
    parser.add_argument("--experts", default="0,65,131")
    parser.add_argument("--rows", type=int, default=4)
    parser.add_argument("--nonexpert", action="store_true", help="verify BF16 embedding, output norm, and LM head")
    parser.add_argument("--fp8", action="store_true", help="verify dequantized FP8 backbone payloads against GGML Q8_0")
    parser.add_argument("--sample-bytes", type=int, default=65536)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.sample_bytes < 1:
        parser.error("--sample-bytes must be positive")
    if args.nonexpert and args.fp8:
        parser.error("--nonexpert and --fp8 are mutually exclusive")
    report = verify_nonexpert(args.source, args.gguf, args.sample_bytes) if args.nonexpert else (
        verify_fp8(args.source, args.gguf, [int(x) for x in args.layers.split(",")], args.rows)
        if args.fp8 else verify(args.source, args.gguf, [int(x) for x in args.layers.split(",")],
                                [int(x) for x in args.experts.split(",")], args.rows)
    )
    encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.report:
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
