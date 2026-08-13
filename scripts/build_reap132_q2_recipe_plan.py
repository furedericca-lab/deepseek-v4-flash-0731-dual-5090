#!/usr/bin/env python3
"""Build the frozen K132 puwaer-Q2-routed plus IQ4_XS plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


OUTPUT_FILENAME = "DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-Q2K-Q3Kexp-IQ4XSbb.gguf"
EXPECTED_RECIPE = (
    "token_embd\\.weight=q8_0\n"
    "output\\.weight=q8_0\n"
    "blk\\.[0-9]+\\.attn_[a-z_]+\\.weight=q8_0\n"
    "blk\\.[0-9]+\\.indexer[._][a-z_]+\\.weight=q8_0\n"
    "blk\\.[0-9]+\\.ffn_(gate|down|up)_shexp\\.weight=q8_0\n"
    "output_hc_fn\\.weight=f32\n"
    "blk\\.[0-9]+\\.hc_(attn|ffn)_fn\\.weight=f32\n"
    "blk\\.([0-2]|4[12])\\.ffn_(gate|down|up)_exps\\.weight=mxfp4\n"
    "blk\\.[0-9]+\\.ffn_down_exps\\.weight=q3_K\n"
    "blk\\.[0-9]+\\.ffn_(gate|up)_exps\\.weight=q2_K\n"
)
ROUTED_TYPE_FILE = (
    "^blk\\.([0-2]|4[12])\\.ffn_(gate|down|up)_exps\\.weight$=MXFP4\n"
    "^blk\\.([3-9]|[12][0-9]|3[0-9]|40)\\.ffn_down_exps\\.weight$=Q3_K\n"
    "^blk\\.([3-9]|[12][0-9]|3[0-9]|40)\\.ffn_(gate|up)_exps\\.weight$=Q2_K\n"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(
    recipe_path: Path,
    external_imatrix_path: Path,
    production_imatrix_path: Path,
    compatibility_report_path: Path,
    imatrix_audit_path: Path,
    golden_path: Path,
    golden_sha256: str,
    golden_provenance_path: Path,
    source_revision: str,
    llama_cpp_commit: str,
) -> tuple[dict, str]:
    if recipe_path.read_text() != EXPECTED_RECIPE:
        raise ValueError("puwaer Q2 recipe content drift")
    if len(source_revision) != 40 or len(llama_cpp_commit) != 40:
        raise ValueError("source and llama.cpp commits must be 40-character hashes")
    if len(golden_sha256) != 64:
        raise ValueError("Golden SHA256 must be a 64-character digest")

    audit = json.loads(imatrix_audit_path.read_text())
    stage = next((item for item in audit.get("stages", []) if item.get("path") == str(external_imatrix_path)), None)
    if audit.get("status") != "PASS" or stage is None or not stage.get("coverage_pass"):
        raise ValueError("final external imatrix is not accepted")
    if stage.get("chunks") != 812 or stage.get("sha256") != sha256(external_imatrix_path):
        raise ValueError("final external imatrix identity drift")
    if stage.get("zero_count_experts") or stage.get("missing_entries") or stage.get("malformed_entries") or stage.get("count_mismatches"):
        raise ValueError("final external imatrix coverage drift")
    compatibility = json.loads(compatibility_report_path.read_text())
    expected_output = compatibility.get("output", {})
    if compatibility.get("status") != "PASS" or expected_output.get("path") != str(production_imatrix_path):
        raise ValueError("production compatibility imatrix is not accepted")
    if expected_output.get("sha256") != sha256(production_imatrix_path) or expected_output.get("entries") != 769 or expected_output.get("chunks") != 812:
        raise ValueError("production compatibility imatrix identity drift")
    if compatibility.get("external", {}).get("sha256") != sha256(external_imatrix_path) or compatibility.get("external", {}).get("entries_copied") != 768:
        raise ValueError("external imatrix provenance drift")
    if compatibility.get("supplemental", {}).get("entry_copied") != "output_hc_fn.weight" or compatibility.get("overlapping_entries_replaced") != 0:
        raise ValueError("compatibility imatrix supplementation drift")

    provenance = json.loads(golden_provenance_path.read_text())
    coverage = provenance.get("coverage", {})
    if provenance.get("status") != "PASS" or provenance.get("gguf") != str(golden_path):
        raise ValueError("Golden routed provenance is not accepted")
    if coverage.get("routed_tensors") != 129 or coverage.get("expert_comparisons") != 17028 or not coverage.get("all_rows_and_blocks"):
        raise ValueError("Golden routed provenance coverage is incomplete")

    plan = {
        "schema": "heretic-reap132-puwaer-q2-routed-iq4xs-plan-v1",
        "output_filename": OUTPUT_FILENAME,
        "base_ftype": "IQ4_XS",
        "pure": False,
        "llama_cpp_commit": llama_cpp_commit,
        "source_revision": source_revision,
        "sources": {
            "golden": {
                "path": str(golden_path),
                "size": golden_path.stat().st_size,
                "sha256": golden_sha256,
                "routed_provenance_path": str(golden_provenance_path),
                "routed_provenance_sha256": sha256(golden_provenance_path),
            },
            "puwaer_recipe": {"path": str(recipe_path), "size": recipe_path.stat().st_size, "sha256": sha256(recipe_path)},
            "puwaer_imatrix": {"path": str(external_imatrix_path), "size": external_imatrix_path.stat().st_size, "sha256": sha256(external_imatrix_path), "chunks": 812, "entries": 768},
            "production_imatrix": {"path": str(production_imatrix_path), "size": production_imatrix_path.stat().st_size, "sha256": sha256(production_imatrix_path), "chunks": 812, "entries": 769},
            "compatibility_report": {"path": str(compatibility_report_path), "sha256": sha256(compatibility_report_path)},
            "imatrix_audit": {"path": str(imatrix_audit_path), "sha256": sha256(imatrix_audit_path)},
        },
        "routed_policy": [
            {"layers": [0, 1, 2, 41, 42], "projections": ["gate", "up", "down"], "type": "MXFP4", "tensor_count": 15},
            {"layers": list(range(3, 41)), "projections": ["down"], "type": "Q3_K", "tensor_count": 38},
            {"layers": list(range(3, 41)), "projections": ["gate", "up"], "type": "Q2_K", "tensor_count": 76},
        ],
        "counts": {"MXFP4": 15, "Q2_K": 76, "Q3_K": 38, "routed_total": 129},
        "non_routed_policy": "K96 Profile A default non-pure IQ4_XS mixed selector",
        "tensor_type_sha256": hashlib.sha256(ROUTED_TYPE_FILE.encode()).hexdigest(),
    }
    logical = {key: plan[key] for key in ("output_filename", "base_ftype", "pure", "llama_cpp_commit", "source_revision", "sources", "routed_policy", "counts", "non_routed_policy", "tensor_type_sha256")}
    plan["logical_sha256"] = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return plan, ROUTED_TYPE_FILE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--imatrix", type=Path, required=True)
    parser.add_argument("--production-imatrix", type=Path, required=True)
    parser.add_argument("--compatibility-report", type=Path, required=True)
    parser.add_argument("--imatrix-audit", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--golden-sha256", required=True)
    parser.add_argument("--golden-provenance", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--llama-cpp-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tensor-type-output", type=Path, required=True)
    args = parser.parse_args()
    plan, type_file = build(args.recipe.resolve(), args.imatrix.resolve(), args.production_imatrix.resolve(), args.compatibility_report.resolve(), args.imatrix_audit.resolve(), args.golden.resolve(), args.golden_sha256, args.golden_provenance.resolve(), args.source_revision, args.llama_cpp_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.tensor_type_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    args.tensor_type_output.write_text(type_file)
    print(json.dumps({"logical_sha256": plan["logical_sha256"], "tensor_type_sha256": plan["tensor_type_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
