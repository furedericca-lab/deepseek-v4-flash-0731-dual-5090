import importlib.util
import sys
from pathlib import Path

import torch


SCRIPT = Path(__file__).parents[1] / "scripts" / "native_reap132_smoke.py"
SPEC = importlib.util.spec_from_file_location("native_reap132_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_tensor_metadata_preserves_layout_evidence():
    base = torch.arange(24, dtype=torch.float32).reshape(2, 3, 4)
    tensor = base.transpose(1, 2)

    metadata = MODULE.tensor_metadata(tensor)

    assert metadata["shape"] == [2, 4, 3]
    assert metadata["stride"] == list(tensor.stride())
    assert metadata["storage_offset"] == 0
    assert metadata["is_contiguous"] is False
    assert "finite" not in metadata
    assert "min" not in metadata
    assert "max" not in metadata
    assert metadata["data_ptr_mod_16"] == tensor.data_ptr() % 16
    assert metadata["data_ptr_mod_128"] == tensor.data_ptr() % 128
    assert metadata["data_ptr_mod_256"] == tensor.data_ptr() % 256


def test_tensor_value_trace_is_explicit_and_mask_aware():
    tensor = torch.tensor([1.0, 2.0])
    values = MODULE.tensor_metadata(tensor, trace_values=True)
    mask = MODULE.tensor_metadata(
        torch.tensor([0.0, float("-inf"), float("inf"), float("nan")]),
        trace_values=True,
        mask_semantics=True,
    )

    assert values["finite"] is True
    assert values["min"] == 1.0
    assert values["max"] == 2.0
    assert mask["nan_count"] == 1
    assert mask["positive_infinity_count"] == 1
    assert mask["negative_infinity_count"] == 1
