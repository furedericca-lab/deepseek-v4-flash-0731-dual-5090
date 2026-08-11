---
description: API and schema contracts for deepseek-v4-flash-0731-dual-5090.
---

# deepseek-v4-flash-0731-dual-5090 Contracts

## API Contracts

Primary endpoint:

```text
http://127.0.0.1:8000/v1
```

Expected capabilities from llama-server:

- OpenAI-compatible Chat Completions
- OpenAI-compatible Responses API where available
- reasoning content extraction via `--reasoning-format deepseek`

Minimum smoke request after boot:

```bash
curl -s http://127.0.0.1:8000/v1/models
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "DeepSeek-V4-Flash-0731-reap-150b-Q2_K",
    "messages": [{"role":"user","content":"ping"}],
    "max_tokens": 32
  }'
```

## Shared Types / Schemas

Deployment identity:

| Field | Value |
|---|---|
| model_family | DeepSeek-V4-Flash-0731 |
| compression | REAP-150B |
| quant | Q2_K |
| gguf_size | 58.11 GiB / 62394667168 bytes |
| sha256 | 2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48 |
| source_path | /data/toshiba-1tb/model/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf |
| runtime_path | /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf |
| gpus | 2× RTX 5090 32GB |
| split_mode | layer |
| tensor_split | 1,1 |
| kv_location | system RAM |
| kv_dtype | f16 |
| context_start | 65536 |
| parallel_slots | 1 |

## Event and Streaming Contracts

- Streaming may be enabled by clients after non-stream smoke passes.
- Thinking is on by default in the model template; clients that need plain answers should pass chat template kwargs to disable thinking when supported.
- Do not assume MTP speculative decoding exists; MTP modules are absent in this checkpoint.

## Error Model

| Symptom | First action | Next action | Last resort |
|---|---|---|---|
| CUDA OOM at boot | lower `-b/-ub` | lower `-c` to 32768 | limited CPU offload only if unavoidable |
| process thrash / host RAM pressure | lower context | reduce batch | add RAM or accept short context |
| slow model load | ensure runtime path is NVMe ext4 | avoid Toshiba FUSE path | keep local page cache warm |
| only one GPU visible | check `nvidia-smi` and `--list-devices` | fix driver/CUDA visibility | do not proceed with dual-split flags |
| checksum mismatch | re-copy or re-download | do not serve | quarantine bad file |

## Validation and Compatibility Rules

- First-boot command must include:
  `-ngl all -sm layer -ts 1,1 --no-kv-offload -ctk f16 -ctv f16 -c 65536 -np 1 -b 1024 -ub 256 -fa on --reasoning-format deepseek`
- Do not mark deployment complete without:
  - dual-GPU visibility evidence
  - checksum evidence
  - successful API smoke
  - recorded VRAM snapshot
- Context increases require a new evidence note; do not silently jump to 128K+.

## Requirement Boundary Notes

- This contract is for single-node local serving.
- LAN bind (`0.0.0.0`) and auth/TLS are future hardening, not part of the first boot contract.
- Host RAM currently under the recommended band remains an accepted residual risk for long context.
