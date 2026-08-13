---
description: Execution and verification hub for K132 fixed 17/26 mixed expert quantization.
---

# Phases Checklist: heretic-v2-reap132-mixed-expert-quant

## Input

- Scope contracts and technical documentation in the parent directory.
- Immutable K132 Golden and archived K96 score report.
- Pinned production llama.cpp submodule
  `efb81abc6a261dcceb014e853beb0ffc5e4a49a0`, based on `2abf1748`.

## Global Status Board

| Phase | Status | Completion | Health | Blockers |
|---|---|---:|---|---:|
| Phase 1 - Structural prior and imatrix | Complete | 100% | PASS | 0 |
| Phase 2 - Freeze 17/26 plan | Complete | 100% | PASS | 0 |
| Phase 3 - DIO production artifact | Complete | 100% | PASS | 0 |
| Phase 4 - Runtime acceptance | Complete | 100% | Semantic FAIL; candidate rejected | 0 |

## Locked Rules

- Exactly 17 IQ3_XXS-recipe and 26 Q2_K_S-recipe routed-expert layers.
- Shared Expert, Core Backbone, and sensitive non-routed weights use the same
  default non-pure IQ4_XS mixed policy as archived K96 Profile A.
- No size gate, `--pure`, second profile, or all-IQ3 artifact.
- No K132 Golden, router, `tid2eid`, or expert-count changes.

## Phase Entry Links

1. [Phase 1](phase-1-heretic-v2-reap132-mixed-expert-quant.md)
2. [Phase 2](phase-2-heretic-v2-reap132-mixed-expert-quant.md)
3. [Phase 3](phase-3-heretic-v2-reap132-mixed-expert-quant.md)
4. [Phase 4](phase-4-heretic-v2-reap132-mixed-expert-quant.md)

## Phase Execution Records

### Phase 1

- Scope branch created from pushed `master` commit `992cd90`.
- Source inspection confirmed IQ3 and Q2_K_S imatrix requirements, the lack of
  stock per-region ftypes,
  DIO imatrix loading, and packed-expert per-ID collection.
- Read-only dry-runs recorded all-Q2 and all-IQ3 feasibility sizes; these do not
  alter the fixed ratio.
- T001 PASS: structural-prior extractor validated the archived K96 report,
  produced all 43 contracted records, and reproduced byte-identically. Source
  SHA256 is `ae090c1b...47bfa`; report logical SHA256 is
  `4493d0e9...a7e64f`; focused tests passed `2/2`.
- Frozen: vendored-source corpus contract and cumulative 100/200/300/400-chunk
  coverage/stability gate.
- PASS: accepted 200-chunk imatrix SHA256 `f528ab31...897f2`; routed coverage is
  complete, 100-to-200 Spearman is `1.0`, both Top17 churn values are zero, and
  the post-run kernel/Xid gate is clean.
- The hard all-IQ4 gate exposed a missing non-block `output_hc_fn.weight` entry.
  The collector now records this real matrix input; the accepted entry is finite,
  16,384-wide, and has count 102,400.

### Phase 2

- PASS: corrected K132 Golden rebuilt all 129 complete routed tensors from
  accepted native K132. Full provenance compared 17,028 projection-experts and
  75,884,396,544 bytes with zero failures. Corrected Golden O_DIRECT SHA256 is
  `752a0146...cfdd`.
- PASS: frozen 17/26 plan generated twice byte-identically and independently
  verified. Current plan SHA256 is `9f87f453...c3ef7`, logical SHA256 is
  `49b9c651...88d2`, and tensor-ftype SHA256 is `db05988d...269e`.
- PASS: imatrix-backed DIO dry-run under `efb81ab` predicts
  `55,348,319,104` bytes and verifies the complete 1,328-tensor inventory,
  including 43 DeepSeek-V4 attention-KV Q5_K promotions and 62 unchanged
  compressor positional-embedding lookup tensors.

### Phase 3

- The first production attempt rejected the old K132 GGUF on an infinite Q2_K
  block. The old K132, mutated converter intermediate, and both REAP96 GGUFs
  were deleted with user authorization. The corrected dry-run independently
  passed the full 1,328-tensor inventory.
- A corrected-Golden production run was interrupted by an unclean host restart
  at tensor 943/1328. Sysstat and journals exclude system RAM OOM: memory use
  remained 27-28%, swap was zero, and no OOM killer fired. Its unpublished
  staging file was deleted.
- PASS: a fresh corrected-Golden 200-chunk imatrix produced the same Rank-I,
  Rank-P, activation Top17, and final Top17 as the accepted imatrix. Spearman is
  `1.0` and both churn values are zero, so the frozen plan and accepted imatrix
  remain authoritative.
- PASS: the hardened `efb81ab` reader uses reusable 1 MiB aligned buffers and
  double-reads every direct-I/O window. It detected and rejected one transient
  chipset-NVMe mismatch without publishing output; the same 8 MiB range then
  passed 100 repeated reads and the boot remained clean.
- PASS: the CPU-attached root-NVMe production A/B completed `1328/1328` and
  published exactly `55,348,319,104` bytes. Post-run kernel/Xid signatures are
  empty. Independent verification passed the full inventory and compared all
  600 unchanged tensors (`63,307,072` bytes) byte-for-byte with zero unstable
  reads. Root-NVMe O_DIRECT SHA256 is `67e6990f...77ab3`.
- PASS: direct-I/O copy to the frozen final filename on `/data/linux-fast`,
  destination size/hash equality, mode `0444`, and the Phase 3 acceptance record.

### Phase 4

- PASS: dual-5090 DIO 64K startup/API, 32,767-token prefill, resource, and
  kernel/Xid stability gates completed under `efb81ab`.
- LIMITATION: raw France is correct, but chat/Chinese/JSON/Python and long-prefill
  decode exhibit repeated `<` collapse or fail to emit final content.
- CONTROLLED A/B: corrected MXFP4 under the same `efb81ab` binary, DIO,
  dual-GPU/64K flags, prompts, seed, and greedy sampling produced coherent
  Chinese, valid JSON, and valid Python without repeated-symbol collapse.
- IMPLEMENTATION AUDIT: regional recipe selection, packed-expert imatrix order,
  MXFP4 CPU dequantization, and CUDA `MUL_MAT_ID` for 132 experts/top-6 passed.
- DECISION: the mixed candidate fails the semantic release gate and is rejected.
  Corrected K132 MXFP4 is restored as the sole deployment artifact.

## Final Release Gate

- 43 layers, 132 experts, top-k 6, no routing drift.
- Exactly 51 IQ3_XXS-recipe and 78 Q2_K_S-recipe routed-expert tensors, with
  concrete types matching the pinned selectors.
- Non-routed type selection matches default K96 Profile A-style IQ4_XS mixed
  behavior without manual overrides.
- Direct-only hash/provenance and clean runtime gates pass.
- Semantic result and rejection decision are explicit; corrected K132 MXFP4
  remains deployed.

## Archive Record

- Archived on 2026-08-13 under
  `.scopes/archive/heretic-v2-reap132-mixed-expert-quant/`.
- The experiment is complete with a rejection result: structural, direct-I/O,
  startup, and long-prefill infrastructure gates passed, but controlled
  same-runtime semantic A/B failed.
- The 17/26 plan, its ranking, and its regional `Q2_K_S` implementation remain
  historical evidence and are not inputs to the replacement candidate.
- Replacement quantization work is owned by Phase 4 of
  `.scopes/deepseek-v4-flash-0731-dual-5090/`.
- Archived documents are read-only except for factual errata and path
  maintenance.
