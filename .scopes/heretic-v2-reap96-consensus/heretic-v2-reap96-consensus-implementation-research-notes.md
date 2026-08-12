---
description: Evidence-based design for deriving a separate K96 plan from REAP132.
---

# heretic-v2-reap96-consensus Implementation Research Notes

## Baseline (Current State)

`squanchyzx-puwaer-reap132-mask.json` is an immutable 43-layer, 132-expert
plan. It produced an accepted 35,620-tensor no-MTP checkpoint and canonical
85,049,305,696-byte MXFP4 GGUF. The K132 artifact remains the only deployment
release during this scope.

The user supplied a ranked source set: puwaer K178, 0xSero K160 and K216,
Blivion K192, and REAP25 K192. These are evidence sources only. Their weights
or GGUF payloads are not required and must not be downloaded.

## Gap Analysis

The original `scripts/extract_puwaer_reap132_mask.py` was K132-specific and
recovered original expert IDs from exact router row matching. It now supports
parameterized K, atomic per-layer fragments, layer ranges, and resume without
changing the exact matching contract. `scripts/reap96_evidence.py`,
`scripts/normalize_reap96_evidence.py`, `scripts/score_reap96_consensus.py`,
`scripts/build_reap96_plan.py`, and `scripts/verify_reap96_plan.py` now own the
normalized evidence, scoring, hash-routing generation, and independent plan
verification stages.

The three K132 hash-layer tables encode compact K132 IDs. They become invalid
when 36 retained experts are removed per layer and therefore cannot be copied
into K96.

## Candidate Designs and Trade-offs

| Design | Benefits | Cost / Risk | Result |
|---|---|---|---|
| Independent fresh K96 REAP | One direct score | Reopens calibration and frozen-mask work | Rejected |
| Intersection of every source | Simple | Often not exactly K96 and destroys ranking information | Rejected |
| K132 subset with lineage-aware score | Preserves accepted baseline and uses independent signals | Requires transparent source/identity validation | Selected |

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Candidate universe is K132 | 5 | 5 | User instruction and frozen plan | None | 5 | 5 | 5 | Strictly retains accepted survivor lineage | Accepted |
| Use four independent ranking lineages | 5 | 5 | Pinned and normalized source evidence | Layer coverage differs | 5 | 5 | 4 | puwaer is the universe/audit lineage; 0xSero is ordinal; three independent masks resolve boundaries | Accepted |
| Use tiers only after nesting checks | 5 | 4 | User lineage analysis | K132/K178 and K160/K216 nesting unknown | 5 | 5 | 5 | Avoids treating non-nested masks as ranks | Accepted |
| Use True2456 only on Layers 3-42 | 5 | 4 | Pinned published `keep` lists | Hash layers use REAM merge | 5 | 5 | 5 | Its learned-layer original IDs are valid supplemental evidence; Layers 0-2 remain excluded | Accepted |

## Selected Design

Normalize all evidence into original 256-expert ID masks. Score only K132
members. Use 0xSero K160/K216 as +2/+1 ordinal evidence only when K160 is a
subset of K216; otherwise record each as separate binary evidence. Treat puwaer
K178 similarly only after testing K132 subset relation. Blivion and REAP25 add
one vote where they cover a layer. Stable tie-breaking is mandatory: descending
score, source-agreement vector, the pinned K216 plan's complete per-layer
semantic rank, then original expert ID only as a fallback. The final report
must expose every selected/deleted expert's score and evidence vector.

For Layers 0-2, derive a new `tid2eid` table from the trusted base/router data
and the final keep set. Preserve direct surviving assignments; map deleted K132
compact IDs by squared L2 distance between K132 router rows, resolve equal
distances by compact ID, and exclude row-local duplicates.

## Validation Plan

1. Unit-test source normalization with malformed IDs, incomplete layers,
   duplicate entries, and compact-ID rejection cases.
2. Unit-test consensus selection against synthetic nested and non-nested masks.
3. Validate every K96 layer is a 96-member subset of K132 and report overlaps,
   Jaccard values, and score-boundary ties.
4. Validate K96 hash routing is `[129280, 6]`, `int64`, values `0..95`, and
   has unique IDs in every row.
5. Only after these pass, use the existing production builder/verifier and
   llama.cpp gates on a clean boot.

## Risks and Assumptions

Published pages cited by the user must be fetched and revision-pinned before
their content becomes build evidence. The user-provided description is a design
input, not proof of an exact JSON schema. K96 may fail semantic/runtime gates;
that outcome leaves K132 deployable and does not reopen the archived scope.

The frozen result is K132-constrained and 0xSero-dominant rather than five
equal votes. It removes no score-5 expert, but removes 309 score-4 experts and
therefore represents aggressive-but-evidence-guided pruning. The largest
semantic risk is the regenerated static hash routing: replacement rates rise
from 21.43% in Layer 0 to 30.38% in Layer 2. These are model-quality risks for
Phase 3, not unresolved structural defects in the plan.
