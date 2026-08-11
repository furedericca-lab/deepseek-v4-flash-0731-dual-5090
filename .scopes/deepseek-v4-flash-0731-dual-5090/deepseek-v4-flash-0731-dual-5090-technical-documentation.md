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
/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8/ # REAP base
/opt/llama.cpp/ or ./vendor/llama.cpp/               # source build location (to be chosen in phase 2)
```

### Preferred model path

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf
```

Why runtime artifacts stay on NVMe:

- the former Toshiba copies were deleted after their hashes disagreed with
  Hugging Face metadata
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

### REAP-132 reproduction provenance

- Exact plan: `squanchyzx-puwaer-reap132-mask.json`
- Base repo: `squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8`
- Base commit: `e7efd043c5e072da4d40f0f98ade554c5713bad9` (v2)
- Pruned commit: `868fa38e2f2964699ad065dc8d9382c136cc60b8`
- Logical SHA256:
  `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`
- The plan contains 43 layers with 132 survivor IDs each and three byte-exact
  `[129280, 6]` `int64` `tid2eid` tables.
- Exact-plan compression requires a local checkpoint root containing
  `.checkpoint-source.json`. The manifest repo/revision must match the plan,
  and local `config.json` plus `model.safetensors.index.json` must match the
  SHA256 values recorded in the manifest before model loading begins.
- `--source-revision` is only an optional compatibility assertion; it is not
  accepted as provenance by itself.
- This plan maps puwaer's published survivor set onto squanchyzx v2. It does
  not represent a fresh saliency calibration on the abliterated hidden states.

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

REAP plan validation:

- `uv run pytest vendor/moe-expert-compress/tests -q`
- `uv run python scripts/extract_puwaer_plan.py`
- independently decompress and validate all `tid2eid` hashes, shapes, ranges,
  and per-row distinctness
