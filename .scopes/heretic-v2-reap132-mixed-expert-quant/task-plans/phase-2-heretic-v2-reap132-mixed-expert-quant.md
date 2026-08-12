---
description: Freeze and verify the deterministic 17 IQ3 / 26 Q2 layer plan.
---

# Tasks: K132 Mixed Expert Quantization Phase 2

## Input

- Accepted Phase 1 structural and imatrix reports.
- Quantization-plan schema in the scope contracts.

## Canonical architecture / Key constraints

- `P_l = 0.4 R_l + 0.6 I_l`.
- Exactly 17 layers map to IQ3_XXS and 26 to Q2_K.
- Only routed expert tensor regexes may appear in the type file.

## Phase 2: Frozen 17/26 Plan

Goal: Produce an immutable, reproducible layer assignment and quantizer input.

Definition of Done: Two plan generations are byte-identical, an independent
verifier passes, and dry-run reports the contracted type split.

Tasks:

- [ ] T021 [Backend] Implement combined ranking and plan generator
  - DoD: The generator validates inputs, computes all 43 scores and stable tie-breaks, assigns top 17 IQ3_XXS and remaining 26 Q2_K, and emits logical/file SHA256.
- [ ] T022 [Backend] Generate routed-only tensor-type file
  - DoD: The file expands 43 assignments to anchored gate/up/down expert regexes and contains no Shared Expert, Core Backbone, router, or structural override.
- [ ] T023 [QA] Implement independent plan verifier
  - DoD: A separately structured verifier checks source hashes, formula, sorting, 17/26 counts, 51/78 tensor expansion, and deterministic hashes.
- [ ] T024 [QA] Run imatrix-backed DIO dry-run
  - DoD: `llama-quantize --dry-run --direct-io-input --allow-requantize --imatrix ... --tensor-type-file ... IQ4_XS` exits zero and records exact output size and type inventory.
- [ ] T025 [Docs] Freeze plan and output identity
  - DoD: The accepted plan, imatrix, corpus, llama.cpp commit, dry-run log, and output filename are recorded; later phases do not rerank layers.

Checkpoint: Phase 3 requires T021-T025 PASS and an immutable plan SHA.

## Dependencies & Execution Order

- Phase 2 depends on all Phase 1 tasks.
- T021 blocks T022-T025; T023 and T024 independently validate generator output.
