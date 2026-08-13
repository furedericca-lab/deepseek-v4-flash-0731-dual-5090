#!/usr/bin/env python3
"""Verify every routed MXFP4 byte in a K132 GGUF against accepted native tensors."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_mxfp4_gguf_repack as base


LAYERS = 43
EXPERTS = 132


def repack_expert(weight_bytes: bytes, scale_bytes: bytes, rows: int, packed_cols: int) -> bytes:
    blocks = packed_cols // 16
    weight = np.frombuffer(weight_bytes, dtype=np.uint8).reshape(rows, blocks, 16)
    scales = np.frombuffer(scale_bytes, dtype=np.uint8).reshape(rows, blocks)
    values = np.stack((weight & 0x0F, weight >> 4), axis=-1).reshape(rows, blocks, 32)
    output = np.empty((rows, blocks, 17), dtype=np.uint8)
    output[:, :, 0] = scales
    output[:, :, 1:] = values[:, :, :16] | (values[:, :, 16:] << 4)
    return output.tobytes()


def verify(source_root: Path, gguf_path: Path) -> dict[str, object]:
    source = base.source_tensors(source_root)
    gguf = base.gguf_expert_tensors(gguf_path)
    failures: list[str] = []
    tensor_records: list[dict[str, object]] = []
    expert_comparisons = 0
    compared_bytes = 0

    expected_names = {
        f"blk.{layer}.{gguf_projection}.weight"
        for layer in range(LAYERS)
        for gguf_projection in base.PROJECTIONS.values()
    }
    if set(gguf) != expected_names:
        failures.append(
            f"routed tensor namespace mismatch: missing={sorted(expected_names - set(gguf))}, "
            f"extra={sorted(set(gguf) - expected_names)}"
        )

    for layer in range(LAYERS):
        layer_experts = base.expert_ids_for_layer(source, layer)
        if layer_experts != list(range(EXPERTS)):
            failures.append(f"layer {layer}: expected {EXPERTS} contiguous experts")
            continue
        for projection, gguf_projection in base.PROJECTIONS.items():
            gguf_name = f"blk.{layer}.{gguf_projection}.weight"
            target = gguf.get(gguf_name)
            if target is None:
                continue
            target_digest = hashlib.sha256()
            expected_digest = hashlib.sha256()
            tensor_compared = 0
            for expert in layer_experts:
                weight_name = f"layers.{layer}.ffn.experts.{expert}.{projection}.weight"
                scale_name = f"layers.{layer}.ffn.experts.{expert}.{projection}.scale"
                weight = source.get(weight_name)
                scale = source.get(scale_name)
                if weight is None or scale is None:
                    failures.append(f"missing native tensor pair: {weight_name}")
                    continue
                rows, packed_cols = weight.shape
                scale_rows, blocks = scale.shape
                logical_cols = packed_cols * 2
                if scale_rows != rows or blocks != packed_cols // 16:
                    failures.append(f"invalid native shapes: {weight_name}={weight.shape}, {scale_name}={scale.shape}")
                    continue
                if target.shape != (EXPERTS, rows, logical_cols):
                    failures.append(f"unexpected GGUF shape: {gguf_name}={target.shape}")
                    continue

                native_weight = base.direct_read(weight.data, 0, weight.data.size)
                native_scale = base.direct_read(scale.data, 0, scale.data.size)
                expected = repack_expert(native_weight, native_scale, rows, packed_cols)
                target_relative = expert * len(expected)
                actual = base.direct_read(target.data, target_relative, len(expected))
                expert_comparisons += 1
                compared_bytes += len(actual)
                tensor_compared += len(actual)
                expected_digest.update(expected)
                target_digest.update(actual)
                if actual != expected:
                    first = next(index for index, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1])
                    failures.append(
                        f"payload mismatch: {gguf_name} expert={expert} byte={first} "
                        f"actual={actual[first]:02x} expected={expected[first]:02x}"
                    )
            tensor_records.append({
                "tensor": gguf_name,
                "expert_comparisons": len(layer_experts),
                "compared_bytes": tensor_compared,
                "expected_sha256": expected_digest.hexdigest(),
                "actual_sha256": target_digest.hexdigest(),
                "match": expected_digest.digest() == target_digest.digest(),
            })

    return {
        "schema": "reap132-mxfp4-full-provenance-v1",
        "source": str(source_root),
        "gguf": str(gguf_path),
        "coverage": {
            "layers": LAYERS,
            "routed_tensors": len(tensor_records),
            "experts_per_layer": EXPERTS,
            "expert_comparisons": expert_comparisons,
            "compared_bytes": compared_bytes,
            "all_rows_and_blocks": True,
        },
        "tensors": tensor_records,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--gguf", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.source, args.gguf)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "coverage": report["coverage"],
        "failure_count": len(report["failures"]),
    }, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
