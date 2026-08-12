import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "checkpoint_content_manifest.py"
SPEC = importlib.util.spec_from_file_location("checkpoint_content_manifest", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MANIFEST_NAME = MODULE.MANIFEST_NAME
build_manifest = MODULE.build_manifest
canonical_bytes = MODULE.canonical_bytes
check_manifest = MODULE.check_manifest
write_manifest = MODULE.write_manifest


def test_manifest_is_canonical_stable_and_excludes_control_files(tmp_path):
    (tmp_path / "z.bin").write_bytes(b"z")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "data.bin").write_bytes(b"data")
    (tmp_path / ".checkpoint-source.json").write_text('{"revision":"abc"}\n')
    (tmp_path / ".cache").mkdir()
    (tmp_path / ".cache" / "download.lock").write_bytes(b"")
    (tmp_path / ".hfd").mkdir()
    (tmp_path / ".hfd" / "manifest").write_text("local transfer metadata")

    first = write_manifest(tmp_path, "source")
    second = write_manifest(tmp_path, "source")

    assert first == second
    assert [entry["path"] for entry in first["files"]] == [
        ".checkpoint-source.json",
        "a/data.bin",
        "z.bin",
    ]
    payload = {key: value for key, value in first.items() if key != "manifest_sha256"}
    assert first["manifest_sha256"] == hashlib.sha256(canonical_bytes(payload)).hexdigest()
    assert check_manifest(tmp_path, "source") == first


def test_manifest_detects_content_drift(tmp_path):
    artifact = tmp_path / "model.safetensors"
    artifact.write_bytes(b"before")
    write_manifest(tmp_path, "source")
    artifact.write_bytes(b"after")

    with pytest.raises(ValueError, match="does not match"):
        check_manifest(tmp_path, "source")


@pytest.mark.parametrize("suffix", [".aria2", ".incomplete", ".lock", ".part", ".tmp"])
def test_manifest_rejects_partial_files(tmp_path, suffix):
    (tmp_path / f"model.safetensors{suffix}").write_bytes(b"partial")

    with pytest.raises(ValueError, match="partial or temporary"):
        build_manifest(tmp_path, "source")


def test_manifest_excludes_itself(tmp_path):
    (tmp_path / "config.json").write_text("{}\n")
    (tmp_path / MANIFEST_NAME).write_text(json.dumps({"stale": True}))
    (tmp_path / "post-prune-verification.json").write_text(json.dumps({"failures": []}))

    manifest = build_manifest(tmp_path, "source")

    assert [entry["path"] for entry in manifest["files"]] == ["config.json"]


def test_manifest_stays_valid_after_verification_sidecar_is_written(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"payload")
    manifest = write_manifest(tmp_path, "native-reap132")
    (tmp_path / "post-prune-verification.json").write_text(json.dumps({"failures": []}))

    assert check_manifest(tmp_path, "native-reap132") == manifest
