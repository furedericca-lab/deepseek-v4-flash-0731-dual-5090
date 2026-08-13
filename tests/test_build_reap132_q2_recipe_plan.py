import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILDER = load("q2_builder", ROOT / "scripts" / "build_reap132_q2_recipe_plan.py")
VERIFIER = load("q2_verifier", ROOT / "scripts" / "verify_reap132_q2_recipe_plan.py")


def inputs(tmp_path: Path):
    recipe = tmp_path / ".recipe.q2k.txt"
    recipe.write_text(BUILDER.EXPECTED_RECIPE)
    imatrix = tmp_path / "imatrix.gguf"
    imatrix.write_bytes(b"imatrix")
    production_imatrix = tmp_path / "production-imatrix.gguf"
    production_imatrix.write_bytes(b"production-imatrix")
    compatibility = tmp_path / "compatibility.json"
    compatibility.write_text(json.dumps({
        "status": "PASS",
        "output": {"path": str(production_imatrix.resolve()), "sha256": BUILDER.sha256(production_imatrix), "entries": 769, "chunks": 812},
        "external": {"sha256": BUILDER.sha256(imatrix), "entries_copied": 768},
        "supplemental": {"entry_copied": "output_hc_fn.weight"},
        "overlapping_entries_replaced": 0,
    }))
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({
        "status": "PASS",
        "stages": [{
            "path": str(imatrix.resolve()),
            "sha256": BUILDER.sha256(imatrix),
            "chunks": 812,
            "coverage_pass": True,
            "zero_count_experts": [],
            "missing_entries": [],
            "malformed_entries": [],
            "count_mismatches": [],
        }],
    }))
    golden = tmp_path / "golden.gguf"
    golden.write_bytes(b"golden")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({
        "status": "PASS",
        "gguf": str(golden.resolve()),
        "coverage": {"routed_tensors": 129, "expert_comparisons": 17028, "all_rows_and_blocks": True},
    }))
    return recipe, imatrix, production_imatrix, compatibility, audit, golden, provenance


def test_builds_deterministic_routed_only_plan(tmp_path):
    recipe, imatrix, production_imatrix, compatibility, audit, golden, provenance = inputs(tmp_path)
    args = (recipe.resolve(), imatrix.resolve(), production_imatrix.resolve(), compatibility.resolve(), audit.resolve(), golden.resolve(), "b" * 64, provenance.resolve(), "c" * 40, "a" * 40)
    plan_a, types_a = BUILDER.build(*args)
    plan_b, types_b = BUILDER.build(*args)
    assert plan_a == plan_b
    assert types_a == types_b == BUILDER.ROUTED_TYPE_FILE
    assert plan_a["counts"] == {"MXFP4": 15, "Q2_K": 76, "Q3_K": 38, "routed_total": 129}
    assert "shexp" not in types_a and "attn" not in types_a and "output" not in types_a

    plan_path = tmp_path / "plan.json"
    type_path = tmp_path / "types.txt"
    plan_path.write_text(json.dumps(plan_a, indent=2, sort_keys=True) + "\n")
    type_path.write_text(types_a)
    report = VERIFIER.verify(plan_path.resolve(), type_path.resolve(), recipe.resolve(), imatrix.resolve(), production_imatrix.resolve(), compatibility.resolve(), audit.resolve(), golden.resolve(), "b" * 64, provenance.resolve(), "c" * 40, "a" * 40)
    assert report["status"] == "PASS"

    type_path.write_text(types_a.replace("Q3_K", "Q2_K", 1))
    report = VERIFIER.verify(plan_path.resolve(), type_path.resolve(), recipe.resolve(), imatrix.resolve(), production_imatrix.resolve(), compatibility.resolve(), audit.resolve(), golden.resolve(), "b" * 64, provenance.resolve(), "c" * 40, "a" * 40)
    assert report["status"] == "FAIL"
    assert "tensor type content" in report["failures"]


def test_rejects_recipe_drift(tmp_path):
    recipe, imatrix, production_imatrix, compatibility, audit, golden, provenance = inputs(tmp_path)
    recipe.write_text(BUILDER.EXPECTED_RECIPE.replace("q3_K", "q2_K"))
    try:
        BUILDER.build(recipe.resolve(), imatrix.resolve(), production_imatrix.resolve(), compatibility.resolve(), audit.resolve(), golden.resolve(), "b" * 64, provenance.resolve(), "c" * 40, "a" * 40)
    except ValueError as exc:
        assert "recipe content drift" in str(exc)
    else:
        raise AssertionError("drifted recipe was accepted")


def test_rejects_unaccepted_imatrix(tmp_path):
    recipe, imatrix, production_imatrix, compatibility, audit, golden, provenance = inputs(tmp_path)
    doc = json.loads(audit.read_text())
    doc["status"] = "INCOMPLETE"
    audit.write_text(json.dumps(doc))
    try:
        BUILDER.build(recipe.resolve(), imatrix.resolve(), production_imatrix.resolve(), compatibility.resolve(), audit.resolve(), golden.resolve(), "b" * 64, provenance.resolve(), "c" * 40, "a" * 40)
    except ValueError as exc:
        assert "not accepted" in str(exc)
    else:
        raise AssertionError("unaccepted imatrix was accepted")
