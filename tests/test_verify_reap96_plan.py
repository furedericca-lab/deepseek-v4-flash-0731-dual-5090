import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_reap96_plan.py"
SPEC = importlib.util.spec_from_file_location("verify_reap96_plan", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_verifier_rejects_selection_outside_k132():
    layers = {str(layer): {"kept_experts": list(range(96))} for layer in range(43)}
    score = {"layers": {str(layer): {
        "selected_experts": list(range(96)),
        "ranked_experts": [
            {"selected": expert < 96, "score": 5 if expert < 96 else 0}
            for expert in range(132)
        ],
    } for layer in range(43)}}
    k132 = {"logical_sha256": "x", "layers": {str(layer): {"kept_experts": list(range(132))} for layer in range(43)}}
    plan = {
        "schema": "heretic-reap96-consensus-v1",
        "k132_plan": {"sha256": "k", "logical_sha256": "x"},
        "score_report": {"sha256": "s"},
        "layers": layers,
        "hash_routing": {},
    }
    plan["layers"]["0"]["kept_experts"][-1] = 255
    report = MODULE.verify_plan(plan, k132, score, k132_sha="k", score_sha="s")
    assert report["status"] == "FAIL"
    assert any("not a K132 subset" in failure for failure in report["failures"])
