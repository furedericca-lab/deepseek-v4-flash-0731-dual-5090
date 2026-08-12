---
description: Task list for heretic-v2-reap132-build-validation phase 3.
---

# Tasks: heretic-v2-reap132-build-validation Phase 3

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/archive/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-scope-milestones.md`
  - `.scopes/archive/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-brainstorming.md`
  - `.scopes/archive/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-implementation-research-notes.md`
  - `.scopes/archive/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-technical-documentation.md`
  - `.scopes/archive/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-contracts.md`

## Canonical architecture / Key constraints
- Convert only the Phase 2 byte-verified native checkpoint; a documented native
  HF runtime limitation does not block this deployment-runtime phase.
- Pin and record the llama.cpp converter commit and exact command.
- MXFP4 is the final deployment format; puwaer A/B and IQ3/Q2 are cancelled.
- Runtime binds to localhost and uses both RTX 5090s with existing OOM order.
- A/B prompts, flags, and scoring must be identical between artifacts.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 3: Golden GGUF and Dual-5090 Runtime
Goal: Convert the verified native checkpoint without losing any tensor payload, then validate the final MXFP4 deployment artifact locally.

Definition of Done: A fully hashed MXFP4 GGUF passes direct payload provenance, metadata, and dual-5090 runtime gates.

Tasks:
- [x] T041 [Config] Pin and inspect the llama.cpp converter
  - DoD: Converter commit, DeepSeek-V4 support, accepted flags, and routed-expert output type are recorded before conversion.
- [x] T042 [Infra] Convert the accepted native checkpoint
  - DoD: Exact command converts the Phase 2 artifact to a GGUF under `/data/linux-fast/models/DeepSeek-V4-Flash-0731/` without reading any unverified checkpoint.

T041 outcome: use the `vendor/llama.cpp` submodule from the project fork at
commit `8704e31`, based on upstream
`89e0aa6fd362617d9073e0dafc18e41241521572`. Its converter registers
`DeepseekV4ForCausalLM`, accepts `--no-mtp`, emits hash routing as I32, combines
each routed expert's frozen weight+E8M0 scale into GGUF `MXFP4`, and marks the
file `MOSTLY_MXFP4_MOE`. This is a deterministic repack into the GGML block
layout, not a floating-point requantization.

T042 preparation: the pinned converter now exposes `--direct-io-input` and
`--direct-io-output`. Input uses aligned 64 MiB bounded O_DIRECT reads for
arbitrary tensor offsets. Output stages arbitrary GGUF writes into aligned
64 MiB O_DIRECT writes, then truncates the final padded block to the exact
logical length. Small fixtures pass for non-aligned tensor ranges, a 70 MiB
cross-boundary output stream, and existing GGUF reader validation. The full
conversion remains pending because the current boot contains Xid 31; start it
only after reboot and a clean boot gate.

The first real dry-run exposed upstream writer retention: converted tensors were
kept in RAM until final output, exhausting 45 GiB RAM around Layer 24. Commit
`8704e31` changes only the explicit direct-I/O output path to stage each tensor
immediately into a same-filesystem O_DIRECT temporary payload and release its
array; dry-run records metadata without retaining payloads. The full 43-layer
dry-run now passes with 1,328 tensors, an estimated 85.0 GB output, 1.67 GiB peak
RSS, zero process swaps, and no kernel fault.

The first 80 GiB full output is quarantined after successful structure/load
checks but failed semantic output (`D` repetition). Native HF returns ` Paris`
for the same raw prompt. Direct provenance shows all sampled MXFP4 expert blocks
pass while nonexpert embedding, output norm, and head samples fail. Root cause:
the direct writer called `np.ascontiguousarray()` on `LazyNumpyTensor`, which
uses a zero-valued metadata array without evaluating the deferred payload.
The repair materializes lazy tensors in `write_array()` and is covered by seven
small GGUF payload tests. The replacement direct-I/O conversion completed as
`DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf` at
85,049,305,696 bytes.
- [x] T043 [QA] Verify and freeze the golden GGUF candidate
  - DoD: Full GGUF SHA256, size, metadata, expert count/type, architecture, tokenizer, and source native manifest SHA are recorded; routed experts satisfy the MXFP4 baseline contract.
- [x] T044 [Infra] Run dual-5090 llama.cpp smoke
  - DoD: `--list-devices`, localhost boot, `/v1/models`, one completion, VRAM/RAM snapshots, 64K start or documented 32K fallback, and shutdown all pass.
  - 2026-08-12 evidence: corrected candidate SHA256
    `f436ed2f92e6d6d49b5c73c546f2d52a6fa277b9f72d9915bff08b9385bb286b`;
    90/90 routed-expert, 9/9 nonexpert, and 52/52 sampled FP8-backbone
    dequantization/Q8_0 comparisons passed.
    The 64K localhost runtime loaded in 43.8 s through `--load-mode dio` with
    auto-fit, `/health` and `/v1/models` passed, and raw France completion
    started ` Paris.` at 24.6 tok/s with no Xid/BAD_PAGE/Oops.
- [x] T045 [QA] Run GGUF behavior probes
  - Chat JSON, Chinese response, and Python-code probes passed through the OpenAI-compatible endpoint. The exact 11-token native-smoke code prompt has matching native/GGUF first greedy token (`\n`). A 32,767-token prefill plus eight-token decode completed at 371.5 prompt tok/s with no routing errors, NaN, Xid, or kernel fault.
- [x] T047 [Docs] Close scope evidence and define next quantization scope
  - Scope/wiki contain hashes, commands, PASS/fail evidence, and residual risks. puwaer A/B and IQ3/Q2 remain out of scope; MXFP4 is the sole deployment artifact.

Cancelled: T046 puwaer/HERETIC A/B by user decision. Further quantization is out of scope.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- Phase 3 depends on the completed Phase 1 artifact and Phase 2 byte-verification
  acceptance. It does not depend on fixing the upstream native HF CUDA runtime.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
