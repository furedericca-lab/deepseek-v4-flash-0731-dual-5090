#!/usr/bin/env python3
"""Independently verify the K132 Q2 routed-recipe plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_reap132_q2_recipe_plan import EXPECTED_RECIPE, OUTPUT_FILENAME, ROUTED_TYPE_FILE, sha256


EXPECTED_COUNTS = {"MXFP4": 15, "Q2_K": 76, "Q3_K": 38, "routed_total": 129}


def verify(plan_path: Path, type_path: Path, recipe_path: Path, imatrix_path: Path, production_imatrix_path: Path, compatibility_report_path: Path, audit_path: Path, golden_path: Path, golden_sha256: str, provenance_path: Path, source_revision: str, llama_cpp_commit: str) -> dict:
    plan = json.loads(plan_path.read_text())
    failures = []
    if plan.get("schema") != "heretic-reap132-puwaer-q2-routed-iq4xs-plan-v1": failures.append("schema")
    if plan.get("output_filename") != OUTPUT_FILENAME: failures.append("output filename")
    if plan.get("base_ftype") != "IQ4_XS" or plan.get("pure") is not False: failures.append("base policy")
    if plan.get("source_revision") != source_revision or plan.get("llama_cpp_commit") != llama_cpp_commit: failures.append("commit identity")
    if plan.get("counts") != EXPECTED_COUNTS: failures.append("routed counts")
    if recipe_path.read_text() != EXPECTED_RECIPE: failures.append("recipe content")
    if type_path.read_text() != ROUTED_TYPE_FILE: failures.append("tensor type content")
    if hashlib.sha256(type_path.read_bytes()).hexdigest() != plan.get("tensor_type_sha256"): failures.append("tensor type hash")
    sources = plan.get("sources", {})
    expected_sources = {
        "golden": {"path": str(golden_path), "size": golden_path.stat().st_size, "sha256": golden_sha256, "routed_provenance_path": str(provenance_path), "routed_provenance_sha256": sha256(provenance_path)},
        "puwaer_recipe": {"path": str(recipe_path), "size": recipe_path.stat().st_size, "sha256": sha256(recipe_path)},
        "puwaer_imatrix": {"path": str(imatrix_path), "size": imatrix_path.stat().st_size, "sha256": sha256(imatrix_path), "chunks": 812, "entries": 768},
        "production_imatrix": {"path": str(production_imatrix_path), "size": production_imatrix_path.stat().st_size, "sha256": sha256(production_imatrix_path), "chunks": 812, "entries": 769},
        "compatibility_report": {"path": str(compatibility_report_path), "sha256": sha256(compatibility_report_path)},
        "imatrix_audit": {"path": str(audit_path), "sha256": sha256(audit_path)},
    }
    if sources != expected_sources: failures.append("source identity")
    provenance = json.loads(provenance_path.read_text())
    coverage = provenance.get("coverage", {})
    if provenance.get("status") != "PASS" or coverage.get("routed_tensors") != 129 or coverage.get("expert_comparisons") != 17028 or not coverage.get("all_rows_and_blocks"): failures.append("Golden provenance")
    audit = json.loads(audit_path.read_text())
    stage = next((item for item in audit.get("stages", []) if item.get("path") == str(imatrix_path)), None)
    if audit.get("status") != "PASS" or stage is None or stage.get("chunks") != 812 or not stage.get("coverage_pass"): failures.append("imatrix audit")
    return {"schema": "heretic-reap132-puwaer-q2-routed-plan-verification-v1", "status": "PASS" if not failures else "FAIL", "failures": failures, "plan_sha256": sha256(plan_path), "tensor_type_sha256": sha256(type_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("plan", "tensor-type", "recipe", "imatrix", "production-imatrix", "compatibility-report", "imatrix-audit", "golden", "golden-provenance", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--golden-sha256", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--llama-cpp-commit", required=True)
    args = parser.parse_args()
    report = verify(args.plan.resolve(), args.tensor_type.resolve(), args.recipe.resolve(), args.imatrix.resolve(), args.production_imatrix.resolve(), args.compatibility_report.resolve(), args.imatrix_audit.resolve(), args.golden.resolve(), args.golden_sha256, args.golden_provenance.resolve(), args.source_revision, args.llama_cpp_commit)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
