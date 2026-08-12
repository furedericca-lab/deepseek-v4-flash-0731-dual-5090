---
description: Produce and verify one DIO K132 heterogeneous quantization artifact.
---

# Tasks: K132 Mixed Expert Quantization Phase 3

## Input

- Immutable K132 Golden, accepted imatrix, frozen plan, and tensor-type file.
- Pinned DIO quantizer and clean-boot contract.

## Canonical architecture / Key constraints

- One production candidate only.
- Base ftype is non-pure IQ4_XS; routed overrides are plan-owned.
- Full input/output/hash/provenance access is direct-I/O only.

## Phase 3: Production Artifact

Goal: Build one structurally correct, stable, direct-verified mixed candidate.

Definition of Done: Quantizer exits zero on a clean boot and the candidate
passes structure, type, routing, source, hash, and kernel gates.

Tasks:

- [ ] T041 [Infra] Pass production clean-boot preflight
  - DoD: Kernel/Xid/process/RAM/swap, source identity, free-space, plan, imatrix, binary commit, and command are captured before payload work.
- [ ] T042 [Infra] Run atomic DIO production quantization
  - DoD: The one authorized quantizer invocation exits zero, publishes only the final atomic output, and post-run kernel gate remains clean.
- [ ] T043 [Backend] Implement mixed-candidate verifier
  - DoD: Direct-only verifier checks metadata, namespace, 51 IQ3 expert tensors, 78 Q2 expert tensors, non-routed policy inventory, and byte-identical router/`tid2eid`/structural payloads.
- [ ] T044 [QA] Produce direct-only content identity
  - DoD: Candidate has stable O_DIRECT SHA256, read-only mode, zero unstable reads, no MTP/DSpark, and explicit file-size evidence without a size threshold.
- [ ] T045 [Docs] Record artifact acceptance or rejection
  - DoD: Reports distinguish intended lossy routed quantization from forbidden routing/metadata drift and identify K132 as rollback baseline.

Checkpoint: Phase 4 starts only with an accepted T045 artifact and clean boot.

## Dependencies & Execution Order

- Phase 3 depends on frozen Phase 2 evidence.
- T041 blocks T042; T042 blocks T043-T045.
