---
description: Execution and verification hub for K132 fixed 17/26 mixed expert quantization.
---

# Phases Checklist: heretic-v2-reap132-mixed-expert-quant

## Input

- Scope contracts and technical documentation in the parent directory.
- Immutable K132 Golden and archived K96 score report.
- Pinned llama.cpp submodule `2abf1748`.

## Global Status Board

| Phase | Status | Completion | Health | Blockers |
|---|---|---:|---|---:|
| Phase 1 - Structural prior and imatrix | In progress | 25% | Healthy | 0 |
| Phase 2 - Freeze 17/26 plan | Not started | 0% | Unknown | 1 |
| Phase 3 - DIO production artifact | Not started | 0% | Unknown | 1 |
| Phase 4 - Runtime acceptance | Not started | 0% | Unknown | 1 |

## Locked Rules

- Exactly 17 IQ3_XXS and 26 Q2_K routed-expert layers.
- Shared Expert, Core Backbone, and sensitive non-routed weights use the same
  default non-pure IQ4_XS mixed policy as archived K96 Profile A.
- No size gate, `--pure`, second profile, or all-IQ3 artifact.
- No K132 Golden, router, `tid2eid`, or expert-count changes.

## Phase Entry Links

1. [Phase 1](phase-1-heretic-v2-reap132-mixed-expert-quant.md)
2. [Phase 2](phase-2-heretic-v2-reap132-mixed-expert-quant.md)
3. [Phase 3](phase-3-heretic-v2-reap132-mixed-expert-quant.md)
4. [Phase 4](phase-4-heretic-v2-reap132-mixed-expert-quant.md)

## Phase Execution Records

### Phase 1

- Scope branch created from pushed `master` commit `992cd90`.
- Source inspection confirmed IQ3 imatrix requirement, Q2_K override support,
  DIO imatrix loading, and packed-expert per-ID collection.
- Read-only dry-runs recorded all-Q2 and all-IQ3 feasibility sizes; these do not
  alter the fixed ratio.
- T001 PASS: structural-prior extractor validated the archived K96 report,
  produced all 43 contracted records, and reproduced byte-identically. Source
  SHA256 is `ae090c1b...47bfa`; report logical SHA256 is
  `4493d0e9...a7e64f`; focused tests passed `2/2`.
- Pending: calibration corpus contract, imatrix run, and coverage gate.

### Phase 2

- Blocked by Phase 1 imatrix acceptance.

### Phase 3

- Blocked by frozen and independently verified Phase 2 plan.

### Phase 4

- Blocked by verified Phase 3 candidate.

## Final Release Gate

- 43 layers, 132 experts, top-k 6, no routing drift.
- Exactly 51 IQ3_XXS and 78 Q2_K routed-expert tensors.
- Non-routed type selection matches default K96 Profile A-style IQ4_XS mixed
  behavior without manual overrides.
- Direct-only hash/provenance and clean runtime gates pass.
- Semantic result and deployment decision are explicit; K132 remains rollback.
