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
  its canonical payload excludes its own `manifest_sha256` field. The derived
  `post-prune-verification.json` report is sidecar evidence and is excluded from
  the checkpoint artifact file set so writing the report cannot invalidate the
  content manifest it references.
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
- Native smoke is bounded diagnostic evidence, not a permanent GGUF blocker.
  Clean GPU0-only 1/16-token forwards are retained. One final 32-token QK+AV
  contiguous A/B is allowed; if it passes, only a 128-token confirmation runs.
  Either outcome is recorded before moving to the llama.cpp deployment gate.
- GGUF validation uses converter metadata inspection plus localhost llama.cpp
  API smoke on both RTX 5090s.
- A/B uses identical prompts, generation settings, and evaluator logic, with
  artifact hashes embedded in the result record.

## Current Native Gate

The writer blocker is closed by the Transformers-free deterministic
safetensors builder. Under a clean Linux 7.0 boot, Python 3.12 Build A and B
produced byte-identical 27-file manifests at
`9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`.
The final 35,620-tensor, 22-shard noMTP artifact passed the independent verifier
with zero failures and is read-only. Phase 2 checkpoint acceptance is complete.
Tokenizer/config and meta-device model construction pass, but standard HF
loading and the vendor pread loader do not satisfy the required O_DIRECT bulk
read boundary. The implemented direct-I/O loader supplied the bounded native
evidence. The later runtime fault is governed by the native-debug stop-loss rule
and does not invalidate the accepted checkpoint or block GGUF conversion after
a clean reboot.

The direct loader and one-token 43-layer forward now pass. Multi-token native
cross-device execution is not accepted: switching to GPU1 triggered NVIDIA
`Xid 31` and an MMU virtual-read fault. Native correctness smoke therefore uses
one GPU per process with `CUDA_VISIBLE_DEVICES=0`, requires exactly one visible
CUDA device, and runs independent 1/16/32/64/128-token prefill cases with
per-layer streaming after a clean reboot. Each case synchronizes CUDA and must
leave the boot free of BAD_PAGE, Oops, GPF, and NVIDIA Xid events before the
next begins. Dual-GPU and semantic generation acceptance remain in the llama.cpp
runtime gate.

The first isolated matrix run refined the runtime failure boundary. T1 at one
token and T2 at 16 tokens completed all 43 layers on physical GPU0 with finite
logits and clean post-case kernel gates. T3 at 32 tokens failed in Layer 2 eager
attention at the batched `attn_weights x value_states` matmul, followed by CUDA
illegal memory access and NVIDIA Xid 31 on GPU0 (`01:00.0`). GPU1 was invisible
and PyTorch reported one CUDA device, so neither GPU1 nor a cross-device switch
is necessary to reproduce the native failure. T4/T5 were not run. The current
boot was quarantined for GPU evidence, while the accepted checkpoint bytes
remained unchanged.

The final bounded layout A/B materialized both the Layer 2 QK key operand and AV
value operand. Both GEMMs completed and Layers 2-3 passed. Layer 4 then used the
original unpatched eager-attention function and reproduced Xid 31 at QK. A full
native HF workaround would therefore require model-wide runtime patching. The
stop-loss rule closes that investigation: clean 1/16-token results remain
accepted, 32-token native HF is recorded as a current Torch/CUDA/Blackwell
limitation, and the 128-token case is not run. Phase 3 owns deployment
acceptance through pinned GGUF and llama.cpp.

The failing harness also exposed a concrete lifetime-ordering suspect: it
released the streamed layer and invoked `empty_cache()` before any explicit
per-layer CUDA synchronization. The next A/B synchronizes the target device
immediately after each layer forward, then frees that layer. An exception no
longer runs cleanup that can mask the original CUDA error. This ordering change
must be validated on a new clean boot and is not yet a proven Xid root cause.

Layer-type resolution adds a second live hypothesis: Layers 0-1 are sliding
attention, while Layer 2 is the first compressed sparse attention layer. The
failure may therefore be specific to the 32-token CSA/eager cuBLAS path. A
clean-boot rerun with corrected synchronization is required to distinguish the
two explanations.
