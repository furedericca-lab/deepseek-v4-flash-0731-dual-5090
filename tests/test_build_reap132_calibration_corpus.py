import importlib.util
import hashlib
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_reap132_calibration_corpus.py"
SPEC = importlib.util.spec_from_file_location("build_reap132_calibration_corpus", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_frozen_policy_constants():
    assert sum(MODULE.WEIGHTS.values()) == 1.0
    assert MODULE.WEIGHTS == {
        "code": 0.30,
        "math": 0.20,
        "chinese": 0.20,
        "tools": 0.15,
        "english": 0.10,
        "structured": 0.05,
    }
    assert MODULE.STAGES == (100, 200, 300, 400)
    assert MODULE.CHUNK_SIZE == 512
    assert MODULE.MAX_SAMPLE_TOKENS == 256
    assert MODULE.SOURCE_DATASET == "eaddario/imatrix-calibration"
    assert MODULE.SOURCE_REVISION == "e87ed55dcba9d9c3a3e41539f3e728e981b1daa4"


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    contents = {
        "code_micro.parquet": "def alpha x return x\ndef beta y return y\n",
        "math_micro.parquet": "solve alpha plus beta\nprove beta plus gamma\n",
        "text_cn_micro.parquet": "中文 技术 分析\n中文 系统 指令\n",
        "tools_micro.parquet": (
            "agent execute command alpha\n"
            "tool call json arguments alpha beta\n"
            "agent inspect output beta\n"
            "api schema json gamma delta\n"
        ),
        "text_en_micro.parquet": "english technical prose alpha\nsystem design beta\n",
    }
    checksums = []
    for name, content in contents.items():
        pq.write_table(pa.table({"content": [content]}), source / name)
    (source / "README.upstream.md").write_text("fixture\n", encoding="utf-8")
    for path in sorted(source.iterdir()):
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (source / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    vocab = {"[UNK]": 0}
    for token in sorted(set(" ".join(contents.values()).split())):
        vocab[token] = len(vocab)
    tokenizer = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer.save(str(tokenizer_path))
    return source, tokenizer_path


def test_build_is_deterministic_and_balanced(tmp_path, monkeypatch):
    source, tokenizer = _write_fixture(tmp_path)
    monkeypatch.setattr(MODULE, "STAGES", (1, 2))
    monkeypatch.setattr(MODULE, "CHUNK_SIZE", 8)
    monkeypatch.setattr(MODULE, "MAX_SAMPLE_TOKENS", 8)

    corpus_a, manifest_a = MODULE.build(source, tokenizer)
    corpus_b, manifest_b = MODULE.build(source, tokenizer)
    assert corpus_a == corpus_b
    assert manifest_a == manifest_b
    assert manifest_a["corpus_sha256"] == hashlib.sha256(corpus_a.encode()).hexdigest()
    assert [stage["chunks"] for stage in manifest_a["stages"]] == [1, 2]
    assert manifest_a["source"]["revision"] == MODULE.SOURCE_REVISION
    assert set(manifest_a["completed_sample_ratios"]) == set(MODULE.WEIGHTS)


def test_source_checksum_mismatch_fails(tmp_path):
    source, _ = _write_fixture(tmp_path)
    with (source / "code_micro.parquet").open("ab") as handle:
        handle.write(b"corrupt")
    try:
        MODULE.verify_source_snapshot(source)
    except ValueError as exc:
        assert "sha256 mismatch" in str(exc)
    else:
        raise AssertionError("corrupt source snapshot was accepted")
