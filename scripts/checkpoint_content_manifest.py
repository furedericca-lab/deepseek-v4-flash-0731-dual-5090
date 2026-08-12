#!/usr/bin/env python3
"""Create and verify canonical content manifests for checkpoint directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import sys
from pathlib import Path


SCHEMA = "checkpoint-content-manifest-v1"
MANIFEST_NAME = "checkpoint-content-manifest.json"
SIDECAR_EVIDENCE = frozenset({"post-prune-verification.json"})
EXCLUDED_DIRECTORIES = frozenset({".cache", ".git", ".hfd", "__pycache__"})
PARTIAL_SUFFIXES = (".aria2", ".incomplete", ".lock", ".part", ".tmp")
BLOCK = 8 * 1024 * 1024
DIRECT_ALIGN = 4096


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
    try:
        size = os.fstat(fd).st_size
        position = 0
        while position < size:
            wanted = min(BLOCK, size - position)
            aligned_size = ((wanted + DIRECT_ALIGN - 1) // DIRECT_ALIGN) * DIRECT_ALIGN
            buffer = mmap.mmap(-1, aligned_size)
            try:
                view = memoryview(buffer)
                read = os.preadv(fd, [view], position)
                if read < wanted:
                    view.release()
                    raise ValueError(f"short O_DIRECT file payload: {path}")
                digest.update(view[:wanted])
                view.release()
            finally:
                buffer.close()
            position += wanted
    finally:
        os.close(fd)
    return digest.hexdigest()


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def artifact_files(checkpoint: Path) -> list[Path]:
    files: list[Path] = []
    for path in checkpoint.rglob("*"):
        relative = path.relative_to(checkpoint)
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"checkpoint contains unsupported symlink: {relative.as_posix()}")
        if not path.is_file() or relative.as_posix() in {MANIFEST_NAME, *SIDECAR_EVIDENCE}:
            continue
        if path.name.endswith(PARTIAL_SUFFIXES):
            raise ValueError(f"checkpoint contains partial or temporary file: {relative.as_posix()}")
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(checkpoint).as_posix())


def build_manifest(checkpoint: Path, artifact_role: str) -> dict:
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_dir():
        raise ValueError(f"checkpoint directory does not exist: {checkpoint}")
    entries = []
    for path in artifact_files(checkpoint):
        entries.append(
            {
                "path": path.relative_to(checkpoint).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = {"schema": SCHEMA, "artifact_role": artifact_role, "files": entries}
    return {**payload, "manifest_sha256": hashlib.sha256(canonical_bytes(payload)).hexdigest()}


def write_manifest(checkpoint: Path, artifact_role: str) -> dict:
    manifest = build_manifest(checkpoint, artifact_role)
    destination = checkpoint.resolve() / MANIFEST_NAME
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return manifest


def check_manifest(checkpoint: Path, artifact_role: str) -> dict:
    destination = checkpoint.resolve() / MANIFEST_NAME
    try:
        recorded = json.loads(destination.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"checkpoint content manifest does not exist: {destination}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read checkpoint content manifest {destination}: {exc}") from exc
    computed = build_manifest(checkpoint, artifact_role)
    if recorded != computed:
        raise ValueError("checkpoint content manifest does not match current checkpoint files")
    return computed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint_dir", type=Path)
    parser.add_argument(
        "--artifact-role", required=True, choices=("source", "native-reap132", "native-reap96")
    )
    parser.add_argument(
        "--check", action="store_true", help="verify the existing manifest without rewriting it"
    )
    args = parser.parse_args()

    if args.check:
        manifest = check_manifest(args.checkpoint_dir, args.artifact_role)
        action = "verified"
    else:
        manifest = write_manifest(args.checkpoint_dir, args.artifact_role)
        action = "wrote"
    destination = args.checkpoint_dir.resolve() / MANIFEST_NAME
    print(f"{action} {destination}")
    print(f"files: {len(manifest['files'])}")
    print(f"manifest_sha256: {manifest['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
