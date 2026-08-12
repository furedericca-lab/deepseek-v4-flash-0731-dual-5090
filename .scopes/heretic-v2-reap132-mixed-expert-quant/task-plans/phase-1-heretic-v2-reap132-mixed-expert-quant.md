---
description: Build K132 structural and activation evidence without quantizing a model.
---

# Tasks: K132 Mixed Expert Quantization Phase 1

## Input

- Immutable K132 Golden and archived K96 score report.
- Scope contracts, research notes, and technical documentation.
- Pinned llama.cpp `llama-imatrix` at `2abf1748`.

## Canonical architecture / Key constraints

- Phase 1 creates reports and an imatrix only; no quantized GGUF.
- K132 model access uses `--load-mode dio` on a clean boot.
- Structural importance and activation importance remain separate recorded
  signals before normalization.

## Phase 1: Structural Prior and Imatrix

Goal: Produce accepted 43-layer structural and K132 activation evidence.

Definition of Done: Deterministic structural report and finite, coverage-audited
K132 imatrix exist with recorded source and corpus identities.

Tasks:

- [x] T001 [Backend] Implement structural-prior extraction
  - DoD: A script reads the archived score report and writes all contracted 43-layer fields plus deterministic SHA256; unit tests cover layer 0-2 and 3-42 normalization.
  - Evidence: `scripts/build_reap132_structural_prior.py` validates the complete
    source boundary and produced `evidence/reap132-structural-prior.json` twice
    byte-identically. `uv run pytest tests/test_build_reap132_structural_prior.py
    -q` passed `2/2`; report logical SHA256 is
    `4493d0e9917aa66da70454d68a1b88e8ba0fd5d9730f6a58d8a19d7291a7e64f`.
- [ ] T002 [Docs] Freeze calibration corpus contract
  - DoD: Scope evidence records corpus files, hashes, composition, tokenizer handling, context/chunk budget, and why they exercise code, math, Chinese, JSON/tool, and prose behavior.
- [ ] T003 [Infra] Pass clean-boot imatrix preflight
  - DoD: Kernel taint/signature, Xid, RAM/swap, GPU, process, Golden size/mode/hash identity, and DIO CLI gates are captured with explicit PASS.
- [ ] T004 [Infra] Collect checkpointed K132 imatrix
  - DoD: `llama-imatrix --load-mode dio` completes the contracted chunks and publishes GGUF imatrix checkpoints without a kernel/Xid event.
- [ ] T005 [Backend] Implement imatrix coverage and layer aggregation
  - DoD: A script verifies finite values, 129 routed entries, 132 expert counts per entry, reports zero-count experts, derives raw `I_l`, and writes deterministic evidence.
- [ ] T006 [QA] Verify Phase 1 determinism and coverage
  - DoD: Independent tests and reruns reproduce structural and imatrix-derived reports; unresolved zero-count coverage is recorded as a blocker rather than silently filled.

Checkpoint: Phase 2 starts only after T001-T006 pass and Phase 1 evidence is
recorded in `4phases-checklist.md`.

## Dependencies & Execution Order

- T001 and T002 may proceed before the large imatrix run.
- T003 blocks T004; T004 blocks T005; T005 blocks T006.
- Phase 1 blocks all later phases.
