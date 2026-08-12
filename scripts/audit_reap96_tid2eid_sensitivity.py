#!/usr/bin/env python3
"""Audit REAP96 hash-routing sensitivity without changing the frozen plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from build_reap96_plan import decode_matrix, decode_tid, direct_read, tensor_ref


HASH_LAYERS = range(3)


def raw_l2_cost(router: np.ndarray, survivors: list[int]) -> np.ndarray:
    selected = router[survivors]
    return np.sum(
        (router[:, None, :].astype(np.float64) - selected[None, :, :].astype(np.float64)) ** 2,
        axis=2,
    )


def cosine_cost(router: np.ndarray, survivors: list[int]) -> np.ndarray:
    values = router.astype(np.float64)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    normalized = values / np.maximum(norms, np.finfo(np.float64).tiny)
    return 1.0 - normalized @ normalized[survivors].T


def preference_order(cost: np.ndarray, survivors: list[int]) -> np.ndarray:
    survivor_ids = np.asarray(survivors, dtype=np.int64)
    return np.stack(
        [np.lexsort((survivor_ids, row)) for row in cost], axis=0
    )


def greedy_remap(
    table: np.ndarray, survivors: list[int], cost: np.ndarray
) -> tuple[np.ndarray, dict[str, int]]:
    survivor_set = set(survivors)
    compact = {old_id: new_id for new_id, old_id in enumerate(survivors)}
    order = preference_order(cost, survivors)
    output = np.empty_like(table)
    collisions = replacements = 0
    for row_index, row in enumerate(table):
        assigned: dict[int, int] = {}
        used: set[int] = set()
        values = row.tolist()
        for position, old_id in enumerate(values):
            if old_id in survivor_set:
                assigned[position] = old_id
                used.add(old_id)
        for position, old_id in enumerate(values):
            if position in assigned:
                continue
            replacements += 1
            for preference_index in order[old_id]:
                candidate = survivors[int(preference_index)]
                if candidate not in used:
                    assigned[position] = candidate
                    used.add(candidate)
                    collisions += int(preference_index != order[old_id, 0])
                    break
        output[row_index] = [compact[assigned[position]] for position in range(len(values))]
    return output, {"replacements": replacements, "collision_avoids": collisions}


def optimal_remap(
    table: np.ndarray, survivors: list[int], cost: np.ndarray
) -> tuple[np.ndarray, dict[str, float | int]]:
    survivor_set = set(survivors)
    compact = {old_id: new_id for new_id, old_id in enumerate(survivors)}
    output = np.empty_like(table)
    optimized_rows = changed_rows = 0
    greedy_total = optimal_total = 0.0
    greedy, _ = greedy_remap(table, survivors, cost)

    for row_index, row in enumerate(table):
        values = row.tolist()
        assigned = {
            position: old_id
            for position, old_id in enumerate(values)
            if old_id in survivor_set
        }
        used = set(assigned.values())
        dropped_positions = [position for position in range(len(values)) if position not in assigned]
        available = [old_id for old_id in survivors if old_id not in used]
        if dropped_positions:
            matrix = np.asarray(
                [[cost[values[position], compact[candidate]] for candidate in available]
                 for position in dropped_positions],
                dtype=np.float64,
            )
            row_indices, column_indices = linear_sum_assignment(matrix)
            for local_row, column in zip(row_indices.tolist(), column_indices.tolist()):
                assigned[dropped_positions[local_row]] = available[column]
            optimized_rows += 1
            for position in dropped_positions:
                old_id = values[position]
                greedy_id = survivors[int(greedy[row_index, position])]
                greedy_total += float(cost[old_id, compact[greedy_id]])
                optimal_total += float(cost[old_id, compact[assigned[position]]])
        output[row_index] = [compact[assigned[position]] for position in range(len(values))]
        changed_rows += int(not np.array_equal(output[row_index], greedy[row_index]))

    return output, {
        "rows_with_replacements": optimized_rows,
        "rows_changed_vs_greedy": changed_rows,
        "greedy_total_cost": greedy_total,
        "optimal_total_cost": optimal_total,
        "absolute_improvement": greedy_total - optimal_total,
        "relative_improvement": (greedy_total - optimal_total) / greedy_total if greedy_total else 0.0,
    }


def distribution(values: np.ndarray, k: int) -> dict:
    counts = np.bincount(values.reshape(-1), minlength=k).astype(np.int64)
    return count_distribution(counts)


def count_distribution(counts: np.ndarray) -> dict:
    median = float(np.median(counts))
    return {
        "minimum": int(counts.min()),
        "maximum": int(counts.max()),
        "median": median,
        "p95": float(np.percentile(counts, 95)),
        "p99": float(np.percentile(counts, 99)),
        "max_to_median": float(counts.max() / median) if median else None,
        "coefficient_of_variation": float(counts.std() / counts.mean()),
        "top10": [
            {"compact_expert": int(index), "slots": int(counts[index])}
            for index in np.argsort(-counts, kind="stable")[:10]
        ],
        "counts": counts.tolist(),
    }


def audit_layer(layer: int, k132: dict, k96: dict, checkpoint: Path) -> dict:
    k132_original = k132["layers"][str(layer)]["kept_experts"]
    k96_original = k96["layers"][str(layer)]["kept_experts"]
    original_to_k132 = {original: compact for compact, original in enumerate(k132_original)}
    survivors = [original_to_k132[original] for original in k96_original]
    survivor_set = set(survivors)
    dropped = sorted(set(range(132)) - survivor_set)

    tensor = f"layers.{layer}.ffn.gate.weight"
    path, dtype, shape, start, end = tensor_ref(checkpoint, tensor)
    router = decode_matrix(direct_read(path, start, end), dtype, shape)
    table = decode_tid(k132["hash_routing"][str(layer)])
    frozen = decode_tid(k96["hash_routing"][str(layer)])

    l2 = raw_l2_cost(router, survivors)
    cosine = cosine_cost(router, survivors)
    l2_primary = np.argmin(l2[dropped], axis=1)
    cosine_primary = np.argmin(cosine[dropped], axis=1)
    primary_different = int(np.count_nonzero(l2_primary != cosine_primary))

    l2_greedy, l2_stats = greedy_remap(table, survivors, l2)
    cosine_greedy, cosine_stats = greedy_remap(table, survivors, cosine)
    if not np.array_equal(cosine_greedy, frozen):
        raise ValueError(f"layer {layer}: audit cosine result differs from frozen plan")
    optimal, optimal_stats = optimal_remap(table, survivors, cosine)

    replacement_load = Counter()
    for old_row, new_row in zip(table, frozen):
        for old_id, new_id in zip(old_row.tolist(), new_row.tolist()):
            if old_id not in survivor_set:
                replacement_load[int(new_id)] += 1
    replacement_counts = np.asarray([replacement_load[index] for index in range(96)], dtype=np.int64)

    return {
        "layer": layer,
        "router": {"tensor": tensor, "dtype": dtype, "shape": list(shape)},
        "metric_sensitivity": {
            "dropped_experts": len(dropped),
            "primary_replacement_different": primary_different,
            "primary_replacement_different_fraction": primary_different / len(dropped),
            "slot_assignments_different": int(np.count_nonzero(l2_greedy != cosine_greedy)),
            "slot_assignments_total": int(table.size),
            "slot_assignments_different_fraction": float(np.count_nonzero(l2_greedy != cosine_greedy) / table.size),
            "raw_l2": l2_stats,
            "cosine": cosine_stats,
        },
        "greedy_sensitivity": {
            **optimal_stats,
            "slot_assignments_different": int(np.count_nonzero(cosine_greedy != optimal)),
        },
        "load": {
            "k132": distribution(table, 132),
            "k96": distribution(frozen, 96),
            "replacement_only": count_distribution(replacement_counts),
        },
    }


def build_report(k132_path: Path, k96_path: Path, checkpoint: Path) -> dict:
    k132 = json.loads(k132_path.read_text(encoding="utf-8"))
    k96 = json.loads(k96_path.read_text(encoding="utf-8"))
    layers = [audit_layer(layer, k132, k96, checkpoint) for layer in HASH_LAYERS]
    return {
        "schema": "reap96-tid2eid-sensitivity-v1",
        "inputs": {
            "k132_plan": str(k132_path.resolve()),
            "k132_plan_sha256": hashlib.sha256(k132_path.read_bytes()).hexdigest(),
            "k96_plan": str(k96_path.resolve()),
            "k96_plan_sha256": hashlib.sha256(k96_path.read_bytes()).hexdigest(),
            "checkpoint": str(checkpoint.resolve()),
        },
        "layers": {str(item["layer"]): item for item in layers},
        "summary": {
            "primary_replacements_compared": sum(item["metric_sensitivity"]["dropped_experts"] for item in layers),
            "primary_replacements_different": sum(item["metric_sensitivity"]["primary_replacement_different"] for item in layers),
            "slot_assignments_different_l2_vs_cosine": sum(item["metric_sensitivity"]["slot_assignments_different"] for item in layers),
            "rows_changed_greedy_vs_optimal": sum(item["greedy_sensitivity"]["rows_changed_vs_greedy"] for item in layers),
            "cosine_cost_relative_improvement_optimal": (
                sum(item["greedy_sensitivity"]["absolute_improvement"] for item in layers)
                / sum(item["greedy_sensitivity"]["greedy_total_cost"] for item in layers)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k132-plan", type=Path, required=True)
    parser.add_argument("--k96-plan", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.k132_plan, args.k96_plan, args.checkpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
