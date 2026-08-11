#!/usr/bin/env python3
"""Verify checkpoint metadata against Hugging Face and write its source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from huggingface_hub import HfApi, HfFileSystem
from moe_compress.checkpoint_source import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_INDEX_FILE,
    MANIFEST_NAME,
    sha256_file,
)


COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind a local checkpoint's config/index to an immutable HF commit."
    )
    parser.add_argument("checkpoint_dir", type=Path)
    parser.add_argument("--repo", required=True, help="Hugging Face model repository")
    parser.add_argument("--revision", required=True, help="40-character commit SHA")
    parser.add_argument("--config-file", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--index-file", default=DEFAULT_INDEX_FILE)
    parser.add_argument(
        "--token",
        default=os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"),
    )
    args = parser.parse_args()

    if not COMMIT_SHA.fullmatch(args.revision):
        parser.error("--revision must be a lowercase 40-character commit SHA")
    checkpoint = args.checkpoint_dir.resolve()
    if not checkpoint.is_dir():
        parser.error(f"checkpoint directory does not exist: {checkpoint}")
    for filename in (args.config_file, args.index_file):
        if Path(filename).name != filename:
            parser.error("metadata file names must refer to checkpoint-root files")

    resolved = HfApi(token=args.token).model_info(args.repo, revision=args.revision).sha
    if resolved != args.revision:
        raise RuntimeError(
            f"Hugging Face resolved {args.repo}@{args.revision} to unexpected SHA {resolved}"
        )

    fs = HfFileSystem(token=args.token)
    manifest = {"repo": args.repo, "revision": resolved}
    for filename, hash_key, file_key in (
        (args.config_file, "config_sha256", "config_file"),
        (args.index_file, "index_sha256", "index_file"),
    ):
        local_path = checkpoint / filename
        local_hash = sha256_file(local_path)
        with fs.open(f"{args.repo}/{filename}", "rb", revision=resolved) as handle:
            remote_hash = hashlib.sha256(handle.read()).hexdigest()
        if local_hash != remote_hash:
            raise RuntimeError(
                f"{filename} does not match {args.repo}@{resolved}: "
                f"local {local_hash}, remote {remote_hash}"
            )
        manifest[file_key] = filename
        manifest[hash_key] = local_hash

    destination = checkpoint / MANIFEST_NAME
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    print(f"wrote {destination}")
    print(f"revision: {resolved}")
    print(f"config_sha256: {manifest['config_sha256']}")
    print(f"index_sha256: {manifest['index_sha256']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
