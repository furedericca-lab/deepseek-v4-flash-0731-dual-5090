---
description: Scope boundaries and gates for K132 fixed-ratio mixed expert quantization.
---

# K132 Mixed Expert Quantization Scope and Milestones

## In Scope

- K132 structural-prior extraction from archived K96 evidence.
- K132 DIO imatrix calibration and routed-expert coverage analysis.
- Deterministic 17 IQ3_XXS-recipe / 26 Q2_K_S-recipe layer plan.
- One candidate whose Shared Expert, Core Backbone, and sensitive non-routed
  weights use the same default non-pure IQ4_XS mixed policy as the archived K96
  Profile A release.
- DIO production, provenance, O_DIRECT SHA256, and dual-5090 acceptance.

## Out of Scope

- Any expert pruning, REAP recalculation, router or `tid2eid` rewrite.
- A 60GB pass/fail target or size-driven changes to the 17/26 ratio.
- All-IQ3, all-Q2, global Q2_K_S, `--pure`, or second-profile artifacts.
- Promotion over canonical K132 before full semantic acceptance.
- Changes to the archived K96 plan or K96 artifacts.

## Decision Log

| Boundary / Decision | Evidence Source | Evidence Strength | Conflict | Confidence | Confidence Reason | Result |
|---|---|---:|---|---:|---|---|
| Exactly 17 IQ3 and 26 Q2_K_S recipe layers | User direction | 5 | All-IQ3 dry-run is below 60GB | 5 | Fixed experiment, not size optimization | Frozen |
| `P=0.4R+0.6I` | User direction and imatrix source support | 4 | Corpus sensitivity remains | 4 | Coverage gate controls remaining uncertainty | Phase 1 gate |
| Q2_K_S is a true regional recipe | User clarification and pinned selector | 5 | Stock CLI has one global ftype | 4 | Add routed-only effective-ftype override | Frozen with fork gate |
| Default non-pure IQ4_XS for non-routed | User direction and accepted K96 release | 5 | None | 5 | Existing tested policy | Frozen |
| Size is measurement only | User direction | 5 | Earlier 60GB objective | 5 | Latest requirement supersedes old gate | Frozen |

## Milestones

### M1 - Evidence and Imatrix

Produce accepted structural-prior and K132 imatrix coverage reports. No model
quantization may begin in this milestone.

### M2 - Frozen 17/26 Plan

Generate and independently verify a deterministic 43-layer plan and exact
`--tensor-ftype-file` input. Dry-run must report the expected 51/78 expert recipe
split and that imatrix is available.

### M3 - Production Artifact

On a clean boot, run one DIO quantization, verify zero exit and post-run kernel
health, then run direct-only structure, type, routing, and SHA gates.

### M4 - Runtime Acceptance

Run the established dual RTX 5090 64K baseline, raw/chat/Chinese/JSON/Python,
32K prefill, memory/swap, and kernel/Xid probes. Record semantic differences
against canonical K132; do not auto-promote.

## Dependencies

- M1 blocks M2-M4.
- M2 blocks production payload creation.
- M3 requires a clean boot and blocks runtime acceptance.
- M4 uses only the verified M3 artifact.

## Exit Criteria

- Exact 17/26 assignment and 129 routed-expert effective-recipe/type inventory.
- K132 routing and structural tensors remain byte-identical.
- Output identity, direct-only provenance, runtime behavior, and residual
  semantic risk are recorded.
- K132 Golden remains immutable and deployable.

## Escalation Triggers

- Imatrix cannot provide finite per-expert data for packed K132 expert tensors.
- Coverage remains materially incomplete after the contracted calibration
  budget, making the 17-layer selection ungrounded.
- Pinned quantizer does not honor the generated 51/78 tensor-ftype split.
- Any BAD_PAGE, compound_head, Oops, GPF, SIGSEGV, or NVIDIA Xid occurs during
  a large task; stop and require a clean boot.
- The candidate would overwrite or mutate the canonical K132 Golden.
