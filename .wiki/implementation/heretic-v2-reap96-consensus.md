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
updated: 2026-08-13T01:58:00+08:00
---

# HERETIC v2 REAP96 consensus candidate

K96 is a separate candidate derived only from the immutable 43-layer REAP132
survivor universe. Phases 1 and 2 are complete, and the Phase 3 native A/B build
and GGUF provenance gates have passed. The canonical REAP132 GGUF remains
immutable and deployed until K96 passes runtime acceptance.

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
578adbbd4ac13bec75f5ab726e6406f9bec50ec8154f6d773d9c5bd83105be11

plan logical SHA256:
e82c3649af2607e798b88e39ac0dd9a4b71dc3b31b5f4f17b60fc12aa74c01cf

score report SHA256:
ae090c1b70b476d7f116827d9342f8d2a7ff68ee36996912ce33a42735c47bfa
```

A deterministic regeneration was byte-identical and the independent verifier
reports `PASS` with zero failures.

## Hash routing

The K132 `tid2eid` tables cannot be reused because they contain compact IDs for
132 experts. For Layers 0-2, direct K96 survivors are preserved. Deleted K132
assignments map to the nearest available K96 router row by normalized cosine
similarity; equal similarity uses K132 compact ID and IDs already used in the
token row are excluded. This is the vendor-aligned fallback.

| Layer | Direct | Replaced | Replacement rate | Collision avoids |
|---:|---:|---:|---:|---:|
| 0 | 609,445 | 166,235 | 21.43% | 10,513 |
| 1 | 580,282 | 195,398 | 25.19% | 13,768 |
| 2 | 540,025 | 235,655 | 30.38% | 35,979 |

Every table is `[129280, 6]` int64, has values `0..95`, uses all 96 experts,
and every token row contains six distinct expert IDs.

The routing audit compared all 108 deleted hash experts. Raw L2 and cosine chose
different primary replacements for 89 and changed 481,044 actual slots, so raw
L2 is superseded. A row-global assignment changed 12,169 rows but improved the
cosine cost by only 0.0225%; deterministic greedy collision repair remains
canonical.

## Native acceptance

The accepted K132 manifest was rechecked at
`9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`.
Two clean-boot O_DIRECT K96 builds each produced 17 shards and 26,332 tensors.
Independent verification passed expert weight/scale, router, `tid2eid`, shared
expert, HERETIC overlay, no-MTP, and dangling-ID checks with zero failures.

Both builds had 22 identical manifest entries totaling `63,989,574,313` bytes
at manifest SHA
`62e40f7cecc2d1018faa8c386b39268f9d13cb3833c9f82f365e99bfa5f574ed`.
Build B was promoted read-only to
`/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP`.
Build A was deleted after A/B acceptance to recover disk space.

## GGUF acceptance

The pinned llama.cpp converter at
`1e17097be2c19c7ae4ff4f635fef25f24f25dbd2` converted the accepted K96 native
checkpoint with direct input and output I/O. The resulting read-only candidate
is:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4.gguf
```

It is `64,340,873,568` bytes with O_DIRECT SHA256
`697309d18ada765bdce2a72b52cb1497ed5e374cd5c77edfa7fc0085aa68ff31`.
Header inspection reports `deepseek4`, 43 blocks, 96 routed experts, six active
experts, 1,328 tensors, file type 38 (`MOSTLY_MXFP4_MOE`), three hash-routing
tensors, and 129 routed-expert MXFP4 tensors.

Independent aligned direct-I/O payload provenance passed:

| Class | Result | Report SHA256 |
|---|---:|---|
| MXFP4 routed experts | 108/108 | `bcba6c76...a76966` |
| Nonexpert tensors | 7/7 | `c8cbbc60...52675a` |
| FP8 backbone to runtime Q8_0 | 104/104 | `078d5303...4ed622` |

The compact acceptance record is
`.scopes/heretic-v2-reap96-consensus/evidence/gguf/reap96-gguf-acceptance.json`.

## Risk and next gate

This is K132-constrained, 0xSero-dominant, multi-source boundary consensus. It
is aggressive-but-evidence-guided pruning, not conservative pruning: no score-5
expert is removed, but 309 score-4 experts are removed and 36 learned-router
layers cross into their score-4 group. Layer 26 is the only strict 4/3 boundary.
Layers 37, 39, and 41 are quality-sensitive examples. The 21.43%-30.38% static
hash-route replacement is the largest early-layer semantic risk.

These risks do not invalidate the plan's structural correctness. The native and
GGUF provenance gates are complete. Phase 3 must next run dual-5090
semantic/runtime acceptance. Any failure leaves the deployed K132 GGUF
canonical.
