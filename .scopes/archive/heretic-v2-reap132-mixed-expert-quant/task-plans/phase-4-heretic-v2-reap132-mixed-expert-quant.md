---
description: Evaluate the verified K132 mixed candidate on the established dual-5090 runtime.
---

# Tasks: K132 Mixed Expert Quantization Phase 4

## Input

- Verified Phase 3 candidate and canonical K132 runtime baseline.

## Canonical architecture / Key constraints

- Use dual RTX 5090 layer split, DIO load, auto-fit, F16 CPU KV, 64K context,
  and localhost single-slot serving.
- Runtime testing does not change the K132 deployment script until promotion is
  explicitly accepted.

## Phase 4: Runtime Acceptance

Goal: Determine whether the fixed heterogeneous policy preserves useful K132
behavior and stability.

Definition of Done: Startup, API, behavior, long-prefill, resource, and kernel
results are recorded with an explicit deployment decision.

Tasks:

- [x] T061 [Infra] Pass runtime preflight and 64K startup
  - DoD: Idle baseline is recorded; server loads the candidate with contracted flags; `/health` and `/v1/models` pass without kernel/Xid events.
- [x] T062 [QA] Run raw and structured behavior probes
  - DoD: Fixed greedy raw France, chat, Chinese, valid JSON, and Python/code probes are compared with canonical K132 and checked for repetition or formatting collapse.
- [x] T063 [QA] Run 32K prefill and decode probe
  - DoD: The established 32,767-token input plus decode completes untruncated and records prompt/decode throughput.
- [x] T064 [Infra] Record GPU, RAM, swap, and kernel health
  - DoD: GPU0/GPU1 memory, server RAM/swap peaks, load time, and clean post-run BAD_PAGE/Oops/GPF/Xid gate are stored.
- [x] T065 [Docs] Make explicit promotion decision
  - DoD: Scope records PASS, rejection, or accepted-with-limitation; no script or canonical artifact changes without separate promotion authority.

Checkpoint: Scope closeout requires all evidence, residual risks, and rollback
path to be explicit.

## Acceptance Result

- Infrastructure PASS: build `266 (efb81ab)`, dual-5090 DIO 64K startup in
  18.83 seconds, `/health` and `/v1/models` PASS, peak GPU memory approximately
  26,745/27,427 MiB, server RAM peak 1,965,486,080 bytes, swap peak zero, and
  zero kernel/Xid fault signatures.
- Long-prefill infrastructure PASS: 32,767 prompt tokens plus eight decode
  tokens completed untruncated at 1095.86 prompt tok/s and 31.44 decode tok/s.
- Behavior limitation: raw France begins with ` Paris.`, but exact chat consumes
  its budget in reasoning, and Chinese/JSON/Python probes reproducibly collapse
  into repeated `<` tokens with no final content. The long-prefill decode is
  also `<<<<<<<<`.
- Controlled A/B: corrected MXFP4 was loaded with the same `efb81ab` binary,
  DIO, dual-GPU/64K flags, KV, batch sizes, reasoning format, prompts, seed, and
  greedy sampling. It returned coherent Chinese, valid JSON, and valid Python,
  without repeated-symbol collapse. The comparison isolates the failure to the
  mixed weights rather than the runtime or chat template.
- Implementation audit: regional recipe selection, packed-expert imatrix order,
  MXFP4 CPU dequantization, and CUDA `MUL_MAT_ID` for 132 packed experts/top-6
  passed for both Q2_K and IQ3_XXS. No implementation defect was found that
  justifies publishing the failed weights.
- Allocation risk: `raw_I_l` has Spearman `0.9651` with layer index and the
  frozen allocation places layers 0-19 continuously in Q2_K_S. This explains a
  plausible quality risk but does not authorize silently changing the frozen
  experiment.
- Decision: status `REJECTED_FOR_DEPLOYMENT`. Restore corrected K132 MXFP4 as
  the sole deployment artifact and delete the failed mixed payload after its
  hash, verifier, runtime, and A/B evidence are retained.

## Dependencies & Execution Order

- Phase 4 depends on accepted Phase 3 artifact.
- T061 blocks T062-T064; T065 depends on all runtime evidence.
