---
description: Implementation research notes for heretic-v2-reap132-build-validation.
---

# heretic-v2-reap132-build-validation Implementation Research Notes

## Baseline (Current State)

- Active plan: `squanchyzx-puwaer-reap132-mask.json`.
- Full file SHA256:
  `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`.
- Logical SHA256:
  `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`.
- Base provenance: squanchyzx HERETIC v2 commit
  `e7efd043c5e072da4d40f0f98ade554c5713bad9`.
- Target provenance: puwaer REAP-150B commit
  `868fa38e2f2964699ad065dc8d9382c136cc60b8`.
- Extractor evidence: 43 layers, 132 sorted survivor IDs per layer, three
  `[129280, 6]` `int64` `tid2eid` tables, and 43/43 byte-exact router matches.
- Executable root build commit:
  `8071c7c64101f16ea0959881b86d180862bd514b`.
- Executable vendor build commit:
  `56137d189fd36c1c8881ca99233614b177442425`.
- The fixed source now exists at
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8/`.
  Official `hf` CLI confirmation exited zero at the fixed revision. All 96
  remote files match: 50 LFS files passed remote SHA256 checks and 46 small
  files passed byte comparison after `tokenizer.json` was repaired.
- Source provenance and the 97-entry canonical content manifest pass. The source
  content manifest SHA256 is
  `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`.
- `/data/linux-fast` is ext4 with 714 GiB available at the pre-prune baseline.
- Pre-prune code review found 4,705 model-ignored MTP/DSpark tensors totaling
  10,862,838,300 bytes. The writer retains generic ignored-tensor passthrough,
  but this build selects `--drop-mtp` because the dual-5090 llama.cpp/Hermes
  target does not use speculative decoding.

## Gap Analysis

| Gap | Current evidence | Required closure |
|---|---|---|
| Frozen source-code identity | Root and vendor build commits contain the exact extractor, provenance gate, manifest tool, plan-mode validation, and tests | Closed; execute only these committed identities |
| Complete source checkpoint | Official fixed-revision confirmation, remote comparison, provenance, and content manifest pass | Closed; preserve source read-only for pruning |
| Native REAP132 output | No output checkpoint exists | Run deterministic `--plan --streaming` without calibration |
| Byte-exact output proof | Only plan provenance is proven | Implement `post-prune-verification.json` generator and tests |
| Output content identity | No output manifest exists | Hash every output file and hash a canonical manifest payload |
| Native functionality | No native output exists | Run chat/reasoning/coding/tool/long-context smoke without NaN or routing faults |
| Golden GGUF | No conversion has run | Pin converter, preserve MXFP4 experts, hash output, validate metadata |
| Controlled A/B | No paired run exists | Compare puwaer REAP-150B and HERETIC v2 + same REAP132 under one harness |

## Candidate Designs and Trade-offs

1. Deterministic plan application with streaming.
   - Lowest conceptual drift and compatible with the 46 GiB RAM constraint.
2. Fresh calibration.
   - Rejected for this scope because it changes the controlled expert set.
3. Post-prune verifier based on tensor values loaded through Transformers.
   - Easy to prototype but can hide checkpoint conversion and dtype details.
4. Post-prune verifier based directly on safetensors indexes and tensor bytes.
   - Selected. It can prove packed FP4 weights/scales, router rows, shared
     experts, HERETIC overlay, MTP absence, and `tid2eid` without loading the full model.
5. Whole-file hashes only.
   - Necessary for artifact identity but insufficient for semantic mapping.

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Freeze current mapped plan | 5 | 5 | User instruction, plan SHA, exact mapping run | None | 5 | 5 | 3 | Immutable inputs are reversible only by opening a new scope | Accepted |
| Apply plan without calibration | 5 | 5 | User instruction and plan-mode tests | Earlier fresh-calibration option rejected | 5 | 5 | 3 | Output can be rebuilt, but the run is resource-intensive | Accepted |
| Verify direct checkpoint bytes | 5 | 5 | Source index and DeepSeek adapter layout | Higher implementation effort | 5 | 4 | 3 | Required proof is deterministic but I/O-heavy | Accepted |
| Native smoke before GGUF | 5 | 4 | Failure-isolation requirement | Native runtime resource uncertainty | 5 | 3 | 3 | Failures are reversible but can consume significant runtime | Accepted |
| MXFP4-preserving GGUF first | 5 | 4 | User instruction and source dtype evidence | Converter support must be confirmed | 5 | 3 | 3 | Conversion is reproducible after native acceptance | Accepted with Phase 3 evidence gate |
| Defer IQ3/Q2 | 5 | 5 | User instruction | None | 5 | 5 | 3 | A later scope can add quantization after the golden gate | Accepted |
| Drop all MTP/DSpark tensors | 5 | 5 | User instruction plus 4,705-tensor/10.86-GB source audit | Generic writer can preserve them, but runtime does not consume them | 5 | 5 | 3 | Explicit policy removes unused weight while keeping source/plan provenance unchanged | Accepted |

## Selected Design

Phase 1 freezes the plan/source identities, completes and manifests the fixed
source snapshot, captures a clean memory/process baseline, then executes only:

```text
moe-compress compress --plan <frozen-plan> --streaming --drop-mtp
```

Phase 2 implements a direct-safetensors verifier. For every layer and selected
old expert ID, output expert `new_id` must equal source expert `old_id` for all
`w1/w2/w3.weight` and `.scale` tensors. Router rows must follow the same map;
shared experts and all retained non-pruned tensors must be byte-identical;
layers 10-42 HERETIC `attn.wo_b` tensors must remain source-identical; all
MTP/DSpark tensors must be absent; hash-layer `tid2eid` must equal the frozen plan.

Phase 3 converts only the verified native output, creates a golden GGUF content
identity, validates it with llama.cpp on both RTX 5090s, and runs the controlled
puwaer-versus-HERETIC A/B.

## Validation Plan

- Freeze check: recompute full file SHA256 and `load_plan()` logical SHA.
- Source check: verify `.checkpoint-source.json`, complete index inventory, and
  canonical per-file content manifest.
- Plan-mode check: inspect command/log metadata and prove no calibration dataset
  or saliency path was invoked.
- Post-prune verifier output must report:
  `43/43 layers PASS`, `router PASS`, `experts PASS`, `scales PASS`,
  `tid2eid PASS`, `shared_experts PASS`, `HERETIC overlay PASS`, and
  `MTP/DSpark absent PASS`.
- Output config must declare 132 routed experts and preserve all unrelated
  architecture/tokenizer fields.
- Native smoke set: chat, reasoning, coding, tool call, and a longer-context
  probe; record NaN, repetition, routing, tokenizer/config, and memory signals.
- GGUF gate: metadata inspection, full SHA256, `llama-server --list-devices`,
  localhost boot, `/v1/models`, and one completion before A/B.
- Regression tests: `uv run pytest vendor/moe-expert-compress/tests -q` plus
  focused tests for new manifest/verifier scripts.

## Risks and Assumptions

- Assumption: source and output use the upstream per-expert tensor names found in
  the fixed source index, including `w1/w2/w3.weight` and `.scale`.
- Decision: all 4,705 MTP/DSpark tensors are intentionally absent. Any retained
  MTP tensor is a verification failure for the noMTP artifact.
- Risk: output naming conversion may be semantically correct but differ from the
  source namespace. The verifier must normalize only through documented mapping,
  never by skipping unknown tensors.
- Risk: computing whole-checkpoint hashes is I/O-heavy. It remains mandatory and
  should run sequentially on NVMe without competing doctor/wiki scans.
- Risk: native HF smoke may require CPU/GPU placement tuning. OOM recovery must
  not alter checkpoint contents or skip the structural gate.
- Risk: a converter may requantize routed experts. Phase 3 must prove the actual
  GGUF expert type before calling it the MXFP4 golden baseline.
