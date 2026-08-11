#!/usr/bin/env python3
"""Verify every local checkpoint file against an immutable Hugging Face revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import BinaryIO, Callable

from huggingface_hub import HfApi, HfFileSystem


SCHEMA = "hf-fixed-revision-local-sha256-verification-v1"
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
EXCLUDED_DIRECTORIES = frozenset({".cache", ".git", ".hfd", "__pycache__"})
EXCLUDED_FILES = frozenset(
    {
        ".checkpoint-source.json",
        "checkpoint-content-manifest.json",
        "hf-sha256-verification.json",
    }
)


def print_progress(message: str) -> None:
    print(message, flush=True)


def hash_stream(handle: BinaryIO, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hash_stream(handle)


def git_blob_sha1(path: Path, size: int) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {size}\0".encode())
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_repository_paths(checkpoint: Path) -> set[str]:
    paths: set[str] = set()
    for path in checkpoint.rglob("*"):
        relative = path.relative_to(checkpoint)
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"checkpoint contains unsupported symlink: {relative.as_posix()}")
        if path.is_file() and relative.as_posix() not in EXCLUDED_FILES:
            paths.add(relative.as_posix())
    return paths


def verify_checkpoint(
    checkpoint: Path,
    repo: str,
    revision: str,
    *,
    api: HfApi | None = None,
    filesystem: HfFileSystem | None = None,
    progress: Callable[[str], None] | None = print_progress,
) -> dict:
    if not COMMIT_SHA.fullmatch(revision):
        raise ValueError("revision must be a lowercase 40-character commit SHA")
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_dir():
        raise ValueError(f"checkpoint directory does not exist: {checkpoint}")

    started = time.monotonic()
    api = api or HfApi()
    filesystem = filesystem or HfFileSystem()
    info = api.model_info(repo, revision=revision, files_metadata=True)
    if info.sha != revision:
        raise RuntimeError(f"Hugging Face resolved {revision} to unexpected SHA {info.sha}")

    siblings = sorted(info.siblings, key=lambda sibling: sibling.rfilename)
    remote_paths = {sibling.rfilename for sibling in siblings}
    local_paths = local_repository_paths(checkpoint)
    results: list[dict] = []

    for number, sibling in enumerate(siblings, 1):
        local_path = checkpoint / sibling.rfilename
        entry = {
            "path": sibling.rfilename,
            "kind": "lfs" if sibling.lfs else "git",
            "remote_size": sibling.size,
        }
        if not local_path.is_file():
            entry.update(match=False, error="missing local file")
        else:
            entry["local_size"] = local_path.stat().st_size
            entry["local_sha256"] = sha256_file(local_path)
            if sibling.lfs:
                entry["remote_sha256"] = sibling.lfs["sha256"]
                entry["match"] = (
                    entry["local_size"] == sibling.size
                    and entry["local_sha256"] == entry["remote_sha256"]
                )
            else:
                with filesystem.open(
                    f"{repo}/{sibling.rfilename}", "rb", revision=revision
                ) as remote_handle:
                    entry["remote_sha256"] = hash_stream(remote_handle)
                entry["local_git_blob_sha1"] = git_blob_sha1(
                    local_path, entry["local_size"]
                )
                entry["remote_blob_sha1"] = sibling.blob_id
                entry["match"] = (
                    entry["local_size"] == sibling.size
                    and entry["local_sha256"] == entry["remote_sha256"]
                    and entry["local_git_blob_sha1"] == sibling.blob_id
                )
        results.append(entry)
        if progress:
            state = "PASS" if entry.get("match") else "FAIL"
            progress(
                f"[{number:02d}/{len(siblings):02d}] {state} "
                f"{entry['kind']} {sibling.rfilename}"
            )

    payload = {
        "schema": SCHEMA,
        "repo": repo,
        "revision": revision,
        "resolved_revision": info.sha,
        "checkpoint_dir": str(checkpoint),
        "remote_file_count": len(remote_paths),
        "local_repository_file_count": len(local_paths),
        "paths_match": local_paths == remote_paths,
        "lfs_count": sum(result["kind"] == "lfs" for result in results),
        "git_count": sum(result["kind"] == "git" for result in results),
        "matched_count": sum(bool(result.get("match")) for result in results),
        "mismatched_count": sum(not bool(result.get("match")) for result in results),
        "extra_local_paths": sorted(local_paths - remote_paths),
        "missing_local_paths": sorted(remote_paths - local_paths),
        "mismatches": [result for result in results if not result.get("match")],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "files": results,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint_dir", type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, help="write detailed JSON evidence")
    args = parser.parse_args()

    payload = verify_checkpoint(args.checkpoint_dir, args.repo, args.revision)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"evidence: {args.output.resolve()}")

    summary_keys = (
        "resolved_revision",
        "remote_file_count",
        "local_repository_file_count",
        "paths_match",
        "lfs_count",
        "git_count",
        "matched_count",
        "mismatched_count",
        "elapsed_seconds",
    )
    print(json.dumps({key: payload[key] for key in summary_keys}, indent=2))
    if not payload["paths_match"] or payload["mismatches"]:
        print(
            json.dumps(
                {
                    "extra_local_paths": payload["extra_local_paths"],
                    "missing_local_paths": payload["missing_local_paths"],
                    "mismatches": payload["mismatches"],
                },
                indent=2,
            )
        )
    return 0 if payload["paths_match"] and payload["mismatched_count"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
