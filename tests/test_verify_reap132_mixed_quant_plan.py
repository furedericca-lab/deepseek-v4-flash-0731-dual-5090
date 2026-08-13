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


BUILDER = load("builder", ROOT / "scripts" / "build_reap132_mixed_quant_plan.py")
VERIFIER = load("verifier", ROOT / "scripts" / "verify_reap132_mixed_quant_plan.py")


def fixture(tmp_path: Path):
    structural = tmp_path / "structural.json"
    audit = tmp_path / "audit.json"
    structural.write_text(json.dumps({"layers": [
        {"layer": layer, "R_l": layer / 42, "k216_rank_mean": 100 - layer}
        for layer in range(43)
    ]}))
    layers = [{"layer": layer, "I_l": layer / 42, "P_l": layer / 42,
               "raw_I_l": float(layer)} for layer in range(43)]
    audit.write_text(json.dumps({"status": "PASS", "accepted_chunks": 200, "stages": [{
        "chunks": 200, "coverage_pass": True, "layers": layers,
        "path": "/tmp/imatrix.gguf", "sha256": "a" * 64, "size": 1,
    }]}))
    plan, types = BUILDER.build(structural, audit)
    plan_path = tmp_path / "plan.json"
    type_path = tmp_path / "types.txt"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    type_path.write_text(types)
    return structural, audit, plan_path, type_path


def test_independent_verifier_passes_and_detects_drift(tmp_path):
    structural, audit, plan, types = fixture(tmp_path)
    assert VERIFIER.verify(plan, structural, audit, types)["status"] == "PASS"
    doc = json.loads(plan.read_text())
    doc["layers"][0]["P_l"] += 0.01
    plan.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    report = VERIFIER.verify(plan, structural, audit, types)
    assert report["status"] == "FAIL"
    assert "layer 0 formula" in report["failures"]
