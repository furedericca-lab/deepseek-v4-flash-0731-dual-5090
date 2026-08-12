---
title: Derive K96 only as a REAP132 subset
type: decision
status: accepted
scope: heretic-v2-reap96-consensus
related_scopes:
  - deepseek-v4-flash-0731-dual-5090
related_files:
  - squanchyzx-puwaer-reap132-mask.json
  - .scopes/heretic-v2-reap96-consensus
source_docs: []
tags:
  - reap96
  - consensus
  - release-policy
last_checked: 2026-08-13
updated: 2026-08-12T16:52:47Z
decision_date: 2026-08-12
---

# Derive K96 only as a REAP132 subset

K96 is a new candidate, not a revision of REAP132. Every layer selects exactly
96 original expert IDs from its immutable K132 set. Published external masks
provide lineage-audited ranking evidence only; no external weights were
downloaded and no fresh REAP calibration ran.

## Accepted rule

0xSero contributes ordinal evidence (`K160 +2`, `K216-only +1`). Blivion K192,
REAP25 K192, and REAP37 K163 each contribute one independent vote where their
layer coverage applies. puwaer K178 has zero selection weight and proves only
that K132 is nested within the broader puwaer tier.

Ties resolve by total score, ordered evidence vector, K216 semantic rank, then
expert ID. K216 rank is same-lineage secondary ordering, not another vote. The
frozen result uses K216 rank in 39 layers and never uses expert ID at an actual
96/97 boundary.

## Accepted plan

The plan contains 4,128 selected experts, exactly 96 per layer, and is a strict
K132 subset. Its file SHA256 is
`2890f1cfebc53e0a4c4b9f391af84789e6289d9a40800182a97ca91c190c3934`;
its logical SHA256 is
`7d69d87208e2d2776adc291e68db7c15ff09ff78665798b2828d66ea536a822a`.
Independent verification passes subset, source digest, score histogram, and all
three regenerated hash-routing invariants.

## Consequence

The accepted plan is frozen for Phase 3 and must not be rescored to improve a
runtime or quality result. It is explicitly aggressive-but-evidence-guided:
309 score-4 experts are removed and early hash-layer assignment replacement
reaches 30.38% in Layer 2. K96 therefore requires the full deterministic
O_DIRECT build, provenance, GGUF, and dual-5090 semantic acceptance sequence
before it can replace K132. A failed K96 gate leaves the canonical K132
deployment unchanged.
