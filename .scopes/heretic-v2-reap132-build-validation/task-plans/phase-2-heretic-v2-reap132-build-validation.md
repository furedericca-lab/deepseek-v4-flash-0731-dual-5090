---
description: Task list for heretic-v2-reap132-build-validation phase 2.
---

# Tasks: heretic-v2-reap132-build-validation Phase 2

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-scope-milestones.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-brainstorming.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-implementation-research-notes.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-technical-documentation.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-contracts.md`

## Canonical architecture / Key constraints
- Verification reads source/output safetensors directly and sequentially.
- Unknown names and absent tensors are failures, not skipped checks.
- Native smoke cannot begin until every structural/byte category passes.
- The source and output directories are not modified by verification.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 2: Post-Prune Verification and Native HF Smoke
Goal: Prove the native output preserves every selected expert and HERETIC v2 overlay, then demonstrate basic native functionality.

Definition of Done: `post-prune-verification.json` contains all PASS categories and the output content manifest is frozen. Native HF evidence includes clean 1/16-token forwards plus one final QK+AV-contiguous 32-token A/B. If that A/B passes, a clean 128-token confirmation completes native acceptance; if either fails, the limitation is recorded without invalidating the byte-verified checkpoint or blocking Phase 3.

Tasks:
- [x] T021 [Backend] Implement direct-safetensors post-prune verifier
  - DoD: `scripts/verify_reap132_checkpoint.py` consumes source/output/plan/manifests and emits the contracted JSON without full-model loading.
- [x] T022 [QA] Add adversarial verifier fixtures
  - DoD: Tests fail on expert reorder, packed-weight mutation, scale mutation, router mismatch, shared expert drift, overlay drift, retained MTP, bad `tid2eid`, dangling ID, missing tensor, and manifest drift.
- [x] T023 [QA] Verify all 43 expert mappings
  - DoD: For every layer and new expert ID, all source old-ID `w1/w2/w3.weight` and `.scale` bytes equal the output new-ID tensors; report says `43/43 layers PASS`.
- [x] T024 [QA] Verify router and hash routing
  - DoD: All router rows follow the plan, three `tid2eid` tables equal plan blobs, and no routing ID is outside `0..131`.
- [x] T025 [QA] Verify preserved non-expert tensors
  - DoD: Shared experts and layers 10-42 HERETIC `attn.wo_b` are source-identical; all 4,705 source MTP/DSpark tensors are absent; unknown/unclassified tensors are zero.
- [x] T026 [Backend] Generate the output content manifest
  - DoD: Every native output file is hashed under `checkpoint-content-manifest-v1`, its manifest SHA is stable across two runs, and differs conceptually from the plan logical SHA.
- [x] T027 [QA] Freeze the post-prune report
  - DoD: `post-prune-verification.json` references exact plan/source/output hashes, has all contracted PASS fields, 43 layer results, and no failures.
- [x] T028 [Infra] Run native HF smoke matrix
  - DoD: Preserve the accepted clean 1/16-token evidence. Run the final 32-token case with physical GPU1 hidden, O_DIRECT streaming, launch blocking, and both QK key and AV value broadcast operands materialized. If it passes, run only 128 tokens with the same workaround. Record either PASS or the bounded native HF runtime limitation, then stop native CUDA debugging and hand the byte-verified checkpoint to Phase 3.

Outcome: The final A/B made Layer 2 QK and AV pass and completed Layers 2-3.
Layer 4 then entered unpatched eager attention and reproduced Xid 31 at QK.
Native HF is recorded as limited beyond the clean 16-token prefill; the optional
128-token confirmation is not run. No model-wide native runtime patch or
further upstream CUDA investigation is in scope.

Checkpoint: The independently byte-verified native checkpoint is accepted as the sole input to GGUF conversion. Native HF runtime limitations are documented residual risk, not a reason to alter or rebuild it.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- Phase 2 depends on Phase 1.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
