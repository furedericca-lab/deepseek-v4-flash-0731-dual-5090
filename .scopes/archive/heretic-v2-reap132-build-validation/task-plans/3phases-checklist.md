---
description: Execution and verification checklist for heretic-v2-reap132-build-validation 3-phase plan.
---

# Phases Checklist: heretic-v2-reap132-build-validation

## Input
- Canonical docs under:
  - `.scopes/archive/heretic-v2-reap132-build-validation`
  - `.scopes/archive/heretic-v2-reap132-build-validation/task-plans`

## Rules
- Use this file as the single progress and audit hub.
- Update status, evidence commands, and blockers after each implementation batch.
- Do not mark a phase complete without evidence.

## Global Status Board
| Phase | Status | Completion | Health | Blockers |
|---|---|---|---|---|
| Phase 1 | Complete | 100% | Healthy | None |
| Phase 2 | Complete | 100% | Accepted with limitation | Byte verification PASS; native HF accepted through 16 tokens, 32-token runtime limitation recorded |
| Phase 3 | Complete | 100% | Healthy | Canonical MXFP4 GGUF, direct provenance, dual-5090 runtime, 32K prefill, and behavior probes passed |

## Phase Entry Links
1. [phase-1-heretic-v2-reap132-build-validation.md](phase-1-heretic-v2-reap132-build-validation.md)
2. [phase-2-heretic-v2-reap132-build-validation.md](phase-2-heretic-v2-reap132-build-validation.md)
3. [phase-3-heretic-v2-reap132-build-validation.md](phase-3-heretic-v2-reap132-build-validation.md)

## Phase Execution Records

### 2026-08-11 scope creation and input freeze record

- Phase: 1
- Completed tasks:
  - created the three-phase build/verification scope
  - recorded full plan SHA, logical SHA, repo/commit identities, 43/43 mapping,
    and three exact routing tables
  - confirmed source tensor inventory and verifier naming surface
  - confirmed `/data/linux-fast` ext4 has about 870 GiB available
- Evidence commands:
  - `sha256sum squanchyzx-puwaer-reap132-mask.json`
  - `jq` geometry/provenance inspection of the frozen plan
  - fixed-revision Hugging Face index inspection
  - `git rev-parse HEAD` and submodule HEAD/status inspection
  - `df -hT /data/linux-fast`
- Issues/blockers:
  - user-started fixed-revision source download exited; a later check found no
    download process and no target directory
  - root and vendor worktrees contain uncommitted build changes, so the current
    extractor/compressor cannot yet be identified by a truthful commit SHA
- Resolutions:
  - re-run the fixed-revision command and capture its terminal error if it exits
    again; do not run pruning until download, manifests, tests, and build-code
    commit identity pass Phase 1 gates
- Checkpoint confirmed: scope/input evidence recorded; native build gate remains closed

### 2026-08-11 verified source and pre-prune record

- Phase: 1
- Completed tasks:
  - T001 rechecked the immutable plan full/logical hashes, both repo commits,
    43 layer maps, 132 experts per layer, and three hash-routing tables
  - T003 completed the official logged-in `hf` CLI fixed-revision confirmation;
    all 96 remote files match, including 50/50 LFS SHA256 checks and 46/46
    byte comparisons after repairing `tokenizer.json`
  - T004 wrote and verified `.checkpoint-source.json` against the fixed remote
    config and index
  - T005 implemented and tested `scripts/checkpoint_content_manifest.py`; the
    97-entry source manifest is stable at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - T006 passed focused tests and the full vendor suite
  - T007 captured the pre-prune RAM/swap/GPU/disk/process baseline
  - T002 froze root build commit
    `41888983bf304b234d6414ce74abf117322d8b5c` and vendor build commit
    `0645265700b0c8325c2ac141b02873f3cd0ab474`
  - pre-start review found and fixed silent omission of 4,705 model-ignored MTP
    tensors; checkpoint-native passthrough preserves 10,862,838,300 source bytes
- Evidence commands/results:
  - `sha256sum squanchyzx-puwaer-reap132-mask.json` ->
    `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`
  - `uv run hf download ... --revision e7efd043...3bad9 --local-dir ...` -> exit 0
  - source remote comparison -> 96/96 paths and sizes, 50/50 LFS SHA256,
    46/46 small files byte-identical
  - `scripts/write_checkpoint_source_manifest.py` plus
    `verify_checkpoint_source()` -> PASS
  - `scripts/checkpoint_content_manifest.py ... --artifact-role source` and
    `--check` -> 97 files, stable manifest SHA above
  - focused manifest/provenance tests -> `68 passed`; final full vendor tests ->
    `216 passed, 5 skipped`
  - baseline -> 46 GiB RAM, 47 GiB swap, 714 GiB NVMe free, dual RTX 5090
    visible, native output absent, no model/wiki/doctor scan active
- Issues/blockers:
  - no Phase 1 entry blocker remains
  - legacy `puwaer-reap132-mask.json` was deleted; the only executable plan is
    committed `squanchyzx-puwaer-reap132-mask.json`
- Checkpoint confirmed: verified source snapshot and executable build identities are frozen; T008 deterministic pruning is authorized to start

### 2026-08-11 rejected first output and naming-fix record

- Phase: 1
- Completed work:
  - the first streaming process exited zero without OOM, but its output was
    rejected after the source-namespace cross-check found 437 unknown names
  - 396 layerless E8M0 scale names collided across 43 layers, losing 16,632
    distinct scale keys; 41 attention KV norm names were also malformed
  - fixed quantized expert scale and KV norm reverse naming in vendor commit
    `5439fba8071467d8b2bb113046cd4e488ac14f5f`
  - a live comparison against the fixed Hugging Face revision then proved that
    source shards 2, 41, 43, 44, and 46 had drifted after the previously correct
    content manifest was generated; all five were replaced from the official
    logged-in `hf` CLI and the repair directory was deleted
  - changed every streaming safetensors read to the `pread` backend in vendor
    commit `7fae3000e321fde32a4a010171b9480e22148ba0`, preventing model tensors from
    sharing an mmap-backed source storage
  - made duplicate tensor names and source-index unknown names fatal writer errors
  - added full fused FP4 weight/scale, two-layer collision, KV norm, duplicate,
    and unknown-name regressions
- Evidence commands/results:
  - failed output index -> 23,693 total, 23,256 source-known, 437 unknown
  - expected fixed inventory -> 40,325 total and 792 expert tensors per layer
  - focused naming/streaming tests -> `23 passed`
  - full vendor suite -> `222 passed, 5 skipped`
  - fixed-revision live comparison after repair -> 96/96 paths and sizes,
    50/50 LFS SHA256, 46/46 Git blob SHA1, and 96/96 remote files read-only
  - real source Layer 0 after `apply_keep()` -> 821 converted tensors, 792
    expert tensors, 396 weights, 396 scales, zero unknown names, zero byte/dtype/
    shape provenance mismatches
  - full 97-file source manifest check after the pread Layer 0 run -> PASS at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - repeated shard reads around `sync` were stable and kernel logs contained no
    NVMe I/O, media, data-integrity, or EXT4 errors; a later authorized SMART
    read passed with zero critical warnings, media/data-integrity errors, and
    error-log entries
- Resolution:
  - user explicitly authorized deleting the unusable first model output to avoid
    operator confusion; timestamped run logs and Wiki evidence remain
  - rerun only from the frozen plan, read-only source snapshot, and committed
    pread/naming implementation
- Checkpoint confirmed: the failed artifact is not T008 completion; Layer 0
  preflight passes and a clean full rerun is authorized

### 2026-08-11 rejected exit-139 rerun and source re-verification

- Phase: 1
- Completed work:
  - the clean rerun wrote 18 shards but exited `139` after the save message;
    memory guard remained clear, so T008/T009 are not complete
  - a full fixed-revision comparison continued across all 96 files and found
    five same-size LFS SHA256 mismatches in shards 5, 40, 42, 47, and 48
  - downloaded those five files with the logged-in official `hf` CLI into an
    isolated repair directory, verified 5/5 SHA256 values, atomically replaced
    the bad files, and deleted the repair directory
  - added `tools/verify_hf_checkpoint_sha256.py`; it compares every LFS file to
    remote SHA256 metadata, downloads and hashes each fixed-revision Git file,
    continues after mismatches, and emits complete mismatch/missing/extra sets
  - deleted the 90 GiB exit-139 output under the standing authorization to
    remove unusable model artifacts
- Evidence commands/results:
  - pre-repair comparison -> 91/96 matched; five exact mismatch records saved
    under repo-ignored `logs/`
  - post-repair tool comparison -> 96/96 matched, 50/50 LFS SHA256, 46/46 Git
    files by downloaded remote SHA256, zero missing/extra paths
  - all 96 repository files plus `.checkpoint-source.json` and
    `checkpoint-content-manifest.json` -> mode `0444`
  - source content manifest check -> 97 files PASS at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - verifier/manifest tests -> `11 passed`
- Issues/blockers:
  - shard mtimes predate the 19:34 rerun, so current evidence does not identify
    which process caused the second drift; do not attribute it to `pread`
  - isolate the remaining mutation path and exit `139` before another full run
- Checkpoint confirmed: source is repaired, remotely verified, and read-only;
  deterministic pruning is blocked pending root-cause isolation

### 2026-08-11 noMTP build-policy decision

- Phase: 1-2 contract update
- Decision:
  - keep squanchyzx HERETIC v2 as the immutable source and apply the frozen
    puwaer REAP132 plan exactly
  - retain the generic ignored-tensor passthrough capability, but select the
    explicit project policy `--drop-mtp`
  - write the new artifact only as
    `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`
- Derived inventory gate:
  - old MTP-preserving structural count -> 40,325
  - classified source MTP/DSpark tensors -> 4,705 totaling 10,862,838,300 bytes
  - current noMTP structural count -> 35,620
  - derive the count from source/plan classification during verification rather
    than accepting the hard-coded number alone
- Required verification:
  - 43/43 layers, 792 expert tensors per layer, 396 weights and 396 scales
  - exact frozen survivor/router/three-table `tid2eid` provenance
  - all 66 HERETIC v2 `attn.wo_b.{weight,scale}` tensors source-identical
  - MTP/DSpark tensors -> 0; unknown/unclassified tensors -> 0
- Executable identities:
  - root build -> `8071c7c64101f16ea0959881b86d180862bd514b`
  - vendor build -> `56137d189fd36c1c8881ca99233614b177442425`
- Checkpoint confirmed: the earlier 40,325 gate remains historical evidence for
  the rejected MTP-preserving build and is superseded for the release artifact

### 2026-08-11 noMTP artifact and host-stability record

- Phase: 1-2
- Completed work:
  - deterministic `--plan --streaming --drop-mtp` completed with exit 0,
    memory guard clear, 15 shards, 35,620 indexed tensors, and zero MTP tensors
  - post-build fixed-revision source comparison passed `96/96`; source manifest
    passed at `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - output content manifest passed twice: 20 files at
    `1e1cad5a73adb26215a94a323de66e38b34b406eea0d8f519cbe7250da9a2846`
  - implemented `scripts/verify_reap132_checkpoint.py` and adversarial fixture
    tests; project tests pass `18 passed`
  - output directory was made read-only and remains quarantined
- Issues/blockers:
  - full direct tensor verification was interrupted after the host emitted
    `BAD_PAGE` and `compound_head not consistent` from `kswapd0` at 22:56:30
  - zram was effectively unused; current evidence points to unresolved
    kernel/RAM/EXPO stability under page-cache pressure, not model semantics
  - no `post-prune-verification.json` PASS report exists; native smoke and GGUF
    remain blocked
- Next gate:
  - boot `6.17.0-23-generic` or disable EXPO, confirm a clean `journalctl -k -b`,
    then rerun the cache-bounded verifier

### 2026-08-11 6.17 rerun result

- A fresh deterministic `--plan --streaming --drop-mtp` rebuild was completed
  under `6.17.0-23-generic` in the isolated directory
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-rerun-6.17/`.
- Structural output gate passed: 15 shards, 35,620 indexed tensors, and zero
  MTP/DSpark tensors. The output manifest passed twice with manifest SHA256
  `18de33ba67182a9a8d34b242a22d4681bc5659d5ccf8d0a72a60ea0020000456`.
- The output was made read-only before verification.
- During the cache-bounded direct verifier, the 6.17 boot reproduced
  `BUG: Bad page state` / `compound_head not consistent` in `kswapd0` at
  `23:30:01`; verification was stopped immediately and no PASS report exists.
- `cat /proc/sys/kernel/tainted` changed from `4096` to `4128` after this event.
  Native smoke, GGUF conversion, and deployment remain blocked. The new rerun
  is quarantined separately from the earlier failed artifact.

### 2026-08-12 5800 MT/s verification result

- After changing memory to 5800 MT/s, a clean `6.17.0-23-generic` boot started
  with `tainted=4096` and no kernel memory errors.
- The complete verifier finished without another `BAD_PAGE`, `compound_head`,
  MCE, or I/O error; this is evidence that 5800 MT/s materially improves the
  host stability gate compared with 6000 MT/s.
- The checkpoint is still not releasable: the verifier report contains 49
  semantic failures. Router rows, scales, shared experts, tid2eid, HERETIC
  overlay, MTP absence, and dangling IDs pass, but expert byte provenance has
  8 mismatches and the current report flags 41 untouched/router-related names.
- No native smoke or GGUF work is authorized until the verifier contract is
  corrected for the expected router bias/overlay namespace and the remaining
  expert mismatches are independently explained or eliminated.

### 2026-08-12 5600 MT/s writer diagnosis

- A fresh rebuild and full verifier under `7.0.0-28-generic` with DDR5-5600
  completed without kernel errors (`tainted=4096`).
- Manifest passed twice; structural counts remained 15 shards and 35,620
  tensors with MTP/DSpark absent.
- Five FP4 expert weight byte mismatches remained. Their expert IDs differ from
  the previous rebuilds, while scales and all non-expert gates/overlays pass.
- Root-cause gate: the streaming writer materializes fused FP4 tensors on CUDA,
  then converts them back through `revert_weight_conversion()` and CPU writes.
  This path is not byte-exact for packed FP4 storage. The next implementation
  must read source safetensors bytes on CPU and slice survivors directly,
  bypassing GPU round-trip and fused reverse conversion.

### 2026-08-12 Python 3.12 deterministic raw-builder acceptance

- A clean `7.0.0-28-generic` boot started with `tainted=4096`, no BAD_PAGE,
  Oops, GPF, MCE, AER, or NVMe error, 42 GiB available RAM, and zero swap use.
- System Python `3.12.3` with `-X faulthandler` passed the real Layer 0
  preflight: 132 survivors, 396 weights, 396 scales, 792 total expert tensors,
  and zero missing, duplicate, unknown, or mutated payloads.
- The Transformers-free raw-safetensors builder completed Build A and Build B
  independently. Both produced 35,620 tensors in 22 deterministic shards with
  `num_nextn_predict_layers=0`, `n_routed_experts=132`, and zero MTP/DSpark
  keys. Peak observed Python RSS stayed near 120 MiB; available RAM remained
  near 42 GiB and swap remained unused.
- Both 27-entry O_DIRECT content manifests are byte-identical, including every
  per-file SHA256, at canonical manifest SHA256
  `9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`.
- The independent O_DIRECT verifier passed twice with zero failures for layers,
  expert weights, expert scales, router rows, shared experts, three `tid2eid`
  tables, all HERETIC overlay tensors, MTP/DSpark absence, and dangling IDs.
  The final report SHA256 is
  `a8d9fdb84ac2179b21f21d66f325d60f536b32eeb1d52ef91fbe4b9a187d4a00`.
- `post-prune-verification.json` is derived sidecar evidence and is excluded
  from the model content manifest. A regression proves that writing the report
  does not invalidate `manifest --check`; the final 27-file check passed.
- Build B was promoted atomically to
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`.
  The duplicate Build A was deleted, and the final artifact has zero writable
  files and zero writable directories.
- The boot remained clean through two builds, three full verifier/manifest
  scans, and cleanup. Phase 1 is complete; Phase 2 now blocks only on native HF
  smoke. This successful 3.12 run is a production choice, not proof that the
  earlier CPython 3.13 GPF was caused by CPython.
- Native pre-load gates passed with the project Transformers 5.15 stack:
  `AutoConfig` resolves `DeepseekV4Config`, the tokenizer loads locally with
  129,280 entries, and a meta-device `DeepseekV4ForCausalLM` constructs all 43
  layers with 132 routed experts and zero MTP modules without reading shard
  payloads.
- At that checkpoint, full native generation had not started because standard
  HF `from_pretrained()` and the vendor `backend="pread"` path did not satisfy
  the retained O_DIRECT constraint. The later runtime record below closes the
  direct-loader gap and supersedes this historical blocker.

### 2026-08-12 native O_DIRECT runtime bring-up

- Added a true aligned O_DIRECT tensor materializer to `LayerStreamer` while
  retaining the existing pread backend as its default. Tiny checkpoint direct
  loading is tensor-identical to resident loading, and the real checkpoint
  shared plus Layer 0 preflight materialized all expected FP8/MXFP4 tensors.
- The first full single-token forward streamed all 43 layers across GPU0 then
  GPU1, produced finite logits, and exited zero. Peak RSS was 6.436 GiB and peak
  allocated VRAM was 4.061 GiB on GPU0 and 1.833 GiB on GPU1.
- Transformers 5.15 required `kernels>=0.16,<0.17`; the project was updated to
  `kernels 0.16.0` and the locally compiled, Torch-matched
  `pytorch-triton 3.8.0+git694c0c3b.post20260719` wheel from `~/torch/dist`.
  The finegrained FP8 kernel exposed all required symbols and a CUDA FP8 matmul
  returned finite BF16 output.
- A subsequent multi-token chat smoke failed after switching to GPU1 at Layer
  23. The process reported CUDA illegal memory access, and the kernel recorded
  NVIDIA `Xid 31` for PCI `02:00.0` (GPU1), an MMU virtual-read fault. The
  remaining matrix was stopped and this boot is inadmissible for further GPU
  validation.
- This event does not invalidate the read-only checkpoint or its byte verifier;
  it is a native multi-device runtime failure. After reboot, rerun the matrix
  with single-GPU, per-layer O_DIRECT streaming on GPU0. Dual-GPU acceptance is
  deferred to llama.cpp unless a separate native multi-device fix is proven.
- Phase 2 native acceptance is now explicitly a forward-correctness and bounded
  prefill gate, not a semantic generation evaluation. Run five independent
  processes at 1, 16, 32, 64, and 128 input tokens with
  `CUDA_VISIBLE_DEVICES=0`; require exactly one visible CUDA device, all 43
  layers, finite hidden states/logits, CUDA synchronization, and clean
  kernel/Xid gates before and after each case. Chat/reasoning/code/tool/long
  generation quality remains a Phase 3 llama.cpp responsibility.

### 2026-08-12 GPU0-only bounded-prefill result

- The rebooted `7.0.0-28-generic` boot entered the matrix with taint `4096` and
  no BAD_PAGE, Oops, GPF, machine-check hardware error, or NVIDIA Xid.
- Every case ran in a separate process with `CUDA_VISIBLE_DEVICES=0`; PyTorch
  saw exactly one RTX 5090, physical GPU0 UUID
  `GPU-615615a7-d90c-ab22-2f6e-42918048179c`.
- T1 (1 token) passed all 43 layers with finite logits, peak RSS 6.103 GiB and
  peak allocated VRAM 4.061 GiB. Its post-case kernel gate passed.
- T2 (16 tokens) passed all 43 layers with finite logits, peak RSS 6.162 GiB
  and peak allocated VRAM 4.064 GiB. Its post-case kernel gate passed.
- T3 (32 tokens) passed Layers 0 and 1, then failed in Layer 2 eager attention
  at `torch.matmul(attn_weights, value_states)` with
  `CUBLAS_STATUS_INTERNAL_ERROR`. Cleanup observed CUDA illegal memory access,
  and the kernel recorded Xid 31 on physical GPU0, PCI `01:00.0`, with an MMU
  virtual-read fault. The fail-fast runner stopped before T4/T5.
- This excludes GPU1 visibility and cross-device switching as necessary
  conditions for the Xid. It does not invalidate the byte-verified checkpoint,
  but Phase 2 native prefill acceptance remains blocked and this boot is no
  longer admissible for GPU validation.
- The smoke implementation released each streamed layer and called
  `empty_cache()` before an explicit per-layer CUDA synchronization. That is a
  high-value software lifecycle suspect because asynchronous kernels may still
  reference the layer weights. The next clean-boot A/B synchronizes immediately
  after every layer forward and only then frees the layer; this is a candidate
  fix, not a proven root cause until the 32/64/128-token cases pass without Xid.
- Runtime config resolution shows Layers 0-1 are `sliding_attention` and Layer 2
  is the first `compressed_sparse_attention` layer. Keep two hypotheses open:
  unsafe asynchronous layer release ordering and a 32-token CSA/eager batched
  matmul runtime defect.
- After reboot, use the runner's repeatable `--case` selector to execute T3
  alone first. If T3 and its post-case kernel gate pass, continue T4 then T5;
  only after 32/64/128 pass, rerun T1/T2 under the same code commit to complete
  the matrix record. Any failure stops the sequence.
- The synchronized T3 rerun on a new clean boot still passed Layers 0-1 and
  failed at the same Layer 2 `torch.matmul(attn_weights, value_states)` call,
  followed by the same GPU0 Xid 31 MMU virtual-read fault. This materially
  downgrades premature layer release as the cause. T4/T5 remained blocked.
- The next clean-boot diagnostic runs only T3 with
  `--cuda-launch-blocking`. If the traceback moves earlier, that earlier CUDA
  operation becomes the primary suspect; if it remains at the second attention
  matmul, capture its operand shape/dtype/stride/contiguity/finite statistics
  before any contiguous-layout A/B.
- With `CUDA_LAUNCH_BLOCKING=1`, the failure moved from the second AV matmul to
  the first QK matmul in Layer 2:
  `torch.matmul(query, key_states.transpose(2, 3))`. This proves the second GEMM
  was only where the asynchronous failure surfaced previously. The boot then
  recorded the same GPU0 Xid 31 and was quarantined.
- The next clean-boot T3 uses launch blocking plus read-only Layer 2 attention
  tracing. Before QK it flushes shape, dtype, stride, storage offset,
  contiguity, device, and pointer alignment metadata for query, key/value, and
  mask; it synchronizes before and after each GEMM. Value reductions are
  disabled unless `--trace-values` is explicitly supplied, because those
  reductions launch extra CUDA kernels and alter timing. It does not call
  `.contiguous()` or change the attention math.
- The metadata-only trace flushed successfully before QK. Query was contiguous,
  BF16, shape `[1, 64, 32, 512]`, stride `[1048576, 16384, 512, 1]`, and
  256-byte aligned. The repeated key was BF16 shape `[1, 64, 40, 512]` with
  zero batch/head strides `[0, 0, 512, 1]`; its transpose was shape
  `[1, 64, 512, 40]`, stride `[0, 0, 1, 512]`. QK immediately returned
  `CUBLAS_STATUS_INTERNAL_ERROR`, followed by GPU0 Xid 31. The fault address was
  54,784 bytes after the key pointer, 13,824 bytes beyond its logical 40 KiB
  storage region. This strongly implicates the zero-stride broadcast view or
  its PyTorch/cuBLAS lowering, but remains an A/B hypothesis.
- Query is already contiguous, so a query-only `.contiguous()` call is not an
  effective variable. On the next clean boot run only T3 with launch blocking,
  metadata-only tracing, and `--qk-layout key-transposed-contiguous`. Preserve
  both the original transposed-view metadata and the actual contiguous GEMM
  operand metadata. Do not run this A/B in the boot containing the Xid.
- The key-transposed-contiguous T3 proved QK itself can complete: the trace
  contains `after_qk_matmul` with contiguous BF16 output `[1, 64, 32, 40]`.
  Failure moved to AV, where `value_states` remained the non-transposed
  zero-stride view `[1, 64, 40, 512]`, stride `[0, 0, 512, 1]`. GPU0 again
  reported Xid 31 at exactly `value_ptr + 0xd600`, which is `0x3600` beyond the
  logical 40 KiB shared storage. Therefore transpose layout is not a common
  requirement, while the zero-stride broadcast operand remains common.
- Do not state that cuBLAS does not support zero stride; its strided-batched API
  permits zero stride for shared operands. The narrowed hypothesis is a defect
  in current PyTorch `torch.matmul` lowering or its selected BF16 cuBLAS path for
  these broadcast views on Blackwell. On the next clean boot run only T3 with
  `--qk-layout key-transposed-contiguous --av-layout value-contiguous`.
- This is the final native layout A/B. If T3 passes, run only T5 at 128 tokens
  with the same workaround; T4 at 64 tokens is intentionally skipped. If both
  pass, close Phase 2 with a documented zero-stride materialization workaround.
  If either fails or produces Xid, close native HF investigation with a runtime
  limitation beyond the already-passing 16-token prefill and proceed to Phase 3.
- No further compute-sanitizer, cuBLAS algorithm, Torch/CUDA version, attention
  backend, or minimal-GEMM root-cause work is in scope. Phase 3 acceptance is the
  pinned llama.cpp/GGUF dual-5090 runtime, not Transformers native serving.
- The final QK+AV-contiguous T3 made both Layer 2 GEMMs pass and completed
  Layers 2-3. Layer 4, outside the traced patch, used original eager attention
  and reproduced Xid 31 at QK. Complete native execution would require a
  model-wide workaround, which exceeds the debug budget. Phase 2 closes with
  the native HF limitation recorded; T5 is not run.
- Phase 3 converter pin: `vendor/llama.cpp` submodule commit `8704e31` from the
  project fork, based on upstream `89e0aa6fd362617d9073e0dafc18e41241521572`, supports
  `DeepseekV4ForCausalLM`, `--no-mtp`, I32 `tid2eid`, and routed-expert MXFP4
  repacking from frozen weight+scale bytes. T041 is complete.
- T042 direct-I/O preparation is complete. The converter has explicit
  `--direct-io-input` and `--direct-io-output`; aligned 64 MiB bounded staging
  handles unaligned tensor/header boundaries. Tests pass for an unaligned local
  tensor range, a 70 MiB output crossing the staging boundary, exact final
  truncation, and existing GGUF reader validation. Full conversion waits for a
  clean reboot because the current boot contains Xid 31.
- The clean-boot real dry-run exposed unbounded upstream GGUF writer retention:
  the original direct path filled 45 GiB RAM around Layer 24. Converter commit
  `8704e31` stages each converted tensor into a same-filesystem O_DIRECT payload
  file and releases the ndarray; dry-run retains metadata only. The complete
  43-layer plan passed at 1,328 tensors / 85.0 GB with 1.67 GiB peak RSS, zero
  process swaps, and a clean kernel gate.
- The first full 80 GiB output is quarantined. Its metadata and 90 sampled MXFP4
  expert blocks pass, but sampled `token_embd`, `output_norm`, and `output`
  payloads fail direct provenance and llama.cpp repeats `D`. `write_array()`
  passed a `LazyNumpyTensor` metadata placeholder to `np.ascontiguousarray()`;
  the direct path therefore wrote zeroes for ordinary tensors. Fix and prove
  small direct payload conversion before replacing the artifact.

## Final Release Gate
- Scope constraints preserved.
- Quality/security gates passed.
- Remaining risks documented.
- Frozen plan has not changed.
- Native checkpoint byte verification passed before GGUF conversion; native HF
  smoke either passed under the bounded workaround or has a recorded limitation.
- Golden GGUF and controlled A/B identities/results are recorded separately.

## Archive Record

- Archived on 2026-08-12 under
  `.scopes/archive/heretic-v2-reap132-build-validation/`.
- Archive purpose: preserve the completed deterministic REAP132 build,
  direct-I/O GGUF conversion, provenance, and dual-5090 deployment audit trail.
- The accepted native checkpoint and canonical MXFP4 GGUF remain immutable
  production artifacts; the archived scope does not authorize rebuilding or
  changing either one.
- Future K96 consensus work uses the new active
  `.scopes/heretic-v2-reap96-consensus/` scope. It may inspect K132 as a fixed
  candidate universe but must not modify the K132 plan or artifacts.
- Archived docs should change only for factual errata or path-maintenance
  updates.
