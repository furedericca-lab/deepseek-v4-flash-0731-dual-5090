---
description: Approved Phase 1 evidence sources and minimal retrieval policy for K96 consensus.
---

# K96 Phase 1 Evidence Source Matrix

## Retrieval Policy

Use the logged-in `hf` CLI to retrieve only revision-pinned JSON, manifest, or
other small text evidence files into this scope's evidence directory. Never
download an external model shard or GGUF payload. puwaer K178 is the only source
without a published mask: read its router tensors through bounded remote range
requests after its `config.json` and index are pinned; do not save the shard.

| Priority | Evidence source | Declared K | Layers usable | Minimal evidence | Original-ID proof | Lineage | Phase 1 state |
|---|---|---:|---|---|---|---|---|
| S | Local `squanchyzx-puwaer-reap132-mask.json` | 132 | 0-42 | Existing local frozen plan | Existing 43/43 exact router recovery | puwaer | Ready; candidate universe only |
| S | `puwaer/DeepSeek-V4-Flash-0731-reap-200b` | 178 | 0-42 | `config.json`, index, bounded router tensor ranges | 43/43 exact base-to-pruned router row recovery | puwaer | Accepted and normalized at `c1dd22d...`; exact logical SHA `09f66d7...82200`; zero scoring weight |
| S | `0xSero/DeepSeek-V4-Flash-0731-REAP` | 160 | 0-42 | Published metadata plus bounded native router tensor ranges | 43/43 byte-exact base-to-pruned router recovery | 0xSero | Accepted and normalized at `ddc0454...`; exact logical SHA `ccb46a9...25596` |
| S | `heath0xFF/DeepSeek-V4-Flash-0731-REAP-K216-GGUF` | 216 | 0-42 | `metadata/REAP_K216_PLAN.json` | Published original-ID plan | 0xSero | Accepted and normalized at `9f8c8a7...` |
| A | `BlivionIaG/DeepSeek-V4-Flash-0731-Int4-FP8-REAP-216B` | 192 | 0-42 | `reap_saliency.json` | Published original-ID lists | Blivion | Accepted and normalized at `eb6e347...` |
| A- | `ljubomirj/ds4@reap-compact-support` | 192 | 3-42 | `tools/reap25-prune/keep_map_bexact.json` | Published B-exact four-part recovery to original IDs | REAP25 | Accepted at `01bdc35...`; the linked HF model card points to this source |
| B | `True2456/DeepSeek-V4-Flash-0731-REAP37-native-MLX` | 163 | 3-42 | `reap-plan.json` | Published original-ID `keep` lists | REAP37 | Accepted supplemental mask at `1697a22...` |

## Required Evidence Record

Before normalization, record each source's repository, resolved commit SHA,
requested revision, exact path, local SHA256, declared K, layer coverage,
lineage, and original-ID recovery method. Failure to obtain any of these fields
excludes that source rather than guessing its mask.

## Retrieval Record

Network access recovered on 2026-08-12. All retrieved files are stored below
`evidence/upstream/` with their `hf` download metadata (resolved commit plus
Hub blob identifier). No external weight shard or GGUF payload was downloaded.
The first report is `evidence/reap96-phase1-overlap.json`.
