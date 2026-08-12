---
description: Build and accept a separate K96 candidate only after the plan passes.
---

# Tasks: heretic-v2-reap96-consensus Phase 3

## Input

- Frozen Phase 2 K96 plan and reports
- Existing read-only HERETIC v2 source checkpoint
- Existing production O_DIRECT builder, verifier, converter, and runtime gate

## Canonical Architecture / Key Constraints

- The K132 checkpoint and canonical GGUF remain untouched.
- All bulk I/O uses the existing aligned O_DIRECT paths and clean-boot gate.
- MXFP4 is the only candidate deployment format.

## Phase 3: Candidate Build, Provenance, and Runtime

Goal: produce and accept a K96 artifact only if it completes the entire proven
production validation sequence.

Definition of Done: separate K96 native checkpoint, GGUF provenance, and
dual-5090 runtime pass; otherwise record the failed gate and retain K132.

Tasks:

- [ ] T041 [Infra] Run clean-boot gate and deterministic Python 3.12 O_DIRECT
  K96 native build.
  - DoD: K96 output is a new path, no frozen K132 artifact changes, and build
    logs/manifests are complete.
- [ ] T042 [QA] Run independent K96 O_DIRECT structural and byte provenance
  verification.
  - DoD: Every retained expert/raw tensor, router, new hash routing, no-MTP
    config, and manifest contract passes.
- [ ] T043 [Infra] Convert K96 native checkpoint with the pinned direct-I/O
  llama.cpp converter and validate GGUF provenance.
  - DoD: MXFP4, nonexpert, and FP8-backbone provenance reports pass before
    runtime promotion.
- [ ] T044 [QA] Run localhost dual-5090 64K/API/behavior and long-prefill gates.
  - DoD: No kernel/NVIDIA faults, raw/chat/JSON/Chinese/Python probes pass, and
    K96 is promoted only with recorded SHA256 and read-only status.

Checkpoint: Phase 3 completion may add a new canonical K96 deployment artifact;
any failed gate leaves K132 as the only canonical deployment.

## Dependencies & Execution Order

Phase 3 depends on a frozen Phase 2 plan. T041 blocks T042, which blocks T043,
which blocks T044. No task authorizes mutation of K132.
