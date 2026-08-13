import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "llama.cpp" / "gguf-py"))
from gguf import GGUFReader, GGUFWriter

SPEC = importlib.util.spec_from_file_location("compat", ROOT / "scripts" / "build_reap132_q2_compat_imatrix.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write(path: Path, include_output: bool):
    writer = GGUFWriter(path, "imatrix")
    writer.add_type("imatrix")
    writer.add_array("imatrix.datasets", ["fixture"])
    writer.add_uint32("imatrix.chunk_count", 812 if not include_output else 200)
    writer.add_uint32("imatrix.chunk_size", 512)
    for index in range(768):
        writer.add_tensor(f"fixture.{index}.weight.in_sum2", np.arange(8, dtype=np.float32))
        writer.add_tensor(f"fixture.{index}.weight.counts", np.array([812], dtype=np.float32))
    if include_output:
        writer.add_tensor("output_hc_fn.weight.in_sum2", np.arange(16, dtype=np.float32))
        writer.add_tensor("output_hc_fn.weight.counts", np.array([200], dtype=np.float32))
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file(progress=False)
    writer.close()


def test_adds_only_missing_output_entry(tmp_path):
    external = tmp_path / "external.gguf"
    supplemental = tmp_path / "supplemental.gguf"
    output = tmp_path / "output.gguf"
    write(external, False)
    write(supplemental, True)
    report = MODULE.build(external.resolve(), supplemental.resolve(), output.resolve())
    reader = GGUFReader(output)
    names = {tensor.name for tensor in reader.tensors}
    assert len(names) == 1538
    assert {"output_hc_fn.weight.in_sum2", "output_hc_fn.weight.counts"} <= names
    assert report["external"]["entries_copied"] == 768
    assert report["overlapping_entries_replaced"] == 0
    assert output.stat().st_mode & 0o777 == 0o444
