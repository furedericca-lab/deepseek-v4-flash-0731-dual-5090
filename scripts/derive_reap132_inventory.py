#!/usr/bin/env python3
"""Derive the deterministic REAP output tensor inventory from source and plan."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


EXPERT_NAME = re.compile(
    r"^layers\.(?P<layer>\d+)\.ffn\.experts\.(?P<expert>\d+)\."
    r"(?P<projection>w[123])\.(?P<payload>weight|scale)$"
)
MTP_PREFIX = "mtp."
EXPECTED_PROJECTIONS = frozenset(
    (projection, payload)
    for projection in ("w1", "w2", "w3")
    for payload in ("weight", "scale")
)


def derive_inventory(index_path: Path, plan_path: Path) -> dict:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    source_names = set(index["weight_map"])
    layers = plan["layers"]

    expert_entries: dict[int, dict[int, set[tuple[str, str]]]] = {}
    for name in source_names:
        match = EXPERT_NAME.fullmatch(name)
        if match is None:
            continue
        layer = int(match.group("layer"))
        expert = int(match.group("expert"))
        expert_entries.setdefault(layer, {}).setdefault(expert, set()).add(
            (match.group("projection"), match.group("payload"))
        )

    failures: list[str] = []
    source_expert_count = 0
    output_expert_count = 0
    layer_results = []
    for layer_key, layer_plan in sorted(layers.items(), key=lambda item: int(item[0])):
        layer = int(layer_key)
        source_experts = expert_entries.get(layer, {})
        keep = layer_plan["kept_experts"]
        incomplete = sorted(
            expert for expert, entries in source_experts.items()
            if entries != EXPECTED_PROJECTIONS
        )
        missing_keep = sorted(set(keep) - set(source_experts))
        if incomplete:
            failures.append(f"layer {layer} has incomplete source experts: {incomplete[:5]}")
        if missing_keep:
            failures.append(f"layer {layer} plan references missing experts: {missing_keep[:5]}")
        if len(keep) != len(set(keep)):
            failures.append(f"layer {layer} plan contains duplicate kept expert IDs")

        source_tensors = sum(len(entries) for entries in source_experts.values())
        output_tensors = len(keep) * len(EXPECTED_PROJECTIONS)
        source_expert_count += source_tensors
        output_expert_count += output_tensors
        layer_results.append(
            {
                "layer": layer,
                "source_experts": len(source_experts),
                "kept_experts": len(keep),
                "source_expert_tensors": source_tensors,
                "output_expert_tensors": output_tensors,
            }
        )

    unexpected_layers = sorted(set(expert_entries) - {int(layer) for layer in layers})
    if unexpected_layers:
        failures.append(f"source has expert layers absent from plan: {unexpected_layers}")

    mtp_names = sorted(name for name in source_names if name.startswith(MTP_PREFIX))
    dropped_expert_count = source_expert_count - output_expert_count
    expected_output_count = len(source_names) - dropped_expert_count - len(mtp_names)
    return {
        "schema": "reap132-inventory-v1",
        "source_index": str(index_path.resolve()),
        "plan": str(plan_path.resolve()),
        "source_tensor_count": len(source_names),
        "source_expert_tensor_count": source_expert_count,
        "output_expert_tensor_count": output_expert_count,
        "dropped_expert_tensor_count": dropped_expert_count,
        "source_mtp_dspark_tensor_count": len(mtp_names),
        "expected_output_tensor_count": expected_output_count,
        "expected_output_mtp_dspark_tensor_count": 0,
        "layer_count": len(layer_results),
        "layer_results": layer_results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_index", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = derive_inventory(args.source_index, args.plan)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output.resolve()}")
    summary = {key: value for key, value in result.items() if key != "layer_results"}
    print(json.dumps(summary, indent=2))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
