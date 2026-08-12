#!/usr/bin/env python3
"""Build the frozen 43-layer REAP structural-prior report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def build(source: dict, *, source_sha256: str, source_size: int) -> dict:
    if source.get("candidate_k") != 132 or source.get("target_k") != 96:
        raise ValueError("expected K132 candidate universe and K96 target")
    if set(source.get("layers", {})) != {str(layer) for layer in range(43)}:
        raise ValueError("expected exactly layers 0 through 42")
    layers = []
    for layer in range(43):
        data = source["layers"][str(layer)]
        ranked = data["ranked_experts"]
        if len(ranked) != 132:
            raise ValueError(f"layer {layer}: expected 132 experts")
        if [item["rank"] for item in ranked] != list(range(1, 133)):
            raise ValueError(f"layer {layer}: ranks are not 1 through 132")
        if sum(bool(item["selected"]) for item in ranked) != 96:
            raise ValueError(f"layer {layer}: expected exactly 96 selected experts")
        if any(bool(item["selected"]) != (item["rank"] <= 96) for item in ranked):
            raise ValueError(f"layer {layer}: selected flags do not match rank boundary")
        if len({item["expert_id"] for item in ranked}) != 132:
            raise ValueError(f"layer {layer}: duplicate expert IDs")
        max_score = 3 if layer < 3 else 5
        if any(not 0 <= item["score"] <= max_score for item in ranked):
            raise ValueError(f"layer {layer}: score outside 0..{max_score}")
        mass = sum(item["score"] for item in ranked) / (132 * max_score)
        threshold = 3 if layer < 3 else 4
        high = sum(item["score"] >= threshold for item in ranked)
        deleted_high = sum(not item["selected"] and item["score"] >= threshold for item in ranked)
        tie = bool(data["boundary"]["tie_crosses_boundary"])
        ranks = [item["0xsero_k216_rank"] for item in ranked]
        r_value = (
            0.50 * mass
            + 0.20 * (ranked[96]["score"] / max_score)
            + 0.15 * (high / 132)
            + 0.10 * (deleted_high / 36)
            + 0.05 * int(tie)
        )
        layers.append({
            "layer": layer,
            "normalized_consensus_mass": mass,
            "rank96_normalized_score": ranked[95]["score"] / max_score,
            "rank97_normalized_score": ranked[96]["score"] / max_score,
            "high_score_count": high,
            "deleted_high_count": deleted_high,
            "boundary_tie": tie,
            "k216_rank_mean": sum(ranks) / 132,
            "R_l": r_value,
        })
    report = {
        "schema": "heretic-reap132-structural-prior-v1",
        "source": {
            "sha256": source_sha256,
            "size": source_size,
        },
        "normalization": {
            "layers_0_2_max_score": 3,
            "layers_3_42_max_score": 5,
            "high_score_threshold_layers_0_2": 3,
            "high_score_threshold_layers_3_42": 4,
        },
        "formula": "0.50*mass+0.20*rank97+0.15*(high/132)+0.10*(deleted_high/36)+0.05*tie",
        "layers": layers,
    }
    report["logical_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    report = build(
        json.loads(source_bytes),
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_size=len(source_bytes),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"layers": 43, "logical_sha256": report["logical_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
