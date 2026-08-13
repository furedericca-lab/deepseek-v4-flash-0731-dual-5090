# DeepSeek-V4-Flash-0731 HERETIC REAP132 Deployment and K96 Releases

This repository contains the completed deterministic no-MTP REAP132 delivery
and a separate K96 consensus-planning line. REAP132 remains the deployed
canonical MXFP4 GGUF while K96 is derived only from its survivor universe and
independently published mask evidence.

The active experiment is
`.scopes/heretic-v2-reap132-mixed-expert-quant/`. It keeps all 132 routed
experts and top-k 6, assigns exactly 17 protected layers to the IQ3_XXS recipe
and 26 ordinary layers to the Q2_K_S recipe, and reuses the archived K96 Profile A default
non-pure IQ4_XS mixed policy for all eligible non-routed weights. The ratio is
fixed independently of output size; the canonical K132 Golden remains read-only
and deployed.

The completed independent K96 Profile A IQ4_XS-backbone release is archived
under `.scopes/archive/heretic-v2-reap96-iq4xs-backbone/`. It consumed the
read-only K96 MXFP4 Golden and preserved all 129 routed-expert MXFP4 payloads
byte-for-byte. Only llama.cpp's default mixed Profile A was used; the release
did not use `--pure`, imatrix, or a second quantization profile. Shared Expert
and Core Backbone weights were non-routed inputs to the default IQ4_XS mixed
policy; router, `tid2eid`, norms, and other structural tensors remained
unchanged.

## Current Status

| Phase | Status | Result |
|---|---|---|
| 1. Checkpoint build | Complete | Deterministic Python 3.12 A/B builds and independent byte-provenance verification passed |
| 2. Native HF smoke | Complete with limitation | 1- and 16-token prefills passed; 32-token CSA exposed a reproducible Torch/cuBLAS zero-stride runtime fault on Blackwell |
| 3. GGUF and runtime | Complete | Canonical MXFP4 GGUF passed provenance, dual-5090 64K load, 32K prefill, API, and behavior probes |
| 4. REAP96 consensus | Complete; candidate rejected | Native/GGUF provenance and runtime stability passed, but semantic acceptance failed; K132 remains deployed |
| 5. K96 IQ4_XS non-routed weights | Complete | Profile A passed provenance and runtime gates; K96 MXFP4 Golden remains immutable and K132 remains deployed |
| 6. K132 mixed routed-expert quantization | In progress | Phase 1 freezes structural and activation-importance evidence before the fixed 17/26 plan |

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

`squanchyzx-puwaer-reap132-mask.json` is the frozen REAP132 survivor plan. Do
not edit or recalculate it. The K96 scope may select only a 96-expert subset of
each existing 132-expert layer and must write a new plan plus new hash-routing
tables; it never changes the REAP132 plan or artifacts.

Accepted K96 native source checkpoint:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP/
```

It is read-only, contains 26,332 tensors in 17 shards, and has O_DIRECT content
manifest SHA256
`62e40f7cecc2d1018faa8c386b39268f9d13cb3833c9f82f365e99bfa5f574ed`.
The former K96 GGUF candidate was:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4.gguf
```

It was `64,340,873,568` bytes and had O_DIRECT SHA256
`697309d18ada765bdce2a72b52cb1497ed5e374cd5c77edfa7fc0085aa68ff31`.
Its metadata reports `deepseek4`, 43 blocks, 96 routed experts, six active
experts, 1,328 tensors, and `MOSTLY_MXFP4_MOE`. Payload provenance passed
108 routed-expert, 7 nonexpert, and 104 FP8-backbone comparisons. It remains a
an archived diagnostic candidate, not a deployment artifact. Dual-5090 64K and
32K-prefill stability passed, but both Native K96 and GGUF selected `',` instead
of ` Paris` for the raw France prompt. This identifies K96 quality loss rather
than conversion failure. The frozen plan will not be rescored; K132 remains the
sole deployed model. The file was deleted on 2026-08-13 to prevent accidental
reuse after routed-payload defects were discovered in the parent K132 GGUF line.

The former independent K96 Profile A release was:

```text
/data/linux-fast/models/DeepSeek-V4-Flash-0731/
DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP-MXFP4exp-IQ4XSbb.gguf
```

It was `59,256,121,472` bytes and had O_DIRECT SHA256
`845a0b91d17fddd6990068b995c8af031945af55f5bff94acc5a1c08389c63c3`.
All 129 routed-expert tensors remain byte-identical MXFP4. Shared Expert and
Core Backbone weights use llama.cpp's default IQ4_XS mixed policy: 655 tensors
are IQ4_XS, five early shared-expert down tensors are Q5_K, and
`output.weight` is Q6_K. Dual-5090 64K/API, Chinese, JSON, Python, and
32,767-token prefill passed. Its France-prompt behavior still matches the known
K96 quality limitation, so it is an independent release rather than the K132
deployment replacement. This file was also deleted on 2026-08-13.

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
payload-level direct-I/O tests. The prior artifact ending in
`REAP132-noMTP-MXFP4.gguf` was later proven to contain three local routed-payload
mutations and was deleted. The accepted quantization input is now
`DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-routed-rebuild.gguf`:
`85,049,305,696` bytes and O_DIRECT SHA256
`752a0146f54d5c5bc34491d53f9e1acbb63540b1e3c38bd352185b508418cfdd`.
It passed full byte-exact provenance for all 129 routed tensors, covering
17,028 projection-expert comparisons and 75,884,396,544 bytes, plus non-routed
and FP8-backbone acceptance checks.

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
  --outfile /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-provenance-rebuild.gguf \
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
  -m /data/linux-fast/models/DeepSeek-V4-Flash-0731/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP-MXFP4.full-routed-rebuild.gguf \
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

- Archived K96 rejected-candidate scope:
  `.scopes/archive/heretic-v2-reap96-consensus/`
- Deployment scope: `.scopes/deepseek-v4-flash-0731-dual-5090/`
- Archived REAP132 delivery scope:
  `.scopes/archive/heretic-v2-reap132-build-validation/`
- Durable implementation records:
  `.wiki/implementation/heretic-v2-reap132-build-validation.md` and
  `.wiki/implementation/heretic-v2-reap96-consensus.md`
- Operator and safety rules: `AGENTS.md`
- Frozen-plan details: `docs/puwaer-reap132-mask-README.md`

The native HF CSA fault is documented and closed under the Phase 2 stop-loss
rule. Phase 3 acceptance is based on the pinned llama.cpp/GGUF deployment path;
do not reopen Torch/cuBLAS root-cause debugging as a prerequisite. The archived
K96 scope did not download puwaer or other external weights and did not replace
the canonical K132 deployment.
