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
updated: 2026-08-12T13:45:00+08:00
---

# HERETIC v2 REAP132 build and validation

The current execution scope is `.scopes/heretic-v2-reap132-build-validation/`. It turns the frozen mapped plan into a native checkpoint, proves the output byte-by-byte, runs native HF smoke, then creates and validates one MXFP4-preserving golden GGUF before any IQ3/Q2 work.

The immutable build input is `squanchyzx-puwaer-reap132-mask.json`. Its full file SHA256 is `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`; its logical SHA256 is `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`. The base is squanchyzx HERETIC v2 commit `e7efd043c5e072da4d40f0f98ade554c5713bad9`; the mapped target is puwaer REAP-150B commit `868fa38e2f2964699ad065dc8d9382c136cc60b8`. The extractor proved 43/43 exact router mappings and three exact `[129280, 6]` `tid2eid` tables. The plan must not be regenerated or edited.

Phase 1 freezes the build-code commit, verifies the user-started fixed-revision download, creates source provenance/content manifests, captures clean host baselines, and runs deterministic `--plan --streaming` pruning without calibration or saliency. The native output remains quarantined after writing.

Phase 2 implements direct-safetensors verification. For every layer, output expert `new_id` must equal source expert `kept_experts[new_id]` for `w1/w2/w3.weight` and `.scale`; router rows and three `tid2eid` tables must match; shared experts and layers 10-42 HERETIC `attn.wo_b` must remain source-identical; all MTP/DSpark tensors must be absent. The required report is `post-prune-verification.json`. Native GPU0-only prefill is bounded diagnostic evidence: 1/16 tokens already pass, one final 32-token layout A/B is allowed, and a PASS receives one 128-token confirmation. This is not semantic generation scoring and a documented native runtime limitation does not invalidate the checkpoint.

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
BAD_PAGE. Its partial output was deleted. The clean-boot Python 3.12 A/B then
completed successfully with `-X faulthandler`: both builds produced 35,620
tensors in 22 shards, zero MTP/DSpark keys, and byte-identical 27-entry
manifests. The canonical output manifest SHA256 is
`9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`.
The independent O_DIRECT verifier passed twice with zero failures; final report
SHA256 is `a8d9fdb84ac2179b21f21d66f325d60f536b32eeb1d52ef91fbe4b9a187d4a00`.
The accepted artifact is read-only at
`/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`, and
the duplicate A build has been deleted. Python 3.12 is the production builder
baseline, but one successful A/B does not prove CPython 3.13 caused the earlier
GPF. Local tokenizer/config loading and meta-device model construction pass with
Transformers 5.15: 43 layers, 132 routed experts, 129,280 tokenizer entries, and
zero MTP modules. Full native weight loading has not started because standard HF
loading is mmap/buffered, while the existing vendor `pread` backend is not
`O_DIRECT`; either path would violate the production bulk-read constraint. The
remaining Phase 2 work is the bounded native prefill matrix before GGUF.

The aligned direct-I/O native loader is now implemented and proven against a
tiny resident checkpoint plus the real shared/Layer 0 FP8 payloads. A full
single-token 43-layer forward passed with finite logits and bounded memory. The
runtime dependency is pinned to `kernels 0.16.0` and the locally compiled
Torch-matched `pytorch-triton 3.8.0+git694c0c3b.post20260719` wheel. However, a
multi-token run that switched from GPU0 to GPU1 triggered NVIDIA `Xid 31` on PCI
`02:00.0` (GPU1), an MMU virtual-read fault at Layer 23. The remaining matrix was
stopped and the current boot is not admissible for more GPU evidence. After
reboot, native correctness smoke uses GPU0-only per-layer streaming; dual-GPU
acceptance remains a llama.cpp Phase 3 gate unless separately fixed.

The accepted Phase 2 matrix physically hides GPU1 with
`CUDA_VISIBLE_DEVICES=0` and hard-fails unless PyTorch sees exactly one CUDA
device. Five separate processes execute 1/16/32/64/128-token prefill forwards;
each records the GPU identity, placement, input tokens, RSS and VRAM peaks, then
synchronizes CUDA. The runner checks the current boot before and after every
case and stops immediately on a nonzero exit, missing report, BAD_PAGE, Oops,
GPF, machine-check hardware error, or NVIDIA Xid. Real chat, reasoning, coding,
tool-call, and long-context generation are Phase 3 llama.cpp acceptance tests.

The first clean-boot isolated matrix passed T1 (1 token) and T2 (16 tokens)
through all 43 layers with finite logits and clean post-case kernel gates. T3
(32 tokens) failed in Layer 2 eager attention at the batched
`attn_weights x value_states` matmul with `CUBLAS_STATUS_INTERNAL_ERROR`, then
CUDA illegal memory access. The kernel recorded Xid 31 and an MMU virtual-read
fault on physical GPU0 (`01:00.0`). GPU1 was hidden and PyTorch saw exactly one
CUDA device, proving that GPU1 and cross-device switching are not necessary
conditions. The runner correctly stopped before T4/T5. This is a native CUDA
runtime blocker, not new evidence of checkpoint corruption; the boot is now
inadmissible for further GPU validation.

The harness previously freed each streamed layer and called `empty_cache()`
before an explicit per-layer CUDA synchronization. Because CUDA execution is
asynchronous, this is now the leading software-lifecycle A/B: synchronize the
target GPU immediately after each layer forward, then release its weights. The
exception path also preserves the original forward error instead of triggering
secondary cleanup errors. This remains a candidate explanation until a new
clean boot passes the 32/64/128-token cases without Xid.

Layer 2 is also the first `compressed_sparse_attention` layer after two sliding
attention layers. The next clean-boot rerun therefore distinguishes two live
hypotheses: premature asynchronous weight release versus a 32-token CSA/eager
cuBLAS defect. Current evidence does not select between them.

The matrix runner supports repeatable `--case` selection. On the next clean
boot, run only `t3-32-token-code` first. A clean PASS advances to T4/T5 and then
backfills T1/T2 for a complete same-commit record; any failure stops immediately
for targeted Layer 2 diagnosis.

The synchronized clean-boot T3 rerun still failed at the same Layer 2 second
attention matmul and produced the same GPU0 Xid 31 MMU virtual-read fault.
Layers 0-1 completed under explicit synchronization, so premature release of
their weights is no longer a leading explanation. T4/T5 were not run. The next
clean boot runs only T3 with `CUDA_LAUNCH_BLOCKING=1`; an earlier traceback will
identify the actual preceding operation, while an unchanged traceback advances
to read-only operand layout/statistics capture before a contiguous-layout A/B.

The launch-blocking T3 made the traceback move to the first Layer 2 QK matmul,
`query x key_states.transpose(2, 3)`. The second AV GEMM was therefore a delayed
observation point, not the first failing API. The kernel again recorded GPU0
Xid 31, so that boot was quarantined. The next clean boot keeps launch blocking
and enables read-only Layer 2 tracing: shape, dtype, stride, storage offset,
contiguity, device, and pointer alignment metadata are flushed before QK, with
explicit synchronization around both GEMMs. Value reductions are opt-in via
`--trace-values`, so the first diagnostic does not add finite/min/max CUDA
reduction kernels or require an attention mask containing expected `-inf` to be
fully finite. No layout or math
change is allowed before this evidence is captured.

That metadata-only trace completed and was flushed before QK. Query was a
contiguous, 256-byte-aligned BF16 tensor with shape `[1, 64, 32, 512]`. The
repeated key was BF16 shape `[1, 64, 40, 512]` with stride `[0, 0, 512, 1]`;
after transpose it was `[1, 64, 512, 40]` with stride `[0, 0, 1, 512]`. Thus all
64 heads broadcast the same key storage through zero batch/head strides. QK
then immediately returned `CUBLAS_STATUS_INTERNAL_ERROR` and GPU0 recorded Xid
31. The reported virtual-read fault was 54,784 bytes after the key pointer,
13,824 bytes beyond the logical 40 KiB key storage region. This is strong but
not conclusive evidence that the PyTorch/cuBLAS strided-batched lowering reads
past a zero-stride broadcast view.

Query is already contiguous, so query-only `.contiguous()` would be a no-op.
The next clean-boot A/B changes only the transposed key operand using
`--qk-layout key-transposed-contiguous`, while tracing both the original view
and actual GEMM operand. It keeps launch blocking and value reductions off. No
further GPU work is admissible in the boot containing this Xid.

The key-transposed-contiguous A/B made QK complete successfully and flush an
`after_qk_matmul` record. Execution then failed at AV. Its value operand was not
transposed, but still broadcast one 40 KiB storage region across 64 heads with
stride `[0, 0, 512, 1]`. The Xid 31 virtual-read address was again exactly
`0xd600` bytes after that storage pointer, or `0x3600` bytes past its logical
end. This removes transpose matrix layout as the common trigger and preserves
zero-stride broadcast lowering as the strongest current hypothesis.

This is not evidence that cuBLAS APIs generally reject zero stride; cuBLAS
strided-batched GEMM explicitly supports shared operands through zero batch
stride. The suspected defect is the current PyTorch `torch.matmul` lowering or
selected BF16 cuBLAS path for these broadcast views on Blackwell. The next
clean-boot A/B keeps the now-passing QK key contiguous and changes only AV via
`--av-layout value-contiguous`. The current Xid boot remains quarantined.

This QK+AV-contiguous T3 is the final native layout A/B. A clean PASS permits
one 128-token confirmation with the same workaround and skips the 64-token
case. If both pass, Phase 2 records a native zero-stride materialization
workaround. If either fails, Phase 2 records that the current Torch/CUDA/
Blackwell native HF path is not accepted beyond the already-passing 16-token
prefill. In both branches the deterministic checkpoint remains accepted and
Phase 3 proceeds to the pinned GGUF/llama.cpp dual-5090 runtime. Further
compute-sanitizer, GEMM algorithm, backend, Torch/CUDA version, or upstream
root-cause investigation is outside this project scope.

The final A/B materialized both Layer 2 operands. Its trace contains successful
`after_qk_matmul` and `after_av_matmul` events, and the forward completed Layers
2 and 3. Layer 4 was outside the traced patch, returned to original eager
attention, and reproduced Xid 31 at QK. Local materialization therefore avoids
the targeted operations, but a full native run would require a model-wide
runtime workaround. That exceeds the stop-loss budget. Phase 2 is complete with
a documented native HF limitation beyond the clean 16-token prefill; the
128-token case is skipped. The deterministic checkpoint remains accepted for
Phase 3 GGUF/llama.cpp conversion after a clean reboot.

Phase 3 pins the `vendor/llama.cpp` submodule from the project fork at commit
`8704e31`, based on upstream `89e0aa6fd362617d9073e0dafc18e41241521572`. The registered
`DeepseekV4ForCausalLM` converter supports `--no-mtp`, writes `tid2eid` as I32,
and deterministically repacks every routed expert's packed weight plus E8M0
scale into GGUF MXFP4 blocks, marking the result `MOSTLY_MXFP4_MOE`. This is the
intended golden conversion path rather than a floating-point requantization.

The pinned converter's default local safetensors reader uses `np.memmap`, so it
must not be used for the full checkpoint on this host. The local checkout now
adds explicit `--direct-io-input` and `--direct-io-output` modes. Input performs
aligned bounded 64 MiB reads for arbitrary tensor offsets. Output accepts the
GGUF writer's small and unaligned logical writes, stages them into aligned
64 MiB O_DIRECT blocks, and truncates the final padded block to the exact GGUF
length. Tests pass for an unaligned tensor range, a 70 MiB cross-boundary output
stream, exact content/length, and existing GGUF reader validation. Full
conversion starts only after a clean reboot because the current boot has Xid 31.

After that reboot, the first real dry-run exposed an independent converter
memory issue: upstream GGUFWriter retained every converted ndarray until the
final write and exhausted the host's 45 GiB RAM around Layer 24. Fork commit
`8704e31` makes explicit direct-I/O output stage each converted payload
immediately into a same-filesystem O_DIRECT temporary file and release the
array; dry-run retains metadata only. The complete 43-layer dry-run then passed
with 1,328 output tensors, an estimated 85.0 GB GGUF, 1.67 GiB peak RSS, zero
process swaps, and no kernel fault.
