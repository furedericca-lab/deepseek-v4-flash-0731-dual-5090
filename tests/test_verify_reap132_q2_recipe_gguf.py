import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("q2_gguf", ROOT / "scripts" / "verify_reap132_q2_recipe_gguf.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_dry_run_inventory_parses_targets(tmp_path):
    log = tmp_path / "dry.log"
    lines = []
    for index in range(1328):
        suffix = " -> 1.00 MiB (q3_K)" if index == 0 else ""
        lines.append(f"[{index + 1:4d}/1328] tensor.{index} - [ 1, 1, 1, 1], type = f32, size = 1.0 MiB{suffix}")
    log.write_text("\n".join(lines) + "\n")
    result = MODULE.dry_run_inventory(log)
    assert result["tensor.0"] == "q3_K"
    assert result["tensor.1"] == "unchanged"


def test_dry_run_inventory_rejects_partial_log(tmp_path):
    log = tmp_path / "dry.log"
    log.write_text("[   1/1328] tensor.0 - [ 1, 1, 1, 1], type = f32\n")
    try:
        MODULE.dry_run_inventory(log)
    except ValueError as exc:
        assert "1 tensors" in str(exc)
    else:
        raise AssertionError("partial dry-run inventory was accepted")


def test_unstable_reads_are_a_failure():
    report = {"comparisons": [{"unstable_reads": 1}], "failures": []}
    unstable_reads = sum(item["unstable_reads"] for item in report["comparisons"])
    if unstable_reads:
        report["failures"].append(f"unstable O_DIRECT reads: {unstable_reads}")
    assert report["failures"] == ["unstable O_DIRECT reads: 1"]
