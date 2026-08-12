from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_reap132_raw.py"
SPEC = importlib.util.spec_from_file_location("build_reap132_raw", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_direct_pread_supports_unaligned_tensor_payload(tmp_path):
    path = tmp_path / "source.safetensors"
    payload = bytes(range(256)) * 64
    path.write_bytes(payload)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    except OSError as exc:
        pytest.skip(f"filesystem does not support O_DIRECT fixture: {exc}")
    try:
        assert MODULE._direct_pread(fd, 137, 8193) == payload[137:8330]
    finally:
        os.close(fd)


def test_direct_writer_preserves_unaligned_segments(tmp_path):
    path = tmp_path / "output.safetensors"
    parts = [b"header", bytes(range(251)) * 37, b"tail"]
    try:
        writer = MODULE.DirectWriter(path)
    except OSError as exc:
        pytest.skip(f"filesystem does not support O_DIRECT fixture: {exc}")
    for part in parts:
        writer.write(part)
    writer.close()
    assert path.read_bytes() == b"".join(parts)
