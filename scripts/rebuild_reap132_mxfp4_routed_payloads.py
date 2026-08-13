#!/usr/bin/env python3
"""Recompose every routed MXFP4 tensor in a K132 GGUF from accepted native bytes."""

from __future__ import annotations

import argparse
import mmap
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_mxfp4_gguf_repack as base
from verify_reap132_mxfp4_full_provenance import repack_expert


ALIGNMENT = 4096
CHUNK = 64 * 1024 * 1024
LAYERS = 43
EXPERTS = 132


def direct_copy(source: Path, destination: Path) -> None:
    size = source.stat().st_size
    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECT)
    destination_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_DIRECT, 0o600)
    buffer = mmap.mmap(-1, CHUNK)
    try:
        view = memoryview(buffer)
        offset = 0
        while offset < size:
            logical = min(CHUNK, size - offset)
            io_size = (logical + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
            received = os.preadv(source_fd, [view[:io_size]], offset)
            if received < logical:
                raise OSError(f"short O_DIRECT copy read at {offset}: {received}/{logical}")
            written = os.pwritev(destination_fd, [view[:io_size]], offset)
            if written != io_size:
                raise OSError(f"short O_DIRECT copy write at {offset}: {written}/{io_size}")
            offset += logical
        view.release()
        os.ftruncate(destination_fd, size)
        os.fsync(destination_fd)
    finally:
        buffer.close()
        os.close(source_fd)
        os.close(destination_fd)


def direct_replace(path: Path, offset: int, payload: bytes) -> None:
    fd = os.open(path, os.O_RDWR | os.O_DIRECT)
    try:
        position = 0
        while position < len(payload):
            absolute = offset + position
            base_offset = absolute - absolute % ALIGNMENT
            leading = absolute - base_offset
            logical = min(len(payload) - position, CHUNK - leading)
            io_size = (leading + logical + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
            buffer = mmap.mmap(-1, io_size)
            try:
                view = memoryview(buffer)
                received = os.preadv(fd, [view], base_offset)
                if received != io_size:
                    raise OSError(f"short O_DIRECT replace read at {base_offset}: {received}/{io_size}")
                view[leading:leading + logical] = payload[position:position + logical]
                written = os.pwritev(fd, [view], base_offset)
                if written != io_size:
                    raise OSError(f"short O_DIRECT replace write at {base_offset}: {written}/{io_size}")
                view.release()
            finally:
                buffer.close()
            position += logical
        os.fsync(fd)
    finally:
        os.close(fd)


def rebuild(source_root: Path, converter_output: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    staging = output.with_name(output.name + ".staging")
    if staging.exists():
        raise FileExistsError(staging)

    source = base.source_tensors(source_root)
    gguf = base.gguf_expert_tensors(converter_output)
    direct_copy(converter_output, staging)

    for layer in range(LAYERS):
        if base.expert_ids_for_layer(source, layer) != list(range(EXPERTS)):
            raise ValueError(f"layer {layer}: invalid native expert namespace")
        for projection, gguf_projection in base.PROJECTIONS.items():
            gguf_name = f"blk.{layer}.{gguf_projection}.weight"
            target = gguf[gguf_name]
            packed_tensor = bytearray(target.data.size)
            expert_size: int | None = None
            for expert in range(EXPERTS):
                weight = source[f"layers.{layer}.ffn.experts.{expert}.{projection}.weight"]
                scale = source[f"layers.{layer}.ffn.experts.{expert}.{projection}.scale"]
                rows, packed_cols = weight.shape
                expected = repack_expert(
                    base.direct_read(weight.data, 0, weight.data.size),
                    base.direct_read(scale.data, 0, scale.data.size),
                    rows,
                    packed_cols,
                )
                if expert_size is None:
                    expert_size = len(expected)
                elif len(expected) != expert_size:
                    raise ValueError(f"{gguf_name}: inconsistent expert payload sizes")
                start = expert * expert_size
                packed_tensor[start:start + expert_size] = expected
            if len(packed_tensor) != target.data.size:
                raise ValueError(f"{gguf_name}: rebuilt payload size mismatch")
            direct_replace(staging, target.data.offset, packed_tensor)
            print(f"rebuilt {gguf_name}: {len(packed_tensor)} bytes", flush=True)

    os.chmod(staging, 0o444)
    os.replace(staging, output)
    directory_fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--converter-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rebuild(args.source, args.converter_output, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
