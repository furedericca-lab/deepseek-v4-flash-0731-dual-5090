---
description: Task list for deepseek-v4-flash-0731-dual-5090 phase 1.
---

# Tasks: deepseek-v4-flash-0731-dual-5090 Phase 1

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-scope-milestones.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-brainstorming.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-implementation-research-notes.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-technical-documentation.md`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/deepseek-v4-flash-0731-dual-5090-contracts.md`

## Canonical architecture / Key constraints
- Dual RTX 5090 layer split, full GPU weights, F16 KV in system RAM.
- Runtime model path must be NVMe ext4 under `/data/linux-fast/models/...`.
- Toshiba NTFS path is source/download only.
- First context target remains 64K; monitor GPU compute/graph buffers and host runtime memory, with 32K as the fallback if startup fails.
- Do not begin with expert CPU offload.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 1: Host readiness and model placement
Goal: freeze the deployment plan and make the model file usable from a suitable disk.

Definition of Done: planning docs are host-specific, model runtime path is chosen, and remaining blockers are explicit.

Tasks:
- [x] T001 [Docs] Convert generic scaffold into a dual-5090 deployment plan
  - DoD: brainstorming, research notes, milestones, technical docs, and contracts contain concrete host paths, flags, and residual risks.
- [x] T002 [Infra] Inventory host GPUs, CUDA, RAM, and candidate model disks
  - DoD: dual 5090, CUDA 13.3, ~46 GiB RAM, and disk free space are recorded with commands.
- [x] T003 [Infra] Select runtime model location
  - DoD: preferred path is `/data/linux-fast/models/DeepSeek-V4-Flash-0731/...`; Toshiba remains source-only.
- [ ] T004 [Infra] Create runtime model directory and copy/verify GGUF
  - DoD: file exists on NVMe path and SHA256 matches
    `2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48`.
  - Copy completed, but the destination currently hashes to
    `ae0ff224f4dfe160df3f2226ee9b9ca0d7c5c44186390eb8fa851ce36d9362d`.
    The expected digest does not match, so the model is not trusted yet.
- [ ] T005 [QA] Record phase-1 evidence in checklist
  - DoD: checklist contains copy/checksum command results or an explicit deferred reason.

Checkpoint: Phase 1 planning is complete; model copy/verify remains the implementation gate before phase 2 runtime work.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- T001-T003 can complete from local inventory.
- T004 must finish before phase 2 launch attempts.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
