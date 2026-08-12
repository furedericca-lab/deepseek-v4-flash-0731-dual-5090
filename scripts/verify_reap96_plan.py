#!/usr/bin/env python3
"""Independently validate a HERETIC REAP96 consensus plan."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import zlib
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_plan(plan: dict[str, Any], k132: dict[str, Any], score: dict[str, Any], *, k132_sha: str, score_sha: str) -> dict[str, Any]:
    failures = []
    if plan.get("schema") != "heretic-reap96-consensus-v1":
        failures.append("plan schema mismatch")
    if plan.get("k132_plan", {}).get("sha256") != k132_sha:
        failures.append("K132 file SHA mismatch")
    if plan.get("k132_plan", {}).get("logical_sha256") != k132.get("logical_sha256"):
        failures.append("K132 logical SHA mismatch")
    if plan.get("score_report", {}).get("sha256") != score_sha:
        failures.append("score report SHA mismatch")

    selected_scores: Counter[int] = Counter()
    deleted_scores: Counter[int] = Counter()
    for layer in map(str, range(43)):
        keep = plan.get("layers", {}).get(layer, {}).get("kept_experts")
        expected = score.get("layers", {}).get(layer, {}).get("selected_experts")
        universe = set(k132.get("layers", {}).get(layer, {}).get("kept_experts", []))
        if not isinstance(keep, list) or len(keep) != 96 or keep != sorted(keep) or len(set(keep)) != 96:
            failures.append(f"layer {layer}: malformed K96 keep set")
        elif not set(keep) <= universe:
            failures.append(f"layer {layer}: K96 is not a K132 subset")
        if keep != expected:
            failures.append(f"layer {layer}: selection differs from score report")
        ranked = score.get("layers", {}).get(layer, {}).get("ranked_experts", [])
        if sum(bool(row.get("selected")) for row in ranked) != 96 or len(ranked) != 132:
            failures.append(f"layer {layer}: score report selection cardinality mismatch")
        for row in ranked:
            (selected_scores if row.get("selected") else deleted_scores)[row.get("score")] += 1

    expected_selected = Counter({5: 1969, 4: 1867, 3: 277, 2: 15})
    expected_deleted = Counter({4: 309, 3: 913, 2: 293, 1: 31, 0: 2})
    if selected_scores != expected_selected or sum(selected_scores.values()) != 4128:
        failures.append("selected score histogram mismatch")
    if deleted_scores != expected_deleted or sum(deleted_scores.values()) != 1548:
        failures.append("deleted score histogram mismatch")

    routing = plan.get("hash_routing", {})
    if set(routing) != {"0", "1", "2"}:
        failures.append("hash routing layer coverage mismatch")
    routing_report = {}
    for layer in ("0", "1", "2"):
        item = routing.get(layer, {})
        try:
            raw = zlib.decompress(base64.b64decode(item["data"], validate=True))
            shape = tuple(item["shape"])
            if hashlib.sha256(raw).hexdigest() != item["sha256"]:
                raise ValueError("payload SHA mismatch")
            if shape != (129280, 6) or item["dtype"] != "int64" or len(raw) != 129280 * 6 * 8:
                raise ValueError("payload geometry mismatch")
            table = np.frombuffer(raw, dtype="<i8").reshape(shape)
            duplicates = int(np.any(np.diff(np.sort(table, axis=1), axis=1) == 0, axis=1).sum())
            minimum, maximum = int(table.min()), int(table.max())
            unique = int(len(np.unique(table)))
            if minimum != 0 or maximum != 95 or duplicates or unique != 96:
                raise ValueError("payload range/uniqueness mismatch")
            routing_report[layer] = {"minimum": minimum, "maximum": maximum, "duplicate_rows": duplicates, "unique_experts": unique}
        except (KeyError, ValueError, TypeError, zlib.error) as error:
            failures.append(f"hash layer {layer}: {error}")

    logical = {key: plan.get(key) for key in ("k132_plan", "score_report", "layers", "hash_routing")}
    logical_sha = hashlib.sha256(json.dumps(logical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if logical_sha != plan.get("logical_sha256"):
        failures.append("plan logical SHA mismatch")
    return {
        "schema": "heretic-reap96-consensus-plan-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "layers": 43,
        "kept_per_layer": 96,
        "score_histogram": {
            "selected": {str(score): count for score, count in sorted(selected_scores.items())},
            "deleted": {str(score): count for score, count in sorted(deleted_scores.items())},
            "selected_total": sum(selected_scores.values()),
            "deleted_total": sum(deleted_scores.values()),
        },
        "routing": routing_report,
        "logical_sha256": logical_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--k132-plan", type=Path, required=True)
    parser.add_argument("--score-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    k132 = json.loads(args.k132_plan.read_text(encoding="utf-8"))
    score = json.loads(args.score_report.read_text(encoding="utf-8"))
    report = verify_plan(plan, k132, score, k132_sha=sha256_file(args.k132_plan), score_sha=sha256_file(args.score_report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
