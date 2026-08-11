---
description: Implementation research notes for deepseek-v4-flash-0731-dual-5090.
---

# deepseek-v4-flash-0731-dual-5090 Implementation Research Notes

## Baseline (Current State)

Host (captured 2026-08-11):

- OS: Ubuntu Linux `7.0.0-28-generic`
- CPU: 32 logical cores
- RAM: ~46 GiB total / ~42 GiB available
- GPUs:
  - CUDA0 `NVIDIA GeForce RTX 5090` 32607 MiB
  - CUDA1 `NVIDIA GeForce RTX 5090` 32607 MiB
  - driver `610.43.02`
  - compute capability `12.0`
- CUDA toolkit: `13.3` (`/usr/local/cuda`, `nvcc` present)
- `llama-server` not installed on PATH yet
- Project root: `/home/build/work/deepseek-v4-flash-0731-dual-5090`
- Model source file:
  - `/data/toshiba-1tb/model/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf`
  - size `62394667168` bytes (`58.11 GiB`)
  - filesystem: NTFS via FUSE on Toshiba 1TB HDD

Disk candidates:

| Mount | Type | Free | Role |
|---|---|---:|---|
| `/data/linux-fast` | NVMe ext4 | ~991 GiB | preferred runtime model store |
| `/data/wd-2tb` | HDD ext4 | ~1.8 TiB | cold backup candidate |
| `/data/marshal-2tb` | HDD ext4 | ~1.8 TiB | cold backup candidate |
| `/data/toshiba-1tb` | NTFS/FUSE | ~830 GiB | current download location, not preferred runtime path |
| `/` system root | ext4 | ~349 GiB | project docs only; do not store 62GB model here permanently |

Upstream model facts:

- repo: `puwaer/DeepSeek-V4-Flash-0731-reap-150b-gguf`
- file: `DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf`
- architecture: DeepSeek-V4 REAP-150B, 43 layers, 132 routed experts, 6 experts/token
- Attention / Indexer / Shared Experts remain Q8_0
- published SHA256 for Q2_K:
  `2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48`
- author verified full-GPU offload; partial offload historically fragile
- Q2_K quality not separately benchmarked
- MTP modules absent → no MTP speculative decoding

llama.cpp facts:

- latest release observed: `b10344` (2026-08-10)
- Linux recommendation: build from source with `GGML_CUDA=ON`
- server supports OpenAI-compatible Chat Completions and Responses APIs
- relevant flags confirmed in current server docs:
  `-ngl`, `-sm layer`, `-ts`, `--no-kv-offload`, `-ctk`, `-ctv`, `-c`,
  `-np`, `-b`, `-ub`, `-fa`, `--reasoning-format`, `--host`, `--port`,
  `--list-devices`

## Gap Analysis

| Gap | Evidence | Impact |
|---|---|---|
| Runtime model path on slow/FUSE NTFS | model currently on `/data/toshiba-1tb` | slow load, potential mmap friction |
| llama.cpp not installed | `llama-server` missing | cannot serve yet |
| Host RAM only ~46 GiB | `free -h` plus V4 KV measurements | KV alone is expected to be modest at 64K; host runtime/pinned/page-cache behavior remains unverified |
| No project launch contract yet | empty scaffold docs | agents cannot reproduce the intended stack |
| No SHA256 verification yet | checksum not run | 62GB file integrity unknown |

## Candidate Designs and Trade-offs

### A. Preferred dual-5090 layout

- weights: full GPU via `-ngl all -sm layer -ts 1,1`
- KV: system RAM F16 via `--no-kv-offload -ctk f16 -ctv f16`
- context: start 64K, single slot
- batch: conservative `-b 1024 -ub 256`

Pros: maximizes GPU free space for compute; matches Master’s preferred architecture.
Cons: host runtime, pinned buffers, mmap/page cache, and compute staging still need measurement.

### B. GPU KV layout

- keep weights full GPU, leave KV on GPU

Pros: lower host RAM pressure.
Cons: consumes scarce remaining VRAM; contradicts the dual-5090 headroom strategy.

### C. CPU expert offload

- move some MoE weights to CPU

Pros: may reduce VRAM pressure.
Cons: upstream warned about partial offload fragility; not first choice.

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Use Q2_K REAP-150B | 5 | 5 | Master brief + HF card | none | 5 | 5 | 4 | Explicit preferred quant and file | Accept |
| Full GPU weights + layer split 1:1 | 5 | 5 | Master brief + HF serving notes | none | 5 | 4 | 4 | Dual 5090 present; full offload preferred | Accept |
| KV in system RAM F16 | 5 | 4 | Master brief + llama.cpp flags | host only 46 GiB RAM | 5 | 3 | 3 | Architecture accepted, host capacity risk remains | Accept with residual risk |
| Move model to `/data/linux-fast` | 4 | 5 | local disk inventory + FUSE mount type | none | 4 | 5 | 5 | NVMe ext4 is clearly better runtime path | Accept |
| Start context at 64K | 5 | 3 | Master brief vs current RAM | capacity conflict | 5 | 2 | 4 | Keep as target, allow 32K fallback | Accept with fallback |
| Source-build llama.cpp CUDA | 4 | 5 | Linux host + CUDA 13.3 + build docs | none | 4 | 4 | 5 | Best fit for this Linux dual-GPU host | Accept |
| Avoid expert CPU offload first | 4 | 4 | HF card partial-offload warning | none | 4 | 4 | 4 | Prefer stability over early offload tricks | Accept |

## Selected Design

Canonical first deployment:

```text
Model runtime path:
  /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf

Source/download path:
  /data/toshiba-1tb/model/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf

Runtime:
  llama-server from local CUDA build

Launch v1:
  llama-server \
    -m /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf \
    -ngl all \
    -sm layer \
    -ts 1,1 \
    --no-kv-offload \
    -ctk f16 \
    -ctv f16 \
    -c 65536 \
    -np 1 \
    -b 1024 \
    -ub 256 \
    -fa on \
    --reasoning-format deepseek \
    --host 127.0.0.1 \
    --port 8000
```

Memory topology target:

```text
2×5090 VRAM (~64 GiB)
  └── ~58.11 GiB model weights (layer split 1:1)
  └── ~5.9 GiB compute / runtime buffers

System RAM
  └── F16 KV cache
  └── context state
  └── llama-server process / page cache
```

## Validation Plan

1. Verify dual CUDA devices with `nvidia-smi` and `llama-server --list-devices`.
2. Copy model to NVMe path and verify SHA256.
3. Build llama.cpp with CUDA and confirm `llama-server` binary.
4. Launch with v1 flags and capture:
   - process start success
   - per-GPU memory use
   - `/health` or OpenAI models endpoint
   - one short chat completion
5. If OOM:
   - reduce batch first
   - then reduce context to 32K
   - only then consider limited CPU offload
6. If 64K stable, climb context: 64K → 128K → 256K, recording GPU and host buffers at each step.

## Risks and Assumptions

- Assumption: Master accepts localhost-first bind (`127.0.0.1`) until security review.
- Assumption: Q2_K quality is acceptable despite missing public benchmarks.
- Risk: compute/graph and temporary indexer buffers may exhaust the roughly 5.9 GiB GPU headroom; KV arithmetic alone does not prove runtime stability.
- Risk: first full load from Toshiba NTFS would be slower/less reliable than NVMe.
- Risk: remaining ~5.9 GiB GPU headroom can still be consumed by attention temps at high batch/context.
