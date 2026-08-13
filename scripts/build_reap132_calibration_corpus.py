#!/usr/bin/env python3
"""Build the frozen cumulative K132 imatrix calibration corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import tempfile
from pathlib import Path

import pyarrow.parquet as pq
from tokenizers import Tokenizer


WEIGHTS = {
    "code": 0.30,
    "math": 0.20,
    "chinese": 0.20,
    "tools": 0.15,
    "english": 0.10,
    "structured": 0.05,
}
FILES = {
    "code": "code_micro.parquet",
    "math": "math_micro.parquet",
    "chinese": "text_cn_micro.parquet",
    "tools": "tools_micro.parquet",
    "english": "text_en_micro.parquet",
}
STRUCTURED = re.compile(
    r"(?i)(\bjson\b|\byaml\b|\bxml\b|\bschema\b|\bapi\b|tool call|"
    r"function call|arguments|markdown table|\|[^\n]+\|)"
)
SEED = 132_017_026
CHUNK_SIZE = 512
STAGES = (100, 200, 300, 400)
MAX_SAMPLE_TOKENS = 256
SOURCE_DATASET = "eaddario/imatrix-calibration"
SOURCE_REVISION = "e87ed55dcba9d9c3a3e41539f3e728e981b1daa4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_snapshot(source_dir: Path) -> dict[str, dict[str, int | str]]:
    checksum_path = source_dir / "SHA256SUMS"
    expected: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        expected[name.strip()] = digest
    required = set(FILES.values()) | {"README.upstream.md"}
    if not required <= expected.keys():
        missing = sorted(required - expected.keys())
        raise ValueError(f"SHA256SUMS missing required files: {missing}")
    result = {}
    for name in sorted(required):
        path = source_dir / name
        actual = sha256(path)
        if actual != expected[name]:
            raise ValueError(f"{name}: sha256 mismatch: {actual} != {expected[name]}")
        result[name] = {"size": path.stat().st_size, "sha256": actual}
    return result


def read_lines(path: Path) -> list[str]:
    table = pq.read_table(path, columns=["content"])
    if table.num_rows != 1 or table.column_names != ["content"]:
        raise ValueError(f"{path}: expected one string content row")
    value = table.column("content")[0].as_py()
    if not isinstance(value, str):
        raise ValueError(f"{path}: content is not a string")
    return [line.strip() for line in value.splitlines() if line.strip()]


def split_tokens(tokenizer: Tokenizer, text: str) -> list[str]:
    ids = tokenizer.encode(text, add_special_tokens=False).ids
    return [tokenizer.decode(ids[start:start + MAX_SAMPLE_TOKENS])
            for start in range(0, len(ids), MAX_SAMPLE_TOKENS)]


def load_pools(source_dir: Path, tokenizer: Tokenizer) -> dict[str, list[str]]:
    raw = {category: read_lines(source_dir / filename) for category, filename in FILES.items()}
    structured = [line for category in ("code", "tools") for line in raw[category]
                  if STRUCTURED.search(line)]
    raw["code"] = [line for line in raw["code"] if not STRUCTURED.search(line)]
    raw["tools"] = [line for line in raw["tools"] if not STRUCTURED.search(line)]
    raw["structured"] = structured
    pools = {
        category: [part for line in lines for part in split_tokens(tokenizer, line) if part.strip()]
        for category, lines in raw.items()
    }
    rng = random.Random(SEED)
    for category in WEIGHTS:
        if not pools[category]:
            raise ValueError(f"no samples for {category}")
        rng.shuffle(pools[category])
    return pools


def build(source_dir: Path, tokenizer_path: Path) -> tuple[str, dict]:
    source_files = verify_source_snapshot(source_dir)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    pools = load_pools(source_dir, tokenizer)
    indices = {category: 0 for category in WEIGHTS}
    category_tokens = {category: 0 for category in WEIGHTS}
    records: list[tuple[str, str]] = []
    target_tokens = STAGES[-1] * CHUNK_SIZE + CHUNK_SIZE

    while sum(category_tokens.values()) < target_tokens:
        category = min(WEIGHTS, key=lambda key: (category_tokens[key] / WEIGHTS[key], key))
        if indices[category] >= len(pools[category]):
            raise ValueError(f"exhausted {category} pool")
        text = pools[category][indices[category]]
        indices[category] += 1
        token_count = len(tokenizer.encode(text + "\n\n", add_special_tokens=False).ids)
        category_tokens[category] += token_count
        records.append((category, text))

    corpus = "\n\n".join(text for _, text in records) + "\n"
    ids = tokenizer.encode(corpus, add_special_tokens=False).ids
    if len(ids) < STAGES[-1] * CHUNK_SIZE:
        raise ValueError("corpus did not reach the final chunk target")
    stages = []
    consumed = 0
    prefix_counts = {category: 0 for category in WEIGHTS}
    stage_index = 0
    for category, text in records:
        consumed += len(tokenizer.encode(text + "\n\n", add_special_tokens=False).ids)
        prefix_counts[category] += len(tokenizer.encode(text + "\n\n", add_special_tokens=False).ids)
        while stage_index < len(STAGES) and consumed >= STAGES[stage_index] * CHUNK_SIZE:
            chunks = STAGES[stage_index]
            stages.append({
                "chunks": chunks,
                "nominal_tokens": chunks * CHUNK_SIZE,
                "completed_sample_tokens": dict(prefix_counts),
                "completed_sample_total": sum(prefix_counts.values()),
                "completed_sample_ratios": {
                    category: prefix_counts[category] / sum(prefix_counts.values())
                    for category in WEIGHTS
                },
            })
            stage_index += 1
    manifest = {
        "schema": "heretic-reap132-imatrix-corpus-v1",
        "seed": SEED,
        "chunk_size": CHUNK_SIZE,
        "stages": stages,
        "weights": WEIGHTS,
        "max_sample_tokens": MAX_SAMPLE_TOKENS,
        "source": {
            "dataset": SOURCE_DATASET,
            "revision": SOURCE_REVISION,
            "files": source_files,
        },
        "tokenizer": {
            "size": tokenizer_path.stat().st_size,
            "sha256": sha256(tokenizer_path),
            "vocab_size": tokenizer.get_vocab_size(),
            "add_special_tokens": False,
        },
        "samples": len(records),
        "completed_sample_tokens": category_tokens,
        "completed_sample_ratios": {
            category: category_tokens[category] / sum(category_tokens.values())
            for category in WEIGHTS
        },
        "tokenizer_token_count": len(ids),
        "corpus_sha256": hashlib.sha256(corpus.encode()).hexdigest(),
    }
    return corpus, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    corpus, manifest = build(args.source_dir, args.tokenizer)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent,
                                     prefix=args.output.name + ".", delete=False) as handle:
        handle.write(corpus)
        corpus_tmp = Path(handle.name)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.manifest.parent,
                                     prefix=args.manifest.name + ".", delete=False) as handle:
        handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        manifest_tmp = Path(handle.name)
    corpus_tmp.replace(args.output)
    manifest_tmp.replace(args.manifest)
    print(json.dumps({"corpus_sha256": manifest["corpus_sha256"],
                      "tokens": manifest["tokenizer_token_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
