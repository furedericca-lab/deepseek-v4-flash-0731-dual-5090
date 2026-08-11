---
title: Dual 5090 Q2_K full-GPU with RAM F16 KV
type: decision
status: accepted
scope: deepseek-v4-flash-0731-dual-5090
related_scopes: []
related_files: []
source_docs: []
tags:
  - deployment
  - llama-cpp
  - dual-5090
last_checked: 2026-08-11
updated: 2026-08-10T18:26:38Z
decision_date: 2026-08-11
---

# Dual 5090 Q2_K full-GPU with RAM F16 KV

Accepted architecture: DeepSeek-V4-Flash-0731 REAP-150B Q2_K on 2x RTX 5090 with -ngl all, -sm layer, -ts 1,1, --no-kv-offload, -ctk/-ctv f16, start -c 65536 -np 1 -b 1024 -ub 256. Runtime model path preferred on /data/linux-fast (NVMe ext4); Toshiba NTFS path is source only. Residual risk: host currently has only ~46 GiB RAM versus 128-256 GiB comfort band.
