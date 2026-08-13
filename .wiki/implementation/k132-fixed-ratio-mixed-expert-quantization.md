---
title: K132 fixed-ratio mixed expert quantization
type: implementation
status: current
scope: heretic-v2-reap132-mixed-expert-quant
related_scopes:
  - heretic-v2-reap96-consensus
  - heretic-v2-reap96-iq4xs-backbone
related_files:
  - .scopes/heretic-v2-reap132-mixed-expert-quant
  - vendor/llama.cpp/src/llama-quant.cpp
  - vendor/llama.cpp/tools/imatrix/imatrix.cpp
source_docs:
  - .scopes/heretic-v2-reap132-mixed-expert-quant/heretic-v2-reap132-mixed-expert-quant-technical-documentation.md
tags:
  - reap132
  - imatrix
  - iq3-xxs
  - q2-k
last_checked: 2026-08-13
updated: 2026-08-12T23:37:18Z
---

# K132 fixed-ratio mixed expert quantization

Active fixed-ratio K132 heterogeneous routed-expert quantization experiment.

## Immutable baseline

The sole model input is the read-only canonical K132 MXFP4 GGUF with size
`85,049,305,696` bytes and SHA256
`f436ed2f92e6d6d49b5c73c546f2d52a6fa277b9f72d9915bff08b9385bb286b`.
It remains the deployed and rollback artifact.

## Fixed experiment

- Preserve 43 layers, 132 routed experts per layer, top-k 6, router, and
  `tid2eid`.
- Exactly 17 protected/high-priority layers use IQ3_XXS.
- Exactly 26 ordinary layers use the true llama.cpp Q2_K_S recipe.
- The ratio is fixed independently of output size. There is no 60GB gate and
  no all-IQ3 comparison artifact in this scope.
- The fork supplies routed-only per-region effective ftypes so Q2_K_S keeps its
  built-in selector behavior; a flat Q2_K tensor override is not equivalent.

Only the 129 routed-expert packed tensors receive manual overrides. Shared
Expert, Core Backbone, attention, indexer, embedding, output, and other eligible
non-routed weights use the same default non-pure IQ4_XS mixed policy as the
archived K96 Profile A release, including llama.cpp's automatic Q5/Q6 choices.

## Layer evidence

The structural prior is fixed as:

```text
R_l = 0.50 * consensus_mass
    + 0.20 * rank97_normalized_score
    + 0.15 * (high_score_count / 132)
    + 0.10 * (deleted_high_count / 36)
    + 0.05 * boundary_tie
```

The activation score first normalizes each gate/up/down imatrix entry by route
count and activation width, averages the three projections per expert, then
forms a route-count-weighted mean over all 132 experts. The 43 raw layer values
become `I_l` through ascending mid-rank percentile normalization. Zero-count or
projection-count-mismatched experts block plan generation.

```text
P_l = 0.4 * R_l + 0.6 * I_l
```

Ranks 1-17 become the IQ3_XXS recipe; ranks 18-43 become the Q2_K_S recipe. Imatrix is activation
importance evidence, not a direct per-layer quantization-sensitivity test.

The fork hard-requires the same accepted imatrix for IQ3_XXS, Q2_K_S, and all
quantizable effective-IQ4_XS tensors except the existing embedding/output
exceptions. The gate follows the effective recipe, so a Q2_K_S tensor promoted
to Q4_K remains covered. A missing, wrong-width, or non-finite entry blocks
production, including dry-run validation. Embedding and output retain their
existing exceptions and llama.cpp remains responsible for their concrete types.

## Current gate

Phase 1 must implement and verify structural extraction, freeze calibration
corpus identity, collect cumulative 100/200/300/400-chunk K132 imatrix through
`--load-mode dio`, and pass finite
per-expert coverage before the 17-layer list is generated.
