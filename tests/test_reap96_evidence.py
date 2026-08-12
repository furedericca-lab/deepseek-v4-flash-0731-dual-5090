import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "reap96_evidence.py"
SPEC = importlib.util.spec_from_file_location("reap96_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def mask(*, k=2, layers=("0",), experts=(1, 2)):
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": k,
        "source": {
            "repo": "org/repo", "revision_sha": "a" * 40, "path": "mask.json",
            "sha256": "b" * 64, "lineage": "test", "original_id_proof": "fixture",
        },
        "layers": {layer: {"kept_experts": list(experts)} for layer in layers},
    }


def test_validate_normalized_mask_accepts_original_ids():
    payload = mask(layers=("0",), experts=(1, 2))
    assert MODULE.validate_mask(payload, expected_k=2, expected_layers={"0"}) is payload


@pytest.mark.parametrize("experts", [(2, 1), (1, 1), (1, 256)])
def test_validate_rejects_noncanonical_expert_ids(experts):
    with pytest.raises(MODULE.EvidenceError):
        MODULE.validate_mask(mask(layers=("0",), experts=experts), expected_layers={"0"})


def test_validate_rejects_incomplete_layer_coverage():
    with pytest.raises(MODULE.EvidenceError, match="coverage"):
        MODULE.validate_mask(mask(layers=("0",)), expected_layers={"0", "1"})


def test_overlap_reports_k132_subset_relation():
    k132 = mask(k=2, layers=MODULE.LAYER_KEYS, experts=(1, 2))
    other = mask(k=3, layers=MODULE.LAYER_KEYS, experts=(1, 2, 3))
    other["source"]["repo"] = "org/other"
    report = MODULE.overlap_report(k132, [other])
    cell = next(iter(report["layers"][0]["sources"].values()))
    assert cell["intersection_with_k132"] == 2
    assert cell["k132_subset_of_source"] is True
    assert cell["jaccard_with_k132"] == pytest.approx(2 / 3, abs=1e-8)


def test_load_mask_records_independent_file_hash(tmp_path):
    path = tmp_path / "mask.json"
    path.write_text(json.dumps(mask(layers=("0",))), encoding="utf-8")
    loaded = MODULE.load_mask(path, expected_layers={"0"})
    assert loaded["normalized_file_sha256"] == MODULE.sha256_file(path)
