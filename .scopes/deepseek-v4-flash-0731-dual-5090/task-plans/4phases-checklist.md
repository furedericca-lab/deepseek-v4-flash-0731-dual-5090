---
description: Execution and acceptance record for corrected K132 deployment and its Q2-recipe repair candidate.
---

# Phases Checklist: deepseek-v4-flash-0731-dual-5090

## Global Status Board

| Phase | Status | Completion | Health | Blockers |
|---|---|---:|---|---:|
| Phase 1 - Accepted artifact | Complete | 100% | PASS | 0 |
| Phase 2 - Dual-5090 runtime | Complete | 100% | PASS | 0 |
| Phase 3 - Operator handoff | Complete | 100% | PASS | 0 |
| Phase 4 - Q2 routed-recipe repair | In progress | 20% | Evidence PASS | 0 |

## Phase Entry Links

1. [Phase 1](phase-1-deepseek-v4-flash-0731-dual-5090.md)
2. [Phase 2](phase-2-deepseek-v4-flash-0731-dual-5090.md)
3. [Phase 3](phase-3-deepseek-v4-flash-0731-dual-5090.md)
4. [Phase 4](phase-4-deepseek-v4-flash-0731-dual-5090.md)

## Accepted Artifact

- Path: `/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-routed-rebuild.gguf`
- Size: `85,049,305,696` bytes.
- O_DIRECT SHA256: `752a0146f54d5c5bc34491d53f9e1acbb63540b1e3c38bd352185b508418cfdd`.
- Mode: `0444`.
- Full routed provenance: 129 tensors, 17,028 comparisons,
  75,884,396,544 bytes, zero failures.

## Runtime Acceptance

- Pinned llama.cpp fork with DIO, dual-GPU layer auto-fit, 64K, F16 CPU KV,
  one slot, batch 512, ubatch 128, and flash attention.
- `/health`, `/v1/models`, raw France, Chinese, JSON, Python, and 32K-prefill
  probes passed without new Xid or kernel faults.
- `scripts/llama-server-first-boot.sh` points to the accepted MXFP4 path.

## Rejected Candidate Record

- The fixed 17/26 mixed candidate passed structure and infrastructure but
  failed semantic behavior with repeated `<` output.
- Same-runtime corrected MXFP4 A/B passed Chinese, JSON, and Python, isolating
  the failure to the mixed weights.
- The mixed payload is deleted; its archived scope and small evidence remain.

## Phase 4 Execution Record

- PASS: external source revision fixed at
  `326e2f17f02dde8fadb8eab2b8aa379d658b2940`.
- PASS: requested `.recipe.iq3xxs.txt`, `imatrix.gguf.prev`, and
  `imatrix.gguf` are read-only under `/data/linux-fast/models/external/`.
- PASS: final imatrix is 812 chunks, SHA256 `8bca12cc...48de8`, complete routed
  coverage, zero zero-count experts, and minimum expert count 408.
- PASS: 620-to-812 raw-I Spearman is `0.9996979764`; activation and final Top17
  churn are zero. Corrected-Golden-to-puwaer Spearman is `0.9989429175` with
  zero Top17 churn.
- FROZEN: selected candidate uses 15 routed MXFP4 tensors, 76 Q2_K gate/up
  tensors, 38 Q3_K down tensors, and K96 Profile A default non-pure IQ4_XS
  mixed policy for eligible non-routed weights.
- Pending: deterministic plan/tooling, DIO dry-run, production, direct-only
  verification, short semantics, 32K prefill, and explicit deployment decision.

## Final Release Gate

- Launcher, README, AGENTS, deployment scope, and Wiki name the same artifact.
- Artifact remains read-only and no failed/obsolete GGUF duplicate remains.
- Full-model reads, hashes, and provenance remain O_DIRECT-only.
- Docker and unrelated scanners remain stopped during model validation.
