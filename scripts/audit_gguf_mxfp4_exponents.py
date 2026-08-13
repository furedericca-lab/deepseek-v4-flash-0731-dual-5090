#!/usr/bin/env python3
"""Audit MXFP4 exponent bytes in one GGUF tensor using O_DIRECT reads."""

from __future__ import annotations

import argparse
import collections
import json
import mmap
import os
import re
from pathlib import Path

from verify_reap96_iq4xs_gguf import ALIGNMENT, GGUF_MXFP4, parse_gguf


BLOCK_SIZE = 17
BLOCK_ELEMENTS = 32
CHUNK = 64 * 1024 * 1024 // BLOCK_SIZE * BLOCK_SIZE


ROUTED_PATTERN = re.compile(r"^blk\.\d+\.ffn_(gate|up|down)_exps\.weight$")


def audit_tensor(path: Path, tensor_name: str, tensor) -> dict[str, object]:
    if tensor.tensor_type != GGUF_MXFP4:
        raise ValueError(f"{tensor_name} is not MXFP4: {tensor.tensor_type}")
    logical_size = tensor.size - tensor.size % BLOCK_SIZE
    if logical_size == 0:
        raise ValueError(f"empty MXFP4 tensor: {tensor_name}")

    ne0, ne1, ne2 = tensor.shape
    blocks_per_row = ne0 // BLOCK_ELEMENTS
    histogram: collections.Counter[int] = collections.Counter()
    high_blocks: list[tuple[int, int, bytes]] = []
    fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    try:
        consumed = 0
        while consumed < logical_size:
            logical = min(CHUNK, logical_size - consumed)
            start = tensor.offset + consumed
            base = start - start % ALIGNMENT
            lead = start - base
            read_size = (lead + logical + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
            buffer = mmap.mmap(-1, read_size)
            try:
                view = memoryview(buffer)
                received = os.preadv(fd, [view], base)
                if received < lead + logical:
                    raise OSError(f"short O_DIRECT read at {start}")
                data = view[lead:lead + logical]
                first_block = consumed // BLOCK_SIZE
                for local in range(0, logical, BLOCK_SIZE):
                    exponent = data[local]
                    quants = bytes(data[local + 1:local + BLOCK_SIZE])
                    block = first_block + local // BLOCK_SIZE
                    histogram[exponent] += 1
                    if exponent >= 128:
                        high_blocks.append((block, exponent, quants))
                data.release()
                view.release()
            finally:
                buffer.close()
            consumed += logical
    finally:
        os.close(fd)

    records = []
    for block, exponent, quants in high_blocks[:100]:
        row_block = block % blocks_per_row
        row_index = block // blocks_per_row
        expert = row_index // ne1
        row = row_index % ne1
        records.append({
            "block": block,
            "exponent": exponent,
            "expert": expert,
            "row": row,
            "col": row_block * BLOCK_ELEMENTS,
            "quants": quants.hex(),
        })
    return {
        "tensor": tensor_name,
        "shape": tensor.shape,
        "blocks": logical_size // BLOCK_SIZE,
        "exponent_min": min(histogram),
        "exponent_max": max(histogram),
        "top_exponents": {str(key): histogram[key] for key in sorted(histogram)[-16:]},
        "high_count": len(high_blocks),
        "high_blocks": records,
    }


def audit(path: Path, tensor_name: str | None, all_routed: bool) -> dict[str, object]:
    gguf = parse_gguf(path)
    names = (
        sorted(name for name in gguf.tensors if ROUTED_PATTERN.match(name))
        if all_routed else [tensor_name]
    )
    if any(name is None for name in names):
        raise ValueError("--tensor is required unless --all-routed is used")
    records = [audit_tensor(path, name, gguf.tensors[name]) for name in names]
    return {
        "gguf": str(path),
        "tensor_count": len(records),
        "high_tensor_count": sum(record["high_count"] > 0 for record in records),
        "high_block_count": sum(record["high_count"] for record in records),
        "tensors": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gguf", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tensor")
    group.add_argument("--all-routed", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.gguf, args.tensor, args.all_routed)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
