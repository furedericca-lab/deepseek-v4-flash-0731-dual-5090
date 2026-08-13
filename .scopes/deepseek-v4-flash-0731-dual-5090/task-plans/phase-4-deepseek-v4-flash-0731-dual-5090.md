---
description: Build and evaluate the boundary-protected K132 Q2 routed-expert candidate.
---

# Tasks: deepseek-v4-flash-0731-dual-5090 Phase 4

## Input

- Corrected read-only K132 MXFP4 Golden and its full routed provenance.
- Archived K96 Profile A non-routed IQ4_XS policy.
- puwaer repository revision
  `326e2f17f02dde8fadb8eab2b8aa379d658b2940`.
- `.recipe.q2k.txt`, final 812-chunk `imatrix.gguf`, and 620-chunk
  `imatrix.gguf.prev` stability evidence.
- Archived rejected 17/26 experiment under
  `.scopes/archive/heretic-v2-reap132-mixed-expert-quant/`.

## Canonical architecture / Key constraints

- Preserve all 132 experts per layer and top-k 6; do not change router or
  `tid2eid`.
- Routed layers 0-2 and 41-42 remain MXFP4.
- Routed gate/up in layers 3-40 use Q2_K; routed down uses Q3_K.
- Eligible non-routed tensors use default non-pure IQ4_XS mixed policy without
  manual Q5/Q6/Q8 overrides.
- Use only final `imatrix.gguf` for quantization; never merge it with `.prev`.
- Corrected MXFP4 remained deployed throughout Phase 4 and remains deployed
  after candidate rejection.
- All large model reads, writes, hashes, and comparisons use aligned O_DIRECT.

## Phase 4: Q2 Routed-Recipe Repair

Goal: Produce one compact K132 candidate that avoids the rejected early-layer
Q2_K_S allocation while preserving puwaer's published boundary and down-projection
protections.

Definition of Done: External evidence, deterministic plan, DIO dry-run, atomic
candidate, direct-only verification, short semantics, 32K prefill, resources,
kernel health, and deployment decision are recorded.

Tasks:

- [x] T081 [Infra] Freeze external revision and payloads
  - DoD: The revision, three requested files, sizes, modes, and SHA256 values are recorded; no model GGUF is downloaded.
- [x] T082 [QA] Audit external imatrix coverage and stability
  - DoD: Both 620- and 812-chunk files have complete 129-entry routed coverage, zero zero-count experts, finite values, matching gate/up/down counts, Spearman at least 0.95, and zero Top17 churn.
- [x] T083 [Backend] Generate deterministic Q2 routed recipe plan
  - DoD: Generator emits exactly 15 MXFP4, 76 Q2_K, and 38 Q3_K routed tensor assignments, no non-routed override, and immutable source hashes.
- [x] T084 [QA] Verify complete DIO dry-run inventory
  - DoD: Pinned quantizer exits zero; independent verifier checks all 1,328 tensors, routed counts, K96 Profile A non-routed mixed selection, imatrix requirements, and exact predicted size.
- [x] T085 [Infra] Build one atomic DIO candidate
  - DoD: Clean-boot preflight passes; quantizer uses corrected Golden and final puwaer imatrix; no partial output is published; post-run kernel/Xid gate is clean.
- [x] T086 [QA] Verify artifact and immutable identity
  - DoD: Direct-only verifier checks metadata, 129 routed concrete types, unchanged structural payloads, no MTP/DSpark, stable O_DIRECT SHA256, mode 0444, and zero unstable reads.
- [x] T087 [QA] Run short semantic acceptance
  - DoD: Same-runtime raw France, chat, Chinese, JSON, and Python probes pass without empty final content, repeated-symbol collapse, routing errors, or invalid required formats.
- [x] T088 [QA] Run 32K prefill and resource acceptance
  - DoD: Only after T087, the 32,767-token prefill plus decode completes with coherent output; GPU/RAM/swap and clean kernel/Xid evidence are recorded.
- [x] T089 [Docs] Promote or reject and clean payloads
  - DoD: Deployment decision is explicit; launcher changes only on full PASS; rejected/obsolete payloads and intermediates are safely deleted after compact evidence retention.

Checkpoint: T083-T084 block production. T087 failed, so T088 was intentionally
not run. T089 records rejection and preserves corrected MXFP4 as rollback.

## Phase 4 Closeout

The candidate passed production, structure, direct-I/O, and dual-5090 startup,
but failed the fixed short semantic gate under the same `efb81ab` runtime and
canonical flags. Corrected MXFP4 remained the sole deployment artifact. The
candidate was rejected and deleted; no 32K run was authorized after T087.

## Dependencies & Execution Order

- T081-T082 are complete discovery gates.
- T083 blocks T084; T084 blocks T085.
- T085 blocks T086; T086 blocks runtime testing.
- T087 must pass before T088.
- No task authorizes branch creation; all work remains on `master`.
