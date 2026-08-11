---
description: Task list for deepseek-v4-flash-0731-dual-5090 phase 3.
---

# Tasks: deepseek-v4-flash-0731-dual-5090 Phase 3

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-scope-milestones.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-brainstorming.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-implementation-research-notes.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-technical-documentation.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-contracts.md`

## Canonical architecture / Key constraints
- Harden the working first-boot recipe into an operator-ready service contract.
- Climb context only with evidence.
- Keep single-slot local serving unless Master expands scope.
- Preserve residual-risk honesty about compute/graph buffers, host runtime memory, and unbenchmarked Q2_K quality; do not infer stability from KV arithmetic alone.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 3: Hardening and operator handoff
Goal: freeze the production launch recipe, optional context climb, and Hermes integration notes.

Definition of Done: final launch recipe, recovery ladder, and agent integration notes are current; residual risks remain explicit.

Tasks:
- [ ] T041 [QA] Context climb or freeze
  - DoD: either 64K is proven stable, or the forced lower context is documented with evidence; optional 96K/128K results recorded if attempted.
- [ ] T042 [Config] Finalize operator launch/recovery docs and scripts
  - DoD: one canonical launch command and OOM ladder are referenced from README/AGENTS/wiki.
- [ ] T043 [Agentic] Document Hermes/local client connection
  - DoD: base URL `http://127.0.0.1:8000/v1`, reasoning-format expectation, and single-slot constraint are written for future agent use.
- [ ] T044 [Security] Confirm bind/auth posture
  - DoD: localhost-only remains default, or an approved LAN exposure plan with controls is recorded.
- [ ] T045 [Docs] Closeout evidence package
  - DoD: checklist contains final commands, VRAM/RAM notes, wiki alignment class, and residual risks.

Checkpoint: Phase 3 artifacts are merged, verified, and recorded in 3phases-checklist.md before archive/closeout.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- Phase 3 depends on completion of phases 1-2.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
