import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "derive_reap132_inventory.py"
SPEC = importlib.util.spec_from_file_location("derive_reap132_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def expert_names(layer, expert):
    return {
        f"layers.{layer}.ffn.experts.{expert}.{projection}.{payload}"
        for projection in ("w1", "w2", "w3")
        for payload in ("weight", "scale")
    }


def write_inputs(tmp_path, names, keep):
    index = tmp_path / "model.safetensors.index.json"
    plan = tmp_path / "plan.json"
    index.write_text(json.dumps({"weight_map": {name: "model.safetensors" for name in names}}))
    plan.write_text(json.dumps({"layers": {"0": {"kept_experts": keep}}}))
    return index, plan


def test_derives_no_mtp_output_count(tmp_path):
    names = expert_names(0, 0) | expert_names(0, 1) | {
        "mtp.0.extra.weight",
        "model.embed_tokens.weight",
    }
    index, plan = write_inputs(tmp_path, names, [1])

    result = MODULE.derive_inventory(index, plan)

    assert result["source_tensor_count"] == 14
    assert result["source_expert_tensor_count"] == 12
    assert result["output_expert_tensor_count"] == 6
    assert result["dropped_expert_tensor_count"] == 6
    assert result["source_mtp_dspark_tensor_count"] == 1
    assert result["expected_output_tensor_count"] == 7
    assert result["expected_output_mtp_dspark_tensor_count"] == 0
    assert result["failures"] == []


def test_reports_incomplete_and_missing_plan_experts(tmp_path):
    names = expert_names(0, 0)
    names.remove("layers.0.ffn.experts.0.w3.scale")
    index, plan = write_inputs(tmp_path, names, [1])

    result = MODULE.derive_inventory(index, plan)

    assert len(result["failures"]) == 2
    assert "incomplete source experts" in result["failures"][0]
    assert "missing experts" in result["failures"][1]
