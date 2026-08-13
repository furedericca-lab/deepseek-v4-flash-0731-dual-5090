#!/usr/bin/env python3
"""Add the one K96-Profile-A-required entry to the puwaer K132 imatrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "llama.cpp" / "gguf-py"))
from gguf import GGUFReader, GGUFWriter  # noqa: E402


ADDED_BASE = "output_hc_fn.weight"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata(reader: GGUFReader, key: str):
    field = reader.fields.get(key)
    if field is None:
        raise ValueError(f"missing metadata: {key}")
    return field.contents()


def build(external_path: Path, supplemental_path: Path, output_path: Path) -> dict:
    external = GGUFReader(external_path)
    supplemental = GGUFReader(supplemental_path)
    external_tensors = {tensor.name: tensor for tensor in external.tensors}
    supplemental_tensors = {tensor.name: tensor for tensor in supplemental.tensors}
    external_bases = {name.removesuffix(".in_sum2").removesuffix(".counts") for name in external_tensors}
    added_names = {f"{ADDED_BASE}.in_sum2", f"{ADDED_BASE}.counts"}
    if added_names & external_tensors.keys():
        raise ValueError("external imatrix unexpectedly already contains supplemental entry")
    if len(external_bases) != 768 or len(external_tensors) != 1536:
        raise ValueError("external imatrix entry count drift")
    if not added_names <= supplemental_tensors.keys():
        raise ValueError("supplemental imatrix is missing output_hc_fn entry")
    if int(metadata(external, "imatrix.chunk_count")) != 812 or int(metadata(external, "imatrix.chunk_size")) != 512:
        raise ValueError("external imatrix metadata drift")

    temp_path = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    writer = GGUFWriter(temp_path, "imatrix")
    writer.add_type("imatrix")
    datasets = list(metadata(external, "imatrix.datasets"))
    datasets.append(f"supplement:{supplemental_path.name}:{ADDED_BASE}")
    writer.add_array("imatrix.datasets", datasets)
    writer.add_uint32("imatrix.chunk_count", 812)
    writer.add_uint32("imatrix.chunk_size", 512)
    for name in sorted(external_tensors):
        writer.add_tensor(name, np.asarray(external_tensors[name].data, dtype=np.float32).copy())
    for name in sorted(added_names):
        writer.add_tensor(name, np.asarray(supplemental_tensors[name].data, dtype=np.float32).copy())
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file(progress=False)
    writer.close()
    os.replace(temp_path, output_path)
    output_path.chmod(0o444)

    result = {
        "schema": "heretic-reap132-puwaer-q2-compat-imatrix-v1",
        "status": "PASS",
        "output": {"path": str(output_path), "size": output_path.stat().st_size, "sha256": sha256(output_path), "mode": "0444", "entries": 769, "chunks": 812},
        "external": {"path": str(external_path), "size": external_path.stat().st_size, "sha256": sha256(external_path), "entries_copied": len(external_bases)},
        "supplemental": {"path": str(supplemental_path), "size": supplemental_path.stat().st_size, "sha256": sha256(supplemental_path), "entry_copied": ADDED_BASE},
        "overlapping_entries_replaced": 0,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external", type=Path, required=True)
    parser.add_argument("--supplemental", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.external.resolve(), args.supplemental.resolve(), args.output.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
