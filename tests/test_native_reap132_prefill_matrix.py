import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_native_reap132_prefill_matrix.py"
SPEC = importlib.util.spec_from_file_location("run_native_reap132_prefill_matrix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CASES = MODULE.CASES
forbidden_kernel_lines = MODULE.forbidden_kernel_lines
select_cases = MODULE.select_cases


def test_prefill_matrix_has_expected_lengths():
    assert [case.tokens for case in CASES] == [1, 16, 32, 64, 128]
    assert len({case.name for case in CASES}) == len(CASES)


def test_select_cases_defaults_to_matrix_and_preserves_requested_order():
    assert select_cases(None) == CASES
    selected = select_cases(["t3-32-token-code", "t1-1-token"])
    assert [case.name for case in selected] == ["t3-32-token-code", "t1-1-token"]


def test_boot_gate_rejects_faults_but_not_mce_decoder_notice():
    log = "\n".join(
        (
            "kernel: MCE: In-kernel MCE decoding enabled.",
            "kernel: NVRM: Xid (PCI:0000:02:00): 31",
            "kernel: page dumped because: corrupted mapping in tail page",
            "kernel: python3[1]: segfault at 0 ip 0 sp 0 error 4",
        )
    )

    assert forbidden_kernel_lines(log) == [
        "kernel: NVRM: Xid (PCI:0000:02:00): 31",
        "kernel: page dumped because: corrupted mapping in tail page",
        "kernel: python3[1]: segfault at 0 ip 0 sp 0 error 4",
    ]


def test_runner_help_exposes_targeted_diagnostics():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--case" in result.stdout
    assert "--cuda-launch-blocking" in result.stdout
    assert "--trace-attention-layer" in result.stdout
    assert "--trace-values" in result.stdout
