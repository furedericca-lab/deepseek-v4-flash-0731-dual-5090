#!/usr/bin/env python3
"""
Extract the exact original-expert survivor map used by a puwaer REAP checkpoint
without downloading either full model.

The script exploits a property of puwaer's REAP implementation: pruning is a
bit-exact slice along the expert axis. It compares router tensors from the base
256-expert checkpoint and the final 132-expert checkpoint through
HfFileSystem seek/read operations, recovers new_expert_id -> original_expert_id
for all 43 layers, and embeds the final hash-routing tid2eid tables for layers
0..2.

Default output: squanchyzx-puwaer-reap132-mask.json

Requirements:
    uv sync

Typical use:
    python extract_puwaer_reap132_mask.py

Optional Hugging Face token (normally not required for these public repos):
    export HF_TOKEN=hf_...

Safety: reads are bounded to 256 MiB per request and use Hugging Face's
official filesystem/Xet transport rather than downloading complete shards.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import struct
import sys
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from huggingface_hub import HfApi, HfFileSystem
except ImportError as exc:  # pragma: no cover - exercised by CLI users
    raise SystemExit("Install dependencies with: uv sync") from exc

DEFAULT_BASE = "squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8"
DEFAULT_PRUNED = "puwaer/DeepSeek-V4-Flash-0731-reap-150b"
DEFAULT_BASE_REVISION = "e7efd043c5e072da4d40f0f98ade554c5713bad9"
DEFAULT_PRUNED_REVISION = "868fa38e2f2964699ad065dc8d9382c136cc60b8"
DEFAULT_OUTPUT = "squanchyzx-puwaer-reap132-mask.json"


class RangeNotSupported(RuntimeError):
    pass


class HFError(RuntimeError):
    pass


@dataclass(frozen=True)
class TensorInfo:
    dtype: str
    shape: Tuple[int, ...]
    data_offsets: Tuple[int, int]


class HFRangeSafetensors:
    MAX_RANGE_BYTES = 256 * 1024 * 1024

    def __init__(self, repo: str, revision: str = "main", token: Optional[str] = None,
                 retries: int = 4):
        self.repo = repo
        self.retries = retries
        self.api = HfApi(token=token)
        # Resolve the requested ref before reading any bytes. Every subsequent
        # read uses this immutable commit so a moving branch cannot mix files.
        self.requested_revision = revision
        self.revision = self._resolve_sha(revision)
        if not self.revision:
            raise HFError(
                f"could not resolve an immutable Hugging Face revision for {repo}@{revision}"
            )
        self.fs = HfFileSystem(token=token)
        self._header_cache: Dict[str, Tuple[int, Dict[str, TensorInfo]]] = {}
        self._index = self._get_json("model.safetensors.index.json")
        self.weight_map: Dict[str, str] = self._index["weight_map"]
        self.config = self._get_json("config.json")
        self.resolved_sha = self.revision
        self.bytes_downloaded = 0
        self.range_requests = 0

    def _url(self, filename: str) -> str:
        return f"{self.repo}/{filename}"

    def _resolve_sha(self, revision: str) -> Optional[str]:
        try:
            return self.api.model_info(self.repo, revision=revision).sha
        except Exception:
            return None

    def _get_json(self, filename: str) -> dict:
        last = None
        for i in range(self.retries):
            try:
                with self.fs.open(self._url(filename), "rb", revision=self.revision) as f:
                    return json.load(f)
            except Exception as e:
                last = e
                if i + 1 < self.retries:
                    time.sleep(1.5 * (i + 1))
        raise HFError(f"failed to fetch {self.repo}/{filename}@{self.revision}: {last}")

    def _range(self, filename: str, start: int, end: int) -> bytes:
        if end < start:
            return b""
        last = None
        for i in range(self.retries):
            stream = None
            try:
                expected = end - start + 1
                if expected > self.MAX_RANGE_BYTES:
                    raise HFError(
                        f"requested Range is too large ({expected} bytes) for {filename}"
                    )
                # Avoid fsspec's default multi-megabyte read-ahead. This
                # extractor seeks to bounded safetensors ranges; caching must
                # not turn those into unrelated Xet payload requests.
                with self.fs.open(
                    self._url(filename), "rb", revision=self.revision,
                    block_size=1, cache_type="none",
                ) as stream:
                    stream.seek(start)
                    data = stream.read(expected)
                if len(data) != expected:
                    raise HFError(
                        f"short Range read for {filename}: expected {expected}, got {len(data)}"
                    )
                self.bytes_downloaded += len(data)
                self.range_requests += 1
                return data
            except RangeNotSupported:
                raise
            except Exception as e:
                last = e
                if stream is not None:
                    stream.close()
                if i + 1 < self.retries:
                    time.sleep(1.5 * (i + 1))
        raise HFError(f"failed Range request for {filename}: {last}")

    def _load_header(self, shard: str) -> Tuple[int, Dict[str, TensorInfo]]:
        cached = self._header_cache.get(shard)
        if cached is not None:
            return cached
        prefix = self._range(shard, 0, 7)
        header_len = struct.unpack("<Q", prefix)[0]
        # Defensive bound. A shard header can be MBs, but should not be absurdly huge.
        if header_len <= 2 or header_len > 256 * 1024 * 1024:
            raise HFError(f"implausible safetensors header length {header_len} in {shard}")
        raw = self._range(shard, 8, 8 + header_len - 1)
        try:
            obj = json.loads(raw.decode("utf-8").rstrip(" \t\r\n\0"))
        except Exception as e:
            raise HFError(f"cannot parse safetensors header for {shard}: {e}") from e
        tensors: Dict[str, TensorInfo] = {}
        for name, meta in obj.items():
            if name == "__metadata__":
                continue
            tensors[name] = TensorInfo(
                dtype=str(meta["dtype"]),
                shape=tuple(int(x) for x in meta["shape"]),
                data_offsets=(int(meta["data_offsets"][0]), int(meta["data_offsets"][1])),
            )
        out = (header_len, tensors)
        self._header_cache[shard] = out
        return out

    def tensor_info(self, name: str) -> TensorInfo:
        shard = self.weight_map.get(name)
        if shard is None:
            raise KeyError(f"tensor not found in {self.repo}: {name}")
        _, tensors = self._load_header(shard)
        if name not in tensors:
            raise KeyError(f"tensor listed in index but absent from shard header: {name} -> {shard}")
        return tensors[name]

    def tensor_bytes(self, name: str) -> Tuple[TensorInfo, bytes]:
        shard = self.weight_map.get(name)
        if shard is None:
            raise KeyError(f"tensor not found in {self.repo}: {name}")
        header_len, tensors = self._load_header(shard)
        info = tensors[name]
        data_base = 8 + header_len
        start = data_base + info.data_offsets[0]
        end = data_base + info.data_offsets[1] - 1
        return info, self._range(shard, start, end)


def axis0_chunks(info: TensorInfo, raw: bytes) -> List[bytes]:
    if not info.shape or info.shape[0] <= 0:
        raise ValueError(f"tensor does not have a usable axis 0: shape={info.shape}")
    n = info.shape[0]
    if len(raw) % n != 0:
        raise ValueError(f"tensor byte length {len(raw)} not divisible by axis0 {n}")
    stride = len(raw) // n
    return [raw[i * stride:(i + 1) * stride] for i in range(n)]


def exact_row_map(base_info: TensorInfo, base_raw: bytes,
                  pruned_info: TensorInfo, pruned_raw: bytes) -> List[int]:
    base_rows = axis0_chunks(base_info, base_raw)
    pruned_rows = axis0_chunks(pruned_info, pruned_raw)
    if tuple(base_info.shape[1:]) != tuple(pruned_info.shape[1:]):
        raise ValueError(
            f"router row shapes differ: base={base_info.shape}, pruned={pruned_info.shape}"
        )
    if base_info.dtype != pruned_info.dtype:
        raise ValueError(f"router dtypes differ: {base_info.dtype} vs {pruned_info.dtype}")

    by_hash: Dict[bytes, List[int]] = {}
    for i, row in enumerate(base_rows):
        h = hashlib.sha256(row).digest()
        by_hash.setdefault(h, []).append(i)

    mapping: List[int] = []
    used = set()
    for new_id, row in enumerate(pruned_rows):
        candidates = by_hash.get(hashlib.sha256(row).digest(), [])
        exact = [i for i in candidates if base_rows[i] == row and i not in used]
        if len(exact) != 1:
            raise ValueError(
                f"cannot uniquely match pruned router row {new_id}: candidates={exact}"
            )
        old_id = exact[0]
        mapping.append(old_id)
        used.add(old_id)

    if mapping != sorted(mapping):
        raise ValueError(
            "recovered map is not sorted ascending; expected puwaer's keep_idx slice order"
        )
    return mapping


def unique_scalar_map(base_info: TensorInfo, base_raw: bytes,
                      pruned_info: TensorInfo, pruned_raw: bytes) -> Optional[List[int]]:
    """Fast path for 1-D gate.bias. Returns None if any value is ambiguous."""
    if len(base_info.shape) != 1 or len(pruned_info.shape) != 1:
        return None
    if base_info.dtype != pruned_info.dtype:
        return None
    base_vals = axis0_chunks(base_info, base_raw)
    pruned_vals = axis0_chunks(pruned_info, pruned_raw)
    lookup: Dict[bytes, List[int]] = {}
    for i, v in enumerate(base_vals):
        lookup.setdefault(v, []).append(i)
    mapping: List[int] = []
    for v in pruned_vals:
        ids = lookup.get(v, [])
        if len(ids) != 1:
            return None
        mapping.append(ids[0])
    if len(set(mapping)) != len(mapping) or mapping != sorted(mapping):
        return None
    return mapping


def compressed_blob(info: TensorInfo, raw: bytes) -> dict:
    dtype_names = {
        "BOOL": "bool",
        "U8": "uint8",
        "I8": "int8",
        "I16": "int16",
        "I32": "int32",
        "I64": "int64",
        "F16": "float16",
        "BF16": "bfloat16",
        "F32": "float32",
        "F64": "float64",
    }
    try:
        dtype = dtype_names[info.dtype]
    except KeyError as exc:
        raise ValueError(f"unsupported plan tensor dtype: {info.dtype}") from exc
    packed = zlib.compress(raw, level=9)
    return {
        "dtype": dtype,
        "shape": list(info.shape),
        "encoding": "zlib+base64",
        "raw_nbytes": len(raw),
        "compressed_nbytes": len(packed),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(packed).decode("ascii"),
    }


def cfg_int(cfg: dict, key: str, fallback: Optional[int] = None) -> Optional[int]:
    v = cfg.get(key, fallback)
    try:
        return int(v) if v is not None else None
    except Exception:
        return fallback


def recover_layer_map(base: HFRangeSafetensors, pruned: HFRangeSafetensors,
                      layer: int, hash_layers: int) -> Tuple[List[int], str]:
    bias_name = f"layers.{layer}.ffn.gate.bias"
    weight_name = f"layers.{layer}.ffn.gate.weight"

    # For non-hash layers, gate.bias is only 256/132 scalars and was sliced
    # by the same keep_idx. Use it if every value maps uniquely.
    if layer >= hash_layers and bias_name in base.weight_map and bias_name in pruned.weight_map:
        bi, br = base.tensor_bytes(bias_name)
        pi, pr = pruned.tensor_bytes(bias_name)
        m = unique_scalar_map(bi, br, pi, pr)
        if m is not None:
            return m, "gate.bias-exact"

    # Universal exact fallback: router rows are bit-exact direct slices.
    bi, br = base.tensor_bytes(weight_name)
    pi, pr = pruned.tensor_bytes(weight_name)
    return exact_row_map(bi, br, pi, pr), "gate.weight-row-sha256-exact"


def fragment_path(directory: Path, layer: int) -> Path:
    return directory / f"layer-{layer:02d}.json"


def validate_fragment(payload: dict, *, layer: int, base_sha: str, pruned_sha: str,
                      expected_kept: int) -> tuple[List[int], str]:
    if payload.get("schema") != "reap-expert-mask-fragment-v1":
        raise ValueError(f"layer {layer}: unsupported fragment schema")
    if payload.get("layer") != layer:
        raise ValueError(f"layer {layer}: fragment layer identity mismatch")
    if payload.get("base_revision_sha") != base_sha or payload.get("pruned_revision_sha") != pruned_sha:
        raise ValueError(f"layer {layer}: fragment revision identity mismatch")
    if payload.get("expected_kept") != expected_kept:
        raise ValueError(f"layer {layer}: fragment expert-count identity mismatch")
    kept = payload.get("kept_experts")
    evidence = payload.get("mapping_evidence")
    if not isinstance(kept, list) or not isinstance(evidence, str):
        raise ValueError(f"layer {layer}: malformed fragment payload")
    if len(kept) != expected_kept or kept != sorted(kept) or len(set(kept)) != expected_kept:
        raise ValueError(f"layer {layer}: invalid fragment survivor set")
    if any(not isinstance(expert, int) or expert < 0 or expert >= 256 for expert in kept):
        raise ValueError(f"layer {layer}: fragment expert outside 0..255")
    return kept, evidence


def write_fragment(directory: Path, *, layer: int, base_sha: str, pruned_sha: str,
                   expected_kept: int, kept: List[int], evidence: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "reap-expert-mask-fragment-v1",
        "layer": layer,
        "base_revision_sha": base_sha,
        "pruned_revision_sha": pruned_sha,
        "expected_kept": expected_kept,
        "kept_experts": kept,
        "mapping_evidence": evidence,
    }
    target = fragment_path(directory, layer)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Recover puwaer's exact DeepSeek-V4 REAP survivor mask using bounded HfFileSystem reads."
    )
    ap.add_argument("--base", default=DEFAULT_BASE, help=f"base HF repo (default: {DEFAULT_BASE})")
    ap.add_argument("--pruned", default=DEFAULT_PRUNED, help=f"pruned HF repo (default: {DEFAULT_PRUNED})")
    ap.add_argument("--base-revision", default=DEFAULT_BASE_REVISION,
                    help="Hugging Face branch or immutable commit SHA")
    ap.add_argument("--pruned-revision", default=DEFAULT_PRUNED_REVISION,
                    help="Hugging Face branch or immutable commit SHA")
    ap.add_argument("--expected-kept", type=int, default=132,
                    help="expected routed-expert count in the pruned checkpoint (default: 132)")
    ap.add_argument("--fragments-dir", type=Path,
                    help="directory for atomic per-layer recovery fragments")
    ap.add_argument("--resume", action="store_true",
                    help="reuse validated fragments from --fragments-dir")
    ap.add_argument("--start-layer", type=int, default=0,
                    help="first layer to recover, inclusive (default: 0)")
    ap.add_argument("--end-layer", type=int, default=42,
                    help="last layer to recover, inclusive (default: 42)")
    ap.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"))
    ap.add_argument("--no-tid2eid", action="store_true",
                    help="omit final hash-routing tables; smaller JSON but not a complete reproduction artifact")
    args = ap.parse_args()

    print(f"[1/4] Reading indexes/configs: {args.base}")
    base = HFRangeSafetensors(args.base, args.base_revision, args.token)
    print(f"[1/4] Reading indexes/configs: {args.pruned}")
    pruned = HFRangeSafetensors(args.pruned, args.pruned_revision, args.token)

    base_e = cfg_int(base.config, "n_routed_experts", 256)
    pruned_e = cfg_int(pruned.config, "n_routed_experts", 132)
    n_layers = cfg_int(pruned.config, "num_hidden_layers", 43)
    hash_layers = cfg_int(pruned.config, "num_hash_layers", 3)
    if base_e != 256 or pruned_e != args.expected_kept or n_layers != 43 or hash_layers != 3:
        raise HFError(
            f"unexpected model geometry: base experts={base_e}, pruned experts={pruned_e}, "
            f"layers={n_layers}, hash_layers={hash_layers}; expected kept={args.expected_kept}"
        )
    if not 0 <= args.start_layer <= args.end_layer < n_layers:
        raise ValueError(f"invalid layer range {args.start_layer}..{args.end_layer} for {n_layers} layers")
    if args.resume and args.fragments_dir is None:
        raise ValueError("--resume requires --fragments-dir")

    result = {
        "schema": "puwaer-reap-mask-v1",
        "model": "DeepSeek-V4-Flash-0731",
        "method": "REAP",
        "base_repo": args.base,
        "base_revision_requested": args.base_revision,
        "base_revision_sha": base.resolved_sha,
        "pruned_repo": args.pruned,
        "pruned_revision_requested": args.pruned_revision,
        "pruned_revision_sha": pruned.resolved_sha,
        "base_num_routed_experts": base_e,
        "kept_num_routed_experts": pruned_e,
        "num_hidden_layers": n_layers,
        "num_hash_layers": hash_layers,
        "top_k": cfg_int(pruned.config, "num_experts_per_tok", cfg_int(pruned.config, "num_experts_per_token", 6)),
        "calibration_recipe": {
            "datasets": ["c4", "math", "code"],
            "mix_ratio": [0.0, 0.3, 0.7],
            "num_samples": 3072,
            "seq_len": 512,
            "note": "Recorded from puwaer's published model card; not recomputed by this extractor."
        },
        "semantics": {
            "kept_experts": "For each layer, new expert id i corresponds to original expert id kept_experts[i].",
            "tid2eid": "For hash layers, this is puwaer's FINAL table after dropped-expert replacement, collision repair, and renumbering to 0..131."
        },
        "layers": {},
        "hash_routing": {},
    }

    print(f"[2/4] Recovering exact survivor IDs for layers {args.start_layer}..{args.end_layer}...")
    recovered_layers: Dict[int, Tuple[List[int], str]] = {}
    for layer in range(args.start_layer, args.end_layer + 1):
        existing = fragment_path(args.fragments_dir, layer) if args.fragments_dir is not None else None
        if args.resume and existing is not None and existing.exists():
            mapping, evidence = validate_fragment(
                json.loads(existing.read_text(encoding="utf-8")), layer=layer,
                base_sha=base.resolved_sha, pruned_sha=pruned.resolved_sha,
                expected_kept=pruned_e,
            )
            recovered_layers[layer] = (mapping, evidence)
            print(f"  layer {layer:02d}: resumed  [{evidence}]")
            continue
        print(f"  layer {layer:02d}: reading router tensors...", flush=True)
        mapping, evidence = recover_layer_map(base, pruned, layer, hash_layers)
        if len(mapping) != pruned_e:
            raise ValueError(f"layer {layer}: expected {pruned_e} survivors, got {len(mapping)}")
        if any(x < 0 or x >= base_e for x in mapping):
            raise ValueError(f"layer {layer}: expert id outside 0..{base_e-1}")
        if len(set(mapping)) != pruned_e:
            raise ValueError(f"layer {layer}: duplicate original expert ids")
        recovered_layers[layer] = (mapping, evidence)
        if args.fragments_dir is not None:
            write_fragment(
                args.fragments_dir, layer=layer, base_sha=base.resolved_sha,
                pruned_sha=pruned.resolved_sha, expected_kept=pruned_e,
                kept=mapping, evidence=evidence,
            )
        print(f"  layer {layer:02d}: {mapping[0]:3d}..{mapping[-1]:3d}  [{evidence}]")

    if args.fragments_dir is not None:
        for layer in range(n_layers):
            existing = fragment_path(args.fragments_dir, layer)
            if existing.exists():
                recovered_layers[layer] = validate_fragment(
                    json.loads(existing.read_text(encoding="utf-8")), layer=layer,
                    base_sha=base.resolved_sha, pruned_sha=pruned.resolved_sha,
                    expected_kept=pruned_e,
                )
    missing_layers = [layer for layer in range(n_layers) if layer not in recovered_layers]
    if missing_layers:
        print(f"[3/4] Fragment checkpoint updated; final mask withheld. Missing layers: {missing_layers}")
        return 0
    for layer in range(n_layers):
        mapping, evidence = recovered_layers[layer]
        result["layers"][str(layer)] = {"kept_experts": mapping, "mapping_evidence": evidence}

    if not args.no_tid2eid:
        print(f"[3/4] Embedding final tid2eid tables for hash layers 0..{hash_layers-1}...")
        for layer in range(hash_layers):
            name = f"layers.{layer}.ffn.gate.tid2eid"
            info, raw = pruned.tensor_bytes(name)
            blob = compressed_blob(info, raw)
            result["hash_routing"][str(layer)] = {
                "tensor_name": name,
                **blob,
            }
            print(
                f"  layer {layer}: shape={list(info.shape)} dtype={info.dtype}, "
                f"{len(raw)/1024/1024:.2f} MiB -> {blob['compressed_nbytes']/1024/1024:.2f} MiB"
            )
    else:
        print("[3/4] Skipping tid2eid (--no-tid2eid).")

    total_dl = base.bytes_downloaded + pruned.bytes_downloaded
    result["extraction"] = {
        "matching": "byte-exact; no floating-point tolerance",
        "range_requests": base.range_requests + pruned.range_requests,
        "range_bytes_downloaded": total_dl,
        "range_mib_downloaded": round(total_dl / 1024 / 1024, 3),
        "note": "Index/config HTTP bytes are not included in range_bytes_downloaded."
    }

    # Deterministic integrity hash over the important logical payload, excluding
    # the hash itself and download counters.
    logical = {
        "layers": result["layers"],
        "hash_routing": result["hash_routing"],
        "base_revision_sha": result["base_revision_sha"],
        "pruned_revision_sha": result["pruned_revision_sha"],
    }
    result["logical_sha256"] = hashlib.sha256(
        json.dumps(logical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    out = Path(args.output)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[4/4] Wrote {out} ({out.stat().st_size/1024/1024:.2f} MiB)")
    print(f"      Range data transferred: {total_dl/1024/1024:.2f} MiB")
    print(f"      logical_sha256: {result['logical_sha256']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(1)
