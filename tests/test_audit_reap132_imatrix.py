import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "llama.cpp" / "gguf-py"))
from gguf import GGUFWriter

SCRIPT = ROOT / "scripts" / "audit_reap132_imatrix.py"
SPEC = importlib.util.spec_from_file_location("audit_reap132_imatrix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_imatrix(path: Path, chunks: int, *, zero=None, scale_shift=0.0):
    writer = GGUFWriter(path, "imatrix")
    writer.add_uint32("imatrix.chunk_count", chunks)
    writer.add_uint32("imatrix.chunk_size", 512)
    for layer in range(43):
        for projection_index, projection in enumerate(("gate", "up", "down")):
            counts = np.full(132, chunks, dtype=np.float32)
            if zero == (layer, projection):
                counts[7] = 0
            values = np.full((132, 4), layer + 1 + projection_index + scale_shift, dtype=np.float32)
            writer.add_tensor(f"blk.{layer}.ffn_{projection}_exps.weight.in_sum2", values)
            writer.add_tensor(f"blk.{layer}.ffn_{projection}_exps.weight.counts", counts)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()


def structural():
    return {
        layer: {"R_l": layer / 42, "k216_rank_mean": float(100 - layer)}
        for layer in range(43)
    }


def test_complete_stage_and_stability(tmp_path):
    first = tmp_path / "first.gguf"
    second = tmp_path / "second.gguf"
    write_imatrix(first, 100)
    write_imatrix(second, 200, scale_shift=0.25)

    report_a = MODULE.audit_stage(first, structural())
    report_b = MODULE.audit_stage(second, structural())
    assert report_a["coverage_pass"] is True
    assert report_a["count_statistics"] == {"min": 100, "p1": 100, "p5": 100, "median": 100}
    assert len(report_a["layers"]) == 43
    assert report_a["layers"][0]["I_l"] == 0.0
    assert report_a["layers"][-1]["I_l"] == 1.0
    assert report_a["top17"]["I"] == list(range(42, 25, -1))

    comparison = MODULE.compare_stages(report_a, report_b)
    assert comparison == {
        "spearman_raw_I": 1.0,
        "activation_top17_churn": 0,
        "final_top17_churn": 0,
        "pass": True,
    }


def test_zero_count_fails_coverage(tmp_path):
    path = tmp_path / "zero.gguf"
    write_imatrix(path, 100, zero=(2, "gate"))
    report = MODULE.audit_stage(path, structural())
    assert report["coverage_pass"] is False
    assert {"layer": 2, "expert": 7} in report["zero_count_experts"]
    assert report["layers"] == []
