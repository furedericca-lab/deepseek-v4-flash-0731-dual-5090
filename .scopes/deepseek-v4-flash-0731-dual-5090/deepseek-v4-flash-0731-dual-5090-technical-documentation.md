---
description: Technical operations for the corrected K132 MXFP4 deployment.
---

# Corrected K132 MXFP4 Deployment

## Architecture

```text
accepted native K132 noMTP
        -> deterministic full routed MXFP4 rebuild
        -> 100% routed byte provenance
        -> read-only corrected GGUF
        -> llama.cpp efb81ab, O_DIRECT
        -> dual RTX 5090 layer split, 64K, one slot
```

The GGUF is stored on ext4 NVMe under `/data/linux-fast/models`; bulk reads,
hashing, and provenance use aligned O_DIRECT. Git stores only code and evidence,
never model payloads.

## Runtime

Use `scripts/llama-server-first-boot.sh`. The server uses layer auto-fit with a
2 GiB target margin on each GPU, full GPU weights, F16 KV in system RAM, 64K
context, one slot, batch 512, ubatch 128, flash attention, and port 8000 on
all host interfaces. The approved LAN entry point is `172.30.0.214:8000`.
`-ngl all` is prohibited for this artifact.

Accepted observations include approximately 28 GiB per GPU for the corrected
MXFP4 run, healthy API startup, coherent raw/chat/Chinese/JSON/Python behavior,
and a clean 32,767-token prefill/decode run. Exact performance varies by build
and boot; acceptance is behavioral and fault-based, not a fixed throughput SLA.

## Host Gate

Before any large model task:

```bash
cat /proc/sys/kernel/tainted
journalctl -k -b --no-pager | \
  rg -i 'BAD_PAGE|compound_head|corrupted mapping in tail page|Oops|general protection|NVRM: Xid|Xid \\('
nvidia-smi
free -h
```

Stop after any model-related kernel fault or unexplained native SIGSEGV and
reboot before collecting acceptance evidence. Docker and unrelated large scans
remain stopped during model validation.

## Candidate Policy

The rejected mixed candidate demonstrated that successful loading, finite
weights, correct tensor types, and long-prefill completion are insufficient.
Promotion requires fixed greedy behavior probes including Chinese, JSON,
Python, and long-prefill decode. Repeated-symbol output is a hard failure.

The fixed 17/26 plan is historical evidence. Its activation score was strongly
correlated with layer depth and concentrated Q2_K_S in layers 0-19. Do not
silently reinterpret or rerank that archived experiment.

Phase 4 instead uses a projection-aware, boundary-protected recipe:

```text
corrected K132 MXFP4
  -> routed layers 0-2,41-42: MXFP4
  -> routed layers 3-40 gate/up: Q2_K
  -> routed layers 3-40 down: Q3_K
  -> non-routed: K96 Profile A IQ4_XS non-pure mixed
  -> puwaer 812-chunk imatrix for all compatible quantized tensors
```

The recipe is applied to our corrected weights; no payload bytes are copied
from the external quantized GGUF. The external `.prev` imatrix proves ranking
convergence but is never merged with the final cumulative imatrix.

## Recovery

If a future candidate fails, stop the server, restore this scope's corrected
MXFP4 path in the launcher, verify the current boot is clean, and rerun health
plus short behavior probes. Do not patch a failed GGUF in place.

## Major Decisions and Trade-offs

- The corrected full-routed MXFP4 GGUF is immutable and remains deployment and
  rollback baseline.
- The Q2/Q3 routed recipe was preferred over the rejected 17/26 plan because
  it protects boundary layers and down projections, but it remained an
  experiment with no size gate.
- A candidate must pass semantic behavior after structure and startup; the
  rejected Q2 candidate proves that successful loading is insufficient.
