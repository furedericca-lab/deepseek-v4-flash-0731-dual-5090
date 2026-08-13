#!/usr/bin/env python3
"""Audit K132 routed-expert imatrix coverage and ranking stability."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "llama.cpp" / "gguf-py"))
from gguf import GGUFReader  # noqa: E402


ENTRY = re.compile(r"^blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight$")
LAYERS = 43
EXPERTS = 132
PROJECTIONS = ("gate", "up", "down")
MIN_ACCEPTED_CHUNKS = 200
SPEARMAN_GATE = 0.95
TOP17_CHURN_GATE = 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def field_int(reader: GGUFReader, name: str) -> int:
    field = reader.fields.get(name)
    if field is None:
        raise ValueError(f"missing GGUF field: {name}")
    return int(field.contents())


def nearest_rank_percentile(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    index = int(math.floor((len(ordered) - 1) * percentile))
    return ordered[index]


def rank_layers(structural: dict[int, dict], normalized_i: dict[int, float]) -> tuple[list[dict], dict]:
    records = []
    for layer in range(LAYERS):
        source = structural[layer]
        r_value = float(source["R_l"])
        i_value = float(normalized_i[layer])
        records.append({
            "layer": layer,
            "R_l": r_value,
            "I_l": i_value,
            "P_l": 0.4 * r_value + 0.6 * i_value,
            "k216_rank_mean": float(source["k216_rank_mean"]),
        })

    orders = {
        "R": sorted(records, key=lambda x: (-x["R_l"], x["k216_rank_mean"], x["layer"])),
        "I": sorted(records, key=lambda x: (-x["I_l"], -x["R_l"], x["k216_rank_mean"], x["layer"])),
        "P": sorted(records, key=lambda x: (-x["P_l"], -x["I_l"], -x["R_l"], x["k216_rank_mean"], x["layer"])),
    }
    for name, ordered in orders.items():
        for rank, item in enumerate(ordered, 1):
            next(record for record in records if record["layer"] == item["layer"])[f"Rank_{name}"] = rank
    records.sort(key=lambda x: x["layer"])
    return records, {name: [x["layer"] for x in value[:17]] for name, value in orders.items()}


def audit_stage(path: Path, structural: dict[int, dict]) -> dict:
    reader = GGUFReader(path)
    chunks = field_int(reader, "imatrix.chunk_count")
    chunk_size = field_int(reader, "imatrix.chunk_size")
    tensors = {tensor.name: tensor for tensor in reader.tensors}
    routed: dict[tuple[int, str], tuple[np.ndarray, np.ndarray]] = {}
    malformed = []
    for name, tensor in tensors.items():
        base = name.removesuffix(".in_sum2").removesuffix(".counts")
        match = ENTRY.fullmatch(base)
        if match is None:
            continue
        key = (int(match.group(1)), match.group(2))
        sums_name = base + ".in_sum2"
        counts_name = base + ".counts"
        if sums_name not in tensors or counts_name not in tensors:
            malformed.append(base)
            continue
        sums = np.asarray(tensors[sums_name].data, dtype=np.float64).reshape(-1)
        raw_counts = np.asarray(tensors[counts_name].data, dtype=np.float64).reshape(-1)
        if raw_counts.size != EXPERTS or sums.size % EXPERTS != 0:
            malformed.append(base)
            continue
        if not np.isfinite(sums).all() or not np.isfinite(raw_counts).all():
            malformed.append(base)
            continue
        counts = np.rint(raw_counts).astype(np.int64)
        if not np.array_equal(raw_counts, counts.astype(np.float64)):
            malformed.append(base)
            continue
        routed[key] = (sums.reshape(EXPERTS, -1), counts)

    expected = {(layer, projection) for layer in range(LAYERS) for projection in PROJECTIONS}
    missing = sorted(expected - routed.keys())
    extra = sorted(routed.keys() - expected)
    zero_count = []
    count_mismatches = []
    raw_i: dict[int, float] = {}
    entropies = {}
    all_counts: list[int] = []
    if not missing and not extra and not malformed:
        for layer in range(LAYERS):
            projection_data = [routed[(layer, projection)] for projection in PROJECTIONS]
            counts = projection_data[0][1]
            for projection, (_, candidate) in zip(PROJECTIONS[1:], projection_data[1:]):
                if not np.array_equal(counts, candidate):
                    count_mismatches.append({"layer": layer, "projection": projection})
            zero_count.extend({"layer": layer, "expert": expert} for expert in np.flatnonzero(counts == 0).tolist())
            all_counts.extend(int(value) for value in counts)
            if np.any(counts <= 0) or count_mismatches:
                continue
            per_projection = []
            for sums, projection_counts in projection_data:
                per_projection.append(sums.sum(axis=1) / (projection_counts * sums.shape[1]))
            activation = np.mean(np.stack(per_projection), axis=0)
            raw_i[layer] = float(np.sum(counts * activation) / np.sum(counts))
            probabilities = counts / np.sum(counts)
            entropies[layer] = float(-np.sum(probabilities * np.log(probabilities)) / math.log(EXPERTS))

    finite_raw = len(raw_i) == LAYERS and all(math.isfinite(value) for value in raw_i.values())
    coverage_pass = not missing and not extra and not malformed and not zero_count and not count_mismatches and finite_raw
    records = []
    top17 = {}
    if finite_raw:
        values = [raw_i[layer] for layer in range(LAYERS)]
        ranks = rankdata(values, method="average") - 1
        normalized = {layer: float(ranks[layer] / (LAYERS - 1)) for layer in range(LAYERS)}
        records, top17 = rank_layers(structural, normalized)
        for record in records:
            record["raw_I_l"] = raw_i[record["layer"]]
            record["routing_entropy"] = entropies[record["layer"]]

    return {
        "path": str(path),
        "sha256": sha256(path),
        "size": path.stat().st_size,
        "chunks": chunks,
        "chunk_size": chunk_size,
        "coverage_pass": coverage_pass,
        "missing_entries": [{"layer": x[0], "projection": x[1]} for x in missing],
        "extra_entries": [{"layer": x[0], "projection": x[1]} for x in extra],
        "malformed_entries": sorted(set(malformed)),
        "zero_count_experts": zero_count,
        "count_mismatches": count_mismatches,
        "count_statistics": ({
            "min": min(all_counts),
            "p1": nearest_rank_percentile(all_counts, 0.01),
            "p5": nearest_rank_percentile(all_counts, 0.05),
            "median": nearest_rank_percentile(all_counts, 0.50),
        } if all_counts else None),
        "layers": records,
        "top17": top17,
    }


def compare_stages(previous: dict, current: dict) -> dict:
    if not previous["layers"] or not current["layers"]:
        return {"pass": False, "reason": "missing complete layer rankings"}
    old = {item["layer"]: item for item in previous["layers"]}
    new = {item["layer"]: item for item in current["layers"]}
    rho = float(spearmanr(
        [old[layer]["raw_I_l"] for layer in range(LAYERS)],
        [new[layer]["raw_I_l"] for layer in range(LAYERS)],
    ).statistic)
    churn_i = len(set(previous["top17"]["I"]) ^ set(current["top17"]["I"])) // 2
    churn_p = len(set(previous["top17"]["P"]) ^ set(current["top17"]["P"])) // 2
    passed = rho >= SPEARMAN_GATE and churn_i <= TOP17_CHURN_GATE and churn_p <= TOP17_CHURN_GATE
    return {"spearman_raw_I": rho, "activation_top17_churn": churn_i,
            "final_top17_churn": churn_p, "pass": passed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--imatrix", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    structural_doc = json.loads(args.structural.read_text())
    structural = {int(item["layer"]): item for item in structural_doc["layers"]}
    if set(structural) != set(range(LAYERS)):
        raise ValueError("structural report must contain layers 0..42")
    stages = sorted((audit_stage(path, structural) for path in args.imatrix), key=lambda x: x["chunks"])
    comparisons = []
    accepted = None
    for previous, current in zip(stages, stages[1:]):
        comparison = {"from_chunks": previous["chunks"], "to_chunks": current["chunks"],
                      **compare_stages(previous, current)}
        comparisons.append(comparison)
        if accepted is None and current["chunks"] >= MIN_ACCEPTED_CHUNKS and current["coverage_pass"] and comparison["pass"]:
            accepted = current["chunks"]
    report = {
        "schema": "heretic-reap132-imatrix-audit-v1",
        "structural_sha256": sha256(args.structural),
        "gates": {"min_chunks": MIN_ACCEPTED_CHUNKS, "spearman": SPEARMAN_GATE,
                  "activation_top17_churn": TOP17_CHURN_GATE, "final_top17_churn": TOP17_CHURN_GATE},
        "stages": stages,
        "comparisons": comparisons,
        "accepted_chunks": accepted,
        "status": "PASS" if accepted is not None else "INCOMPLETE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "accepted_chunks": accepted}))
    return 0 if accepted is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
