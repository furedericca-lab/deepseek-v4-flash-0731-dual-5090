---
description: Canonical technical architecture for deepseek-v4-flash-0731-dual-5090.
---

# deepseek-v4-flash-0731-dual-5090 Technical Documentation

## Canonical Architecture

```text
Hermes / clients
        │
        ▼
llama-server :8000  (OpenAI-compatible)
        │
        ├─ model weights: DeepSeek-V4-Flash-0731 REAP-150B Q2_K
        │     split across CUDA0 + CUDA1 by layer (-sm layer -ts 1,1)
        │
        ├─ KV cache: system RAM, F16 (--no-kv-offload -ctk f16 -ctv f16)
        │
        └─ context slot: single parallel slot (-np 1), start -c 65536
```

### Runtime filesystem layout

```text
/home/build/work/deepseek-v4-flash-0731-dual-5090/   # project docs, scripts, scopes, wiki
/data/linux-fast/models/DeepSeek-V4-Flash-0731/      # preferred runtime model store (NVMe ext4)
/data/toshiba-1tb/model/                             # current download/source path (NTFS/FUSE)
/opt/llama.cpp/ or ./vendor/llama.cpp/               # source build location (to be chosen in phase 2)
```

### Preferred model path

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf
```

Why not keep runtime load on Toshiba:

- mount type is `fuseblk`/NTFS
- 62GB GGUF benefits from native ext4 + NVMe mmap/read performance
- project docs stay on system disk; model bulk stays on data disks

## Key Constraints and Non-Goals

Constraints:

- 2×5090 = 64 GiB VRAM total
- Q2_K weights ≈ 58.11 GiB → only ~5.9 GiB GPU headroom for compute buffers
- host currently has ~46 GiB RAM; community V4 KV estimates suggest this is not an automatic 64K blocker, but host runtime/pinned/page-cache behavior remains unmeasured
- single concurrent slot for first deployment
- full GPU offload preferred; expert CPU offload is last resort

Non-goals:

- do not optimize for multi-user throughput first
- do not chase maximum advertised context before stability
- do not use Windows shared memory assumptions on this Linux host

## Major Decisions and Trade-offs

1. **Weights on GPU, KV on RAM**
   - Trade VRAM headroom for compute stability.
2. **Layer split 1:1**
   - Simple balanced dual-GPU pipeline for equal 5090s.
3. **Conservative first batch**
   - `-b 1024 -ub 256` before raising defaults.
4. **Context climb, not jump**
   - 64K first, then 96/128/192 only after evidence.
5. **Model on NVMe ext4**
   - Prefer load reliability over leaving the file on the download disk.

## Module Boundaries and Data Flow

| Component | Owns | Does not own |
|---|---|---|
| project repo | launch docs, scripts, scopes, wiki | 62GB GGUF binary content in git |
| `/data/linux-fast/models/...` | runtime model file | project source control |
| llama-server | inference, OpenAI API | agent orchestration |
| Hermes / clients | prompts, tools, sessions | model placement/offload policy |

## Interfaces and Contracts

- Local OpenAI-compatible base URL target:
  `http://127.0.0.1:8000/v1`
- First-boot launch command is the contract for runtime behavior.
- Model identity:
  - repo `puwaer/DeepSeek-V4-Flash-0731-reap-150b-gguf`
  - quant `Q2_K`
  - sha256 `2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48`

## Security and Reliability

- Default bind: `127.0.0.1` until explicit LAN exposure is approved.
- Do not commit secrets, API keys, or private chat logs.
- Verify model checksum before first production serve.
- Record OOM recovery order so operators do not immediately switch quants.
- Keep `.wiki/` as durable internal knowledge; it may remain local/ignored.

## Test Strategy

Planning validation:

- repo-task-driven placeholder/sync checks
- wiki rebuild/lint/doctor

Runtime validation (implementation phases):

1. device enumeration
2. model checksum
3. server boot
4. `/v1/models` or health endpoint
5. one short completion
6. memory snapshot from `nvidia-smi`
7. optional longer-context probe
