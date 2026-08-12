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

Definition of Done: `post-prune-verification.json` contains all PASS categories, the output content manifest is frozen, and all five native smoke classes pass without NaN, routing faults, or obvious degeneration.

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
- [ ] T028 [Infra] Run native HF smoke matrix
  - DoD: Local checkpoint passes chat, reasoning, coding, tool-call, and longer-context probes with recorded placement/settings/memory and no NaN, tokenizer/config, routing, or obvious repetition failure.

Checkpoint: The native checkpoint is accepted as the sole input to GGUF conversion.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- Phase 2 depends on Phase 1.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
