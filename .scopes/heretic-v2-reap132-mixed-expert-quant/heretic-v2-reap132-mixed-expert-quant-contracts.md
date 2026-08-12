---
description: Data and artifact contracts for fixed 17/26 K132 routed-expert quantization.
---

# K132 Mixed Expert Quantization Contracts

## Immutable Input Contract

The sole model input is the read-only K132 Golden:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/
DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf
```

| Property | Required value |
|---|---|
| Size | `85,049,305,696` bytes |
| SHA256 | `f436ed2f92e6d6d49b5c73c546f2d52a6fa277b9f72d9915bff08b9385bb286b` |
| Architecture | `deepseek4` |
| Blocks | 43 |
| Routed experts | 132 per layer |
| Experts per token | 6 |
| Routed-expert tensors | 129 packed MXFP4 tensors |
| Tensor count | 1,328 |

The input must remain mode `0444`; this scope never rewrites, renames, or
promotes over it.

## Structural Prior Schema

For each layer `l`, derive from the archived K96 score report:

- `normalized_consensus_mass`
- `rank96_normalized_score`
- `rank97_normalized_score`
- `high_score_count`
- `deleted_high_count`
- `boundary_tie`
- descriptive K216 semantic-rank statistics

Layers 0-2 normalize expert score by 3; layers 3-42 normalize by 5. Define:

```text
H_l = high_score_count / 132
D_l = deleted_high_count / 36
B_l = 1 when boundary_tie is true, otherwise 0

R_l = 0.50 * normalized_consensus_mass
    + 0.20 * rank97_normalized_score
    + 0.15 * H_l
    + 0.10 * D_l
    + 0.05 * B_l
```

Every input is in `[0,1]`, so `R_l` is already in `[0,1]` and receives no
second normalization. `rank96_normalized_score` remains diagnostic because it
is strongly coupled to rank 97. K216 rank is a same-lineage final tie-break,
not another vote and not part of `R_l`.

## Imatrix Contract

`llama-imatrix` runs against the K132 Golden with `--load-mode dio`. Its GGUF
output must provide finite values and per-expert counts for each of the 129
packed routed-expert tensors. The collector's merged-expert format stores one
count and one activation vector per expert.

For layer `l`, projection `p` in `{gate, up, down}`, compact expert `e`, and
activation coordinate `j`, let the imatrix provide raw squared-activation sum
`S_l,p,e,j`, activation width `W_l,p`, and routed count `C_l,p,e`. First remove
projection-width and sample-count scale:

```text
a_l,p,e = sum_j(S_l,p,e,j) / (C_l,p,e * W_l,p)
```

The gate/up/down counts for one expert must be equal and non-zero. A mismatch or
zero-count expert blocks Phase 2; no epsilon, default, interpolation, or
cross-expert fill is allowed. Let their common value be `C_l,e`, then:

```text
A_l,e = (a_l,gate,e + a_l,up,e + a_l,down,e) / 3

raw_I_l = sum_e(C_l,e * A_l,e) / sum_e(C_l,e)
```

Normalize the 43 finite `raw_I_l` values with ascending mid-rank percentile:

```text
I_l = average_zero_based_rank(raw_I_l among 43 layers) / 42
```

Equal raw values receive the same average rank. Ranking uses the exact binary64
aggregation result, not rounded JSON text. Imatrix is activation-importance
evidence, not a direct measurement of per-layer quantization sensitivity. The
plan report records all raw aggregation fields, normalization ranks, corpus
identity, token/chunk counts, coverage result, and input imatrix SHA256.

## Quantization Plan Contract

For every layer:

```text
P_l = 0.4 * R_l + 0.6 * I_l
```

Sort by descending `P_l`, then descending `I_l`, descending `R_l`, ascending
mean K216 semantic rank, and ascending layer ID. Exactly ranks 1-17 use
`IQ3_XXS`; ranks 18-43 use `Q2_K`.

The plan must contain:

- all 43 unique layer IDs;
- exactly 17 `IQ3_XXS` and 26 `Q2_K` assignments;
- the full ranking inputs and tie-break values;
- source artifact identities and llama.cpp commit;
- deterministic logical and file SHA256 values.

`Q2_K_S` may appear only as a human-readable policy label. It is never passed
to `--tensor-type`; the concrete routed tensor encoding is `Q2_K`.

## Artifact Contract

| Tensor class | Treatment |
|---|---|
| Routed Experts in 17 protected layers | `IQ3_XXS` |
| Routed Experts in 26 ordinary layers | `Q2_K` |
| Shared Expert | same default non-pure `IQ4_XS` mixed policy accepted in the archived K96 Profile A scope |
| Core Backbone | same default non-pure `IQ4_XS` mixed policy accepted in the archived K96 Profile A scope |
| Attention, indexer, embedding, output and other eligible non-routed weights | llama.cpp default IQ4_XS selection with automatic Q5/Q6 promotions where its built-in policy requires them |
| Router and `tid2eid` | unchanged type, shape, and bytes |
| Norm, RoPE, sink, structural tensors | unchanged when not quantizable |

The routed-expert overrides are the only manual tensor-type policy. Shared
Expert, Core Backbone, and sensitive attention-related weights must not receive
scope-specific Q5/Q6/Q8 overrides; their concrete types come from the same
llama.cpp IQ4_XS mixed logic used by
`.scopes/archive/heretic-v2-reap96-iq4xs-backbone/`. No `--pure` profile is
allowed. The imatrix is required for IQ3_XXS. Output size is reported but has no
pass/fail threshold.

## Validation and Compatibility Rules

- Metadata remains 43 blocks, 132 experts, top-k 6, no MTP/DSpark.
- The tensor namespace and tensor count remain identical to the Golden.
- All 51 protected-layer packed tensors are IQ3_XXS; all 78 ordinary-layer
  packed tensors are Q2_K.
- All 43 router tensors and three `tid2eid` tensors are byte-identical.
- Output is read-only and has an O_DIRECT SHA256.
- Production quantization begins only after clean boot, imatrix acceptance, and
  frozen plan verification.
- Runtime acceptance never promotes the candidate over K132 without semantic
  gates; K132 remains rollback and deployment baseline.

## Requirement Boundary Notes

This scope does not prune experts, change routing, recompute REAP, change the
17/26 ratio, enforce a 60GB target, build an all-IQ3 comparison artifact, or run
a second quantization profile. Any such experiment requires a new scope.
