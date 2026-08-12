#!/usr/bin/env python3
"""Build REAP96 noMTP from the accepted compact REAP132 checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import build_reap132_raw


EXPECTED_LAYERS = 43
PARENT_K = 132
TARGET_K = 96


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def derive_compact_plan(parent_plan: dict, target_plan: dict) -> dict:
    parent_layers = parent_plan.get("layers") or {}
    target_layers = target_plan.get("layers") or {}
    expected_keys = {str(layer) for layer in range(EXPECTED_LAYERS)}
    if set(parent_layers) != expected_keys or set(target_layers) != expected_keys:
        raise ValueError("parent and target plans must cover Layers 0-42")

    compact_layers = {}
    for layer in range(EXPECTED_LAYERS):
        key = str(layer)
        parent_keep = parent_layers[key].get("kept_experts") or []
        target_keep = target_layers[key].get("kept_experts") or []
        if len(parent_keep) != PARENT_K or len(set(parent_keep)) != PARENT_K:
            raise ValueError(f"layer {layer}: parent plan must contain {PARENT_K} unique experts")
        if len(target_keep) != TARGET_K or len(set(target_keep)) != TARGET_K:
            raise ValueError(f"layer {layer}: target plan must contain {TARGET_K} unique experts")
        parent_index = {original_id: compact_id for compact_id, original_id in enumerate(parent_keep)}
        missing = sorted(set(target_keep) - set(parent_index))
        if missing:
            raise ValueError(f"layer {layer}: K96 is not a K132 subset: {missing[:8]}")
        compact_layers[key] = {
            "kept_experts": [parent_index[original_id] for original_id in target_keep],
            "original_experts": target_keep,
        }

    routing = target_plan.get("hash_routing") or {}
    if set(routing) != {"0", "1", "2"}:
        raise ValueError("target plan must contain hash routing for Layers 0-2")
    return {
        "schema": "heretic-reap96-compact-build-plan-v1",
        "layers": compact_layers,
        "hash_routing": routing,
    }


def validate_source(source: Path) -> None:
    config = json.loads((source / "config.json").read_text(encoding="utf-8"))
    if config.get("n_routed_experts") != PARENT_K:
        raise ValueError(f"source n_routed_experts must be {PARENT_K}")
    if config.get("num_nextn_predict_layers") != 0:
        raise ValueError("source must be the accepted noMTP checkpoint")
    if not (source / "checkpoint-content-manifest.json").is_file():
        raise ValueError("source checkpoint content manifest is missing")


def build(source: Path, output: Path, parent_plan_path: Path, target_plan_path: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    parent_plan_path = parent_plan_path.resolve()
    target_plan_path = target_plan_path.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    validate_source(source)

    parent_bytes = parent_plan_path.read_bytes()
    target_bytes = target_plan_path.read_bytes()
    parent_plan = json.loads(parent_bytes)
    target_plan = json.loads(target_bytes)
    parent_sha = hashlib.sha256(parent_bytes).hexdigest()
    target_sha = hashlib.sha256(target_bytes).hexdigest()
    declared_parent = target_plan.get("k132_plan") or {}
    if declared_parent.get("sha256") != parent_sha:
        raise ValueError("target plan does not reference the supplied parent plan SHA256")
    if declared_parent.get("logical_sha256") != parent_plan.get("logical_sha256"):
        raise ValueError("target plan does not reference the supplied parent logical SHA256")

    compact_plan = derive_compact_plan(parent_plan, target_plan)
    with tempfile.TemporaryDirectory(prefix="reap96-build-plan-") as temporary:
        compact_path = Path(temporary) / "compact-plan.json"
        compact_path.write_text(json.dumps(compact_plan, indent=2) + "\n", encoding="utf-8")
        build_reap132_raw.build(source, output, compact_path)

    config_path = output / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["n_routed_experts"] = TARGET_K
    config["num_nextn_predict_layers"] = 0
    config["moe_compress_args"] = {
        "plan": str(target_plan_path),
        "plan_sha256": target_sha,
        "plan_logical_sha256": target_plan.get("logical_sha256"),
        "parent_plan": str(parent_plan_path),
        "parent_plan_sha256": parent_sha,
        "parent_plan_logical_sha256": parent_plan.get("logical_sha256"),
        "source_expert_space": "reap132-compact",
        "target_expert_space": "reap96-compact",
        "drop_mtp": True,
        "raw_safetensors_slice": True,
        "direct_io": True,
    }
    temporary_config = config_path.with_suffix(".json.tmp")
    temporary_config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary_config.replace(config_path)
    print(f"K96 plan SHA256: {target_sha}")
    print(f"K96 logical SHA256: {target_plan.get('logical_sha256')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="accepted REAP132 noMTP checkpoint")
    parser.add_argument("output", type=Path, help="new REAP96 noMTP checkpoint")
    parser.add_argument("target_plan", type=Path, help="frozen K96 consensus plan")
    parser.add_argument("--parent-plan", type=Path, required=True, help="frozen K132 plan")
    args = parser.parse_args()
    build(args.source, args.output, args.parent_plan, args.target_plan)


if __name__ == "__main__":
    main()
