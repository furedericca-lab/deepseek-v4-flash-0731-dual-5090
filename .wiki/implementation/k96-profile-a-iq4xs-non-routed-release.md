---
title: K96 Profile A IQ4_XS non-routed release
type: implementation
status: archived
scope: heretic-v2-reap96-iq4xs-backbone
related_scopes:
  - heretic-v2-reap96-consensus
related_files:
  - vendor/llama.cpp/src/llama-quant.cpp
  - scripts/finalize_reap96_iq4xs_experts.py
  - scripts/verify_reap96_iq4xs_gguf.py
  - .scopes/archive/heretic-v2-reap96-iq4xs-backbone
source_docs:
  - .scopes/archive/heretic-v2-reap96-iq4xs-backbone/heretic-v2-reap96-iq4xs-backbone-technical-documentation.md
tags:
  - reap96
  - iq4-xs
  - direct-io
last_checked: 2026-08-13
updated: 2026-08-13T03:50:00+08:00
---

# K96 Profile A IQ4_XS non-routed release

This independent release consumes the immutable K96 MXFP4 Golden. It does not
reopen consensus scoring and does not replace the deployed K132 artifact.
Its completed scope is archived under
`.scopes/archive/heretic-v2-reap96-iq4xs-backbone/`.

## Tensor contract

| Class | Treatment |
|---|---|
| Routed Experts | 129 gate/up/down tensors remain MXFP4 and byte-identical |
| Shared Expert | llama.cpp default IQ4_XS mixed policy |
| Core Backbone | llama.cpp default IQ4_XS mixed policy |
| Router, `tid2eid`, norms, RoPE, sinks | Unchanged structural data |

The accepted type distribution is 655 IQ4_XS tensors, five Q5_K Shared Expert
down tensors in layers 0-4, one Q6_K `output.weight`, and 129 MXFP4
routed-expert tensors. No pure profile, imatrix, or second quantization profile
was used.

## Artifact identity

The read-only artifact is
`/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4exp-IQ4XSbb.gguf`.
It is `59,256,121,472` bytes with O_DIRECT SHA256
`845a0b91d17fddd6990068b995c8af031945af55f5bff94acc5a1c08389c63c3`.

Strict provenance passed 129/129 routed experts and 46/46 router/`tid2eid`
tensors over 55,231,776,768 compared bytes.

## Direct-I/O finalization

Two rejected production outputs exposed sparse stable block drift in unchanged
large MXFP4 tensors. Quantizer source streaming reduced but did not eliminate
it, and immediate write read-back did not predict stable post-process contents.

The production chain therefore includes
`scripts/finalize_reap96_iq4xs_experts.py` after quantization exits and the
kernel remains clean. It rewrites all 129 routed-expert payloads from the
immutable Golden using aligned O_DIRECT, without touching Shared Expert, Core
Backbone, routing, metadata, or tensor types.
`scripts/verify_reap96_iq4xs_gguf.py` then requires stable double-read identity
before acceptance.

## Runtime result

Dual RTX 5090 64K startup and OpenAI API passed. Observed GPU memory was about
28,537 and 28,973 MiB, server RAM peak was 3,279,060,992 bytes, and server swap
peak was zero. Chinese, valid JSON, and Python probes passed. A 32,767-token
prefill plus eight-token decode passed at 1000.41 prompt tok/s and 28.46 decode
tok/s without kernel or NVIDIA faults.

The raw France prompt still starts with `"',"` as in the K96 Golden/native
baseline. This is the frozen K96 quality limitation, not an IQ4_XS conversion
regression. K132 remains the sole deployment artifact.
