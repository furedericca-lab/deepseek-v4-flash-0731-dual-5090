# AGENTS.md

## Source of truth

1. Current build/verification scope under
   `.scopes/heretic-v2-reap132-build-validation/`
2. Deployment scope under `.scopes/deepseek-v4-flash-0731-dual-5090/`
3. Durable project knowledge under `.wiki/`
4. `README.md` for operator entry points

## Runtime environment

- The sole runtime environment for this project is the project-local
  `/home/build/work/deepseek-v4-flash-0731-dual-5090/.venv`.
- Manage it with `uv` from the project root: use `uv sync`, `uv run`, and
  `uv pip --python .venv/bin/python`.
- Install all missing runtime or test dependencies into this `.venv`; never
  redirect them to `/home/build/torch/.venv`, a user-global Python, or the
  system Python.
- `/home/build/torch/.venv` is only the build project's environment. Its local
  Torch wheel may be consumed by this project, but packages must be installed
  into this project's `.venv`.
- The current Torch dependency is the locally built wheel referenced in
  `pyproject.toml` and `uv.lock`; verify it with `uv run python` before runtime
  tests.

## Mission

Deploy and operate local llama.cpp CUDA serving for the locally copied
DeepSeek-V4-Flash-0731 REAP artifacts:

- `DeepSeek-V4-Flash-0731-reap-150b-Q2_K.gguf` (legacy diagnostic artifact)
- `DeepSeek-V4-Flash-0731-reap-150b-IQ3_XXS.gguf` (current candidate)

on dual RTX 5090 with:

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
- Current IQ3 destination:
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-reap-150b-IQ3_XXS.gguf`
- Hugging Face remote artifact metadata is the source of truth for these files:
  - Q2_K: size `62.4 GB`, SHA256
    `2e8ab70acda6d9ce4813a8b580d402c30d837d7bd8bf6119d6e84de38aa42d48`,
    Xet hash `63773380bafc18dcffbb9c36f4b6db523433c08a095a66ab4e0dc791baac19e7`.
  - IQ3_XXS: size `67 GB`, SHA256
    `98e448d678760ef50f0e02c9318cfcac94a50d8901dd373e9acdf5d71e668585`,
    Xet hash `d8b2dc5aca12a6e3919bc20f408fe26686c5417794456a762f7002743c7738f3`.
- The previous local copies are deleted. Their observed hashes were different
  from the remote metadata, so they must not be treated as verified artifacts.
- A newly downloaded GGUF may be served only after its local SHA256 matches the
  corresponding remote SHA256 above. Xet hash is an artifact identity hint,
  not a replacement for local SHA256 verification.
- Prefer full GPU offload. Expert CPU offload is last resort only.
- OOM order:
  1. lower `-b/-ub`
  2. lower `-c` to 32768
  3. only then consider limited CPU offload
- Do not jump straight to 128K+ context.
- Default bind is `127.0.0.1` unless Master explicitly approves broader exposure.
- Do not launch IQ3 automatically after copying; serving/testing requires an
  explicit request.
- Before runtime tests, verify no `wiki_nav.py`/doctor scan is reading large
  external files and record a clean RAM/Swap baseline.
- Use `ok-skill` / `repo-task-driven` / `wiki-note` for durable scope and knowledge updates.

- Native REAP verification is currently quarantined by a host stability issue.
  On `7.0.0-28-generic`, large sequential safetensors reads have reproduced
  kernel `BAD_PAGE`/`compound_head not consistent` reports from `kswapd0` even
  with zram nearly unused. Before accepting a post-prune report, check
  `cat /proc/sys/kernel/tainted` and `journalctl -k -b` for these signatures;
  do not run native smoke or GGUF conversion after a bad-page event. The
  alternate installed kernel is `6.17.0-23-generic`.
- Before every large checkpoint build, manifest pass, or full tensor verifier,
  temporarily disable MGLRU for the current boot with
  `echo 0 | sudo tee /sys/kernel/mm/lru_gen/enabled`, then require
  `/sys/kernel/mm/lru_gen/enabled` to read `0x0000`. This setting is normally
  reset by reboot, so repeat the gate after every reboot; do not assume a prior
  disablement remains active. Also require the current boot to contain no
  `BAD_PAGE`, `compound_head`, corrupted-tail-page, or kernel Oops event. If one
  occurs, stop all artifact validation and reboot before rebuilding; disabling
  MGLRU after the event does not make that boot admissible evidence.
- Keep `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`
  read-only and quarantined until `scripts/verify_reap132_checkpoint.py`
  produces a PASS report. The verifier uses bounded reads with
  `POSIX_FADV_DONTNEED` to avoid filling page cache, but this is not a
  substitute for resolving host memory/kernel instability. A fresh rerun under
  `6.17.0-23-generic` reproduced `BAD_PAGE` / `compound_head not consistent`
  in `kswapd0` during verification, so changing kernels alone is not yet a
  sufficient stability gate.
- The 7.0/5600 rebuild completed with a clean kernel and manifest, but direct
  verification found five varying FP4 expert-weight byte mutations across
  rebuilds. Treat this as a writer defect: do not promote any artifact until
  routed FP4 weights are copied and sliced directly from CPU safetensors bytes,
  without a CUDA round-trip or fused Transformers reverse conversion.

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
