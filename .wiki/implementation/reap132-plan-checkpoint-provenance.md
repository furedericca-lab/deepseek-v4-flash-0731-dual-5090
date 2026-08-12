---
title: REAP-132 plan and checkpoint provenance
type: implementation
status: current
scope: deepseek-v4-flash-0731-dual-5090
related_scopes: []
related_files:
  - squanchyzx-puwaer-reap132-mask.json
  - scripts/extract_puwaer_reap132_mask.py
  - scripts/write_checkpoint_source_manifest.py
  - vendor/moe-expert-compress/src/moe_compress/checkpoint_source.py
  - vendor/moe-expert-compress/src/moe_compress/cli.py
  - docs/puwaer-reap132-mask-README.md
source_docs:
  - docs/puwaer-reap132-mask-README.md
tags:
  - reap
  - provenance
  - checkpoint
  - squanchyzx-v2
last_checked: 2026-08-11
updated: 2026-08-11T07:17:07Z
---

# REAP-132 plan and checkpoint provenance

# REAP-132 plan and checkpoint provenance

The active mapped reproduction artifact is `squanchyzx-puwaer-reap132-mask.json`. It uses immutable commit `e7efd043c5e072da4d40f0f98ade554c5713bad9` from `squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8` (HERETIC v2) as the 256-expert base and commit `868fa38e2f2964699ad065dc8d9382c136cc60b8` from puwaer REAP-150B as the 132-expert target. The logical SHA256 is `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`.

All 43 router mappings were recovered byte-exact. The artifact contains 132 sorted survivor IDs per layer and three byte-exact `[129280, 6]` `int64` `tid2eid` tables. Independent validation confirmed zlib/base64 decoding, blob SHA256, byte length, shape, dtype, expert range, and distinct IDs in every row. The survivor maps and routing blobs are byte-identical to the prior puwaer plan; only base provenance and the logical hash differ.

This is a mapped puwaer survivor plan, not a fresh REAP saliency calibration on
squanchyzx v2 hidden states. It is the immutable REAP132 release baseline. The
active K96 consensus scope may only select a new per-layer subset of these 132
survivors; it does not reopen a puwaer-versus-HERETIC A/B.

Exact-plan compression accepts only a local checkpoint directory with `.checkpoint-source.json`. The manifest repo and revision must match `base_repo` and `base_revision_sha` in the plan. Before model loading, `moe-compress` recomputes SHA256 for local `config.json` and `model.safetensors.index.json`. Generate the manifest through `scripts/write_checkpoint_source_manifest.py` after downloading the fixed v2 revision with the logged-in `hf` CLI.

Validated 2026-08-11 with the full vendor suite: `214 passed, 5 skipped`.
