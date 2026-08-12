---
description: Decision framing for fixed 17/26 heterogeneous routed-expert quantization of K132.
---

# K132 Mixed Expert Quantization Brainstorming

## Problem

The canonical K132 MXFP4 GGUF is semantically accepted but weighs
`85,049,305,696` bytes. This experiment keeps every routed expert and all
routing semantics while testing whether layer-selective expert precision can
reduce weight size without repeating K96's expert-deletion quality loss.

## Scope

- Preserve 132 routed experts per layer, top-k 6, router rows, and `tid2eid`.
- Quantize 17 routed-expert layers to `IQ3_XXS` and 26 to `Q2_K`.
- Use default non-pure `IQ4_XS` mixed policy for Shared Expert and Core
  Backbone weights, including llama.cpp's automatic Q5/Q6 promotions.
- Select the 17 protected layers from K96 structural evidence plus a K132
  activation importance matrix.

## Constraints

- The K132 Golden is immutable and remains the deployed artifact.
- Bulk model I/O must use aligned O_DIRECT on a clean boot.
- `IQ3_XXS` requires an imatrix in pinned llama.cpp.
- `Q2_K_S` is a model-level recipe name; per-tensor overrides use the actual
  `Q2_K` GGML encoding.
- Output size is measured evidence, not an acceptance limit.

## Options

| Option | Benefit | Cost / Risk | Decision |
|---|---|---|---|
| All routed layers IQ3_XXS | Highest uniform precision; dry-run is 58,761,560,448 bytes | Does not test the requested heterogeneous policy | Rejected for this scope |
| Fixed 17 IQ3 / 26 Q2 by REAP only | Deterministic and immediately available | Confuses expert-retention consensus with quantization sensitivity | Rejected |
| Fixed 17 IQ3 / 26 Q2 by imatrix only | Direct activation evidence | Ignores durable multi-source structural evidence | Rejected |
| Fixed 17 IQ3 / 26 Q2 by 40% REAP + 60% imatrix | Preserves the requested ratio and combines independent signals | Requires clean K132 calibration and normalization contract | Selected |

## Decision Summary

| Decision | Options Considered | Rationale | Research Note Link |
|---|---|---|---|
| Keep 17/26 allocation fixed | Size-optimized N; all-IQ3; fixed ratio | User explicitly defines the experiment; size is no longer a gate | `Selected Design` |
| Rank with `P_l = 0.4 R_l + 0.6 I_l` | REAP only; imatrix only; combined | Imatrix directly measures activation importance while REAP remains a structural prior | `Selected Design` |
| Use `Q2_K` tensor overrides | `Q2_K_S` override; model-level Q2_K_S | `--tensor-type` parses `ggml_type`, not `llama_ftype` | `Source Findings` |

## Decision

The first and only production candidate in this scope uses exactly 17
IQ3_XXS routed-expert layers and 26 Q2_K routed-expert layers. The layer list is
frozen only after the imatrix coverage and deterministic ranking gates pass.
The term protected does not claim direct quantization sensitivity; imatrix is
activation-importance evidence, not a per-layer Q2 perturbation experiment.

## Risks

- Q2_K requantization from MXFP4 may cause more quality loss than expert
  pruning or uniform IQ3.
- Calibration data may underexercise experts, biasing layer importance.
- A layer aggregate can hide sensitivity differences among gate/up/down packed
  tensors or among experts inside a packed tensor.
- Requantized large payloads require post-build provenance and stability checks;
  source identity cannot be byte-preserved after intentional quantization.

## Open Questions

- Calibration corpus composition and token budget are finalized in Phase 1
  after coverage measurements, without changing the fixed 17/26 allocation.
- The final output filename is frozen with the quantization plan in Phase 2.
