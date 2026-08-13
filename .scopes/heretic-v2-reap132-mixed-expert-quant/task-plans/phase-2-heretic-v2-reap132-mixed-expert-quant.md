---
description: Freeze and verify the deterministic 17 IQ3 / 26 Q2 layer plan.
---

# Tasks: K132 Mixed Expert Quantization Phase 2

## Input

- Accepted Phase 1 structural and imatrix reports.
- Quantization-plan schema in the scope contracts.

## Canonical architecture / Key constraints

- `P_l = 0.4 R_l + 0.6 I_l`.
- Exactly 17 layers map to the IQ3_XXS recipe and 26 to the Q2_K_S recipe.
- Only routed expert tensor regexes may appear in the type file.

## Phase 2: Frozen 17/26 Plan

Goal: Produce an immutable, reproducible layer assignment and quantizer input.

Definition of Done: Two plan generations are byte-identical, an independent
verifier passes, and dry-run reports the contracted type split.

Tasks:

- [x] T021 [Backend] Implement combined ranking and plan generator
  - DoD: The generator validates inputs, computes all 43 scores and stable tie-breaks, assigns top 17 IQ3_XXS and remaining 26 Q2_K_S, and emits logical/file SHA256.
- [x] T022 [Backend] Generate routed-only tensor-ftype file
  - DoD: The file expands 43 assignments to anchored gate/up/down expert regexes and contains no Shared Expert, Core Backbone, router, or structural override.
- [x] T023 [QA] Implement independent plan verifier
  - DoD: A separately structured verifier checks source hashes, formula, sorting, 17/26 counts, 51/78 recipe expansion, mutually exclusive routed-only matching, and deterministic hashes.
- [x] T024 [QA] Run imatrix-backed DIO dry-run
  - DoD: `llama-quantize --dry-run --direct-io-input --allow-requantize --imatrix ... --tensor-ftype-file ... IQ4_XS` exits zero and records exact output size plus the IQ3_XXS/Q2_K_S/IQ4_XS effective-recipe and concrete-type inventories.
- [x] T025 [Docs] Freeze plan and output identity
  - DoD: The accepted plan, imatrix, corpus, llama.cpp commit, dry-run log, and output filename are recorded; later phases do not rerank layers.
  - Evidence: current plan file SHA256 `9f87f4530325924b56ca9059323bf73558036e36a8f006063d73f90d536c3ef7`,
    logical SHA256 `49b9c651ae0cfe17cad427e8c7af46e1df38a98e089f7a71c4fec88667d488d2`,
    and tensor-ftype SHA256 `db05988dd60a8262f353e70360a1a85a7ebb585bec9539fb7f70fe73f7c0269e`.
    Two generations were byte-identical and the independent verifier passed.
    The `efb81ab` CPU-NVMe DIO dry-run passed with output size `55,348,319,104` bytes:
    51 IQ3_XXS, 73 Q2_K, five Q2_K_S Q4_K promotions, 43 attention-KV Q5_K
    promotions, 129 Shared Expert IQ4_XS tensors, and 62 compressor APE lookup
    tensors unchanged.

Checkpoint: Phase 3 requires T021-T025 PASS and an immutable plan SHA.

## Dependencies & Execution Order

- Phase 2 depends on all Phase 1 tasks.
- T021 blocks T022-T025; T023 and T024 independently validate generator output.
