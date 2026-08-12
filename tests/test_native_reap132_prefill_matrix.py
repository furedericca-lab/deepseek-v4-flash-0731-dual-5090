import importlib.util
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


def test_prefill_matrix_has_expected_lengths():
    assert [case.tokens for case in CASES] == [1, 16, 32, 64, 128]
    assert len({case.name for case in CASES}) == len(CASES)


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
