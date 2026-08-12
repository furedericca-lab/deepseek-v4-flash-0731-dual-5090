import base64
import hashlib
import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_reap132_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("verify_reap132_checkpoint", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_safetensors(path, tensors):
    header = {}
    offset = 0
    payload = bytearray()
    for name, (dtype, shape, data) in tensors.items():
        header[name] = {"dtype": dtype, "shape": list(shape), "data_offsets": [offset, offset + len(data)]}
        payload.extend(data)
        offset += len(data)
    encoded = json.dumps(header, separators=(",", ":")).encode()
    path.write_bytes(struct.pack("<Q", len(encoded)) + encoded + payload)


def write_manifest(path):
    payload = {"schema": "test", "artifact_role": "native-reap132", "files": []}
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_fixture(tmp_path, *, mutate=None, retain_mtp=False):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    source_tensors = {}
    output_tensors = {}
    for layer in range(43):
        for expert in (0, 1):
            for projection in ("w1", "w2", "w3"):
                for payload in ("weight", "scale"):
                    name = f"layers.{layer}.ffn.experts.{expert}.{projection}.{payload}"
                    data = bytes((layer, expert, len(projection), len(payload)))
                    source_tensors[name] = ("U8", (len(data),), data)
                    if expert == 1:
                        output_tensors[f"layers.{layer}.ffn.experts.0.{projection}.{payload}"] = (
                            "U8", (len(data),), data
                        )
        source_tensors[f"layers.{layer}.ffn.gate.weight"] = ("BF16", (2, 1), bytes((layer, 1, layer, 2)))
        output_tensors[f"layers.{layer}.ffn.gate.weight"] = ("BF16", (1, 1), bytes((layer, 2)))
        if layer < 3:
            tid = struct.pack("<q", 0)
            source_tensors[f"layers.{layer}.ffn.gate.tid2eid"] = ("I64", (1, 1), tid)
            output_tensors[f"layers.{layer}.ffn.gate.tid2eid"] = ("I64", (1, 1), tid)
        shared = bytes((layer, 9, 9))
        source_tensors[f"layers.{layer}.ffn.shared_experts.w1.weight"] = ("U8", (3,), shared)
        output_tensors[f"layers.{layer}.ffn.shared_experts.w1.weight"] = ("U8", (3,), shared)
    source_tensors["model.embed_tokens.weight"] = ("U8", (3,), b"abc")
    output_tensors["model.embed_tokens.weight"] = ("U8", (3,), b"abc")
    if retain_mtp:
        output_tensors["mtp.0.weight"] = ("U8", (1,), b"x")
    if mutate:
        name, value = mutate
        dtype, shape, _ = output_tensors[name]
        output_tensors[name] = (dtype, shape, value)

    write_safetensors(source / "model.safetensors", source_tensors)
    write_safetensors(output / "model.safetensors", output_tensors)
    config = {
        "model_type": "deepseek_v4", "n_routed_experts": 132,
        "num_hidden_layers": 43, "num_hash_layers": 3,
        "num_experts_per_tok": 6, "num_nextn_predict_layers": 0,
        "moe_compress_args": {"drop_mtp": True},
    }
    for root, tensors in ((source, source_tensors), (output, output_tensors)):
        (root / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {name: "model.safetensors" for name in tensors}}), encoding="utf-8"
        )
        (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
    raw = struct.pack("<q", 0)
    plan = {
        "logical_sha256": "logical-test",
        "layers": {str(layer): {"kept_experts": [1]} for layer in range(43)},
        "hash_routing": {
            str(layer): {"data": base64.b64encode(zlib.compress(raw)).decode(), "shape": [1, 1], "sha256": hashlib.sha256(raw).hexdigest()}
            for layer in range(3)
        },
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    source_manifest = source / "checkpoint-content-manifest.json"
    output_manifest = output / "checkpoint-content-manifest.json"
    write_manifest(source_manifest)
    write_manifest(output_manifest)
    return source, output, plan_path, source_manifest, output_manifest


@pytest.fixture
def patched_plan_hashes(monkeypatch):
    monkeypatch.setattr(MODULE, "PLAN_SHA", "x")
    monkeypatch.setattr(MODULE, "PLAN_LOGICAL_SHA", "logical-test")


def run_fixture(tmp_path, patched_plan_hashes, **kwargs):
    source, output, plan, source_manifest, output_manifest = make_fixture(tmp_path, **kwargs)
    MODULE.PLAN_SHA = hashlib.sha256(plan.read_bytes()).hexdigest()
    return MODULE.verify(source, output, plan, source_manifest, output_manifest)


def test_full_fixture_passes(patched_plan_hashes, tmp_path):
    report = run_fixture(tmp_path, patched_plan_hashes)
    assert report["failures"] == []
    assert all(value == "PASS" for value in report["summary"].values())
    assert report["expected_output_tensor_count"] == report["output_tensor_count"]
    assert len(report["layer_results"]) == 43


@pytest.mark.parametrize(
    "name,value",
    [
        ("layers.0.ffn.experts.0.w1.weight", b"bad!"),
        ("layers.0.ffn.gate.weight", b"bad!"),
        ("layers.0.ffn.gate.tid2eid", struct.pack("<q", 132)),
    ],
)
def test_mutations_fail(patched_plan_hashes, tmp_path, name, value):
    report = run_fixture(tmp_path, patched_plan_hashes, mutate=(name, value))
    assert report["failures"]


def test_retained_mtp_fails(patched_plan_hashes, tmp_path):
    report = run_fixture(tmp_path, patched_plan_hashes, retain_mtp=True)
    assert any("MTP" in failure or "namespace" in failure for failure in report["failures"])


def test_enabled_nextn_config_fails(patched_plan_hashes, tmp_path):
    source, output, plan, source_manifest, output_manifest = make_fixture(tmp_path)
    config_path = output / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["num_nextn_predict_layers"] = 1
    config_path.write_text(json.dumps(config), encoding="utf-8")
    MODULE.PLAN_SHA = hashlib.sha256(plan.read_bytes()).hexdigest()
    report = MODULE.verify(source, output, plan, source_manifest, output_manifest)
    assert any("num_nextn_predict_layers" in failure for failure in report["failures"])
