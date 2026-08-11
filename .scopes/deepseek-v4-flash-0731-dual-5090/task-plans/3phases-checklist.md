---
description: Execution and verification checklist for deepseek-v4-flash-0731-dual-5090 3-phase plan.
---

# Phases Checklist: deepseek-v4-flash-0731-dual-5090

## Input
- Canonical docs under:
  - `.scopes/deepseek-v4-flash-0731-dual-5090`
  - `.scopes/deepseek-v4-flash-0731-dual-5090/task-plans`

## Rules
- Use this file as the single progress and audit hub.
- Update status, evidence commands, and blockers after each implementation batch.
- Do not mark a phase complete without evidence.

## Global Status Board
| Phase | Status | Completion | Health | Blockers |
|---|---|---|---|---|
| Phase 1 | In progress | 40% | Red | Copied GGUF SHA256 differs from expected digest; runtime remains blocked |
| Phase 2 | Complete | 100% | Yellow | 64K booted; long-agent stability and high swap use remain risks |
| Phase 3 | Not started | 0% | Unknown | 0 |

## Phase Entry Links
1. [phase-1-deepseek-v4-flash-0731-dual-5090.md](phase-1-deepseek-v4-flash-0731-dual-5090.md)
2. [phase-2-deepseek-v4-flash-0731-dual-5090.md](phase-2-deepseek-v4-flash-0731-dual-5090.md)
3. [phase-3-deepseek-v4-flash-0731-dual-5090.md](phase-3-deepseek-v4-flash-0731-dual-5090.md)

## Phase Execution Records

### 2026-08-11 planning batch
- Phase: 1
- Batch date: 2026-08-11
- Completed tasks:
  - filled brainstorming / research / milestones / technical docs / contracts
  - selected runtime model path on `/data/linux-fast`
  - recorded dual-5090 + CUDA 13.3 host baseline
- Evidence commands:
  - `nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader`
  - `df -hT /data/linux-fast /data/toshiba-1tb /data/wd-2tb /data/marshal-2tb`
  - `stat -c '%n %s' /data/toshiba-1tb/model/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf`
  - `free -h`
  - `nvcc --version`
- Issues/blockers:
  - model still needs copy from Toshiba NTFS to NVMe runtime path
  - 64K compute/graph and runtime-buffer behavior is not yet measured
  - llama-server not installed yet
- Resolutions:
  - planning docs now encode preferred path, launch recipe, and OOM ladder
- Checkpoint confirmed: planning-only; implementation not complete

### 2026-08-11 runtime preparation batch
- Phase: 2
- Completed tasks:
  - cloned llama.cpp at `030ebb5`
  - configured and built CUDA `llama-server`
  - added `scripts/llama-server-first-boot.sh`
  - verified CUDA0/CUDA1 are both RTX 5090
- Evidence commands:
  - `vendor/llama.cpp/build/bin/llama-server --version`
  - `vendor/llama.cpp/build/bin/llama-server --list-devices`
- Remaining:
  - model copy and SHA256 verification
  - first-boot server and API smoke test

### 2026-08-11 model placement batch
- Phase: 1
- Copy status: completed to the NVMe runtime path.
- Observed destination SHA256: `ae0ff224f4dfe160df3f2226ee9b9ca0d7c5c44186390eb8fa851ce36d9362d`.
- Expected SHA256: `2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48`.
- Blocker: digest mismatch; do not launch until source identity is reconciled.

### 2026-08-11 first-boot batch
- Phase: 2
- Results:
  - `llama-server` loaded the model with `n_ctx_slot = 65536` and listened on `http://127.0.0.1:8000`.
  - `/v1/models` returned the loaded GGUF.
  - One short chat completion returned successfully.
  - `nvidia-smi`: GPU0 used 31,455 MiB; GPU1 used 29,686 MiB.
  - `free -h`: 46 GiB RAM total, 43 GiB swap used after load.
- Residual risks:
  - 64K startup is proven, but high swap use needs operational follow-up.
  - Multi-turn tool-call, rollback/reuse, template leakage, and 128K/256K context tests remain for Phase 3.

## Final Release Gate
- Scope constraints preserved.
- Quality/security gates passed.
- Remaining risks documented.
