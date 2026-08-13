#!/usr/bin/env python3
"""Verify the K132 Q2-recipe GGUF against its Golden and dry-run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verify_reap96_iq4xs_gguf import direct_compare, parse_gguf


GGML_TYPES = {"iq4_xs": 23, "q2_K": 10, "q3_K": 11, "q5_K": 13, "q6_K": 14}
ENTRY = re.compile(r"^\[\s*\d+/1328\]\s+(\S+)\s+-\s+")
TARGET = re.compile(r"->.*\(([^()]+)\)\s*$")
ROUTED = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight$")


def dry_run_inventory(path: Path) -> dict[str, str]:
    inventory = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = ENTRY.match(line)
        if match:
            target = TARGET.search(line)
            inventory[match.group(1)] = target.group(1) if target else "unchanged"
    if len(inventory) != 1328:
        raise ValueError(f"dry-run inventory has {len(inventory)} tensors")
    return inventory


def verify(golden_path: Path, candidate_path: Path, dry_run_path: Path) -> dict:
    golden = parse_gguf(golden_path)
    candidate = parse_gguf(candidate_path)
    expected = dry_run_inventory(dry_run_path)
    failures = []
    required_metadata = {
        "general.architecture": "deepseek4",
        "deepseek4.block_count": 43,
        "deepseek4.expert_count": 132,
        "deepseek4.expert_used_count": 6,
        "deepseek4.hash_layer_count": 3,
        "tensor_count": 1328,
    }
    for key, value in required_metadata.items():
        if candidate.metadata.get(key) != value:
            failures.append(f"candidate metadata {key}: {candidate.metadata.get(key)!r} != {value!r}")
        if key != "tensor_count" and candidate.metadata.get(key) != golden.metadata.get(key):
            failures.append(f"critical metadata drift: {key}")
    if set(candidate.tensors) != set(golden.tensors) or set(candidate.tensors) != set(expected):
        failures.append("tensor namespace mismatch")

    unchanged = []
    type_failures = []
    routed_types = Counter()
    for name, target in expected.items():
        source = golden.tensors.get(name)
        tensor = candidate.tensors.get(name)
        if source is None or tensor is None:
            continue
        if tensor.shape != source.shape:
            failures.append(f"shape drift: {name}")
        if target == "unchanged":
            unchanged.append(name)
            if tensor.tensor_type != source.tensor_type:
                type_failures.append(f"unchanged type drift: {name}")
        elif tensor.tensor_type != GGML_TYPES[target]:
            type_failures.append(f"type mismatch {name}: {tensor.tensor_type} != {GGML_TYPES[target]}")
        if ROUTED.fullmatch(name):
            routed_types["mxfp4" if target == "unchanged" else target] += 1
    failures.extend(type_failures)
    if dict(routed_types) != {"mxfp4": 15, "q2_K": 76, "q3_K": 38}:
        failures.append(f"routed concrete inventory: {dict(routed_types)}")

    comparisons = []
    if not type_failures and set(candidate.tensors) == set(expected):
        for name in sorted(unchanged):
            matched, detail, size, unstable = direct_compare(golden, candidate, name)
            comparisons.append({"name": name, "bytes": size, "sha256": detail if matched else None, "status": "PASS" if matched else "FAIL", "unstable_reads": unstable})
            if not matched:
                failures.append(f"unchanged payload drift: {name}: {detail}")
    routed_unchanged = [item for item in comparisons if ROUTED.fullmatch(item["name"])]
    if len(routed_unchanged) != 15:
        failures.append(f"routed MXFP4 payload comparisons: {len(routed_unchanged)}")
    unstable_reads = sum(item["unstable_reads"] for item in comparisons)
    if unstable_reads:
        failures.append(f"unstable O_DIRECT reads: {unstable_reads}")

    return {
        "schema": "heretic-reap132-puwaer-q2-routed-acceptance-v1",
        "status": "PASS" if not failures else "FAIL",
        "golden": {"path": str(golden.path), "size_bytes": golden.path.stat().st_size},
        "candidate": {"path": str(candidate.path), "size_bytes": candidate.path.stat().st_size},
        "metadata": candidate.metadata,
        "routed_concrete_types": dict(sorted(routed_types.items())),
        "unchanged_tensor_count": len(unchanged),
        "routed_mxfp4_comparison_count": len(routed_unchanged),
        "comparison_count": len(comparisons),
        "comparison_bytes": sum(item["bytes"] for item in comparisons),
        "unstable_reads": unstable_reads,
        "comparisons": comparisons,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--dry-run", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.golden, args.candidate, args.dry_run)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "routed_concrete_types", "unchanged_tensor_count", "routed_mxfp4_comparison_count", "comparison_count", "comparison_bytes", "unstable_reads", "failures")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
