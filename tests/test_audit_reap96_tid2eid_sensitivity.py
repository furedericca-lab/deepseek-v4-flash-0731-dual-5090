from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "audit_reap96_tid2eid_sensitivity.py"
SPEC = importlib.util.spec_from_file_location("audit_reap96_tid2eid_sensitivity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_cosine_and_raw_l2_can_choose_different_primary_replacements():
    router = np.asarray([[10.0, 0.0], [1.0, 0.1], [0.0, 1.0]], dtype=np.float32)
    survivors = [0, 2]
    assert np.argmin(MODULE.raw_l2_cost(router, survivors)[1]) == 1
    assert np.argmin(MODULE.cosine_cost(router, survivors)[1]) == 0


def test_optimal_assignment_improves_greedy_collision_case():
    table = np.asarray([[2, 3]], dtype=np.int64)
    survivors = [0, 1]
    cost = np.asarray([
        [0.0, 0.0],
        [0.0, 0.0],
        [0.0, 2.0],
        [0.1, 100.0],
    ])
    greedy, _ = MODULE.greedy_remap(table, survivors, cost)
    optimal, stats = MODULE.optimal_remap(table, survivors, cost)
    assert greedy.tolist() == [[0, 1]]
    assert optimal.tolist() == [[1, 0]]
    assert stats["rows_changed_vs_greedy"] == 1
    assert stats["absolute_improvement"] > 0


def test_distribution_reports_load_shape():
    report = MODULE.distribution(np.asarray([[0, 1, 1], [2, 1, 0]]), 3)
    assert report["counts"] == [2, 3, 1]
    assert report["maximum"] == 3


def test_count_distribution_does_not_reinterpret_counts_as_ids():
    report = MODULE.count_distribution(np.asarray([10, 2, 0]))
    assert report["counts"] == [10, 2, 0]
    assert report["maximum"] == 10
    assert report["max_to_median"] == 5.0
