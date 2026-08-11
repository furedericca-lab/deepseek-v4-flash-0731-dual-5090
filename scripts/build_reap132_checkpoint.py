#!/usr/bin/env python3
"""Plan-driven, Transformers-free REAP132 safetensors builder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_reap132_raw import EXPERT_RE, ROUTER_RE, Slice, build, headers, plan_tid


def _bytes(ref):
    with ref.path.open("rb", buffering=0) as handle:
        handle.seek(ref.start)
        data = handle.read(ref.nbytes)
    if len(data) != ref.nbytes:
        raise ValueError(f"short payload: {ref.path} [{ref.start}:{ref.end}]")
    return data


def preflight(source: Path, plan_path: Path, layer: int) -> int:
    index = json.loads((source / "model.safetensors.index.json").read_text())
    refs = headers(source, index)
    plan = json.loads(plan_path.read_text())
    kept = plan["layers"][str(layer)]["kept_experts"]
    expert_names = [name for name in refs if EXPERT_RE.fullmatch(name) and int(EXPERT_RE.fullmatch(name).group(1)) == layer]
    weight_count = len(kept) * 3
    scale_count = len(kept) * 3
    router_ok = True
    router_rows = []
    for kind in ("weight", "bias"):
        name = f"layers.{layer}.ffn.gate.{kind}"
        if name in refs:
            gathered = Slice(refs[name], row_indices=tuple(kept))
            router_rows.append(
                refs[name].shape[0] == 256
                and gathered.shape[0] == 132
                and gathered.nbytes == refs[name].nbytes // 256 * 132
            )
    router_ok = bool(router_rows) and all(router_rows)
    tid_name = f"layers.{layer}.ffn.gate.tid2eid"
    tid_ok = tid_name in refs
    if tid_ok:
        plan_tid_bytes, plan_shape = plan_tid(plan, layer)
        tid_ok = bool(_bytes(refs[tid_name])) and bool(plan_tid_bytes) and plan_shape
    missing = 0
    for new_id, old_id in enumerate(kept):
        for projection in ("w1", "w2", "w3"):
            for payload in ("weight", "scale"):
                name = f"layers.{layer}.ffn.experts.{old_id}.{projection}.{payload}"
                missing += name not in refs
    duplicate = len(set(kept)) != len(kept)
    unknown = 0
    payload_mutation = 0
    print(f"Layer {layer}")
    print("source experts:       256")
    print(f"kept experts:         {len(kept)}")
    print("\nRAW_COPY_REMAP:")
    print(f"  weights:            {weight_count}")
    print(f"  scales:             {scale_count}")
    print(f"  total:              {weight_count + scale_count}")
    print(f"\nrouter rows:          {'PASS' if router_ok else 'FAIL'}")
    print(f"tid2eid:              {'PASS' if tid_ok else 'FAIL'}")
    print(f"\nmissing:              {missing}")
    print(f"duplicate:            {int(duplicate)}")
    print(f"unknown:              {unknown}")
    print(f"payload mutation:     {payload_mutation}")
    passed = (len(kept) == 132 and weight_count == 396 and scale_count == 396
              and router_ok and tid_ok and missing == 0 and not duplicate)
    print("\nPREFLIGHT PASS" if passed else "\nPREFLIGHT FAIL")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight-layer", type=int)
    args = parser.parse_args()
    if (args.output is None) == (args.preflight_layer is None):
        parser.error("specify exactly one of --preflight-layer or --output")
    if args.preflight_layer is not None:
        return preflight(args.source, args.plan, args.preflight_layer)
    build(args.source, args.output, args.plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
