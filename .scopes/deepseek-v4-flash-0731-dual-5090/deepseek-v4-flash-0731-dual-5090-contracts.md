---
description: Deployment contract for the accepted corrected K132 MXFP4 artifact on dual RTX 5090.
---

# DeepSeek V4 Flash K132 Deployment And Q2 Recipe Contract

## Context

The deployment target is the corrected, full-routed-rebuild K132 GGUF. It keeps
43 layers, 132 routed experts per layer, top-k 6, and no MTP. The fixed 17/26
IQ3_XXS/Q2_K_S experiment passed structural checks but failed controlled
semantic A/B and is not deployable.

## Artifact Contract

| Field | Accepted value |
|---|---|
| Runtime artifact | `/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-routed-rebuild.gguf` |
| Size | `85,049,305,696` bytes |
| O_DIRECT SHA256 | `752a0146f54d5c5bc34491d53f9e1acbb63540b1e3c38bd352185b508418cfdd` |
| Mode | `0444` |
| Architecture | `deepseek4` |
| Layers / experts / top-k | `43 / 132 / 6` |
| Tensor count | `1328` |
| MTP / DSpark | absent |

The artifact passed 17,028 byte-exact projection/expert comparisons over
75,884,396,544 routed bytes, plus accepted non-routed and FP8-backbone checks.
No other GGUF may replace this path without its own provenance and semantic
acceptance.

## Phase 4 Candidate Contract

The only active candidate combines the corrected HERETIC-v2 K132 weights with
the published puwaer Q2 routed-expert recipe and the archived K96 Profile A
non-routed policy:

| Region | Required target |
|---|---|
| Routed layers 0-2 and 41-42, gate/up/down | preserve `MXFP4` |
| Routed layers 3-40, gate/up | `Q2_K` |
| Routed layers 3-40, down | `Q3_K` |
| Shared Expert and eligible Core Backbone | `IQ4_XS` base, default non-pure mixed selector |
| Attention/indexer/embedding/output | default non-pure `IQ4_XS` mixed selector and its automatic promotions |
| Router, `tid2eid`, norm, RoPE, sink, lookup tensors | unchanged when ineligible for quantization |

The concrete routed inventory is exactly 15 `MXFP4`, 76 `Q2_K`, and 38
`Q3_K` tensors. No `Q2_K_S` regional ftype, 17/26 layer ranking, `--pure`, or
manual non-routed Q5/Q6/Q8 override is allowed.

Production uses the read-only puwaer `imatrix.gguf` from repository revision
`326e2f17f02dde8fadb8eab2b8aa379d658b2940`, size `251,877,376`, SHA256
`8bca12ccf077fc9341b6f3d8ee399e5c5576a7a82c715e529008da68a5548de8`.
It contains 812 chunks, complete routed coverage, zero zero-count experts, and
a minimum routed expert count of 408. `imatrix.gguf.prev` is stability evidence
only and must not be merged with or supplied alongside the final imatrix.

## Runtime Contract

`scripts/llama-server-first-boot.sh` is the canonical launcher. It must use:

```text
--load-mode dio
-dev CUDA0,CUDA1
-sm layer
--fit on
--fit-target 3072,3072
--no-kv-offload
-ctk f16 -ctv f16
-c 65536 -np 1
-b 512 -ub 128
-fa on
--reasoning-format deepseek
--host 127.0.0.1 --port 8000
```

Do not use `-ngl all`; it disables auto-fit and requests an impossible
per-device allocation. Bind remains localhost-only unless separately approved.

## Acceptance Evidence

- 64K dual-5090 startup, `/health`, and `/v1/models`: PASS.
- Raw France, Chinese, JSON, and Python probes: PASS.
- 32,767-token prefill plus eight-token decode: PASS.
- No new Xid, BAD_PAGE, Oops, GPF, or swap use in the accepted runs.
- Same-runtime comparison against the rejected mixed artifact proves the
  repeated-`<` collapse is not caused by the launcher or chat template.

## Rejection And Rollback

The former mixed artifact with SHA256 `67e6990f...77ab3` is rejected for
deployment. Its structural verifier PASS does not override its semantic FAIL.
The failed payload is deleted after evidence retention; it is not a rollback.
The corrected MXFP4 artifact is both the current deployment and the canonical
rollback baseline for future experiments.

The Phase 4 Q2-recipe candidate completed dry-run, production, direct-I/O
artifact verification, and dual-5090 startup, but failed the fixed short
semantic gate. Per contract, 32K was not run. The candidate and root-NVMe
intermediates were deleted; corrected MXFP4 remains the sole deployment.

## Verification

```bash
scripts/llama-server-first-boot.sh
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/models
```

Before startup, require idle GPUs, sufficient RAM, and a clean current-boot
kernel/Xid journal. Full artifact hashing and provenance remain O_DIRECT-only.

## Escalation Triggers

- Artifact identity, size, mode, or tensor metadata differs.
- Any current-boot Xid, BAD_PAGE, Oops, GPF, or unexplained process SIGSEGV.
- Health/API failure, repeated-symbol output, invalid structured output, or
  long-prefill decode collapse.
- A request to change context, offload, KV, bind address, or deployment model.

## Requirement Boundary Notes

- Phase 4 authorized exactly one puwaer-derived routed Q2/Q3 recipe; it did not
  authorize reopening the archived 17/26 experiment or creating another quant.
- Structural, direct-I/O, and startup success cannot override a short semantic
  failure. T087 failure terminates the candidate before T088.
- The corrected MXFP4 identity remains immutable and is both deployment and
  rollback. Deleted candidate paths remain evidence references, not artifacts.
