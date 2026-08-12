from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "build_reap96_raw.py"
SPEC = importlib.util.spec_from_file_location("build_reap96_raw", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def plans():
    parent = {
        "layers": {
            str(layer): {"kept_experts": list(range(10, 142))}
            for layer in range(43)
        }
    }
    target = {
        "layers": {
            str(layer): {"kept_experts": list(range(20, 116))}
            for layer in range(43)
        },
        "hash_routing": {str(layer): {"data": "fixture"} for layer in range(3)},
    }
    return parent, target


def test_derive_compact_plan_maps_original_ids_to_parent_positions():
    parent, target = plans()
    compact = MODULE.derive_compact_plan(parent, target)
    assert compact["layers"]["0"]["kept_experts"] == list(range(10, 106))
    assert compact["layers"]["0"]["original_experts"] == list(range(20, 116))
    assert compact["hash_routing"] is target["hash_routing"]


def test_derive_compact_plan_rejects_target_outside_parent():
    parent, target = plans()
    target["layers"]["7"]["kept_experts"][-1] = 250
    with pytest.raises(ValueError, match="not a K132 subset"):
        MODULE.derive_compact_plan(parent, target)


def test_derive_compact_plan_rejects_wrong_cardinality():
    parent, target = plans()
    target["layers"]["3"]["kept_experts"].pop()
    with pytest.raises(ValueError, match="96 unique"):
        MODULE.derive_compact_plan(parent, target)
