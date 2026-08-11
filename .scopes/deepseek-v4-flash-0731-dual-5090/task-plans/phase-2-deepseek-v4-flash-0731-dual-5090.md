---
description: Task list for deepseek-v4-flash-0731-dual-5090 phase 2.
---

# Tasks: deepseek-v4-flash-0731-dual-5090 Phase 2

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-scope-milestones.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-brainstorming.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-implementation-research-notes.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-technical-documentation.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-contracts.md`

## Canonical architecture / Key constraints
- Build llama.cpp with CUDA on this Linux host.
- Enumerate both 5090 devices before serving.
- First launch uses conservative batch and single slot.
- Keep KV off GPU. Treat GPU compute/graph and temporary buffers as the primary first-boot limit; host F16 KV is expected to be modest at 64K but must still be measured.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 2: Runtime build and first boot
Goal: produce a working llama-server CUDA runtime and complete first successful serve.

Definition of Done: both GPUs are visible to llama-server, the first-boot command starts, and one API smoke request succeeds or a concrete blocker is recorded.

Tasks:
- [x] T021 [Infra] Clone and build llama.cpp with `GGML_CUDA=ON`
  - DoD: `llama-server` binary exists and reports build/version info.
- [x] T022 [QA] Confirm device enumeration
  - DoD: `llama-server --list-devices` shows CUDA0 and CUDA1 as RTX 5090.
- [x] T023 [Config] Add launch script/config using the frozen first-boot flags
  - DoD: script points at the NVMe runtime model path and includes
    `-ngl all -sm layer -ts 1,1 --no-kv-offload -ctk f16 -ctv f16 -c 65536 -np 1 -b 1024 -ub 256 -fa on --reasoning-format deepseek --host 127.0.0.1 --port 8000`.
- [x] T024 [QA] First-boot smoke test
  - DoD: server starts, `/v1/models` or equivalent responds, one short completion works, `nvidia-smi` snapshot is saved.
- [x] T025 [Docs] Record actual VRAM/RAM behavior and any required fallback
  - DoD: checklist/wiki updated with measured numbers and whether 64K held or 32K fallback was required.

Checkpoint: Phase 2 artifacts are merged, verified, and recorded in 3phases-checklist.md before next phase starts.

## Dependencies & Execution Order
- Phase 1 model placement blocks phase 2 launch.
- T021 before T022-T024.
- T023 may be prepared in parallel with the build once the binary path is known.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
