import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "build_reap132_structural_prior.py"
SOURCE = Path(".scopes/archive/heretic-v2-reap96-consensus/evidence/reap96-phase2-score-report.json")
SPEC = importlib.util.spec_from_file_location("build_reap132_structural_prior", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_structural_prior_is_complete_and_deterministic():
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    source_sha256 = __import__("hashlib").sha256(source_bytes).hexdigest()
    first = MODULE.build(source, source_sha256=source_sha256, source_size=len(source_bytes))
    second = MODULE.build(source, source_sha256=source_sha256, source_size=len(source_bytes))
    assert MODULE.canonical_bytes(first) == MODULE.canonical_bytes(second)
    assert first["source"] == {"sha256": source_sha256, "size": len(source_bytes)}
    assert len(first["layers"]) == 43
    assert [x["layer"] for x in first["layers"]] == list(range(43))
    assert all(0 <= x["R_l"] <= 1 for x in first["layers"])
    layer2 = first["layers"][2]
    assert layer2["normalized_consensus_mass"] == 2.75 / 3
    assert layer2["rank97_normalized_score"] == 1.0
    assert layer2["high_score_count"] == 99
    assert layer2["deleted_high_count"] == 3
    assert layer2["boundary_tie"] is True
    assert layer2["R_l"] == (
        0.50 * (2.75 / 3)
        + 0.20
        + 0.15 * (99 / 132)
        + 0.10 * (3 / 36)
        + 0.05
    )


def test_structural_prior_rejects_inconsistent_selection_boundary():
    source = json.loads(SOURCE.read_text())
    source["layers"]["0"]["ranked_experts"][96]["selected"] = True
    try:
        MODULE.build(source, source_sha256="0" * 64, source_size=0)
    except ValueError as exc:
        assert "exactly 96 selected" in str(exc)
    else:
        raise AssertionError("inconsistent selection boundary was accepted")
