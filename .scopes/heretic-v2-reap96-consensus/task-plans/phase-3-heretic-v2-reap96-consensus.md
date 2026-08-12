---
description: Build and accept a separate K96 candidate only after the plan passes.
---

# Tasks: heretic-v2-reap96-consensus Phase 3

## Input

- Frozen Phase 2 K96 plan and reports
- Existing read-only accepted K132 no-MTP checkpoint
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

- [x] T041 [Infra] Run clean-boot gate and deterministic Python 3.12 O_DIRECT
  K96 native build.
  - DoD: K96 output is a new path, no frozen K132 artifact changes, and build
    logs/manifests are complete.
- [x] T042 [QA] Run independent K96 O_DIRECT structural and byte provenance
  verification.
  - DoD: Every retained expert/raw tensor, router, new hash routing, no-MTP
    config, and manifest contract passes.
  - Evidence: Builds A and B each produced 17 shards and 26,332 tensors. Both
    independent reports passed nine verification groups with zero failures;
    their 22 manifest entries were path/size/SHA256 identical at manifest SHA
    `62e40f7c...574ed`. Build B was promoted read-only to
    `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP`;
    Build A was deleted after acceptance. See
    `evidence/reap96-phase3-native-acceptance.json`.
- [ ] T043 [Infra] Convert K96 native checkpoint with the pinned direct-I/O
  llama.cpp converter and validate GGUF provenance.
  - DoD: MXFP4, nonexpert, and FP8-backbone provenance reports pass before
    runtime promotion.
- [ ] T044 [QA] Run localhost dual-5090 64K/API/behavior and long-prefill gates.
  - DoD: No kernel/NVIDIA faults, raw/chat/JSON/Chinese/Python probes pass, and
    K96 is promoted only with recorded SHA256 and read-only status.

Checkpoint: the canonical K96 native source artifact is accepted and read-only.
It is not yet a deployment release. T043 GGUF conversion/provenance and T044
dual-5090 runtime acceptance remain required; K132 remains the deployed model.

## Dependencies & Execution Order

Phase 3 depends on a frozen Phase 2 plan. T041 blocks T042, which blocks T043,
which blocks T044. No task authorizes mutation of K132.
