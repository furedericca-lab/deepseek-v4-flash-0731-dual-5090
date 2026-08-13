import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "build_reap132_mixed_quant_plan.py"
SPEC = importlib.util.spec_from_file_location("build_reap132_mixed_quant_plan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def inputs(tmp_path: Path, status="PASS"):
    structural = tmp_path / "structural.json"
    audit = tmp_path / "audit.json"
    structural.write_text(json.dumps({"layers": [
        {"layer": layer, "R_l": layer / 42, "k216_rank_mean": 100 - layer}
        for layer in range(43)
    ]}))
    layers = [{"layer": layer, "I_l": layer / 42, "P_l": layer / 42,
               "raw_I_l": float(layer)} for layer in range(43)]
    audit.write_text(json.dumps({
        "status": status,
        "accepted_chunks": 200 if status == "PASS" else None,
        "stages": [{"chunks": 200, "coverage_pass": True, "layers": layers,
                    "path": "/tmp/imatrix.gguf", "sha256": "a" * 64, "size": 1234}],
    }))
    golden = tmp_path / "golden.gguf"
    golden.write_bytes(b"golden")
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({
        "status": "PASS",
        "gguf": str(golden.resolve()),
        "coverage": {"routed_tensors": 129, "expert_comparisons": 17028, "all_rows_and_blocks": True},
    }))
    return structural, audit, golden, provenance


def test_plan_is_deterministic_and_routed_only(tmp_path):
    structural, audit, golden, provenance = inputs(tmp_path)
    plan_a, types_a = MODULE.build(structural, audit, golden.resolve(), "b" * 64, provenance.resolve(), "a" * 40)
    plan_b, types_b = MODULE.build(structural, audit, golden.resolve(), "b" * 64, provenance.resolve(), "a" * 40)
    assert plan_a == plan_b
    assert types_a == types_b
    assert plan_a["counts"] == {
        "IQ3_XXS_layers": 17, "Q2_K_S_layers": 26,
        "IQ3_XXS_tensors": 51, "Q2_K_S_tensors": 78,
    }
    assert plan_a["output_filename"] == MODULE.OUTPUT_FILENAME
    assert sum(item["recipe"] == "IQ3_XXS" for item in plan_a["layers"]) == 17
    assert sum(item["recipe"] == "Q2_K_S" for item in plan_a["layers"]) == 26
    lines = types_a.splitlines()
    assert len(lines) == 43
    assert all("ffn_(gate|up|down)_exps" in line for line in lines)
    assert not any("shexp" in line or "router" in line or "tid2eid" in line for line in lines)
    assert {item["layer"] for item in plan_a["layers"] if item["recipe"] == "IQ3_XXS"} == set(range(26, 43))


def test_rejects_unaccepted_audit(tmp_path):
    structural, audit, golden, provenance = inputs(tmp_path, status="INCOMPLETE")
    try:
        MODULE.build(structural, audit, golden.resolve(), "b" * 64, provenance.resolve(), "a" * 40)
    except ValueError as exc:
        assert "not accepted" in str(exc)
    else:
        raise AssertionError("unaccepted imatrix audit was accepted")


def test_rejects_invalid_llama_cpp_commit(tmp_path):
    structural, audit, golden, provenance = inputs(tmp_path)
    try:
        MODULE.build(structural, audit, golden.resolve(), "b" * 64, provenance.resolve(), "not-a-commit")
    except ValueError as exc:
        assert "commit" in str(exc)
    else:
        raise AssertionError("invalid llama.cpp commit was accepted")
