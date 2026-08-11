---
title: Model placement and disk strategy
type: implementation
status: current
scope: deepseek-v4-flash-0731-dual-5090
related_scopes: []
related_files:
  - /data/linux-fast/models/DeepSeek-V4-Flash-0731
  - scripts/write_checkpoint_source_manifest.py
source_docs:
  - AGENTS.md
  - docs/puwaer-reap132-mask-README.md
tags:
  - storage
  - model-path
  - provenance
last_checked: 2026-08-11
updated: 2026-08-11T07:17:23Z
---

# Model placement and disk strategy

# Model placement and disk strategy

The former Q2_K and IQ3_XXS local copies were deleted after their observed SHA256 values disagreed with Hugging Face artifact metadata. They are historical diagnostics, not verification sources.

The selected REAP base is HERETIC v2 at immutable revision `e7efd043c5e072da4d40f0f98ade554c5713bad9` from `squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8`. Download its Transformers snapshot to `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8/`. Generated GGUF/runtime candidates belong under `/data/linux-fast/models/DeepSeek-V4-Flash-0731/`. Do not store model binaries in the git project tree.

Use the logged-in `hf` CLI with the immutable commit SHA and `--local-dir`. Verify the downloaded file list and hashes before compression. Create `.checkpoint-source.json` only through `scripts/write_checkpoint_source_manifest.py`, which checks local config/index bytes against the same remote commit.

The Toshiba NTFS mount is not an accepted fallback verification source. If NVMe space is insufficient, stop and resolve placement rather than silently serving or compressing an unverified copy.
