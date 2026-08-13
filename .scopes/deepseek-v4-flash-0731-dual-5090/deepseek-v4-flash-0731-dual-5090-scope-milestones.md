---
description: Milestones for the accepted corrected K132 MXFP4 deployment.
---

# Deployment Milestones

## Goals

- Keep the corrected K132 MXFP4 GGUF as the sole deployed artifact.
- Serve it through the pinned llama.cpp fork on dual RTX 5090 at 64K context.
- Preserve direct-I/O, clean-boot, provenance, behavior, and rollback evidence.
- Reject and remove candidates that pass structure but fail semantic behavior.
- Evaluate one Q2-recipe repair candidate without replacing the accepted MXFP4
  baseline before full acceptance.

## Non-Goals

- Reopening K132 pruning, routing, or the archived 17/26 experiment.
- Deploying K96, the failed K132 mixed candidate, or external Q2 payloads.
- Broad CUDA/kernel debugging beyond the documented stop-loss boundaries.
- Binding beyond localhost without explicit approval.

## Milestones

| Milestone | Status | Evidence |
|---|---|---|
| Accepted native K132 | Complete | deterministic A/B and independent verifier PASS |
| Corrected MXFP4 construction | Complete | full 129-tensor routed rebuild and provenance PASS |
| Dual-5090 runtime | Complete | 64K startup/API/behavior/32K prefill PASS |
| Mixed candidate evaluation | Complete; rejected | same-runtime MXFP4 A/B isolates semantic collapse |
| Deployment alignment | Complete | launcher and repo entry points target corrected MXFP4 |
| Q2 routed-recipe repair | Complete; rejected | structure/direct-I/O/startup passed; short semantic gate failed and payload was deleted |

## Phase 4 Gates

1. Freeze and audit the external revision, Q2 recipe, final imatrix, and `.prev`
   stability checkpoint.
2. Generate a deterministic routed-only tensor-type plan with 15 MXFP4, 76
   Q2_K, and 38 Q3_K tensors. Non-routed selection remains default non-pure
   IQ4_XS mixed.
3. Complete a DIO dry-run and independently verify all 1,328 tensor targets.
4. On a clean boot, atomically build and O_DIRECT-verify one candidate.
5. Run raw/chat/Chinese/JSON/Python probes first. Only a complete short-probe
   PASS permits the 32K prefill/decode gate.
6. The Q2 candidate failed the short semantic gate, so 32K was intentionally
   skipped and the candidate was deleted; corrected MXFP4 remains deployed.

## Completion Rule

Deployment remains complete only while the launcher, README, AGENTS, Wiki, and
this scope agree on the same artifact identity and runtime flags. A future
candidate needs structural, direct-I/O, kernel, and semantic acceptance before
promotion.

## Decision Log

- The puwaer Q2/Q3 candidate was one bounded Phase 4 trial and did not change
  the deployment baseline.
- Structural and 64K startup PASS did not override the fixed short semantic
  FAIL. T088 was skipped by the dependency rule.
- The candidate was rejected and deleted; no new branch or scope was created.
