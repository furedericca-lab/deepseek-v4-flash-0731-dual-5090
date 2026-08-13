#!/usr/bin/env python3
"""Assemble the corrected K132 MXFP4 Golden acceptance report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_reap96_iq4xs_gguf import parse_gguf


def load_pass(path: Path, failures: list[str]) -> dict:
    report = json.loads(path.read_text())
    if report.get("status") != "PASS":
        failures.append(f"report is not PASS: {path}")
    return report


def accept(args: argparse.Namespace) -> dict[str, object]:
    failures: list[str] = []
    full = load_pass(args.full_provenance, failures)
    sampled = load_pass(args.sampled_provenance, failures)
    nonexpert = load_pass(args.nonexpert_provenance, failures)
    fp8 = load_pass(args.fp8_provenance, failures)
    exponent = json.loads(args.exponent_audit.read_text())
    config = json.loads(args.config.read_text())
    gguf = parse_gguf(args.gguf)

    coverage = full.get("coverage", {})
    if coverage != {
        "layers": 43,
        "routed_tensors": 129,
        "experts_per_layer": 132,
        "expert_comparisons": 17028,
        "compared_bytes": 75884396544,
        "all_rows_and_blocks": True,
    }:
        failures.append("full routed coverage mismatch")
    if exponent.get("tensor_count") != 129 or exponent.get("high_tensor_count") != 0 or exponent.get("high_block_count") != 0:
        failures.append("MXFP4 exponent audit mismatch")
    if config.get("num_nextn_predict_layers") != 0:
        failures.append("config num_nextn_predict_layers is not zero")
    if any(name.startswith(("mtp.", "dspark.")) or ".nextn." in name for name in gguf.tensors):
        failures.append("MTP/DSpark tensor present")
    expected_metadata = {
        "general.architecture": "deepseek4",
        "deepseek4.block_count": 43,
        "deepseek4.expert_count": 132,
        "deepseek4.expert_used_count": 6,
        "general.file_type": 38,
        "tensor_count": 1328,
    }
    for key, value in expected_metadata.items():
        if gguf.metadata.get(key) != value:
            failures.append(f"metadata mismatch: {key}")
    routed = sum(
        tensor.tensor_type == 39 and ".ffn_" in name and "_exps.weight" in name
        for name, tensor in gguf.tensors.items()
    )
    if routed != 129:
        failures.append("routed MXFP4 tensor count mismatch")
    if args.gguf.stat().st_size != args.expected_size:
        failures.append("file size mismatch")
    if args.gguf.stat().st_mode & 0o777 != 0o444:
        failures.append("file mode is not 0444")

    return {
        "schema": "reap132-corrected-mxfp4-golden-acceptance-v1",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "artifact": {
            "path": str(args.gguf),
            "size": args.gguf.stat().st_size,
            "mode": oct(args.gguf.stat().st_mode & 0o777),
            "sha256": args.sha256,
        },
        "metadata": expected_metadata,
        "routed_mxfp4_tensors": routed,
        "full_routed_coverage": coverage,
        "evidence": {
            "full_provenance": str(args.full_provenance),
            "sampled_provenance": str(args.sampled_provenance),
            "nonexpert_provenance": str(args.nonexpert_provenance),
            "fp8_provenance": str(args.fp8_provenance),
            "exponent_audit": str(args.exponent_audit),
            "sampled_comparisons": sampled.get("comparison_count"),
            "nonexpert_comparisons": nonexpert.get("comparison_count"),
            "fp8_comparisons": fp8.get("comparison_count"),
        },
        "no_mtp": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--full-provenance", type=Path, required=True)
    parser.add_argument("--sampled-provenance", type=Path, required=True)
    parser.add_argument("--nonexpert-provenance", type=Path, required=True)
    parser.add_argument("--fp8-provenance", type=Path, required=True)
    parser.add_argument("--exponent-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = accept(args)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "artifact": report["artifact"], "failure_count": len(report["failures"])}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
