from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_mxfp4_gguf_repack.py"
SPEC = importlib.util.spec_from_file_location("verify_mxfp4_gguf_repack", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def source_for(k: int, layer: int = 0):
    return {
        f"layers.{layer}.ffn.experts.{expert}.w1.weight": object()
        for expert in range(k)
    }


def test_auto_samples_follow_source_expert_count():
    assert MODULE.sampled_experts(MODULE.expert_ids_for_layer(source_for(96), 0)) == [0, 48, 95]
    assert MODULE.sampled_experts(MODULE.expert_ids_for_layer(source_for(132), 0)) == [0, 66, 131]


def test_expert_discovery_rejects_non_contiguous_namespace():
    source = source_for(3)
    del source["layers.0.ffn.experts.1.w1.weight"]
    with pytest.raises(ValueError, match="contiguous"):
        MODULE.expert_ids_for_layer(source, 0)
