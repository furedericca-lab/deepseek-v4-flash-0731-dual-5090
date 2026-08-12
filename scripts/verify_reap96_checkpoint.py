#!/usr/bin/env python3
"""Byte-verify a REAP96 noMTP checkpoint built from accepted REAP132."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import verify_reap132_checkpoint as base


EXPECTED_LAYERS = 43
TARGET_K = 96


def config_failures(output: Path, plan: dict, parent_plan: dict) -> list[str]:
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    expected = {
        "model_type": "deepseek_v4",
        "n_routed_experts": TARGET_K,
        "num_hidden_layers": EXPECTED_LAYERS,
        "num_hash_layers": 3,
        "num_experts_per_tok": 6,
        "num_nextn_predict_layers": 0,
    }
    failures = [
        f"config {key}={config.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if config.get(key) != value
    ]
    args = config.get("moe_compress_args") or {}
    required = {
        "plan_sha256": plan["_file_sha256"],
        "plan_logical_sha256": plan.get("logical_sha256"),
        "parent_plan_sha256": parent_plan["_file_sha256"],
        "parent_plan_logical_sha256": parent_plan.get("logical_sha256"),
        "source_expert_space": "reap132-compact",
        "target_expert_space": "reap96-compact",
        "drop_mtp": True,
        "raw_safetensors_slice": True,
        "direct_io": True,
    }
    for key, value in required.items():
        if args.get(key) != value:
            failures.append(f"config moe_compress_args.{key} mismatch")
    return failures


def verify(
    source: Path,
    output: Path,
    plan_path: Path,
    parent_plan_path: Path,
    source_manifest_path: Path,
    output_manifest_path: Path,
) -> dict:
    source = source.resolve()
    output = output.resolve()
    plan_path = plan_path.resolve()
    parent_plan_path = parent_plan_path.resolve()
    plan_bytes = plan_path.read_bytes()
    parent_bytes = parent_plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    parent = json.loads(parent_bytes)
    plan["_file_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
    parent["_file_sha256"] = hashlib.sha256(parent_bytes).hexdigest()
    failures: list[str] = []
    declared = plan.get("k132_plan") or {}
    if declared.get("sha256") != parent["_file_sha256"]:
        failures.append("plan parent file SHA mismatch")
    if declared.get("logical_sha256") != parent.get("logical_sha256"):
        failures.append("plan parent logical SHA mismatch")
    failures.extend(config_failures(output, plan, parent))

    source_manifest = base.load_manifest(source_manifest_path.resolve())
    output_manifest = base.load_manifest(output_manifest_path.resolve())
    source_index = json.loads((source / "model.safetensors.index.json").read_text())
    output_index = json.loads((output / "model.safetensors.index.json").read_text())
    source_refs = base.load_headers(source, source_index)
    output_refs = base.load_headers(output, output_index)
    source_names = set(source_refs)
    output_names = set(output_refs)
    source_experts = {name for name in source_names if base.EXPERT_RE.fullmatch(name)}
    source_mtp = {name for name in source_names if name.startswith(base.MTP_PREFIX)}
    expected_names = source_names - source_experts - source_mtp
    layer_results = []

    for layer in range(EXPECTED_LAYERS):
        key = str(layer)
        parent_keep = parent["layers"][key]["kept_experts"]
        target_keep = plan["layers"][key]["kept_experts"]
        source_compact = {original: compact for compact, original in enumerate(parent_keep)}
        if len(target_keep) != TARGET_K or not set(target_keep) <= set(source_compact):
            failures.append(f"layer {layer}: invalid K96 subset")
            continue
        layer_failures = []
        checked = 0
        for new_id, original_id in enumerate(target_keep):
            old_id = source_compact[original_id]
            for projection in ("w1", "w2", "w3"):
                for payload in ("weight", "scale"):
                    out_name = f"layers.{layer}.ffn.experts.{new_id}.{projection}.{payload}"
                    src_name = f"layers.{layer}.ffn.experts.{old_id}.{projection}.{payload}"
                    expected_names.add(out_name)
                    if out_name not in output_refs or src_name not in source_refs:
                        layer_failures.append(f"missing expert provenance {out_name} <- {src_name}")
                    elif not base.equal_bytes(source_refs[src_name], output_refs[out_name]):
                        layer_failures.append(f"expert bytes mismatch {out_name} <- {src_name}")
                    checked += 1
        failures.extend(layer_failures)
        layer_results.append({
            "layer": layer,
            "kept_experts": len(target_keep),
            "expert_tensors": checked,
            "failures": layer_failures,
        })

    if output_names != expected_names:
        failures.append(
            f"namespace mismatch: unexpected={len(output_names - expected_names)} "
            f"missing={len(expected_names - output_names)}"
        )
    if any(name.startswith(base.MTP_PREFIX) for name in output_names):
        failures.append("MTP/DSpark tensors remain in output")

    router_failures = []
    for name, out_ref in output_refs.items():
        match = base.ROUTER_RE.fullmatch(name) or base.ROUTER_BIAS_RE.fullmatch(name)
        if match:
            layer = int(match.group("layer"))
            parent_keep = parent["layers"][str(layer)]["kept_experts"]
            source_compact = {original: compact for compact, original in enumerate(parent_keep)}
            rows = [source_compact[original] for original in plan["layers"][str(layer)]["kept_experts"]]
            if name not in source_refs or not base.equal_rows(source_refs[name], out_ref, rows):
                router_failures.append(f"router mismatch {name}")
    failures.extend(router_failures)

    tid_failures = []
    dangling = 0
    for layer in range(3):
        name = f"layers.{layer}.ffn.gate.tid2eid"
        expected, shape = base.plan_tid_bytes(plan, layer)
        ref = output_refs.get(name)
        if ref is None or ref.dtype != "I64" or ref.shape != shape or ref.nbytes != len(expected):
            tid_failures.append(f"tid2eid shape/dtype mismatch {name}")
            continue
        actual = b"".join(ref.chunks())
        if actual != expected:
            tid_failures.append(f"tid2eid bytes mismatch {name}")
        import numpy as np
        table = np.frombuffer(actual, dtype="<i8").reshape(shape)
        dangling += int(np.count_nonzero((table < 0) | (table >= TARGET_K)))
        duplicate_rows = int(np.count_nonzero(np.any(np.diff(np.sort(table, axis=1), axis=1) == 0, axis=1)))
        if duplicate_rows:
            tid_failures.append(f"tid2eid duplicate rows {name}: {duplicate_rows}")
        if np.unique(table).size != TARGET_K:
            tid_failures.append(f"tid2eid coverage mismatch {name}")
    if dangling:
        tid_failures.append(f"dangling expert IDs: {dangling}")
    failures.extend(tid_failures)

    untouched_failures = []
    expert_output_names = {name for name in output_names if base.EXPERT_RE.fullmatch(name)}
    tids = {f"layers.{layer}.ffn.gate.tid2eid" for layer in range(3)}
    for name in sorted(output_names - expert_output_names - tids):
        if base.ROUTER_RE.fullmatch(name) or base.ROUTER_BIAS_RE.fullmatch(name):
            continue
        if name not in source_refs or not base.equal_bytes(source_refs[name], output_refs[name]):
            untouched_failures.append(f"untouched tensor mismatch {name}")
    failures.extend(untouched_failures)

    summary = {
        "layers": "PASS" if len(layer_results) == EXPECTED_LAYERS and not any(x["failures"] for x in layer_results) else "FAIL",
        "router": "PASS" if not router_failures else "FAIL",
        "experts": "PASS" if not any(x["failures"] for x in layer_results) else "FAIL",
        "scales": "PASS" if not any(".scale" in failure for failure in failures) else "FAIL",
        "shared_experts": "PASS" if not any("shared_experts" in failure for failure in untouched_failures) else "FAIL",
        "tid2eid": "PASS" if not tid_failures else "FAIL",
        "heretic_overlay": "PASS" if not any("attn.wo_b" in failure for failure in untouched_failures) else "FAIL",
        "mtp_dspark_absent": "PASS" if not any(name.startswith(base.MTP_PREFIX) for name in output_names) else "FAIL",
        "dangling_expert_ids": "PASS" if not dangling else "FAIL",
    }
    return {
        "schema": "heretic-v2-reap96-post-prune-v1",
        "plan": {"file_sha256": plan["_file_sha256"], "logical_sha256": plan.get("logical_sha256")},
        "parent_plan": {"file_sha256": parent["_file_sha256"], "logical_sha256": parent.get("logical_sha256")},
        "source_manifest_sha256": source_manifest["manifest_sha256"],
        "output_manifest_sha256": output_manifest["manifest_sha256"],
        "source_tensor_count": len(source_names),
        "output_tensor_count": len(output_names),
        "expected_output_tensor_count": len(expected_names),
        "summary": summary,
        "layer_results": layer_results,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--parent-plan", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = verify(args.source, args.output, args.plan, args.parent_plan, args.source_manifest, args.output_manifest)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "failures": len(report["failures"]), "report": str(args.report.resolve())}, indent=2))
    return 0 if not report["failures"] and all(value == "PASS" for value in report["summary"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
