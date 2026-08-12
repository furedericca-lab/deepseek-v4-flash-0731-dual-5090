#!/usr/bin/env python3
"""Normalize approved published REAP survivor files into reap-expert-mask-v1."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

_EVIDENCE_PATH = Path(__file__).with_name("reap96_evidence.py")
_EVIDENCE_SPEC = importlib.util.spec_from_file_location("reap96_evidence", _EVIDENCE_PATH)
assert _EVIDENCE_SPEC and _EVIDENCE_SPEC.loader
_EVIDENCE = importlib.util.module_from_spec(_EVIDENCE_SPEC)
_EVIDENCE_SPEC.loader.exec_module(_EVIDENCE)
LAYER_KEYS = _EVIDENCE.LAYER_KEYS
validate_mask = _EVIDENCE.validate_mask


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source(repo: str, revision_sha: str, path: Path, lineage: str, proof: str) -> dict[str, str]:
    return {
        "repo": repo,
        "revision_sha": revision_sha,
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "lineage": lineage,
        "original_id_proof": proof,
    }


def normalize_heath_k216(path: Path, revision_sha: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    keep_by_layer = raw["keep_maps"]["keep_by_layer"]
    ranked_by_layer = raw["keep_maps"]["ranked_by_layer"]
    for layer in LAYER_KEYS:
        ranked = ranked_by_layer[layer]
        if len(ranked) != 256 or sorted(ranked) != list(range(256)):
            raise ValueError(f"K216 layer {layer} ranking is not a permutation of 0..255")
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": 216,
        "source": source(
            "heath0xFF/DeepSeek-V4-Flash-0731-REAP-K216-GGUF", revision_sha, path,
            "0xSero", "published K216 original-ID keep_by_layer plan",
        ),
        "layers": {
            layer: {
                "kept_experts": sorted(keep_by_layer[layer]),
                "ranked_experts": ranked_by_layer[layer],
            }
            for layer in LAYER_KEYS
        },
    }


def normalize_blivion_k192(path: Path, revision_sha: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": 192,
        "source": source(
            "BlivionIaG/DeepSeek-V4-Flash-0731-Int4-FP8-REAP-216B", revision_sha, path,
            "Blivion", "published per-layer kept_expert_ids in original 0..255 space",
        ),
        "layers": {layer: {"kept_experts": sorted(raw[layer]["kept_expert_ids"])} for layer in LAYER_KEYS},
    }


def normalize_true2456_k163(path: Path, revision_sha: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    covered = tuple(str(layer) for layer in range(3, 43))
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": 163,
        "source": source(
            "True2456/DeepSeek-V4-Flash-0731-REAP37-native-MLX", revision_sha, path,
            "REAP37", "published per-layer original-ID keep lists; hash layers excluded by policy",
        ),
        "layers": {layer: {"kept_experts": sorted(raw["layers"][layer]["keep"])} for layer in covered},
    }


def normalize_native_exact(path: Path, revision_sha: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    declared_k = raw.get("kept_num_routed_experts")
    pruned_revision = raw.get("pruned_revision_sha")
    base_revision = raw.get("base_revision_sha")
    if not isinstance(declared_k, int):
        raise ValueError("native exact mask lacks kept_num_routed_experts")
    if revision_sha != pruned_revision:
        raise ValueError("--revision-sha must match native exact pruned_revision_sha")
    if not isinstance(base_revision, str) or len(base_revision) != 40:
        raise ValueError("native exact mask lacks base_revision_sha")
    layers = raw.get("layers")
    if not isinstance(layers, dict):
        raise ValueError("native exact mask lacks layers")
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": declared_k,
        "source": source(
            raw.get("pruned_repo", "unknown"), revision_sha, path,
            "0xSero" if "0xSero" in raw.get("pruned_repo", "") else "puwaer",
            "43-layer base-to-pruned router recovery; byte-exact bias or row SHA256 matching",
        ),
        "base_revision_sha": base_revision,
        "recovery_logical_sha256": raw.get("logical_sha256"),
        "layers": {
            layer: {"kept_experts": sorted(item["kept_experts"])}
            for layer, item in layers.items()
        },
    }


def normalize_reap25_k192(path: Path, revision_sha: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    keep_map = raw.get("keep_map")
    if raw.get("n_experts") != 256 or raw.get("kept_per_scored_layer") != 192:
        raise ValueError("REAP25 map has unexpected expert geometry")
    if raw.get("scored_layers") != [3, 42] or raw.get("hash_layers_keep") != 256:
        raise ValueError("REAP25 map has unexpected layer coverage")
    if not isinstance(keep_map, dict):
        raise ValueError("REAP25 map lacks keep_map")
    covered = tuple(str(layer) for layer in range(3, 43))
    return {
        "schema": "reap-expert-mask-v1",
        "declared_k": 192,
        "source": source(
            "ljubomirj/ds4", revision_sha, path, "REAP25",
            "published B-exact four-part recovery from compact MLX IDs to original 0..255 IDs",
        ),
        "layers": {
            layer: {"kept_experts": sorted(keep_map[layer])}
            for layer in covered
        },
    }


NORMALIZERS = {
    "heath-k216": normalize_heath_k216,
    "blivion-k192": normalize_blivion_k192,
    "true2456-k163": normalize_true2456_k163,
    "native-exact": normalize_native_exact,
    "reap25-k192": normalize_reap25_k192,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(NORMALIZERS), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--revision-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = NORMALIZERS[args.kind](args.input, args.revision_sha)
    supplemental_kinds = {"true2456-k163", "reap25-k192"}
    expected_layers = set(LAYER_KEYS) if args.kind not in supplemental_kinds else {str(layer) for layer in range(3, 43)}
    validate_mask(payload, expected_layers=expected_layers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"kind": args.kind, "output": str(args.output), "source_sha256": payload["source"]["sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
