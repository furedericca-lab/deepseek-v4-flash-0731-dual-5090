from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_reap132_mxfp4_full_provenance.py"
SPEC = importlib.util.spec_from_file_location("verify_reap132_mxfp4_full_provenance", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_repack_expert_matches_reference_rows() -> None:
    rng = np.random.default_rng(7)
    rows = 3
    packed_cols = 32
    weights = rng.integers(0, 256, size=(rows, packed_cols), dtype=np.uint8).tobytes()
    scales = rng.integers(0, 256, size=(rows, packed_cols // 16), dtype=np.uint8).tobytes()
    actual = MODULE.repack_expert(weights, scales, rows, packed_cols)
    expected = b"".join(
        MODULE.base.repack_source_row(
            weights[row * packed_cols:(row + 1) * packed_cols],
            scales[row * (packed_cols // 16):(row + 1) * (packed_cols // 16)],
        )
        for row in range(rows)
    )
    assert actual == expected
