---
description: Brainstorming and decision framing for deepseek-v4-flash-0731-dual-5090.
---

# deepseek-v4-flash-0731-dual-5090 Brainstorming

## Problem

Deploy an OpenAI-compatible local inference service for
`DeepSeek-V4-Flash-0731 REAP-150B Q2_K` on a dual RTX 5090 host using llama.cpp
CUDA, with:

- layer-split multi-GPU offload
- model weights fully on GPU when possible
- F16 KV cache in system RAM
- 64K context as the first target
- Hermes / agent-friendly API surface

## Scope

In scope for this planning scope:

- host readiness and model placement
- llama.cpp CUDA build/runtime selection
- first-boot launch command and OOM recovery ladder
- context growth strategy after 64K is stable
- wiki/scope documentation for future agent sessions

Out of scope:

- model quality benchmarking of Q2_K
- multi-user concurrent serving beyond single slot
- speculative decoding / MTP
- Windows-specific Shared GPU Memory workflows

## Constraints

- Host evidence (2026-08-11):
  - 2× NVIDIA GeForce RTX 5090 32GB, driver 610.43.02, compute capability 12.0
  - CUDA toolkit 13.3 present (`nvcc` 13.3.73)
  - System RAM currently ~46 GiB total
  - Model file already present at
    `/data/toshiba-1tb/model/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf`
    (62,394,667,168 bytes = 58.11 GiB)
  - Toshiba mount is NTFS via FUSE (`fuseblk`) — poor mmap/load path for a 62GB GGUF
  - Fastest free model disk is `/data/linux-fast` (NVMe, ext4, ~991 GiB free)
- Upstream evidence:
  - Model card recommends full GPU offload; partial offload was historically fragile
  - Q2_K is 58.11 GiB; Attention/Indexer/Shared Experts stay Q8_0
  - Q2_K has no published quality benchmark; loss is unmeasured
  - llama.cpp latest release observed as `b10344` (newer than earlier note `b10333`)
  - Official flags support `--no-kv-offload`, `-ctk f16`, `-ctv f16`, `-sm layer`,
    `-ts`, `-ngl all`, `-c`, `-np`, `-fa`, `--reasoning-format deepseek`

## Options

### Model storage location

1. Keep on `/data/toshiba-1tb` (NTFS/FUSE)
2. Copy to `/data/linux-fast/models/...` (NVMe ext4)
3. Copy to large HDD ext4 (`/data/wd-2tb` or `/data/marshal-2tb`)

### Inference layout

1. Weights full GPU + KV RAM F16 + 64K start
2. Weights full GPU + KV GPU F16
3. Mixed CPU offload of experts

### Context policy

1. Start at 64K and climb 64→96→128→192
2. Start at 32K because host RAM is only 46 GiB
3. Jump directly to 128K+

## Decision Summary

| Decision | Options Considered | Rationale | Research Note Link |
|---|---|---|---|
| Model path | Toshiba NTFS vs linux-fast NVMe vs HDD | Prefer NVMe ext4 for mmap/load stability and throughput | research notes / selected design |
| Offload policy | full GPU vs mixed CPU | Upstream verified full GPU; partial offload historically risky | research notes |
| KV placement | RAM F16 vs GPU F16 | Preserve ~5.9 GiB GPU headroom for compute buffers | research notes |
| First context | 64K vs 32K | Plan remains 64K target, but host RAM may force 32K first boot | milestones residual risk |
| Framework | latest llama.cpp CUDA source build | Host is Linux with CUDA 13.3; source CUDA build preferred over Windows package | technical docs |

## Decision

Adopt:

- model runtime path on `/data/linux-fast/models/DeepSeek-V4-Flash-0731/`
- llama.cpp CUDA build from source with `GGML_CUDA=ON`
- dual-GPU layer split `-sm layer -ts 1,1 -ngl all`
- `--no-kv-offload -ctk f16 -ctv f16`
- first launch with `-c 65536 -np 1 -b 1024 -ub 256 -fa on --reasoning-format deepseek`
- if RAM pressure or CUDA OOM appears, follow the documented recovery ladder before changing quant

## Risks

- Host RAM is far below the 128–256 GiB comfort band for long F16 KV contexts.
- Q2_K quality is unbenchmarked.
- Toshiba NTFS path may cause slow load or mmap issues if used as runtime source.
- Dual-GPU layer split still needs temporary GPU compute buffers; 64 GiB VRAM is not pure free space.

## Open Questions

- Confirm whether Master will expand system RAM before long-context production use.
- Confirm preferred API bind address (localhost only vs LAN `0.0.0.0`).
- Confirm whether Hermes should point at this endpoint as a default local model.
