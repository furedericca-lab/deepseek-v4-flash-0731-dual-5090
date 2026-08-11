---
description: Canonical technical architecture for heretic-v2-reap132-build-validation.
---

# heretic-v2-reap132-build-validation Technical Documentation

## Canonical Architecture

```text
frozen plan JSON + verified HERETIC v2 source + committed build code
                              |
                              v
        moe-compress --plan --streaming --drop-mtp
                              |
                              v
          native HERETIC-v2-REAP132-noMTP checkpoint
                              |
              +---------------+----------------+
              |                                |
              v                                v
 post-prune byte verifier            output content manifest
              |                                |
              +---------------+----------------+
                              v
                       native HF smoke
                              |
                              v
             pinned llama.cpp HF-to-GGUF converter
                              |
                              v
                  golden MXFP4-preserving GGUF
                              |
                              v
                 dual-5090 runtime + controlled A/B
```

## Key Constraints and Non-Goals

- `squanchyzx-puwaer-reap132-mask.json` is immutable. No mask logic changes.
- Deterministic plan mode must bypass calibration, datasets, and saliency.
- Full file SHA, logical plan SHA, source manifest SHA, output manifest SHA, and
  GGUF SHA are separate identities.
- Runtime data stays on `/data/linux-fast` ext4. Git stores only code/docs and
  small sanitized summaries.
- Pruning uses the project `.venv` and layer streaming due host RAM limits.
- Full native verification is also host-gated: a `BAD_PAGE`/folio corruption
  event in the active kernel invalidates the run even when SHA256 results pass.
- First server bind remains `127.0.0.1`; single slot and existing OOM order apply.
- IQ3/Q2 and fresh calibration are non-goals for this scope.

## Major Decisions and Trade-offs

1. Existing plan over fresh calibration: reproducibility and A/B isolation win.
2. Direct safetensors verification over model-value comparison: packed bytes and
   scales remain observable without a full model load.
3. Native smoke before GGUF: separates surgery defects from conversion defects.
4. MXFP4-preserving GGUF first: establishes a golden conversion baseline before
   dense-tensor or whole-model quantization experiments.
5. Whole-checkpoint content manifests: expensive I/O is accepted for immutable
   artifact identity.

## Module Boundaries and Data Flow

| Component | Responsibility |
|---|---|
| `squanchyzx-puwaer-reap132-mask.json` | Immutable old-to-new expert map and final hash routing |
| `scripts/write_checkpoint_source_manifest.py` | Bind local source config/index to immutable HF repo/commit |
| `vendor/moe-expert-compress` | Apply existing plan layer-by-layer and write native checkpoint |
| planned `scripts/verify_reap132_checkpoint.py` | Compare source/output/plan tensors and emit verification JSON |
| `scripts/checkpoint_content_manifest.py` | Hash all checkpoint files and canonical manifest payload |
| `scripts/derive_reap132_inventory.py` | Derive source/expert/MTP/output tensor counts from source index and frozen plan |
| `tools/verify_hf_checkpoint_sha256.py` | Compare every local repository file against an immutable HF revision and emit mismatch evidence |
| `/data/linux-fast/models/...HERETIC-Abliterated-FP8/` | Read-only source snapshot after verification |
| `/data/linux-fast/models/...HERETIC-v2-REAP132-noMTP/` | Native output, manifests, verifier report, smoke evidence |
| pinned llama.cpp converter | Convert only the verified native checkpoint |
| llama-server | Local dual-5090 GGUF runtime validation |

The fixed source index contains 72,317 tensors. Routed experts use six entries
per expert (`w1/w2/w3.weight` plus `w1/w2/w3.scale`). Shared experts use the
same weight/scale pattern. HERETIC v2 modifies backbone
`layers.10..42.attn.wo_b.{weight,scale}`. The generic streamer can preserve
model-ignored tensors, but this build uses `--drop-mtp` to omit all 4,705
MTP/DSpark tensors and 10,862,838,300 source bytes without reading their payloads.
All source safetensors reads use the `pread` backend. The 96 fixed-revision
repository files and both local provenance manifests are read-only after source
verification, so compression cannot share or modify mmap-backed source storage.

## Interfaces and Contracts

- Source directory:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8/`.
- Native output directory:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`.
- Frozen plan full SHA:
  `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`.
- Post-prune report: `post-prune-verification.json` in the output directory.
- Verifier implementation: `scripts/verify_reap132_checkpoint.py`; its report is
  written to `logs/` until the host stability gate is clean, then frozen beside
  the output manifest.
- Content manifest: `checkpoint-content-manifest.json` in each checkpoint root;
  its canonical payload excludes its own `manifest_sha256` field.
- Exact JSON contracts are defined in
  `heretic-v2-reap132-build-validation-contracts.md`.

## Operational Behavior

1. Wait for the user-started `hf download` to exit successfully.
2. Verify no partial transfer process remains and validate index inventory.
3. Generate source provenance and content manifests.
4. Capture RAM/swap, GPU, disk, and process baselines; ensure wiki/doctor scans
   are not reading model files.
5. Run `tools/verify_hf_checkpoint_sha256.py` against the fixed revision. Require
   50/50 LFS SHA256 and 46/46 Git files by downloaded remote SHA256, zero
   missing/extra paths, then make the snapshot read-only. The verifier must
   continue after individual mismatches and report their complete collection.
6. Run a real quantized Layer 0 naming preflight through `pread` after
   `apply_keep()`; require
   792 expert tensors, 396 weights, 396 scales, zero unknown source names, and
   zero survivor provenance mismatches.
7. Recheck the full source content manifest after preflight.
8. Run plan streaming with `--drop-mtp`, logging command, source/plan hashes, environment,
   start/end time, exit status, and peak memory.
9. Require writer hard-fail behavior for duplicate or source-unknown names, then
   dynamically derive the noMTP inventory, currently 35,620 indexed tensors,
   and require 792 expert tensors in every layer and zero MTP/DSpark tensors.
10. Treat output as quarantined until post-prune verifier passes.
    Abort and quarantine the report if `journalctl -k -b` records `BAD_PAGE`,
    `corrupted mapping`, or `compound_head not consistent` during the pass.
11. Run native smoke only after structural PASS.
12. Convert to GGUF only after native smoke PASS.

## Observability and Error Handling

- Every long operation writes a timestamped log under repo-ignored `logs/`.
- Partial output, nonzero exit, hash drift, duplicate or unknown tensor names,
  a tensor-count mismatch, missing shards, or any verifier category failure
  blocks the next phase.
- Do not delete failed artifacts automatically. Record size/path and request
  approval before replacement when overwrite is irreversible.
- Record `nvidia-smi`, `free -h`, `df -hT`, and relevant process snapshots around
  pruning, native smoke, conversion, and llama.cpp boot.

## Security and Reliability

- Use the logged-in `hf` CLI only; do not copy tokens into commands, manifests,
  logs, or scope docs.
- Keep checkpoint and GGUF paths off git and on the verified ext4 mount.
- Keep smoke endpoints localhost-only.
- Canonical manifests use relative file paths, sizes, and SHA256; they exclude
  credentials, cache paths, environment values, and absolute home paths.
- Content manifests exclude `.cache/`, `.hfd/`, `.git/`, `__pycache__/`, and the
  manifest itself. Partial or temporary files outside those control directories
  are rejected rather than silently excluded.
- Do not weaken TLS, authentication, or system controls for downloads or tests.

## Test Strategy

- Existing compressor suite:
  `uv run pytest vendor/moe-expert-compress/tests -q`.
- New script unit tests use tiny safetensors fixtures covering reordered experts,
  altered packed weights, altered scales, router mismatches, bad `tid2eid`,
  changed shared/HERETIC tensors, retained MTP tensors, dangling IDs, and manifest drift.
- Inventory tests prove the expected output count is derived from source and plan
  classification rather than accepted as an isolated constant.
- Source/output verification operates sequentially by tensor/shard and does not
  hold either checkpoint in RAM.
- Native smoke covers chat, reasoning, coding, tool call, and longer context.
- GGUF validation uses converter metadata inspection plus localhost llama.cpp
  API smoke on both RTX 5090s.
- A/B uses identical prompts, generation settings, and evaluator logic, with
  artifact hashes embedded in the result record.

## Current Writer Blocker

The 7.0/5600 rebuild is host-stable but still fails five byte-exact FP4 expert
checks. The failing expert IDs change between fixed-source/fixed-plan rebuilds;
scales, routers, shared experts, HERETIC overlay, and MTP policy pass. The
streaming writer currently moves fused FP4 tensors through CUDA and then uses
Transformers `revert_weight_conversion()` before CPU serialization. That
round-trip is not a valid raw-byte preservation path. The corrective design is
CPU safetensors slicing by frozen survivor IDs followed by direct packed-byte
serialization, with a hard failure on any unexpected mutation.
