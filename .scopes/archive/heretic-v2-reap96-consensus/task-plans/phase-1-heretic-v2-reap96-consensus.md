---
description: Lock and validate external survivor-mask evidence for K96 consensus.
---

# Tasks: heretic-v2-reap96-consensus Phase 1

## Input

- `.scopes/archive/heretic-v2-reap96-consensus/` contracts and research notes
- `squanchyzx-puwaer-reap132-mask.json`
- Archived REAP132 scope and implementation wiki record

## Canonical Architecture / Key Constraints

- K132 is immutable and is the only candidate universe.
- Fetch only approved small mask/plan/manifest artifacts at pinned revisions.
- Reject sources that lack original-ID proof; do not download weights or GGUF.

## Phase 1: Evidence Lock and Normalization

Goal: create reproducible normalized masks and a lineage audit without creating
a K96 plan or touching large model artifacts.

Definition of Done: approved sources have revision/digest records, normalized
43-layer masks with valid original IDs, and a reproducible overlap report.

Tasks:

- [ ] T001 [Docs] Record approved source URLs, revision pins, lineage labels,
  coverage, and the explicit no-weights policy.
  - DoD: The evidence lock contains only small machine-readable artifacts and
    rejects unpinned or unverifiable source metadata.
- [ ] T002 [Backend] Generalize mask extraction/normalization without changing
  the frozen K132 extractor or plan.
  - DoD: New code emits `reap-expert-mask-v1` files with sorted original IDs,
    source digest, K, and layer coverage.
- [ ] T003 [QA] Add schema, malformed-input, original-ID, and 43-layer
  coverage tests.
  - DoD: Focused pytest rejects compact/unproven IDs, duplicates, wrong K, and
    missing layers.
- [ ] T004 [Backend] Produce the first lineage-aware overlap report.
  - DoD: Per-layer intersections, Jaccard values, K132 subset checks for K178,
    and K160/K216 nesting are stored with source digests.

Checkpoint: M1 evidence report is reviewed and passes before any scoring or
hash-routing work starts.

## Dependencies & Execution Order

T001 blocks T002/T004. T002 and T003 may proceed together after formats are
defined. Phase 1 blocks all later phases.
