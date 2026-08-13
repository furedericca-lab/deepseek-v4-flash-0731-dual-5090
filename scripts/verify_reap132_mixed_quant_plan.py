#!/usr/bin/env python3
"""Independently verify a frozen K132 regional quantization plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAYERS = 43
OUTPUT_FILENAME = "DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-IQ3XXS-Q2KSexp-IQ4XSbb.gguf"
PATTERN = re.compile(r"^\^blk\\\.(\d+)\\\.ffn_\(gate\|up\|down\)_exps\\\.weight\$=(IQ3_XXS|Q2_K_S)$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(
    plan_path: Path,
    structural_path: Path,
    audit_path: Path,
    type_path: Path,
    golden_path: Path,
    golden_sha256: str,
    golden_provenance_path: Path,
    llama_cpp_commit: str,
) -> dict:
    plan = json.loads(plan_path.read_text())
    structural_doc = json.loads(structural_path.read_text())
    audit = json.loads(audit_path.read_text())
    failures = []
    golden_source = plan.get("sources", {}).get("golden", {})
    golden_provenance = json.loads(golden_provenance_path.read_text())
    coverage = golden_provenance.get("coverage", {})
    expected_golden = {
        "path": str(golden_path),
        "sha256": golden_sha256,
        "size": golden_path.stat().st_size,
        "routed_provenance_path": str(golden_provenance_path),
        "routed_provenance_sha256": sha256(golden_provenance_path),
    }
    if golden_source != expected_golden:
        failures.append("Golden identity")
    if golden_provenance.get("status") != "PASS" or golden_provenance.get("gguf") != str(golden_path):
        failures.append("Golden routed provenance")
    if coverage.get("routed_tensors") != 129 or coverage.get("expert_comparisons") != 17028 or not coverage.get("all_rows_and_blocks"):
        failures.append("Golden routed coverage")
    if plan.get("schema") != "heretic-reap132-mixed-expert-quant-plan-v1":
        failures.append("schema")
    if plan.get("llama_cpp_commit") != llama_cpp_commit:
        failures.append("llama.cpp commit")
    if plan.get("output_filename") != OUTPUT_FILENAME:
        failures.append("output filename")
    if audit.get("status") != "PASS" or audit.get("accepted_chunks") != plan.get("accepted_imatrix_chunks"):
        failures.append("accepted audit")
    accepted = next((x for x in audit.get("stages", []) if x["chunks"] == audit.get("accepted_chunks")), None)
    if accepted is None or not accepted.get("coverage_pass"):
        failures.append("accepted coverage")
        accepted_layers = {}
    else:
        accepted_layers = {int(item["layer"]): item for item in accepted["layers"]}
    structural = {int(item["layer"]): item for item in structural_doc.get("layers", [])}
    layers = {int(item["layer"]): item for item in plan.get("layers", [])}
    if set(structural) != set(range(LAYERS)) or set(accepted_layers) != set(range(LAYERS)) or set(layers) != set(range(LAYERS)):
        failures.append("layer domain")
    else:
        expected = []
        for layer in range(LAYERS):
            r_value = float(structural[layer]["R_l"])
            i_value = float(accepted_layers[layer]["I_l"])
            p_value = 0.4 * r_value + 0.6 * i_value
            item = layers[layer]
            if any(abs(float(item[key]) - value) > 1e-15 for key, value in (("R_l", r_value), ("I_l", i_value), ("P_l", p_value))):
                failures.append(f"layer {layer} formula")
            expected.append((layer, p_value, i_value, r_value, float(structural[layer]["k216_rank_mean"])))
        expected.sort(key=lambda x: (-x[1], -x[2], -x[3], x[4], x[0]))
        expected_recipe = {layer: ("IQ3_XXS" if rank <= 17 else "Q2_K_S") for rank, (layer, *_rest) in enumerate(expected, 1)}
        for rank, (layer, *_rest) in enumerate(expected, 1):
            if layers[layer].get("rank") != rank or layers[layer].get("recipe") != expected_recipe[layer]:
                failures.append(f"layer {layer} assignment")

    lines = type_path.read_text().splitlines()
    parsed = {}
    for line in lines:
        match = PATTERN.fullmatch(line)
        if match is None:
            failures.append(f"invalid tensor-ftype line: {line}")
            continue
        layer = int(match.group(1))
        if layer in parsed:
            failures.append(f"duplicate tensor-ftype layer {layer}")
        parsed[layer] = match.group(2)
    if set(parsed) != set(range(LAYERS)):
        failures.append("tensor-ftype layer domain")
    elif set(layers) == set(range(LAYERS)):
        for layer in range(LAYERS):
            if parsed[layer] != layers[layer]["recipe"]:
                failures.append(f"tensor-ftype recipe {layer}")
    if sha256(type_path) != plan.get("tensor_ftype_sha256"):
        failures.append("tensor-ftype sha256")
    if plan.get("counts") != {"IQ3_XXS_layers": 17, "Q2_K_S_layers": 26,
                               "IQ3_XXS_tensors": 51, "Q2_K_S_tensors": 78}:
        failures.append("recipe counts")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "plan_sha256": sha256(plan_path), "tensor_ftype_sha256": sha256(type_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--imatrix-audit", type=Path, required=True)
    parser.add_argument("--tensor-ftype", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--golden-sha256", required=True)
    parser.add_argument("--golden-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--llama-cpp-commit", required=True)
    args = parser.parse_args()
    report = verify(
        args.plan,
        args.structural,
        args.imatrix_audit,
        args.tensor_ftype,
        args.golden.resolve(),
        args.golden_sha256,
        args.golden_provenance.resolve(),
        args.llama_cpp_commit,
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
