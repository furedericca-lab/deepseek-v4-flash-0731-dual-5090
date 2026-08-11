import hashlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).parents[1] / "tools" / "verify_hf_checkpoint_sha256.py"
SPEC = importlib.util.spec_from_file_location("verify_hf_checkpoint_sha256", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

REVISION = "a" * 40


class FakeApi:
    def __init__(self, siblings):
        self.siblings = siblings

    def model_info(self, repo, revision, files_metadata):
        assert repo == "owner/model"
        assert revision == REVISION
        assert files_metadata is True
        return SimpleNamespace(sha=REVISION, siblings=self.siblings)


class FakeFilesystem:
    def __init__(self, files):
        self.files = files

    def open(self, path, mode, revision):
        assert mode == "rb"
        assert revision == REVISION
        return io.BytesIO(self.files[path])


def git_blob_sha1(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def test_verifies_lfs_and_git_files_and_ignores_control_paths(tmp_path):
    lfs_data = b"large tensor"
    git_data = b'{"model":"test"}\n'
    (tmp_path / "model.safetensors").write_bytes(lfs_data)
    (tmp_path / "config.json").write_bytes(git_data)
    (tmp_path / ".checkpoint-source.json").write_text("{}\n")
    (tmp_path / ".hfd").mkdir()
    (tmp_path / ".hfd" / "manifest").write_text("transfer metadata")
    siblings = [
        SimpleNamespace(
            rfilename="model.safetensors",
            size=len(lfs_data),
            lfs={"sha256": hashlib.sha256(lfs_data).hexdigest()},
            blob_id=None,
        ),
        SimpleNamespace(
            rfilename="config.json",
            size=len(git_data),
            lfs=None,
            blob_id=git_blob_sha1(git_data),
        ),
    ]

    result = MODULE.verify_checkpoint(
        tmp_path,
        "owner/model",
        REVISION,
        api=FakeApi(siblings),
        filesystem=FakeFilesystem({"owner/model/config.json": git_data}),
        progress=None,
    )

    assert result["paths_match"] is True
    assert result["matched_count"] == 2
    assert result["mismatched_count"] == 0
    assert result["lfs_count"] == 1
    assert result["git_count"] == 1


def test_reports_hash_mismatch_and_extra_local_file(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"wrong")
    (tmp_path / "extra.txt").write_text("extra")
    siblings = [
        SimpleNamespace(
            rfilename="model.safetensors",
            size=5,
            lfs={"sha256": hashlib.sha256(b"right").hexdigest()},
            blob_id=None,
        )
    ]

    result = MODULE.verify_checkpoint(
        tmp_path,
        "owner/model",
        REVISION,
        api=FakeApi(siblings),
        filesystem=FakeFilesystem({}),
        progress=None,
    )

    assert result["paths_match"] is False
    assert result["mismatched_count"] == 1
    assert result["extra_local_paths"] == ["extra.txt"]
    assert [entry["path"] for entry in result["mismatches"]] == [
        "model.safetensors"
    ]


def test_rejects_non_commit_revision(tmp_path):
    with pytest.raises(ValueError, match="40-character commit SHA"):
        MODULE.verify_checkpoint(
            tmp_path,
            "owner/model",
            "main",
            api=FakeApi([]),
            filesystem=FakeFilesystem({}),
            progress=None,
        )
