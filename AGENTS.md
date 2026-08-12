# AGENTS.md

## Source of truth

1. Deployment scope under `.scopes/deepseek-v4-flash-0731-dual-5090/`
2. Archived K96 consensus record under
   `.scopes/archive/heretic-v2-reap96-consensus/`
3. Archived REAP132 delivery record under
   `.scopes/archive/heretic-v2-reap132-build-validation/`
4. Durable project knowledge under `.wiki/`
5. `README.md` for operator entry points

## Runtime environment

- The sole runtime environment for this project is the project-local
  `/home/build/work/deepseek-v4-flash-0731-dual-5090/.venv`.
- Manage it with `uv` from the project root: use `uv sync`, `uv run`, and
  `uv pip --python .venv/bin/python`.
- Install all missing runtime or test dependencies into this `.venv`; never
  redirect them to `/home/build/torch/.venv`, a user-global Python, or the
  system Python.
- `/home/build/torch/.venv` is only the build project's environment. This
  project consumes locally built wheels from `/home/build/torch/dist`, but all
  packages must be installed into this project's `.venv`.
- `torch` and `pytorch-triton` are pinned in `pyproject.toml` and `uv.lock` to
  the exact CPython 3.13 wheels under `/home/build/torch/dist`. Do not resolve
  replacement Torch/Triton packages from PyPI. If torchvision, torchaudio,
  xFormers, Flash Attention, SageAttention, or another local CUDA extension is
  later added as a project dependency, install its matching wheel from the same
  `/home/build/torch/dist` build set rather than borrowing
  `/home/build/torch/.venv`.
- Before runtime tests, use `uv run python` to verify the effective Torch and
  Triton versions and that imports resolve inside this repository's `.venv`.

## Mission

Keep the accepted REAP132 MXFP4 GGUF deployable. The completed REAP96 consensus
experiment is archived after runtime semantic rejection and does not replace the
canonical K132 artifact.

The deployment baseline uses llama.cpp on dual RTX 5090 with:

- layer split 1:1
- full GPU weights
- F16 KV in system RAM
- 64K context start
- single slot

## Hard rules

- Hugging Face 模型下载统一使用已登录的 `hf` CLI，不使用临时脚本或其
  他账号；模型 snapshot 默认落在 `/data/linux-fast/models/<model-name>/`。
  对需要复现的 checkpoint，先用 `--revision <commit-sha>` 固定版本，再用
  `--local-dir` 写入该 NVMe 目录。
- 示例：`uv run hf download <repo> --revision <sha> --local-dir
  /data/linux-fast/models/<name>`。下载完成后必须校验文件清单和 SHA256，
  再用于压缩或服务。

- Do not load the runtime model from `/data/toshiba-1tb` if the NVMe copy exists or can be created.
- Preferred runtime directory:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731/`
- Final artifact destination:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf`.
- Do not download, test, or publish puwaer, IQ3, Q2, or other alternative
  quantizations in the REAP132 deployment scope. MXFP4 remains the only
  deployment format. The K96 consensus scope may inspect only the specific
  small external plan/mask/manifest evidence listed in its contracts; it must
  not download external model-weight or GGUF payloads.
- The existing 80 GiB GGUF with SHA256
  `e6dd3c1235e0b0ea6a2efbe13f2f06cc2015e8d6c135025aa3c5d8e75bfff84d` is
  quarantined diagnostic output, not a golden or deployable model.
- `squanchyzx-puwaer-reap132-mask.json`, the accepted REAP132 native
  checkpoint, and the canonical REAP132 GGUF are immutable baselines. K96 is a
  new plan and artifact line; never edit, overwrite, or reinterpret K132 data
  to make a K96 plan fit.
- Prefer full GPU offload. Expert CPU offload is last resort only.
- OOM order:
  1. lower `-b/-ub`
  2. lower `-c` to 32768
  3. only then consider limited CPU offload
- Do not jump straight to 128K+ context.
- Default bind is `127.0.0.1` unless Master explicitly approves broader exposure.
- Before runtime tests, verify no `wiki_nav.py`/doctor scan is reading large
  external files and record a clean RAM/Swap baseline.
- Use `ok-skill` / `repo-task-driven` / `wiki-note` for durable scope and knowledge updates.

- Historical native REAP attempts were quarantined by a host stability issue.
  On `7.0.0-28-generic`, large sequential safetensors reads have reproduced
  kernel `BAD_PAGE`/`compound_head not consistent` reports from `kswapd0` even
  with zram nearly unused. Before accepting a post-prune report, check
  `cat /proc/sys/kernel/tainted` and `journalctl -k -b` for these signatures;
  do not run native smoke or GGUF conversion after a bad-page event.
- Keep the project on the current `7.0.0-28-generic` kernel. Do not make a
  6.15/6.16/6.8 downgrade or broad kernel bisect a prerequisite for checkpoint
  delivery. The only retained root-cause A/B is an explicitly authorized 7.0
  test build that disables ext4 regular-file large folios while keeping all
  other kernel, hardware, filesystem, driver, and workload variables fixed.
  This diagnostic is deferred until after the model delivery work and must not
  block the production direct-I/O workflow.
- The production checkpoint workflow is Linux `7.0.0-28-generic` with aligned
  `O_DIRECT` for all four bulk-data paths: source reads, output shard writes,
  content-manifest hashing, and tensor provenance verification. Do not replace
  any of these paths with buffered I/O for convenience or performance testing.
- Do not disable or check MGLRU for checkpoint work; it is not a build gate or
  an operational workaround. The same tail-page `BAD_PAGE` reproduced with
  MGLRU enabled through `evict_folios` and disabled through the classic
  `shrink_inactive_list` path, excluding MGLRU-specific logic as the common
  cause.
- Never run a full buffered hash, manifest, or tensor scan over multi-GB model
  files on this host. The current failure boundary is ext4 buffered page cache,
  higher-order/large folios, and generic reclaim/free. The checkpoint builder
  source reads, content manifest, and direct tensor verifier must use aligned
  `O_DIRECT`; use `tools/verify_io_paths.py --direct-only` for full-shard I/O
  checks. Restrict buffered-versus-direct comparisons to small fixtures that
  cannot fill page cache. Do not use `drop_caches` or rely on
  `POSIX_FADV_DONTNEED` as a substitute for bypassing page cache.
- Before every large checkpoint build, manifest pass, or full tensor verifier,
  require the current boot to contain no `BAD_PAGE`, `compound_head`,
  corrupted-tail-page, kernel Oops, or unexplained user-process `SIGSEGV` /
  general-protection-fault event. Native GPU validation additionally requires
  no NVIDIA `Xid` event in the current boot. If one occurs during a bulk task,
  stop all artifact validation and reboot; no later runtime setting can make
  that boot admissible evidence. A Python exit `139` without a Python traceback
  is a host-stability event, not an ordinary retryable builder exception.
- Keep `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`
  read-only. Its Python 3.12 A/B manifests are byte-identical at
  `9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`,
  and `scripts/verify_reap132_checkpoint.py` produced a zero-failure PASS report.
  The verifier uses aligned `O_DIRECT` reads to avoid
  filling page cache; this is the supported checkpoint workflow, not proof that
  future buffered or `mmap()` model loading is unaffected by the host issue.
- The 7.0/5600 rebuild completed with a clean kernel and manifest, but direct
  verification found five varying FP4 expert-weight byte mutations across
  rebuilds. Treat this as a writer defect: do not promote any artifact until
  routed FP4 weights are copied and sliced directly from CPU safetensors bytes,
  without a CUDA round-trip or fused Transformers reverse conversion.
- A noMTP artifact must set `num_nextn_predict_layers` to `0` as well as contain
  zero `mtp.*` tensors. The deterministic builder and independent verifier must
  enforce both halves of this contract before native model loading.
- Run future full raw-safetensors builds with system Python 3.12 and fatal-signal
  diagnostics enabled: `/usr/bin/python3.12 -X faulthandler`. The config-correct
  Python 3.12 A/B completed with identical per-file hashes and a clean boot, so
  it is the production builder baseline. Continue to leave Apport/core evidence
  available, and do not treat this success as proof that CPython 3.13 caused the
  earlier GPF.
- Native HF correctness smoke must use aligned O_DIRECT layer streaming on one
  CUDA device per process. A multi-token run that switched from GPU0 to GPU1 in
  one process triggered NVIDIA `Xid 31` on PCI `02:00.0` (GPU1) and an illegal
  virtual read; do not treat the earlier one-token cross-device PASS as a valid
  multi-device acceptance. Keep dual-GPU validation in the later llama.cpp
  runtime gate unless a separate clean-boot native multi-device fix is proven.
- Phase 2 native acceptance is bounded prefill correctness, not semantic
  generation quality. Run independent 1/16/32/64/128-token cases with physical
  GPU1 isolation (`CUDA_VISIBLE_DEVICES=0`), require
  `torch.cuda.device_count() == 1`, synchronize CUDA before PASS, and run the
  clean kernel/Xid gate before and after every case. Evaluate actual chat,
  reasoning, coding, tool-call, and long-context generation in Phase 3 on the
  deployed llama.cpp GGUF path.
- The first GPU0-only matrix passed 1 and 16 input tokens, then reproduced Xid
  31 on physical GPU0 at the 32-token Layer 2 eager-attention batched matmul.
  GPU1 was invisible, so neither GPU1 nor cross-device switching is a necessary
  condition. Do not continue T4/T5 or any other GPU validation in that boot;
  preserve the checkpoint acceptance and treat this as a native CUDA runtime
  blocker.
- A streamed CUDA layer must be synchronized after its forward and before
  `free_layer()` replaces parameters or invokes `empty_cache()`. The first
  isolated matrix freed layers before explicit synchronization; treat the new
  ordering as an unproven lifecycle fix until it passes on a clean boot.
- Layer 2 is the first compressed sparse attention layer, so keep a 32-token
  CSA/eager-cuBLAS defect as a parallel hypothesis. Do not assign the Xid solely
  to layer-release ordering before a clean-boot rerun with synchronization.
- On the next clean boot, run `t3-32-token-code` alone through the matrix
  runner's `--case` selector. Continue to T4/T5 only after T3 and its post-case
  kernel gate pass; then backfill T1/T2 for same-commit acceptance evidence.
- The synchronized T3 rerun still failed at the same Layer 2 second attention
  matmul with GPU0 Xid 31, so downgrade premature layer release as the cause.
  On the next clean boot run only T3 with `--cuda-launch-blocking`; do not run
  T4/T5. If the failure remains at the matmul, record operand metadata before
  changing layout with `.contiguous()`.
- Launch blocking moved the T3 traceback to Layer 2's first QK matmul, proving
  the second AV matmul was a delayed observation point. The next clean boot must
  run only T3 with launch blocking and `--trace-attention-layer 2`; capture the
  flushed operand metadata before any contiguous-layout or backend change.
  Keep the first trace metadata-only: `--trace-values` is opt-in because finite,
  min/max, and mask-count reductions launch extra CUDA kernels and alter timing.
- The metadata-only T3 trace completed immediately before QK, then QK failed
  with Xid 31. Query was contiguous and 256-byte aligned. The repeated key used
  zero batch/head strides `[0, 0, 512, 1]`; after transpose its stride was
  `[0, 0, 1, 512]`. The reported virtual-read fault lay just beyond the logical
  40 KiB shared key storage region. Treat this as strong evidence for a
  PyTorch/cuBLAS zero-stride broadcast-view defect, not yet proof. The next
  clean-boot A/B may change only the transposed key operand to contiguous via
  `--qk-layout key-transposed-contiguous`; do not run it in the Xid-tainted boot.
- The key-transposed-contiguous A/B made QK PASS and produced an `after_qk_matmul`
  trace. The failure then moved to AV, whose value operand still used zero
  batch/head strides `[0, 0, 512, 1]` without a transpose. Its Xid fault was
  again exactly `0xd600` bytes after the shared storage pointer, `0x3600` bytes
  beyond the logical 40 KiB region. This rejects transpose layout as the common
  trigger and strongly implicates the current PyTorch matmul lowering/selected
  cuBLAS path for BF16 zero-stride broadcast operands; cuBLAS API support for
  zero stride itself is not in question. The next clean-boot A/B must keep QK
  key contiguous and additionally use `--av-layout value-contiguous`.
- Native CUDA debugging ends after that final QK+AV-contiguous T3 A/B. If T3
  passes, run only the 128-token case with the same workaround; skip 64 tokens.
  If both pass, record Phase 2 native PASS with the zero-stride materialization
  workaround. If either fails or produces Xid, record the current native HF
  stack as limited beyond the already-passing 16-token prefill and proceed to
  Phase 3 with the independently byte-verified checkpoint. Do not continue with
  compute-sanitizer, alternate GEMM algorithms, Torch/CUDA/backend A/Bs, or
  further upstream root-cause debugging inside this project.
- The final QK+AV-contiguous T3 made both Layer 2 GEMMs pass and completed
  Layers 2-3. Layer 4 then returned to unpatched eager attention and reproduced
  Xid 31 at QK. A full native run would require model-wide runtime patching,
  which exceeds the debug budget. Do not run T5. Phase 2 is complete with native
  HF limited beyond the prior clean 16-token prefill; proceed to Phase 3 with
  the byte-verified checkpoint after a clean reboot.
- Phase 3 pins the `vendor/llama.cpp` submodule from
  `https://github.com/furedericca-lab/llama.cpp.git` at fork commit `1e17097`.
  Its DeepSeek V4 converter repacks routed expert weight+scale into GGUF MXFP4,
  supports `--no-mtp`, and materializes `LazyNumpyTensor` before serializing a
  direct-I/O payload. The default local safetensors materializer uses
  `np.memmap`; never run it over the full checkpoint on this host. Full
  conversion must use the fixture-tested `--direct-io-input` and
  `--direct-io-output` paths with aligned 64 MiB bounded staging and start only
  on a clean boot. Direct-I/O output stages converted tensor payloads immediately
  to a same-filesystem temporary file instead of retaining every array in RAM.
  The replacement output
  `DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf` is
  85,049,305,696 bytes, has SHA256
  `f436ed2f92e6d6d49b5c73c546f2d52a6fa277b9f72d9915bff08b9385bb286b`, and
  passed 90 routed-expert plus 9 nonexpert provenance comparisons, plus 52
  sampled dequantized-FP8-to-Q8_0 backbone row comparisons across layers 0,
  10, and 42. The earlier lazy-zero-payload output was deleted after recording
  its SHA256 and direct-writer root cause; it had zeroed ordinary BF16/F32
  payloads despite correct routed MXFP4 payloads.
- The runtime baseline for the corrected candidate is `--load-mode dio -dev
  CUDA0,CUDA1 -sm layer --fit on --fit-target 3072,3072 --no-kv-offload -ctk
  f16 -ctv f16 -c 65536 -np 1 -b 512 -ub 128 -fa on`. Do not use `-ngl all`:
  it disables auto-fit and requests an impossible roughly-40-GiB allocation per
  GPU. The corrected candidate passed 64K dual-5090 startup, API health, and a
  raw `Paris` completion without a new Xid, BAD_PAGE, Oops, or GPF. It also
  completed a 32,767-token prefill plus eight-token decode at 371.5 prompt
  tok/s, and Chat JSON, Chinese, and Python-code probes passed. The exact native-smoke prompt
  `Write Python: def add(a,b): return a+b` tokenizes to 11 tokens and produces
  a newline as its first greedy token in both native HF and the corrected GGUF;
  this rules out a first-step conversion mismatch for that prompt. The canonical
  GGUF is read-only and is the sole deployment artifact.
- Current relevant PCIe topology: both RTX 5090 GPUs are CPU-attached at PCIe
  5.0 x8; WD SN540 is CPU-attached at PCIe 3.0 x4; the MAP1602/aigo 2 TB NVMe
  backing `/data/linux-fast` is PCIe 4.0 x4 behind the first X670 chipset, whose
  CPU uplink is Gen3 x4. Treat this as an A/B design constraint, not proof that
  the chipset, NVMe controller, IOMMU, or DMA path caused a fault.

## Validation matrix

| Change class | Commands |
|---|---|
| docs/scope only | `python3 $HOME/.codex/skills/ok-skill repo-task-driven check --scope deepseek-v4-flash-0731-dual-5090 --decision --json` |
| wiki updates | `python3 $HOME/.codex/skills/ok-skill wiki-note rebuild --json && python3 $HOME/.codex/skills/ok-skill wiki-note lint --json && python3 $HOME/.codex/skills/ok-skill wiki-note doctor --json` |
| native REAP verification | `uv run pytest tests -q`; verify clean kernel boot before full tensor pass |
| runtime bring-up | `nvidia-smi`, `llama-server --list-devices`, first-boot launch, `/v1/models`, one completion |

## Forbidden shortcuts

- Do not claim 64K is proven without boot evidence.
- Do not hide the current ~46 GiB RAM limitation.
- Do not commit the multi-dozen-GB GGUF into git.
- Do not treat archived future scopes as active instructions.
