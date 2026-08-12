import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_reap96_iq4xs_gguf.py"
SPEC = importlib.util.spec_from_file_location("verify_reap96_iq4xs_gguf", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_quantizer_fixture() -> None:
    path = "/data/linux-fast/models/llama-quantize-dio-fixture/stories260K-copy-dio-v2-20260813.gguf"
    gguf = MODULE.parse_gguf(Path(path))
    assert gguf.metadata["general.architecture"] == "llama"
    assert gguf.metadata["tensor_count"] == 48
    assert len(gguf.tensors) == 48
