---
description: Evaluate the verified K132 mixed candidate on the established dual-5090 runtime.
---

# Tasks: K132 Mixed Expert Quantization Phase 4

## Input

- Verified Phase 3 candidate and canonical K132 runtime baseline.

## Canonical architecture / Key constraints

- Use dual RTX 5090 layer split, DIO load, auto-fit, F16 CPU KV, 64K context,
  and localhost single-slot serving.
- Runtime testing does not change the K132 deployment script until promotion is
  explicitly accepted.

## Phase 4: Runtime Acceptance

Goal: Determine whether the fixed heterogeneous policy preserves useful K132
behavior and stability.

Definition of Done: Startup, API, behavior, long-prefill, resource, and kernel
results are recorded with an explicit deployment decision.

Tasks:

- [ ] T061 [Infra] Pass runtime preflight and 64K startup
  - DoD: Idle baseline is recorded; server loads the candidate with contracted flags; `/health` and `/v1/models` pass without kernel/Xid events.
- [ ] T062 [QA] Run raw and structured behavior probes
  - DoD: Fixed greedy raw France, chat, Chinese, valid JSON, and Python/code probes are compared with canonical K132 and checked for repetition or formatting collapse.
- [ ] T063 [QA] Run 32K prefill and decode probe
  - DoD: The established 32,767-token input plus decode completes untruncated and records prompt/decode throughput.
- [ ] T064 [Infra] Record GPU, RAM, swap, and kernel health
  - DoD: GPU0/GPU1 memory, server RAM/swap peaks, load time, and clean post-run BAD_PAGE/Oops/GPF/Xid gate are stored.
- [ ] T065 [Docs] Make explicit promotion decision
  - DoD: Scope records PASS, rejection, or accepted-with-limitation; no script or canonical artifact changes without separate promotion authority.

Checkpoint: Scope closeout requires all evidence, residual risks, and rollback
path to be explicit.

## Dependencies & Execution Order

- Phase 4 depends on accepted Phase 3 artifact.
- T061 blocks T062-T064; T065 depends on all runtime evidence.
