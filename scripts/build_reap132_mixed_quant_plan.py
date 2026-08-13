#!/usr/bin/env python3
"""Build the frozen K132 17/26 regional quantization plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAYERS = 43
PROTECTED = 17
LLAMA_CPP_COMMIT = "c861db3592ed7a03045d23861249eb43d1b8a039"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(structural_path: Path, audit_path: Path) -> tuple[dict, str]:
    structural_doc = json.loads(structural_path.read_text())
    audit = json.loads(audit_path.read_text())
    if audit.get("status") != "PASS" or audit.get("accepted_chunks") is None:
        raise ValueError("imatrix audit is not accepted")
    accepted = next((stage for stage in audit["stages"] if stage["chunks"] == audit["accepted_chunks"]), None)
    if accepted is None or not accepted["coverage_pass"] or len(accepted["layers"]) != LAYERS:
        raise ValueError("accepted imatrix stage is incomplete")
    structural = {int(item["layer"]): item for item in structural_doc["layers"]}
    activation = {int(item["layer"]): item for item in accepted["layers"]}
    if set(structural) != set(range(LAYERS)) or set(activation) != set(range(LAYERS)):
        raise ValueError("reports must contain layers 0..42")

    records = []
    for layer in range(LAYERS):
        r_value = float(structural[layer]["R_l"])
        i_value = float(activation[layer]["I_l"])
        p_value = 0.4 * r_value + 0.6 * i_value
        if abs(p_value - float(activation[layer]["P_l"])) > 1e-15:
            raise ValueError(f"layer {layer}: P_l formula mismatch")
        records.append({
            "layer": layer,
            "R_l": r_value,
            "I_l": i_value,
            "P_l": p_value,
            "raw_I_l": float(activation[layer]["raw_I_l"]),
            "k216_rank_mean": float(structural[layer]["k216_rank_mean"]),
        })
    ordered = sorted(records, key=lambda x: (-x["P_l"], -x["I_l"], -x["R_l"], x["k216_rank_mean"], x["layer"]))
    protected = {item["layer"] for item in ordered[:PROTECTED]}
    for rank, item in enumerate(ordered, 1):
        item["rank"] = rank
        item["recipe"] = "IQ3_XXS" if item["layer"] in protected else "Q2_K_S"
    records.sort(key=lambda x: x["layer"])

    type_lines = [
        rf"^blk\.{item['layer']}\.ffn_(gate|up|down)_exps\.weight$={item['recipe']}"
        for item in records
    ]
    type_file = "\n".join(type_lines) + "\n"
    plan = {
        "schema": "heretic-reap132-mixed-expert-quant-plan-v1",
        "llama_cpp_commit": LLAMA_CPP_COMMIT,
        "base_ftype": "IQ4_XS",
        "pure": False,
        "accepted_imatrix_chunks": audit["accepted_chunks"],
        "sources": {
            "structural": {"path": str(structural_path), "sha256": sha256(structural_path)},
            "imatrix_audit": {"path": str(audit_path), "sha256": sha256(audit_path)},
            "imatrix": {"path": accepted["path"], "sha256": accepted["sha256"], "size": accepted["size"]},
        },
        "layers": records,
        "counts": {"IQ3_XXS_layers": PROTECTED, "Q2_K_S_layers": LAYERS - PROTECTED,
                   "IQ3_XXS_tensors": PROTECTED * 3, "Q2_K_S_tensors": (LAYERS - PROTECTED) * 3},
        "tensor_ftype_sha256": hashlib.sha256(type_file.encode()).hexdigest(),
    }
    logical = {key: plan[key] for key in ("llama_cpp_commit", "base_ftype", "pure", "accepted_imatrix_chunks", "sources", "layers", "counts", "tensor_ftype_sha256")}
    plan["logical_sha256"] = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return plan, type_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--imatrix-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tensor-ftype-output", type=Path, required=True)
    args = parser.parse_args()
    plan, type_file = build(args.structural.resolve(), args.imatrix_audit.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.tensor_ftype_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    args.tensor_ftype_output.write_text(type_file)
    print(json.dumps({"logical_sha256": plan["logical_sha256"], "tensor_ftype_sha256": plan["tensor_ftype_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
