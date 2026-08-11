from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "verify_io_paths.py"
SPEC = importlib.util.spec_from_file_location("verify_io_paths", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_buffered_hash(tmp_path):
    path = tmp_path / "payload"
    payload = (b"reap132" * 10000) + b"tail"
    path.write_bytes(payload)
    assert MODULE.buffered_sha256(path) == hashlib.sha256(payload).hexdigest()


def test_direct_matches_buffered(tmp_path):
    path = tmp_path / "aligned-payload"
    path.write_bytes(bytes(range(256)) * 20000 + b"tail")
    try:
        result = MODULE.verify(path)
    except OSError as exc:
        pytest.skip(f"filesystem does not support O_DIRECT fixture: {exc}")
    assert result["match"] is True

