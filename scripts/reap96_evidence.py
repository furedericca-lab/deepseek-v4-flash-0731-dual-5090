#!/usr/bin/env python3
"""Validate normalized REAP masks and report their layer-wise overlap."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "reap-expert-mask-v1"
LAYER_KEYS = tuple(str(layer) for layer in range(43))


class EvidenceError(ValueError):
    """Raised when a normalized external mask violates the evidence contract."""


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_mask(payload: dict[str, Any], *, expected_k: int | None = None,
                  expected_layers: set[str] | None = None) -> dict[str, Any]:
    if payload.get("schema") != SCHEMA:
        raise EvidenceError(f"unsupported schema: {payload.get('schema')!r}")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise EvidenceError("source object is required")
    for key in ("repo", "revision_sha", "path", "sha256", "lineage", "original_id_proof"):
        if not isinstance(source.get(key), str) or not source[key]:
            raise EvidenceError(f"source.{key} is required")
    if len(source["revision_sha"]) != 40:
        raise EvidenceError("source.revision_sha must be a 40-character immutable commit SHA")
    if len(source["sha256"]) != 64:
        raise EvidenceError("source.sha256 must be a SHA256 hex digest")
    declared_k = payload.get("declared_k")
    if not isinstance(declared_k, int) or not 1 <= declared_k <= 256:
        raise EvidenceError("declared_k must be an integer in 1..256")
    if expected_k is not None and declared_k != expected_k:
        raise EvidenceError(f"declared_k={declared_k}, expected {expected_k}")
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        raise EvidenceError("layers object is required")
    layer_keys = set(layers)
    target_layers = expected_layers if expected_layers is not None else set(LAYER_KEYS)
    if layer_keys != target_layers:
        missing = sorted(target_layers - layer_keys, key=int)
        extra = sorted(layer_keys - target_layers, key=int)
        raise EvidenceError(f"layer coverage mismatch: missing={missing}, extra={extra}")
    for layer in sorted(target_layers, key=int):
        item = layers[layer]
        if not isinstance(item, dict) or not isinstance(item.get("kept_experts"), list):
            raise EvidenceError(f"layer {layer} lacks kept_experts")
        kept = item["kept_experts"]
        if len(kept) != declared_k:
            raise EvidenceError(f"layer {layer} has {len(kept)} experts, expected {declared_k}")
        if any(not isinstance(expert, int) or expert < 0 or expert >= 256 for expert in kept):
            raise EvidenceError(f"layer {layer} has expert outside original ID range 0..255")
        if kept != sorted(kept) or len(set(kept)) != len(kept):
            raise EvidenceError(f"layer {layer} experts must be sorted and unique")
    return payload


def load_mask(path: Path, *, expected_k: int | None = None,
              expected_layers: set[str] | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    # A supplemental source may intentionally cover only Layers 3-42. When no
    # caller specifies a coverage set, validate the source's own declared keys
    # strictly and let overlap_report mark the missing layers explicitly.
    coverage = expected_layers if expected_layers is not None else set(payload.get("layers", {}))
    validate_mask(payload, expected_k=expected_k, expected_layers=coverage)
    claimed = payload["source"]["sha256"]
    actual = sha256_file(path)
    # The source digest identifies the retrieved upstream file, while the
    # normalized-mask file is independently identified in the report.
    payload["normalized_file_sha256"] = actual
    payload["source_sha256"] = claimed
    return payload


def k132_mask(plan_path: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    layers = {
        layer: {"kept_experts": plan["layers"][layer]["kept_experts"]}
        for layer in LAYER_KEYS
    }
    payload = {
        "schema": SCHEMA,
        "declared_k": 132,
        "source": {
            "repo": plan["pruned_repo"],
            "revision_sha": plan["pruned_revision_sha"],
            "path": str(plan_path),
            "sha256": sha256_file(plan_path),
            "lineage": "puwaer",
            "original_id_proof": "existing-43-layer-byte-exact-router-recovery",
        },
        "layers": layers,
    }
    return validate_mask(payload, expected_k=132)


def overlap_report(k132: dict[str, Any], masks: list[dict[str, Any]]) -> dict[str, Any]:
    report_layers = []
    for layer in LAYER_KEYS:
        universe = set(k132["layers"][layer]["kept_experts"])
        row: dict[str, Any] = {"layer": int(layer), "k132_count": len(universe), "sources": {}}
        for mask in masks:
            source = mask["source"]
            name = f"{source['lineage']}:{source['repo']}@{source['revision_sha'][:12]}"
            if layer not in mask["layers"]:
                row["sources"][name] = {"covered": False}
                continue
            kept = set(mask["layers"][layer]["kept_experts"])
            intersection = universe & kept
            union = universe | kept
            row["sources"][name] = {
                "covered": True,
                "declared_k": mask["declared_k"],
                "intersection_with_k132": len(intersection),
                "k132_subset_of_source": universe <= kept,
                "jaccard_with_k132": round(len(intersection) / len(union), 8),
            }
        report_layers.append(row)
    return {
        "schema": "reap-mask-overlap-report-v1",
        "k132": k132["source"],
        "sources": [mask["source"] for mask in masks],
        "layers": report_layers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k132-plan", type=Path, required=True)
    parser.add_argument("--mask", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    k132 = k132_mask(args.k132_plan)
    masks = [load_mask(path) for path in args.mask]
    report = overlap_report(k132, masks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sources": len(masks), "layers": len(report["layers"])}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as exc:
        raise SystemExit(f"ERROR: {exc}")
