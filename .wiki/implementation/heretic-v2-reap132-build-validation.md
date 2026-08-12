---
title: HERETIC v2 REAP132 build and validation
type: implementation
status: current
scope: heretic-v2-reap132-build-validation
related_scopes:
  - deepseek-v4-flash-0731-dual-5090
related_files:
  - .scopes/heretic-v2-reap132-build-validation
  - squanchyzx-puwaer-reap132-mask.json
  - scripts/checkpoint_content_manifest.py
  - scripts/derive_reap132_inventory.py
  - scripts/write_checkpoint_source_manifest.py
  - scripts/verify_reap132_checkpoint.py
  - tests/test_checkpoint_content_manifest.py
  - tests/test_verify_reap132_checkpoint.py
  - tools/verify_hf_checkpoint_sha256.py
  - tests/test_verify_hf_checkpoint_sha256.py
  - .wiki/debugging/heretic-v2-streaming-writer-namespace-corruption.md
  - scripts/extract_puwaer_reap132_mask.py
  - vendor/moe-expert-compress
  - README.md
  - AGENTS.md
source_docs:
  - .scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-technical-documentation.md
tags:
  - reap132
  - heretic-v2
  - checkpoint-verification
  - gguf
last_checked: 2026-08-12
updated: 2026-08-12T12:40:00+08:00
---

# HERETIC v2 REAP132 build and validation

The current execution scope is `.scopes/heretic-v2-reap132-build-validation/`. It turns the frozen mapped plan into a native checkpoint, proves the output byte-by-byte, runs native HF smoke, then creates and validates one MXFP4-preserving golden GGUF before any IQ3/Q2 work.

The immutable build input is `squanchyzx-puwaer-reap132-mask.json`. Its full file SHA256 is `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`; its logical SHA256 is `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`. The base is squanchyzx HERETIC v2 commit `e7efd043c5e072da4d40f0f98ade554c5713bad9`; the mapped target is puwaer REAP-150B commit `868fa38e2f2964699ad065dc8d9382c136cc60b8`. The extractor proved 43/43 exact router mappings and three exact `[129280, 6]` `tid2eid` tables. The plan must not be regenerated or edited.

Phase 1 freezes the build-code commit, verifies the user-started fixed-revision download, creates source provenance/content manifests, captures clean host baselines, and runs deterministic `--plan --streaming` pruning without calibration or saliency. The native output remains quarantined after writing.

Phase 2 implements direct-safetensors verification. For every layer, output expert `new_id` must equal source expert `kept_experts[new_id]` for `w1/w2/w3.weight` and `.scale`; router rows and three `tid2eid` tables must match; shared experts and layers 10-42 HERETIC `attn.wo_b` must remain source-identical; all MTP/DSpark tensors must be absent. The required report is `post-prune-verification.json`, followed by chat, reasoning, coding, tool-call, and longer-context native smoke.

The verifier implementation is `scripts/verify_reap132_checkpoint.py`. It parses
safetensors headers directly, honors index-selected overlay shards, compares
tensor payloads in bounded chunks, and emits the contracted report without full
model loading. Its fixture suite covers expert/scale mutation, router reorder,
tid2eid dangling IDs, retained MTP, and all 43 layer classifications.

Phase 3 pins the llama.cpp converter, produces one MXFP4-preserving golden GGUF, validates it on both RTX 5090s through localhost llama-server, and runs a controlled puwaer-versus-HERETIC A/B with identical survivor set, prompts, flags, and scoring. Further IQ3/Q2 quantization is deferred.

The source snapshot is verified at `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8/`. The logged-in official `hf` CLI fixed-revision command exits zero; all 96 remote files match through 50 LFS SHA256 checks and 46 byte comparisons. `.checkpoint-source.json` passes, and the 97-entry source content manifest is stable at `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`. The pre-prune baseline records 46 GiB RAM, 47 GiB swap, 714 GiB free NVMe space, two visible RTX 5090s, and no competing model/wiki scan. Pre-start review also proved that 4,705 model-ignored MTP tensors total 10,862,838,300 bytes and added checkpoint-native streaming passthrough so they are not dropped. Executable identities for that run were root build commit `41888983bf304b234d6414ce74abf117322d8b5c` and vendor build commit `0645265700b0c8325c2ac141b02873f3cd0ab474`.

The first deterministic pruning process completed without OOM, but its output was rejected and deleted under explicit user authorization. The output index had 23,693 tensors and 437 names absent from the source namespace. Of those, 396 were layerless expert scale payloads such as `.experts.0.w1.weight`; they collided across all 43 layers and caused 16,632 distinct scale keys to be lost. The other 41 were malformed attention KV norm names such as `layers.42.attn.norm.weight`. A successful content manifest does not override this semantic failure.

Repair also found five source shards changed after the previously correct source manifest was created. They were replaced from the fixed Hugging Face revision, all 96 remote files passed, and all source artifacts were made read-only. Streaming now uses pread in vendor commit `7fae3000e321fde32a4a010171b9480e22148ba0`; a real quantized Layer 0 preflight and a subsequent full source manifest check passed.

A later deterministic full run wrote 18 shards but exited `139`, so its 90 GiB output was rejected and deleted. A fresh fixed-revision comparison found five additional same-size shard SHA256 mismatches. Their mtimes predate that run, so the writer responsible is not yet proven. The five shards were independently redownloaded and verified before replacement. `tools/verify_hf_checkpoint_sha256.py` then proved 96/96 paths and SHA256 values against the immutable remote revision, and the 97-file content manifest again passed at `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`; all 96 repository files and both local control manifests are `0444`. SMART reports no critical warnings, media errors, data-integrity errors, or error-log entries. See [HERETIC v2 streaming writer namespace corruption](../debugging/heretic-v2-streaming-writer-namespace-corruption.md) for the complete evidence and prevention gates. The next gate is to isolate the remaining source-mutation/exit-139 path before another full pruning run.

The release artifact policy is now `HERETIC-v2-REAP132-noMTP`. The generic writer
still supports ignored-tensor passthrough, but this build uses `--drop-mtp` and
does not read or write the 4,705 MTP/DSpark tensors (10,862,838,300 source bytes).
`scripts/derive_reap132_inventory.py` dynamically derives 35,620 output tensors:
72,317 source tensors minus 31,992 removed routed-expert tensors minus 4,705 MTP
tensors. Structural deletion stops here. Shared experts, router, all three
`tid2eid` tables, Lightning Indexer, CSA/HCA, mHC, attention, embedding, LM head,
norm, RoPE, sink tensors, and the 66 HERETIC v2 attention tensors remain.

The production implementation is now a Transformers-free, plan-driven
safetensors builder. Routed expert weights and scales are raw payload remaps;
routers gather the frozen survivor rows; `tid2eid` comes from the frozen plan;
untouched backbone tensors are raw copies; MTP tensors are dropped. Source
reads, output writes, manifest hashing, and provenance verification all use
aligned O_DIRECT.

On 2026-08-12, one complete A build passed the full independent verifier with
35,620 tensors, 22 shards, 43 layers x 792 expert tensors, and zero failures. A
second build was byte-reproducible across all 27 manifest entries at manifest
SHA256 `e3c2d719f4d5a240d5ecd6f707d546b1c14b972d6a01551e489d5091eecbd178`.
Review then found that the noMTP output still copied
`num_nextn_predict_layers: 1` from the source. The builder and verifier now
require `0`; tests pass 23/23.

The first config-correct full rebuild ended in an unexplained CPython 3.13
general-protection fault, exit 139, without a Python traceback or preceding
BAD_PAGE. Its partial output was deleted. Bounded RAM, tuple, O_DIRECT, AER,
SMART, NVMe, and machine-check diagnostics found no persistent error. There is
currently no final native artifact directory. The next delivery gate is a clean
reboot followed by a Python 3.12 `-X faulthandler` Build A, O_DIRECT manifest and
verifier PASS, same-code Build B, per-file SHA equality, read-only promotion,
and only then native HF smoke.
