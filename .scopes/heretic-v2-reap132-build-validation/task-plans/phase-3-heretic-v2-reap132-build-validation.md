---
description: Task list for heretic-v2-reap132-build-validation phase 3.
---

# Tasks: heretic-v2-reap132-build-validation Phase 3

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-scope-milestones.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-brainstorming.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-implementation-research-notes.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-technical-documentation.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-contracts.md`

## Canonical architecture / Key constraints
- Convert only the Phase 2 byte-verified native checkpoint; a documented native
  HF runtime limitation does not block this deployment-runtime phase.
- Pin and record the llama.cpp converter commit and exact command.
- The first GGUF is the MXFP4-preserving golden baseline; no IQ3/Q2 yet.
- Runtime binds to localhost and uses both RTX 5090s with existing OOM order.
- A/B prompts, flags, and scoring must be identical between artifacts.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 3: Golden GGUF, Dual-5090 Runtime, and Controlled A/B
Goal: Convert the verified native checkpoint without losing the intended expert representation, validate it locally, and measure the HERETIC overlay as the controlled variable.

Definition of Done: A fully hashed golden GGUF passes metadata and dual-5090 runtime gates, and a reproducible puwaer-versus-HERETIC A/B report is complete.

Tasks:
- [x] T041 [Config] Pin and inspect the llama.cpp converter
  - DoD: Converter commit, DeepSeek-V4 support, accepted flags, and routed-expert output type are recorded before conversion.
- [ ] T042 [Infra] Convert the accepted native checkpoint
  - DoD: Exact command converts the Phase 2 artifact to a GGUF under `/data/linux-fast/models/DeepSeek-V4-Flash-0731/` without reading any unverified checkpoint.

T041 outcome: use standalone `vendor/llama.cpp` local commit `16f35dd`, based on
upstream `030ebb558a5820b444a8f836ed5cdd46c9b4bd7a`. Its converter registers
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
- [ ] T043 [QA] Verify and freeze the golden GGUF
  - DoD: Full GGUF SHA256, size, metadata, expert count/type, architecture, tokenizer, and source native manifest SHA are recorded; routed experts satisfy the MXFP4 baseline contract.
- [ ] T044 [Infra] Run dual-5090 llama.cpp smoke
  - DoD: `--list-devices`, localhost boot, `/v1/models`, one completion, VRAM/RAM snapshots, 64K start or documented 32K fallback, and shutdown all pass.
- [ ] T045 [QA] Run GGUF behavior probes
  - DoD: Chat, reasoning, coding, tool-call, and longer-context checks show no routing errors, NaN, or obvious repetition degeneration.
- [ ] T046 [QA] Run controlled puwaer/HERETIC A/B
  - DoD: Both artifacts use identical prompts, seeds/settings, runtime flags, and evaluator; report embeds both artifact hashes and isolates the attention overlay as the intended variable.
- [ ] T047 [Docs] Close scope evidence and define next quantization scope
  - DoD: Scope/wiki contain all hashes, commands, PASS/fail evidence, residual risks, and a separate follow-up boundary for IQ3/Q2 experiments.

Checkpoint: Golden MXFP4 GGUF and controlled A/B are complete; further quantization may begin only under an explicit follow-up scope.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- Phase 3 depends on the completed Phase 1 artifact and Phase 2 byte-verification
  acceptance. It does not depend on fixing the upstream native HF CUDA runtime.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
