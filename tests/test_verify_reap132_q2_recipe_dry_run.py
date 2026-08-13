import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("q2_dry_run", ROOT / "scripts" / "verify_reap132_q2_recipe_dry_run.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parse_requires_identity_and_size(tmp_path):
    log = tmp_path / "dry-run.log"
    log.write_text("llama_print_build_info: build = 1 (abcdef0)\nllama_model_quantize_impl: output size = 123 bytes\n")
    entries, size, commit = MODULE.parse(log)
    assert entries == []
    assert size == 123
    assert commit == "abcdef0"


def test_verify_rejects_incomplete_inventory(tmp_path):
    log = tmp_path / "dry-run.log"
    log.write_text("llama_print_build_info: build = 1 (abcdef0)\nllama_model_quantize_impl: output size = 123 bytes\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"llama_cpp_commit": "abcdef0" + "0" * 33}))
    report = MODULE.verify(log, plan)
    assert report["status"] == "FAIL"
    assert any(item.startswith("tensor count") for item in report["failures"])
