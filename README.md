# DeepSeek-V4-Flash-0731 Dual 5090

Local llama.cpp CUDA deployment project for DeepSeek-V4-Flash-0731 REAP-150B
artifacts on 2x RTX 5090.

on 2× RTX 5090 with layer split, full GPU weights, and F16 KV cache in system RAM.

## Model Artifacts

| Item | Value |
|---|---|
| GPUs | 2× RTX 5090 32GB |
| Model | DeepSeek-V4-Flash-0731 REAP-150B |
| Verified baseline | `Q2_K` |
| Current candidate | `IQ3_XXS` |
| Runtime directory | `/data/linux-fast/models/DeepSeek-V4-Flash-0731/` |
| Split | `-sm layer -ts 1,1` |
| Weights | `-ngl all` |
| KV | `--no-kv-offload -ctk f16 -ctv f16` |
| Context start | `-c 65536` |
| Parallel | `-np 1` |
| Batch start | `-b 1024 -ub 256` |
| API | `http://127.0.0.1:8000/v1` |

## Why the model should move off Toshiba

For large GGUF files, the preferred runtime store is the NVMe ext4 mount:

`/data/linux-fast/models/DeepSeek-V4-Flash-0731/`

Do not use a deleted Toshiba source copy as a verification source; compare local
SHA256 with the Hugging Face metadata recorded in `AGENTS.md`.

## First-boot command

```bash
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

## Active scope

Deployment planning and execution are tracked in:

`.scopes/deepseek-v4-flash-0731-dual-5090/`

Durable notes live in:

`.wiki/`

## Important residual risk

The ~46 GiB system RAM figure is not treated as an automatic 64K blocker: current DeepSeek V4 measurements suggest roughly 0.59 GiB F16 KV at 64K, though this is not host-boot evidence. The first suspected limit is the roughly 5.9 GiB GPU headroom for compute/graph and temporary buffers. Keep `-np 1`; prove 64K at first boot, then test 128K/256K only with measured VRAM/RAM behavior. If startup fails, lower `-b/-ub` first, then `-c 32768`, before considering CPU offload.

## Operator docs for agents

See `AGENTS.md` and `.wiki/index.md`.
