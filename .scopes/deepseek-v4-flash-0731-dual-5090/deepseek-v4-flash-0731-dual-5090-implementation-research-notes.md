---
description: Current evidence and decisions for the corrected K132 deployment.
---

# Deployment Research Notes

## Accepted Evidence

- Native K132 noMTP passed deterministic build and independent verification.
- Corrected GGUF rebuilt all 129 routed tensors from accepted native bytes.
- Full routed provenance covered 17,028 expert/projection comparisons and
  75,884,396,544 bytes with zero failures.
- O_DIRECT SHA256 is `752a0146f54d5c5bc34491d53f9e1acbb63540b1e3c38bd352185b508418cfdd`.
- Dual-5090 64K/API/behavior and 32K prefill acceptance passed.

## Rejected Alternative

The 55,348,319,104-byte fixed-ratio mixed artifact was structurally valid but
failed semantic acceptance with repeated `<` output. A controlled A/B changed
only the model file and showed corrected MXFP4 returning coherent Chinese,
valid JSON, and valid Python under the same llama.cpp commit and runtime flags.

Audits found no regional-ftype, imatrix-order, MXFP4-dequantization, or
132-expert CUDA kernel defect. The remaining high-confidence finding is that
the specified lossy mixed weights are not behaviorally acceptable. In
particular, the activation ranking correlates strongly with layer depth and
places layers 0-19 continuously in Q2_K_S, making early-layer accumulated error
a plausible mechanism, not a proven per-layer causal attribution.

## Replacement Decision

Corrected K132 MXFP4 remains the sole deployment artifact while Phase 4 evaluates
one replacement candidate in this deployment scope. The rejected 17/26 scope is
archived and its structural PASS is not inherited as semantic acceptance.

The selected replacement borrows the published puwaer Q2 recipe allocation,
not its quantized weight payload: preserve routed layers 0-2 and 41-42 as
MXFP4, quantize routed gate/up in layers 3-40 to Q2_K, and routed down in those
layers to Q3_K. It uses puwaer's final 812-chunk imatrix values. Eligible
non-routed tensors continue to use the archived K96 Profile A default non-pure
IQ4_XS mixed policy instead of puwaer's manual Q8_0 overrides.

The external imatrix passed the local packed-MoE audit: 129 routed entries,
all 5,676 layer/expert instances covered, no malformed or mismatched counts,
zero zero-count experts, minimum count 408, and 620-to-812 raw-I Spearman
`0.9996979764` with zero Top17 churn. Against the corrected-Golden 200-chunk
imatrix, raw-I Spearman is `0.9989429175` and Top17 churn is zero. This proves
layout compatibility and stable aggregate evidence; runtime acceptance remains
the only quality decision.

## Options And Trade-offs

| Option | Size/quality tendency | Decision |
|---|---|---|
| Reuse rejected 17/26 IQ3/Q2_K_S | Smallest observed, semantic collapse | Rejected and archived |
| Force all 129 routed tensors to IQ3_XXS | Uniform but ignores published projection/layer protections | Not selected |
| puwaer IQ3 routed recipe + K96 Profile A non-routed | More conservative, likely larger | Deferred |
| puwaer Q2 routed recipe + K96 Profile A non-routed | Protects boundary layers and all down projections while retaining stronger compression | Selected |

The published puwaer Q2 GGUF is 62,394,667,168 bytes with Q8_0 non-routed
weights. The hybrid candidate should be smaller because its non-routed base is
IQ4_XS mixed, but size is measured by dry-run and is not a pass/fail gate.

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Use puwaer Q2/Q3 routed allocation | 5 | 5 | pinned recipe, plan verifier, dry-run | None | 5 | 5 | 4 | all frozen sources agree | Accepted for one trial |
| Keep K96 Profile A non-routed policy | 5 | 5 | archived K96 release and dry-run | None | 5 | 5 | 5 | automatic mixed inventory passed | Accepted |
| Require zero unstable O_DIRECT reads | 5 | 5 | live verifier failures | Old verifier only recorded instability | 5 | 5 | 5 | integrity evidence must fail closed | Validator fixed |
| Reject candidate after short semantic failure | 5 | 5 | controlled MXFP4 A/B | Structure and startup passed | 5 | 5 | 5 | semantic gate is release authority | Rejected and deleted |

## Selected Design And Closeout

The candidate completed structural and startup work, but the fixed short
semantic gate failed; T088 was intentionally skipped. Corrected MXFP4 remains
the only deployable artifact. Candidate payloads were deleted after compact
JSON/log evidence was retained.

## Validation Strategy

Focused tests, scope checks, O_DIRECT verification and hashing, dual-5090
health/API, and controlled semantic A/B are recorded under the active scope's
`evidence/` directory. The corrected Golden is the authoritative comparison
source; root-NVMe copies are staging only.
