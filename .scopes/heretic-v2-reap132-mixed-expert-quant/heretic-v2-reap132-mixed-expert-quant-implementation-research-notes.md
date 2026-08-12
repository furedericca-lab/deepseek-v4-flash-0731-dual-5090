---
description: Source evidence and design for K132 heterogeneous routed-expert quantization.
---

# K132 Mixed Expert Quantization Implementation Research Notes

## Baseline

The immutable K132 Golden is the sole deployed artifact and is
`85,049,305,696` bytes. It contains 43 layers, 132 routed experts per layer,
top-k 6, 1,328 tensors, and 129 packed MXFP4 routed-expert tensors totaling
`75,884,396,544` logical payload bytes.

The archived K96 consensus report at
`.scopes/archive/heretic-v2-reap96-consensus/evidence/reap96-phase2-score-report.json`
contains all 132 K132 candidates for every layer, including score, evidence
vector, K216 semantic rank, final rank, and K96 selection state. It is usable as
a structural-importance prior without reopening K96.

## Source Findings

- `vendor/llama.cpp` is pinned at
  `2abf1748cc91d64f6ead12ed535a71cb05fd6d3d`.
- `vendor/llama.cpp/src/llama-quant.cpp` requires imatrix data for
  `GGML_TYPE_IQ3_XXS` and emits
  an explicit error for production quantization without it.
- `vendor/llama.cpp/tools/quantize/quantize.cpp` parses `--tensor-type` values through
  `ggml_type_name`; `Q2_K` is valid while `Q2_K_S` is a model-level ftype.
- `vendor/llama.cpp/tools/imatrix/imatrix.cpp` collects every
  `GGML_OP_MUL_MAT_ID`, supports
  merged 3D expert tensors, and accumulates separate activation values and
  counts for each expert ID.
- The common CLI exposes `--load-mode dio` to `llama-imatrix` and supports the
  established dual-GPU layer split and auto-fit runtime.
- Read-only dry-runs produced:
  - all 43 routed layers Q2_K + non-routed IQ4_XS: `50,949,931,392` bytes;
  - all 43 routed layers IQ3_XXS + non-routed IQ4_XS: `58,761,560,448` bytes.
  These are feasibility evidence only; output size is not the experiment gate.

## Gap Analysis

The structural prior ranks expert-retention consensus, not quantization
sensitivity. A K132-specific imatrix is required before classifying layers.
The repository also needs deterministic scripts for structural aggregation,
imatrix coverage/normalization, plan generation, plan verification, production
tensor-type overrides, and final artifact provenance.

## Candidate Designs and Trade-offs

1. REAP-only ranking is cheap but answers the wrong question by itself.
2. Imatrix-only ranking directly measures activations but discards validated
   structural evidence.
3. A fixed combined score preserves both signals and keeps the user-defined
   17/26 ratio independent of output size. This is selected.

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Preserve all 132 experts and routing | 5 | 5 | User direction and K132 Golden | None | 5 | 5 | 5 | Explicit immutable baseline | Accepted |
| Fix allocation at 17 IQ3 / 26 Q2 | 5 | 5 | Latest user direction | All-IQ3 also fits under 60GB | 5 | 5 | 5 | Experiment ratio overrides size optimization | Accepted |
| Use 40% structural and 60% imatrix score | 5 | 4 | User formula and source capabilities | Aggregation still requires coverage validation | 5 | 4 | 5 | Activation importance gets greater weight for the quantization experiment | Accepted with Phase 1 gate |
| Use Q2_K tensor encoding | 5 | 5 | Pinned quantizer parser/source | User-facing Q2_K_S label differs | 5 | 5 | 5 | Concrete override must be ggml_type | Accepted |
| Keep non-routed default IQ4_XS mixed policy | 5 | 5 | K96 release evidence and user direction | None | 5 | 5 | 5 | Preserves automatic sensitive promotions | Accepted |
| Remove the 60GB gate | 5 | 5 | Latest user direction | Earlier objective used 60GB | 5 | 5 | 5 | Size becomes a reported measurement | Accepted |

## Selected Design

1. Generate a 43-layer structural report from archived K96 evidence.
2. Run DIO K132 imatrix calibration with fixed corpus identity and checkpointed
   outputs until every routed expert has non-zero projection-consistent counts.
3. Normalize `R_l` and `I_l`, compute `P_l = 0.4R_l + 0.6I_l`, and freeze the
   deterministic top-17 plan.
4. Run a no-output dry-run with a generated tensor-type file.
5. Produce one DIO candidate with IQ3_XXS in 17 layers, Q2_K in 26 layers, and
   exactly the archived K96 Profile A default IQ4_XS mixed policy for Shared
   Expert, Core Backbone, attention/indexer/embedding/output, and all other
   eligible non-routed weights. No manual non-routed type override is added.
6. Verify structure, types, unchanged routing, O_DIRECT hash, kernel health,
   and dual-5090 behavior without replacing K132.

## Validation Plan

- `repo-task-driven` placeholder, roundtable, sync, and inventory checks.
- Unit tests for structural aggregation, imatrix parser, normalization, stable
  ranking, tensor-type file generation, and plan verifier.
- imatrix coverage report: 129/129 routed tensors, finite values, 132 counts per
  tensor, explicit zero-count statistics.
- deterministic plan generation twice with byte-identical JSON.
- quantizer dry-run with exact counts: 51 IQ3_XXS expert tensors and 78 Q2_K.
- final O_DIRECT verifier, SHA256, clean kernel/Xid gate, and runtime probes.

## Risks and Assumptions

- Calibration coverage, not a preset corpus size, is the Phase 1 quality gate.
- `R_l` uses the fixed five-term weighted formula in the contracts. `I_l` uses
  count-weighted expert means after each projection is normalized by activation
  width, followed by deterministic mid-rank percentile normalization.
- Imatrix measures activation importance, not direct quantization sensitivity;
  IQ3 layers are called protected or high-priority layers.
- Requantizing MXFP4 into IQ3/Q2 is intentionally lossy and may fail semantic
  acceptance even when provenance and runtime stability pass.
- Layer-level assignment is the finest representable mixed type because each
  projection packs all 132 experts into one GGUF tensor.
- No all-IQ3 artifact is produced in this scope despite its dry-run feasibility.
