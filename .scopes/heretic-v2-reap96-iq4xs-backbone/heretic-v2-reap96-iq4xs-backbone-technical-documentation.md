---
description: Operator commands for the K96 Profile A IQ4_XS backbone release.
---

# K96 Profile A IQ4_XS Technical Documentation

## Paths

```bash
Q=vendor/llama.cpp/build/bin/llama-quantize
IN=/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4.gguf
OUT=/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4exp-IQ4XSbb.gguf
EXPERT_TYPE='^blk\.[0-9]+\.ffn_(gate|up|down)_exps\.weight=MXFP4'
```

## Profile A Dry-Run

```bash
"$Q" \
  --dry-run \
  --direct-io-input \
  --allow-requantize \
  --tensor-type "$EXPERT_TYPE" \
  "$IN" \
  IQ4_XS \
  16
```

Profile A is final. Do not add `--pure` and do not run a second profile.

## Major Decisions and Trade-offs

- Preserve only the 129 Routed Expert tensors. This protects the largest
  REAP96 payload while allowing Shared Expert and Core Backbone compression.
- Keep llama.cpp's default mixed policy. Five early Shared Expert down tensors
  become Q5_K and `output.weight` becomes Q6_K without local type heuristics.
- Add a post-build expert finalizer. It costs one 129-tensor O_DIRECT rewrite,
  but closes the byte-identity contract after sparse stable block drift was
  reproduced in rejected outputs.
- Evaluate against the recorded K96 Golden behavior, not K132 semantics. This
  separates quantization regression from the already-proven K96 quality limit.

## Production Quantization

```bash
systemd-run --user \
  --unit=reap96-iq4xs-quantize \
  --collect \
  --property=WorkingDirectory=/home/build/work/deepseek-v4-flash-0731-dual-5090 \
  "$Q" \
    --direct-io-input \
    --direct-io-output \
    --allow-requantize \
    --tensor-type "$EXPERT_TYPE" \
    "$IN" \
    "$OUT" \
    IQ4_XS \
    16
```

Do not hash, inspect payloads, or start another model scan while quantization is
running. Begin acceptance only after a zero service exit and a clean post-run
kernel gate.

## Required Expert Finalization

After the quantizer exits zero and the boot remains clean, restore the routed
expert payloads from the immutable Golden before acceptance:

```bash
uv run python scripts/finalize_reap96_iq4xs_experts.py \
  --golden "$IN" \
  --candidate "$OUT"
```

This is a full 129-tensor aligned O_DIRECT rewrite. It does not alter Shared
Expert or Core Backbone quantization, tensor types, routing, metadata, or the
Golden. Do not run it concurrently with hashing or provenance scans.

## Acceptance

```bash
uv run python scripts/verify_reap96_iq4xs_gguf.py \
  --golden "$IN" \
  --candidate "$OUT" \
  --report .scopes/heretic-v2-reap96-iq4xs-backbone/evidence/reap96-iq4xs-final-acceptance.json

uv run python tools/verify_io_paths.py --direct-only "$OUT"
```

Accepted identity:

```text
size    59,256,121,472 bytes
SHA256  845a0b91d17fddd6990068b995c8af031945af55f5bff94acc5a1c08389c63c3
mode    0444
```
