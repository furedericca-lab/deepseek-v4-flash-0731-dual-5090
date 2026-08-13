from __future__ import annotations

import importlib.util
import os
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "rebuild_reap132_mxfp4_routed_payloads.py"
SPEC = importlib.util.spec_from_file_location("rebuild_reap132_mxfp4_routed_payloads", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_direct_copy_and_unaligned_replace(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    payload = bytes((index * 37) % 256 for index in range(3 * MODULE.ALIGNMENT + 777))
    source.write_bytes(payload)
    MODULE.direct_copy(source, destination)
    replacement = bytes((index * 19) % 256 for index in range(MODULE.ALIGNMENT + 123))
    offset = MODULE.ALIGNMENT - 31
    MODULE.direct_replace(destination, offset, replacement)
    expected = bytearray(payload)
    expected[offset:offset + len(replacement)] = replacement
    assert destination.read_bytes() == expected
    assert os.stat(destination).st_size == len(payload)
