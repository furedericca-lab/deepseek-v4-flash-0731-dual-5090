import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "extract_puwaer_reap132_mask.py"
SPEC = importlib.util.spec_from_file_location("extract_reap_mask", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_fragment_round_trip_is_identity_bound(tmp_path):
    kept = list(range(160))
    MODULE.write_fragment(
        tmp_path, layer=4, base_sha="a" * 40, pruned_sha="b" * 40,
        expected_kept=160, kept=kept, evidence="gate.bias-exact",
    )
    payload = json.loads((tmp_path / "layer-04.json").read_text())
    assert MODULE.validate_fragment(
        payload, layer=4, base_sha="a" * 40, pruned_sha="b" * 40, expected_kept=160,
    ) == (kept, "gate.bias-exact")


def test_fragment_rejects_revision_mismatch(tmp_path):
    MODULE.write_fragment(
        tmp_path, layer=0, base_sha="a" * 40, pruned_sha="b" * 40,
        expected_kept=2, kept=[1, 2], evidence="gate.weight-row-sha256-exact",
    )
    payload = json.loads((tmp_path / "layer-00.json").read_text())
    with pytest.raises(ValueError, match="revision identity"):
        MODULE.validate_fragment(
            payload, layer=0, base_sha="c" * 40, pruned_sha="b" * 40, expected_kept=2,
        )


def test_fragment_rejects_unsorted_survivors(tmp_path):
    path = tmp_path / "layer-00.json"
    path.write_text(json.dumps({
        "schema": "reap-expert-mask-fragment-v1", "layer": 0,
        "base_revision_sha": "a" * 40, "pruned_revision_sha": "b" * 40,
        "expected_kept": 2, "kept_experts": [2, 1], "mapping_evidence": "fixture",
    }))
    with pytest.raises(ValueError, match="invalid fragment survivor"):
        MODULE.validate_fragment(
            json.loads(path.read_text()), layer=0, base_sha="a" * 40,
            pruned_sha="b" * 40, expected_kept=2,
        )
