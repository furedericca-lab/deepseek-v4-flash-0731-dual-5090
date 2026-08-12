#!/usr/bin/env python3
"""Restore K96 routed-expert payloads from the immutable MXFP4 Golden."""

from __future__ import annotations

import argparse
import importlib.util
import mmap
import os
import sys
from pathlib import Path


ALIGNMENT = 4096
CHUNK = 16 * 1024 * 1024
VERIFIER = Path(__file__).with_name("verify_reap96_iq4xs_gguf.py")


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_reap96_iq4xs_gguf", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VERIFIER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def aligned_read(fd: int, offset: int, size: int) -> bytes:
    base = offset - offset % ALIGNMENT
    lead = offset - base
    read_size = (lead + size + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
    previous: bytes | None = None
    for _ in range(5):
        buffer = mmap.mmap(-1, read_size)
        try:
            view = memoryview(buffer)
            received = os.preadv(fd, [view], base)
            if received < lead + size:
                raise OSError(f"short O_DIRECT read at {offset}")
            data = bytes(view[lead:lead + size])
            view.release()
        finally:
            buffer.close()
        if previous == data:
            return data
        previous = data
    raise OSError(f"O_DIRECT read did not stabilize at {offset}")


def aligned_replace(fd: int, offset: int, data: bytes) -> None:
    base = offset - offset % ALIGNMENT
    lead = offset - base
    write_size = (lead + len(data) + ALIGNMENT - 1) // ALIGNMENT * ALIGNMENT
    existing = aligned_read(fd, base, write_size)
    buffer = mmap.mmap(-1, write_size)
    try:
        buffer[:] = existing
        buffer[lead:lead + len(data)] = data
        view = memoryview(buffer)
        for attempt in range(3):
            written = os.pwritev(fd, [view], base)
            if written == write_size:
                break
            if attempt == 2:
                raise OSError(f"short O_DIRECT write at {offset}: {written}/{write_size}")
        view.release()
    finally:
        buffer.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()

    verifier = load_verifier()
    golden = verifier.parse_gguf(args.golden)
    candidate = verifier.parse_gguf(args.candidate)
    experts = sorted(name for name in golden.tensors if verifier.EXPERT_PATTERN.match(name))
    if len(experts) != 129 or set(experts) != {name for name in candidate.tensors if verifier.EXPERT_PATTERN.match(name)}:
        raise ValueError("routed-expert namespace is not the expected 129 tensors")

    source_fd = os.open(args.golden, os.O_RDONLY | os.O_DIRECT)
    target_fd = os.open(args.candidate, os.O_RDWR | os.O_DIRECT)
    try:
        for index, name in enumerate(experts, 1):
            source = golden.tensors[name]
            target = candidate.tensors[name]
            if source.shape != target.shape or source.tensor_type != verifier.GGUF_MXFP4 or target.tensor_type != verifier.GGUF_MXFP4 or source.size != target.size:
                raise ValueError(f"routed-expert contract mismatch: {name}")
            copied = 0
            while copied < source.size:
                size = min(CHUNK, source.size - copied)
                data = aligned_read(source_fd, source.offset + copied, size)
                aligned_replace(target_fd, target.offset + copied, data)
                copied += size
            os.fsync(target_fd)
            print(f"[{index:3d}/129] {name}", flush=True)
    finally:
        os.close(source_fd)
        os.close(target_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
