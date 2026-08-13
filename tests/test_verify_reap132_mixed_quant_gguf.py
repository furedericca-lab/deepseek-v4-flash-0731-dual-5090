import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("candidate", ROOT / "scripts" / "verify_reap132_mixed_quant_gguf.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_dry_run_inventory_parses_targets(tmp_path):
    log = tmp_path / "dry.log"
    lines = []
    for index in range(1328):
        suffix = " -> 1.00 MiB (iq4_xs)" if index == 0 else ""
        lines.append(f"[{index + 1:4d}/1328] tensor.{index} - [ 1, 1, 1, 1], type = f32, size = 1.0 MiB{suffix}")
    log.write_text("\n".join(lines) + "\n")
    result = MODULE.dry_run_inventory(log)
    assert result["tensor.0"] == "iq4_xs"
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
