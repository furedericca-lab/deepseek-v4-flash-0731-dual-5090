---
title: DeepSeek V4 first-boot and agent stability risks
type: reflection
status: current
scope: deepseek-v4-flash-0731-dual-5090
related_scopes:
  - deepseek-v4-flash-0731-dual-5090
related_files:
  - scripts/llama-server-first-boot.sh
source_docs: []
tags:
  - deepseek-v4
  - llama.cpp
  - agent-stability
last_checked: 2026-08-11
updated: 2026-08-10T19:07:12Z
---

# DeepSeek V4 first-boot and agent stability risks

For this DeepSeek-V4-Flash-0731 deployment, the first boot should keep the frozen baseline: full GPU weights, layer split -ts 1,1, --no-kv-offload, F16/F16 KV, -c 65536, -np 1, -b 1024, -ub 256, mmap default, and no mlock. Community measurements suggest F16 KV is modest at 64K, so the first suspected limit is the roughly 5.9 GiB GPU headroom for per-device compute/graph and temporary buffers, not KV alone. Record nvidia-smi for both GPUs, host RSS, free RAM, prompt and generation throughput, and logs confirming the CUDA Lightning Indexer path. Do not change to quantized KV. After 64K is proven, test 128K then 256K with evidence. Hermes acceptance must include 20-50 multi-turn tool-call rounds, checking SWA/KV rollback reuse failures, premature context-exceeded errors, repeated prefill, special-token leakage, repeated tool calls, and runaway output. reasoning-format deepseek parses reasoning output but does not imply reasoning_effort high/max control. This note is a hypothesis and test checklist, not proof of local stability.
