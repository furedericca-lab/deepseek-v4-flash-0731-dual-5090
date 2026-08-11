---
title: First-boot llama-server recipe
type: how-to
status: current
scope: deepseek-v4-flash-0731-dual-5090
related_scopes: []
related_files: []
source_docs: []
tags:
  - launch
  - llama-server
last_checked: 2026-08-11
updated: 2026-08-10T18:26:39Z
---

# First-boot llama-server recipe

First-boot recipe after model is on NVMe and llama-server is built: llama-server -m /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf -ngl all -sm layer -ts 1,1 --no-kv-offload -ctk f16 -ctv f16 -c 65536 -np 1 -b 1024 -ub 256 -fa on --reasoning-format deepseek --host 127.0.0.1 --port 8000. OOM ladder: reduce batch first, then context to 32768, only then consider limited CPU offload. Context climb only after 64K is stable: 64K -> 96K -> 128K -> 192K.
