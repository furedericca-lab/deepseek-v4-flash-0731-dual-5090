---
description: Scope boundaries and milestones for deepseek-v4-flash-0731-dual-5090.
---

# deepseek-v4-flash-0731-dual-5090 Scope and Milestones

## In Scope

- Document and execute the dual-5090 deployment plan for
  `DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf`
- Relocate the model from Toshiba NTFS download path to a suitable runtime disk
- Build or install llama.cpp CUDA runtime
- Define launch flags, OOM recovery ladder, and context growth policy
- Expose OpenAI-compatible local API for Hermes/agent use
- Keep durable knowledge in `.wiki/` and auditable progress in `.scopes/`

## Out of Scope

- Publishing the endpoint to the public internet
- Requantizing the model or switching to IQ1_M / 200B variants
- Benchmarking Q2_K quality against the base model
- Multi-tenant high concurrency (`-np > 1`)
- Windows Shared GPU Memory workflows

## Decision Log

| Boundary / Decision | Evidence Source | Evidence Strength | Conflict | Confidence | Confidence Reason | Result |
|---|---|---:|---|---:|---|---|
| Prefer `/data/linux-fast` runtime model store | local mount/disk inventory | 5 | current file on Toshiba | 5 | NVMe ext4 free and fast | Accepted |
| Keep Toshiba path as source/download only | FUSE NTFS mount type | 5 | convenience of current location | 5 | FUSE/NTFS is weak for 62GB mmap load | Accepted |
| Full GPU weights + RAM F16 KV | Master brief + HF + llama.cpp flags | 5 | host RAM only 46 GiB | 4 | Architecture preferred; capacity residual | Accepted |
| First context target 64K with 32K fallback | Master brief + free -h | 4 | RAM capacity | 3 | Target kept, fallback required | Accepted |
| Source-build llama.cpp CUDA 13.3 | host CUDA install + build docs | 5 | none | 5 | Linux dual-GPU host already has toolkit | Accepted |
| Do not start with expert CPU offload | HF serving notes | 4 | possible OOM workaround | 4 | full GPU is verified path | Accepted |

## Milestones

### M0 — Planning complete

- Scope docs filled with host-specific paths and residual risks
- Wiki pages capture durable deployment knowledge
- Exit: planning docs and wiki rebuild/lint pass

### M1 — Host and model readiness

- dual GPUs visible
- model copied to runtime path
- SHA256 verified
- Exit: model path ready on NVMe ext4

### M2 — Runtime ready

- llama.cpp CUDA build available
- `llama-server --list-devices` shows both 5090s
- Exit: binary and device enumeration verified

### M3 — First successful serve

- launch with first-boot flags
- health/API smoke test passes
- GPU memory split roughly balanced
- Exit: one successful completion request

### M4 — Context hardening

- prove 64K or document forced lower context
- optional climb to 96K/128K if stable
- Exit: production launch recipe frozen

## Dependencies

- dual RTX 5090 online
- CUDA 13.x toolkit and driver
- free space on `/data/linux-fast` for 62GB+ model
- preferably ≥128 GiB system RAM for comfortable long-context F16 KV
- network only if re-downloading; current local model file already exists

## Exit Criteria

- documented runtime model path is not on NTFS/FUSE
- first-boot launch command is exact and reproducible
- OOM recovery order is explicit
- residual host-RAM risk is recorded, not hidden
- wiki/README/AGENTS point future agents to the same plan

## Escalation Triggers

- Escalate only when code/runtime evidence, authoritative wiki, and scope docs materially conflict and the conflict cannot be resolved from local evidence.
- Escalate if Master requires public bind / multi-user exposure without auth.
- Escalate if host RAM cannot support any usable context and Master rejects lower context or RAM upgrade.
- Escalate if full-GPU offload is impossible on this host and permanent CPU offload becomes required.
