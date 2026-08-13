---
description: Canonical architecture for K132 fixed 17/26 mixed routed-expert quantization.
---

# K132 Mixed Expert Quantization Technical Documentation

## Canonical Architecture

```text
Immutable K132 MXFP4 Golden
        |
        +-- archived K96 full-candidate score report --> structural prior R_l
        |
        +-- llama-imatrix --load-mode dio -----------> activation score I_l
                                                          |
                                  P_l = 0.4 R_l + 0.6 I_l
                                                          |
                                   deterministic 43-layer ranking
                                          |                    |
                                   top 17 layers          remaining 26
                                  IQ3_XXS recipe        Q2_K_S recipe
                                          +---------+----------+
                                                    |
                         llama-quantize base profile IQ4_XS, non-pure
                                                    |
          Shared Expert + Core Backbone + sensitive non-routed weights
                   use the archived K96 Profile A default mixed policy
                                                    |
                                      one independent K132 candidate
```

## Key Constraints and Non-Goals

- Preserve all 132 experts, top-k 6, router, and hash routing.
- The corrected K132 Golden is immutable. The prior canonical GGUF was rejected
  after full routed provenance exposed payload mutation and was deleted.
- Exactly 17 layers use the IQ3_XXS recipe and 26 use the Q2_K_S recipe,
  independent of file size.
- A fork extension supplies per-routed-region effective ftypes; Q2_K_S is not
  reduced to a flat Q2_K tensor override.
- No `--pure`, all-IQ3 artifact, alternate ratio, or quantization A/B.
- No full buffered read, mmap hash, or buffered provenance scan.

## Major Decisions and Trade-offs

The layer score combines structural retention consensus with activation
importance. It ranks protected/high-priority layers and is not a direct
quantization-sensitivity measurement. The 60% imatrix weight reflects the
quantization task; the 40% structural prior prevents calibration data from
being the only protection signal. A fixed 17/26 allocation makes the
heterogeneous policy itself the experiment rather than optimizing size.

Non-routed weights deliberately reuse the accepted K96 Profile A policy. The
quantizer receives only routed-expert regex overrides. Shared Expert, attention,
CSA/HCA/mHC, indexer, embedding, output, and other eligible non-routed tensors
remain subject to llama.cpp's default non-pure IQ4_XS logic and built-in Q5/Q6
promotions. This fork additionally makes imatrix coverage a hard gate for every
quantizable effective-IQ4_XS tensor except the existing embedding/output
exceptions, so all three recipe regions consume the same accepted evidence.

## Module Boundaries and Data Flow

- Archived structural input:
  `.scopes/archive/heretic-v2-reap96-consensus/evidence/reap96-phase2-score-report.json`.
- Model input:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-routed-rebuild.gguf`,
  size `85,049,305,696`, O_DIRECT SHA256 `752a0146...cfdd`.
- Runtime tools: `vendor/llama.cpp/build/bin/llama-imatrix` and
  `vendor/llama.cpp/build/bin/llama-quantize` at production submodule
  `efb81abc6a261dcceb014e853beb0ffc5e4a49a0`, based on `2abf1748`, after the
  complete imatrix and DeepSeek-V4 grouped-attention fixes.
- Planned repository scripts own structural extraction, imatrix audit, plan
  generation, type-file generation, and candidate verification.
- Evidence JSON and logs live under this scope's `evidence/` directory; model
  and imatrix payloads remain under `/data/linux-fast/models/`.

## Interfaces and Contracts

The plan JSON is the sole authority for layer assignment. It maps every layer
to the `IQ3_XXS` or `Q2_K_S` recipe, records `R_l`, `I_l`, `P_l`, rank, source
hashes, and tie-break values. The generated tensor-ftype file expands each
layer assignment to gate/up/down packed expert regexes. Manual non-routed
entries are forbidden; unmatched tensors inherit global IQ4_XS.

## Operational Behavior

1. Require a clean kernel/Xid gate and idle model processes.
2. Run imatrix with `--load-mode dio`, dual-GPU layer split, auto-fit, context
   512, and cumulative 100/200/300/400-chunk GGUF checkpoints.
3. Audit imatrix coverage and adjacent-stage stability. Acceptance starts at
   200 chunks and requires zero missing experts, zero projection-count
   mismatch, Spearman >= 0.95, and activation/final Top17 churn <= 2.
4. Freeze the first accepted deterministic plan; block if 400 chunks fails.
5. Require the independent `17,028`-comparison, `75,884,396,544`-byte full
   routed-provenance PASS, then run the quantizer dry-run and one DIO production
   quantization using the accepted imatrix and tensor-ftype file.
6. Stop on any kernel fault, non-finite imatrix value, missing expert coverage,
   type mismatch, routing drift, or unstable O_DIRECT read.
7. Verify and run the candidate without changing the K132 server entry point.

## Observability and Error Handling

- Capture corpus identity, command, commit, chunk/token counts, per-expert
  counts, zero-count experts, count percentiles, routing entropy, adjacent-stage
  Spearman/Top17 churn, score normalization, dry-run type inventory, file size,
  O_DIRECT SHA256, runtime throughput, VRAM/RAM/swap, and kernel/Xid logs.
- Partial imatrix checkpoints are diagnostic only until merged and verified.
- Failed/rejected GGUF outputs remain non-canonical and are deleted only with
  explicit user authorization.
- The rejected old K132, mutated full-converter intermediate, K96 MXFP4, and K96
  IQ4_XS files were deleted on 2026-08-13. Historical reports remain as audit
  evidence but must not be treated as live artifact paths.

## Security and Reliability

All network-free model processing runs locally. No model payload enters Git.
O_DIRECT, atomic output publication, read-only inputs, and clean-boot gates are
mandatory because this host has reproduced buffered-page-cache corruption.

## Test Strategy

- `uv run pytest tests -q` for repository scripts.
- llama.cpp focused build/tests for any required tool changes.
- deterministic report generation and independent plan verification.
- quantizer dry-run before the production artifact.
- direct-only final provenance and dual-5090 64K/runtime acceptance.
