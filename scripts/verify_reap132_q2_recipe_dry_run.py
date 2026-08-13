#!/usr/bin/env python3
"""Verify the complete K132 Q2-recipe dry-run inventory."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ENTRY = re.compile(r"^\[\s*\d+/1328\]\s+(\S+)\s+-\s+")
TARGET = re.compile(r"->.*\(([^()]+)\)\s*$")
ROUTED = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight$")
BOUNDARY = {0, 1, 2, 41, 42}


def parse(log_path: Path) -> tuple[list[tuple[str, str]], int, str]:
    entries = []
    output_size = None
    commit = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("llama_print_build_info: build = "):
            match = re.search(r"\(([0-9a-f]+)\)", line)
            if match:
                commit = match.group(1)
        match = ENTRY.match(line)
        if match:
            target = TARGET.search(line)
            entries.append((match.group(1), target.group(1) if target else "unchanged"))
        if "llama_model_quantize_impl: output size = " in line:
            output_size = int(line.split("output size = ", 1)[1].split()[0])
    if output_size is None or commit is None:
        raise ValueError("dry-run log is missing build identity or output size")
    return entries, output_size, commit


def verify(log_path: Path, plan_path: Path) -> dict:
    plan = json.loads(plan_path.read_text())
    entries, output_size, short_commit = parse(log_path)
    failures = []
    if len(entries) != 1328:
        failures.append(f"tensor count: {len(entries)}")
    if not plan["llama_cpp_commit"].startswith(short_commit):
        failures.append("llama.cpp build identity")

    by_name = dict(entries)
    routed_targets = Counter()
    for name, target in entries:
        match = ROUTED.fullmatch(name)
        if match is None:
            continue
        layer = int(match.group(1))
        projection = match.group(2)
        expected = "unchanged" if layer in BOUNDARY else ("q3_K" if projection == "down" else "q2_K")
        routed_targets["mxfp4" if target == "unchanged" else target] += 1
        if target != expected:
            failures.append(f"routed type {name}: {target} != {expected}")
    if sum(routed_targets.values()) != 129:
        failures.append(f"routed tensor count: {sum(routed_targets.values())}")
    if dict(routed_targets) != {"mxfp4": 15, "q2_K": 76, "q3_K": 38}:
        failures.append(f"routed concrete inventory: {dict(routed_targets)}")

    attention_kv = [name for name in by_name if re.fullmatch(r"blk\.\d+\.attn_kv\.weight", name)]
    if len(attention_kv) != 43 or any(by_name[name] != "q5_K" for name in attention_kv):
        failures.append("DeepSeek V4 attention KV Q5_K protection")
    shared = [name for name in by_name if re.fullmatch(r"blk\.\d+\.ffn_(gate|up|down)_shexp\.weight", name)]
    if len(shared) != 129 or any(by_name[name] != "iq4_xs" for name in shared):
        failures.append("shared expert IQ4_XS policy")
    ape = [name for name in by_name if name.endswith("_compressor_ape.weight")]
    if len(ape) != 62 or any(by_name[name] != "unchanged" for name in ape):
        failures.append("compressor APE preservation")
    if by_name.get("output.weight") != "q6_K":
        failures.append("output Q6_K promotion")

    return {
        "schema": "heretic-reap132-puwaer-q2-routed-dry-run-v1",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "llama_cpp_commit": plan["llama_cpp_commit"],
        "output_size": output_size,
        "tensor_count": len(entries),
        "concrete_types": dict(sorted(Counter(target for _, target in entries).items())),
        "routed_concrete_types": dict(sorted(routed_targets.items())),
        "attention_kv_q5_k": sum(by_name.get(name) == "q5_K" for name in attention_kv),
        "shared_expert_iq4_xs": sum(by_name.get(name) == "iq4_xs" for name in shared),
        "compressor_ape_unchanged": sum(by_name.get(name) == "unchanged" for name in ape),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.log, args.plan)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
