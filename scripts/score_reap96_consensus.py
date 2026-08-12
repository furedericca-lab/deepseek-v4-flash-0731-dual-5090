#!/usr/bin/env python3
"""Score a deterministic K96 candidate subset from frozen REAP evidence.

This is deliberately report-only. It selects 96 original expert IDs from each
frozen K132 layer but does not create hash routing or authorize a checkpoint.
"""

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
k132_mask = _EVIDENCE.k132_mask
load_mask = _EVIDENCE.load_mask

TARGET_K = 96
SCORING_SOURCES = {
    "0xsero-k160",
    "heath0xff-k216",
    "blivion-k192",
    "reap25-k192",
    "true2456-k163",
}
REQUIRED_SOURCES = SCORING_SOURCES | {"puwaer-k178"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_locked_masks(lock_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    scope_root = lock_path.parent.parent
    records = {record["id"]: record for record in lock["sources"] if record.get("accepted_for_scoring")}
    missing = sorted(REQUIRED_SOURCES - set(records))
    if missing:
        raise ValueError(f"required accepted source missing from evidence lock: {missing}")

    masks: dict[str, dict[str, Any]] = {}
    for source_id in sorted(REQUIRED_SOURCES):
        record = records[source_id]
        normalized_rel = record.get("normalized_path")
        if not isinstance(normalized_rel, str):
            raise ValueError(f"{source_id}: normalized_path missing from evidence lock")
        path = scope_root / normalized_rel
        mask = load_mask(path)
        if mask["source"]["revision_sha"] != record["revision_sha"]:
            raise ValueError(f"{source_id}: normalized revision does not match evidence lock")
        expected_source_sha = record.get("source_sha256")
        if isinstance(expected_source_sha, str) and mask["source"]["sha256"] != expected_source_sha:
            raise ValueError(f"{source_id}: normalized source digest does not match evidence lock")
        masks[source_id] = mask
    return lock, masks


def membership(mask: dict[str, Any], layer: str, expert: int) -> bool | None:
    item = mask["layers"].get(layer)
    return None if item is None else expert in item["kept_experts"]


def score_layer(universe: list[int], layer: str, masks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ranked_experts = masks["heath0xff-k216"]["layers"][layer].get("ranked_experts")
    if not isinstance(ranked_experts, list) or len(ranked_experts) != 256 or sorted(ranked_experts) != list(range(256)):
        raise ValueError(f"layer {layer}: K216 semantic ranking is missing or malformed")
    sero_rank = {expert: rank for rank, expert in enumerate(ranked_experts)}
    rows = []
    for expert in universe:
        sero160 = membership(masks["0xsero-k160"], layer, expert)
        sero216 = membership(masks["heath0xff-k216"], layer, expert)
        blivion = membership(masks["blivion-k192"], layer, expert)
        reap25 = membership(masks["reap25-k192"], layer, expert)
        reap37 = membership(masks["true2456-k163"], layer, expert)
        puwaer178 = membership(masks["puwaer-k178"], layer, expert)
        if sero160 and not sero216:
            raise ValueError(f"layer {layer}, expert {expert}: K160 is not a K216 subset")
        if puwaer178 is not True:
            raise ValueError(f"layer {layer}, expert {expert}: K132 is not a K178 subset")

        # K160/K216 are an ordinal 0xSero tier: strong=2, weak=1, absent=0.
        # K178 adds no selection weight because K132 is fully nested in it.
        score = (2 if sero160 else 1 if sero216 else 0) + int(bool(blivion)) + int(bool(reap25)) + int(bool(reap37))
        evidence = {
            "puwaer_k178": puwaer178,
            "0xsero_k160": sero160,
            "0xsero_k216": sero216,
            "blivion_k192": blivion,
            "reap25_k192": reap25,
            "reap37_k163": reap37,
        }
        # Prefer stronger ordinal membership, then independent confirmations,
        # then original ID. Missing supplemental coverage is not a negative vote.
        tie_break = (
            int(bool(sero160)), int(bool(sero216)), int(bool(blivion)),
            int(bool(reap25)), int(bool(reap37)),
        )
        rows.append({
            "expert_id": expert,
            "score": score,
            "evidence": evidence,
            "tie_break": list(tie_break),
            "0xsero_k216_rank": sero_rank[expert],
        })

    ranked = sorted(rows, key=lambda row: (
        -row["score"], tuple(-value for value in row["tie_break"]),
        row["0xsero_k216_rank"], row["expert_id"],
    ))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
        row["selected"] = rank <= TARGET_K
    selected = sorted(row["expert_id"] for row in ranked if row["selected"])
    boundary = {
        "last_selected": ranked[TARGET_K - 1],
        "first_deleted": ranked[TARGET_K],
        "tie_crosses_boundary": ranked[TARGET_K - 1]["score"] == ranked[TARGET_K]["score"],
    }
    return {"selected_experts": selected, "ranked_experts": ranked, "boundary": boundary}


def score_consensus(k132: dict[str, Any], masks: dict[str, dict[str, Any]], lock: dict[str, Any]) -> dict[str, Any]:
    layers = {}
    for layer in LAYER_KEYS:
        universe = k132["layers"][layer]["kept_experts"]
        layers[layer] = score_layer(universe, layer, masks)
    return {
        "schema": "heretic-reap96-consensus-score-report-v1",
        "target_k": TARGET_K,
        "candidate_k": 132,
        "candidate_universe": lock["candidate_universe"],
        "scoring": {
            "0xsero_ordinal": {"K160": 2, "K216_only": 1, "absent": 0},
            "independent_votes": {"Blivion_K192": 1, "REAP25_K192": 1, "REAP37_K163": 1},
            "puwaer_k178": "nested consistency audit only; zero selection weight",
            "tie_break": [
                "0xsero_k160", "0xsero_k216", "blivion_k192", "reap25_k192",
                "reap37_k163", "0xsero_k216_semantic_rank", "original_expert_id_ascending",
            ],
        },
        "sources": {
            source_id: {"revision_sha": mask["source"]["revision_sha"], "source_sha256": mask["source"]["sha256"], "normalized_file_sha256": mask["normalized_file_sha256"]}
            for source_id, mask in sorted(masks.items())
        },
        "layers": layers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k132-plan", type=Path, required=True)
    parser.add_argument("--evidence-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock, masks = load_locked_masks(args.evidence_lock)
    k132 = k132_mask(args.k132_plan)
    report = score_consensus(k132, masks, lock)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "layers": len(report["layers"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
