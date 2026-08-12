# DeepSeek-V4-Flash-0731 HERETIC REAP132 on Dual RTX 5090

This repository builds and validates a deterministic no-MTP REAP132 checkpoint,
converts it to a golden MXFP4 GGUF, and deploys it with llama.cpp on two RTX
5090 GPUs.

## Current Status

| Phase | Status | Result |
|---|---|---|
| 1. Checkpoint build | Complete | Deterministic Python 3.12 A/B builds and independent byte-provenance verification passed |
| 2. Native HF smoke | Complete with limitation | 1- and 16-token prefills passed; 32-token CSA exposed a reproducible Torch/cuBLAS zero-stride runtime fault on Blackwell |
| 3. GGUF and runtime | Complete | Canonical MXFP4 GGUF passed provenance, dual-5090 64K load, 32K prefill, API, and behavior probes |

Accepted checkpoint:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/
```

Acceptance facts:

- 35,620 tensors in 22 safetensors shards
- 43 layers and 132 routed experts per layer
- zero MTP/DSpark tensors and `num_nextn_predict_layers=0`
- byte-identical Build A/B manifest:
  `9175b91519f0981ed22b3afb3b780c8ba2b2d1bce041277834c0bd057a9e6e5d`
- independent aligned `O_DIRECT` verifier: zero failures
- checkpoint directory is read-only

The frozen survivor plan is
`squanchyzx-puwaer-reap132-mask.json`. Do not edit or recalculate it.

## Checkout

### Runtime dependencies

The project-local `.venv` is the only Python runtime for this repository. Its
PyTorch stack comes from locally built wheels under `/home/build/torch/dist`,
not PyPI and not `/home/build/torch/.venv`:

```text
/home/build/torch/dist/torch-2.14.0a0.post20260719-cp313-cp313-linux_x86_64.whl
/home/build/torch/dist/pytorch_triton-3.8.0+git694c0c3b.post20260719-cp313-cp313-linux_x86_64.whl
```

These wheel paths are pinned in `pyproject.toml` and `uv.lock`. Other locally
built CUDA packages, such as torchvision, torchaudio, xFormers, Flash Attention,
or SageAttention, must also come from `/home/build/torch/dist` if a future
project dependency explicitly requires them. Do not install replacement Torch
or Triton packages from PyPI into this environment.

Clone with submodules:

```bash
git clone --recurse-submodules \
  https://github.com/furedericca-lab/deepseek-v4-flash-0731-dual-5090.git
cd deepseek-v4-flash-0731-dual-5090
test -f /home/build/torch/dist/torch-2.14.0a0.post20260719-cp313-cp313-linux_x86_64.whl
test -f /home/build/torch/dist/pytorch_triton-3.8.0+git694c0c3b.post20260719-cp313-cp313-linux_x86_64.whl
uv sync
```

Verify the effective environment after syncing:

```bash
uv run python -c 'import torch, triton; print(torch.__version__, triton.__version__, torch.__file__)'
```

For an existing checkout:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

`vendor/llama.cpp` tracks the project fork at
`https://github.com/furedericca-lab/llama.cpp.git` and is pinned by the parent
repository gitlink. Do not update it independently without also validating and
committing the new parent pin.

## Golden GGUF Conversion

The pinned converter supports DeepSeek V4, `--no-mtp`, I32 `tid2eid`, routed
expert MXFP4 repacking, and aligned direct I/O. The conversion is a packed-format
repack, not floating-point requantization. The first full output is quarantined:
the direct-output writer serialized lazy ordinary BF16/F32 tensors as zeroes.
Fork commit `1e17097` materializes lazy arrays before writing and is covered by
payload-level direct-I/O tests. The corrected canonical artifact is
`DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf`:
`85,049,305,696` bytes and O_DIRECT SHA256
`f436ed2f92e6d6d49b5c73c546f2d52a6fa277b9f72d9915bff08b9385bb286b`.
It passed 90 routed-expert, 9 nonexpert, and 52 sampled FP8-backbone-to-Q8_0
payload-provenance comparisons.

Full conversion must run only after the clean-boot gate passes:

```bash
uname -r
cat /proc/sys/kernel/tainted
journalctl -k -b --no-pager | \
  rg -i 'BAD_PAGE|compound_head|corrupted mapping in tail page|Oops|general protection|NVRM: Xid|Xid \('
```

Then use both direct-I/O paths:

```bash
uv run python vendor/llama.cpp/convert_hf_to_gguf.py \
  /data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP \
  --outfile /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf \
  --outtype auto \
  --no-mtp \
  --direct-io-input \
  --direct-io-output
```

Never run a full buffered hash, manifest, mmap-based conversion, or tensor scan
over the checkpoint on this host. The production workflow uses aligned
`O_DIRECT` for checkpoint reads, output writes, hashing, and provenance checks.

## Dual-5090 Runtime Baseline

After the golden GGUF passes metadata and direct-I/O SHA256 verification, start
the localhost-only runtime with this initial profile:

```bash
scripts/llama-server-first-boot.sh
```

The script uses direct I/O, automatic two-GPU layer fitting with a 3 GiB margin
per GPU, F16 CPU KV, 64K context, `-b 512`, and `-ub 128`. Do not use `-ngl all`
for this 80 GiB model: it disables fitting and attempts an impossible per-GPU
allocation. The equivalent explicit runtime profile is:

```bash
llama-server \
  -m /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.gguf \
  --load-mode dio \
  -dev CUDA0,CUDA1 \
  -sm layer \
  --fit on \
  --fit-target 3072,3072 \
  --no-kv-offload \
  -ctk f16 \
  -ctv f16 \
  -c 65536 \
  -np 1 \
  -b 512 \
  -ub 128 \
  -fa on \
  --reasoning-format deepseek \
  --host 127.0.0.1 \
  --port 8000
```

On 2026-08-12 this profile loaded the corrected candidate at 64K in 43.8 s,
using approximately 28.1 GiB and 28.5 GiB VRAM with 14 GiB host memory still
available. `/health` and `/v1/models` passed, and the raw prompt `The capital
of France is` began ` Paris.` at 24.6 tok/s with no Xid or kernel fault. It
also completed a 32,767-token prefill plus eight-token decode at 371.5 prompt
tok/s without a fault. Chat JSON, Chinese answer, and Python-code probes passed.
For the exact 11-token native-smoke prompt `Write Python: def add(a,b): return
a+b`, both native HF and the GGUF emit a newline as the first greedy token.

## Project Sources

- Active build scope: `.scopes/heretic-v2-reap132-build-validation/`
- Deployment scope: `.scopes/deepseek-v4-flash-0731-dual-5090/`
- Durable implementation record: `.wiki/implementation/heretic-v2-reap132-build-validation.md`
- Operator and safety rules: `AGENTS.md`
- Frozen-plan details: `docs/puwaer-reap132-mask-README.md`

The native HF CSA fault is documented and closed under the Phase 2 stop-loss
rule. Phase 3 acceptance is based on the pinned llama.cpp/GGUF deployment path;
do not reopen Torch/cuBLAS root-cause debugging as a prerequisite.
