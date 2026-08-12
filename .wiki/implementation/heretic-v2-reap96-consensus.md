---
title: HERETIC v2 REAP96 consensus candidate
type: implementation
status: current
scope: heretic-v2-reap96-consensus
related_scopes:
  - deepseek-v4-flash-0731-dual-5090
related_files:
  - .scopes/heretic-v2-reap96-consensus
  - squanchyzx-puwaer-reap132-mask.json
  - README.md
  - AGENTS.md
source_docs:
  - .scopes/heretic-v2-reap96-consensus/heretic-v2-reap96-consensus-technical-documentation.md
tags:
  - reap96
  - consensus
  - provenance
last_checked: 2026-08-13
updated: 2026-08-12T16:52:47Z
---

# HERETIC v2 REAP96 consensus candidate

K96 is a separate candidate derived only from the immutable 43-layer REAP132
survivor universe. Phases 1 and 2 are complete. The canonical REAP132
checkpoint and GGUF remain immutable and deployed until a separate K96 artifact
passes every Phase 3 gate.

## Evidence matrix

| Source | K / layers | Role | Immutable identity |
|---|---|---|---|
| Frozen puwaer K132 | 132 / 0-42 | Hard candidate universe | Local frozen plan |
| puwaer K178 | 178 / 0-42 | Zero-weight nesting audit | `c1dd22d2...`; exact recovery logical SHA `09f66d74...` |
| 0xSero K160 | 160 / 0-42 | Strong ordinal evidence | `ddc04540...`; exact recovery logical SHA `ccb46a9f...` |
| heath0xFF K216 plan | 216 / 0-42 | Weak 0xSero ordinal tier and semantic rank | `9f8c8a7a...`; payload SHA `cc2bdaf1...` |
| Blivion K192 | 192 / 0-42 | Independent vote | `eb6e3479...`; payload SHA `47b4149e...` |
| REAP25 K192 | 192 / 3-42 | Independent learned-layer vote | `ljubomirj/ds4@01bdc35a...`; B-exact map SHA `ee095012...` |
| True2456 K163 | 163 / 3-42 | Independent learned-layer vote | `1697a22c...`; payload SHA `804d70a1...` |

No external checkpoint shard or GGUF payload was downloaded. K160 and K178
were recovered 43/43 by exact base-to-pruned router matching through bounded
remote reads. `K132 subset K178` and `K160 subset K216` hold in every layer.

## Selection contract

Only K132 members can be selected. The score is:

```text
0xSero K160       +2
0xSero K216-only  +1
Blivion K192      +1
REAP25 K192       +1  (Layers 3-42 only)
REAP37 K163       +1  (Layers 3-42 only)
puwaer K178       +0  (nesting audit only)
```

Descending ties resolve by the evidence vector `K160, K216, Blivion, REAP25,
REAP37`, then K216's complete published semantic rank, then original expert ID
as a theoretical stable fallback. K216 semantic rank is not another vote: it
is finer ordering from the same 0xSero lineage.

The 96/97 score boundary ties in 42 of 43 layers. Three layers resolve by a
stronger evidence vector and 39 invoke K216 semantic rank; no layer reaches the
expert-ID fallback. Across those semantic-rank boundary groups, 700 candidates
are compared, 444 retained, and 256 deleted. Relative to ID-only fallback, the
rank changes 38 layer selections and swaps 113 experts; Layer 39 invokes the
rank but happens to retain the same set.

## Frozen result

The score histogram is exact:

| Score | Candidates selected | Candidates deleted |
|---:|---:|---:|
| 5 | 1,969 | 0 |
| 4 | 1,867 | 309 |
| 3 | 277 | 913 |
| 2 | 15 | 293 |
| 1 | 0 | 31 |
| 0 | 0 | 2 |
| Total | 4,128 | 1,548 |

The earlier 4,171 selected summary was only a report bug that double-counted
one boundary row per layer. The JSON and frozen plan always contained exactly
`43 x 96 = 4,128` selected experts.

Frozen artifacts:

```text
plan file SHA256:
2890f1cfebc53e0a4c4b9f391af84789e6289d9a40800182a97ca91c190c3934

plan logical SHA256:
7d69d87208e2d2776adc291e68db7c15ff09ff78665798b2828d66ea536a822a

score report SHA256:
ae090c1b70b476d7f116827d9342f8d2a7ff68ee36996912ce33a42735c47bfa
```

A deterministic regeneration was byte-identical and the independent verifier
reports `PASS` with zero failures.

## Hash routing

The K132 `tid2eid` tables cannot be reused because they contain compact IDs for
132 experts. For Layers 0-2, direct K96 survivors are preserved. Deleted K132
assignments map to the nearest available K96 router row by squared L2 distance;
equal distances use K132 compact ID and IDs already used in the token row are
excluded.

| Layer | Direct | Replaced | Replacement rate | Collision avoids |
|---:|---:|---:|---:|---:|
| 0 | 609,445 | 166,235 | 21.43% | 16,364 |
| 1 | 580,282 | 195,398 | 25.19% | 31,338 |
| 2 | 540,025 | 235,655 | 30.38% | 21,787 |

Every table is `[129280, 6]` int64, has values `0..95`, uses all 96 experts,
and every token row contains six distinct expert IDs.

## Risk and next gate

This is K132-constrained, 0xSero-dominant, multi-source boundary consensus. It
is aggressive-but-evidence-guided pruning, not conservative pruning: no score-5
expert is removed, but 309 score-4 experts are removed and 36 learned-router
layers cross into their score-4 group. Layer 26 is the only strict 4/3 boundary.
Layers 37, 39, and 41 are quality-sensitive examples. The 21.43%-30.38% static
hash-route replacement is the largest early-layer semantic risk.

These risks do not invalidate the plan's structural correctness. Phase 3 must
build a separate no-MTP checkpoint with the existing aligned O_DIRECT path,
independently verify it, convert and prove the MXFP4 GGUF, then run dual-5090
semantic/runtime acceptance. Any failure leaves K132 canonical.
