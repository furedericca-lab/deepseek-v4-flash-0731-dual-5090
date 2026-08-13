---
title: K132 fixed-ratio mixed expert quantization
type: implementation
status: historical
scope: heretic-v2-reap132-mixed-expert-quant
related_scopes:
  - heretic-v2-reap96-consensus
  - heretic-v2-reap96-iq4xs-backbone
related_files:
  - .scopes/archive/heretic-v2-reap132-mixed-expert-quant
  - vendor/llama.cpp/src/llama-quant.cpp
  - vendor/llama.cpp/tools/imatrix/imatrix.cpp
source_docs:
  - .scopes/archive/heretic-v2-reap132-mixed-expert-quant/heretic-v2-reap132-mixed-expert-quant-technical-documentation.md
tags:
  - reap132
  - imatrix
  - iq3-xxs
  - q2-k
last_checked: 2026-08-13
updated: 2026-08-13T14:10:00+08:00
---

# K132 fixed-ratio mixed expert quantization

Historical record of the rejected fixed-ratio K132 heterogeneous routed-expert
quantization experiment. Active replacement work is Phase 4 of the deployment
scope.

## Immutable baseline

The sole quantization input is the corrected read-only K132 MXFP4 GGUF ending
in `full-routed-rebuild.gguf`, size `85,049,305,696` bytes and O_DIRECT SHA256
`752a0146f54d5c5bc34491d53f9e1acbb63540b1e3c38bd352185b508418cfdd`.
All 129 complete routed tensors were rebuilt from accepted native K132 and the
independent verifier compared 75,884,396,544 bytes with zero failures. The old
K132 GGUF and a mutated converter intermediate were rejected and deleted.

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

Phase 1 and Phase 2 are complete. A clean-boot production run using byte-identical
Golden and imatrix copies on the CPU-attached root NVMe completed all 1,328
tensors and produced the exact dry-run size `55,348,319,104` bytes. The
independent verifier passed the full tensor/type contract, including 51
IQ3_XXS, 73 Q2_K, five Q2_K_S Q4_K promotions, and 600 byte-identical unchanged
tensors with zero unstable reads. The root-NVMe candidate has O_DIRECT SHA256
`67e6990f35db44711c881aee2b55ca789144bec2c0063df2e78957555ea77ab3`.

The fixed-ratio candidate was copied, rehashed, and tested, then rejected after
its same-runtime semantic A/B failed. The payload and root staging copy were
deleted. Phase 4 of the deployment scope later evaluated puwaer's
boundary-protected Q2 recipe; that second candidate also passed structure and
startup but failed its fixed short semantic gate and was deleted without a 32K
run. Corrected MXFP4 remains the sole deployment artifact.

A fresh corrected-Golden imatrix was generated from the same 200-chunk corpus
after the old routed-payload mutations were discovered. Against the accepted
imatrix it has raw-I Spearman `1.0`, no Rank-I or Rank-P changes, and zero
activation/final Top17 churn. The comparison therefore retains the accepted
imatrix and the existing frozen 17/26 assignment rather than introducing a new
plan identity.

The reusable host, artifact-provenance, double-read direct-I/O, atomic
publication, and storage-topology lessons are recorded in
[K132 mixed quant host and direct IO lessons](../reflections/k132-mixed-quant-host-io-lessons.md).
