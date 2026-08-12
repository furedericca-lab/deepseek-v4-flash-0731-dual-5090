import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_reap96_plan.py"
SPEC = importlib.util.spec_from_file_location("build_reap96_plan", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_remap_preserves_survivors_and_avoids_replacement_collision():
    router = np.arange(8, dtype=np.float32).reshape(8, 1)
    table = np.array([[0, 1, 2, 3, 4, 5], [2, 3, 4, 5, 6, 7]], dtype=np.int64)
    remapped, stats = MODULE.remap_tid(table, router, [0, 2, 4, 5, 6, 7])
    assert remapped.shape == (2, 6)
    assert np.all(np.diff(np.sort(remapped, axis=1), axis=1) != 0)
    assert remapped.min() == 0 and remapped.max() == 5
    assert stats["replacements"] == 3


def test_candidate_order_breaks_equal_distance_by_compact_id():
    router = np.array([[0.0], [2.0], [4.0]], dtype=np.float32)
    orders = MODULE.candidate_order(router, [0, 2])
    assert orders[1] == [0, 2]
