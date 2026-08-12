---
license: mit
language:
- en
- zh
base_model: deepseek-ai/DeepSeek-V4-Flash-0731
base_model_relation: quantized
pipeline_tag: text-generation
library_name: gguf
tags:
- gguf
- deepseek
- deepseek-v4
- moe
- reap
- pruning
- imatrix
- 2-bit
- ds4
- dwarfstar
- mac
---

# DeepSeek-V4-Flash-0731 — REAP25 2-bit imatrix GGUF (ds4/DwarfStar)

A 25%-expert-pruned, 2-bit imatrix GGUF of
[deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731),
built for the [antirez/ds4 (DwarfStar)](https://github.com/antirez/ds4) engine and
96 GB Apple Silicon Macs.

| | |
|---|---|
| File | `DeepSeek-V4-Flash-0731-REAP25-IQ2XXS-w2Q2K-AProjQ8-SExpQ8-OutQ8-imatrix.gguf` |
| Size | 68,579,735,164 bytes (63.87 GiB) |
| Experts | 256 → 192 kept in layers 3–42 (REAP25, 25% pruned); layers 0–2 keep 256 |
| Quant | IQ2_XXS (gate/up) + Q2_K (down) routed experts; Q8_0 attention/shared/output; F16 HC/compressor/indexer |
| Engine | ds4 (`--dspark` optional) |
| Context | 1M (compressed KV: ~8.4 GiB at 1M) |

## What this is

This is a **GGUF-level prune** of the stock 2-bit 0731 GGUF: the experts that the
REAP25 saliency pruning dropped are removed from the file and the remaining bytes are
recompacted. **No re-quantization was done** — every kept byte is byte-identical to the
stock file, so quality is exactly the 2-bit quality of the source, minus the REAP
pruning cost. The result is 68.58 GB and fits in 96 GB Macs that cannot hold the
80.8 GiB stock file.

## Why the identity of the dropped experts matters (and how we got it)

REAP25 keeps **192 of the 256 experts** in layers 3–42. In a GGUF, each expert's
weights are stored as a separate contiguous, block-aligned chunk per layer (the expert
axis is the slowest tensor dimension, and quant blocks never straddle expert
boundaries). Pruning therefore means: for every layer, **drop the exact 64 chunks that
the REAP saliency run removed** — not any 64. If the wrong chunks are dropped, the
router addresses experts that are no longer there and the model produces garbage.

The REAP25 MLX weights are compacted to ids `0..191`, so the original expert identity
is not stored in them. We did not find a published list of which experts were dropped
by the REAP saliency run, so we had to work out the mapping ourselves: each REAP25
expert's weights were matched against all 256 stock experts of the same layer on four
independent parts (gate/up/down expert weights + router rows). All four parts agreed
for 192/192 experts in 40/40 layers, with decisive margins — giving us the exact
deletion map used for this file.

## Provenance — who did what

1. **Base model** — [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
   (304B sparse MoE, 43 layers, 256 routed experts, top-6, 1M ctx).
2. **REAP25 pruning** — [pipenetwork/DeepSeek-V4-Flash-MLX-REAP25](https://huggingface.co/pipenetwork/DeepSeek-V4-Flash-MLX-REAP25)
   by [PipeNetwork](https://github.com/PipeNetwork/deepseek-v4-mlx): 25% of routed
   experts pruned by REAP saliency (layers 0–2 hash-routed keep all 256; layers 3–42
   keep 192).
3. **Stock 2-bit GGUF (prune source)** —
   [Rednalreden/DeepSeek-V4-Flash-0731-dwarfstar-q2-gguf](https://huggingface.co/Rednalreden/DeepSeek-V4-Flash-0731-dwarfstar-q2-gguf)
   (86.72 GB): imatrix-guided IQ2XXS-w2Q2K-AProjQ8-SExpQ8-OutQ8 quant of the 0731, built
   with the ds4 toolchain (`gguf-tools/deepseek4-quantize`).
4. **Expert deletion map (recovered here)** — B-exact weight matching, as described
   above. The map and all scripts are published in the
   [reap-compact-support](https://github.com/ljubomirj/ds4/tree/reap-compact-support)
   branch of the ds4 fork (`tools/reap25-prune/`, `docs/REAP25-REPRODUCE.md`).
5. **GGUF surgery (this repo)** — the 64 pruned experts' quantized chunks were dropped
   per layer and the file recompacted; `reap.*` metadata added
   (`reap.enabled`, `reap.layout=ds4-compact-v1`, `reap.layer.expert_count`,
   `reap.layer.keep_count`).
6. **DSpark drafters (optional, third-party)** —
   [antirez/deepseek-v4-gguf](https://huggingface.co/antirez/deepseek-v4-gguf)
   (`DeepSeek-V4-Flash-DSpark-support.gguf`) or
   [bleysg/DeepSeek-V4-Flash-DSpark-drafter-GGUF](https://huggingface.co/bleysg/DeepSeek-V4-Flash-DSpark-drafter-GGUF)
   (`DSpark-drafter-Q2K-Q8-0731.gguf`); load with `--mtp <file> --dspark`.

## Quality & speed (measured on M2 Max 96 GB, ds4-server + llama-benchy)

- Perplexity (131,040 wikitext-2-raw-v1 tokens, ds4, same protocol): stock 4.934 →
  REAP25 5.129, **δ +0.195 ppl (+3.95%)** — better than pipenetwork's published +4.5%
  at 4-bit (different protocol). A model property — engine updates do not change it.
- Speed (pp 2048, tg 128, fixed 1M-ctx server; engine = the
  `reap-compact-support` branch at `01bdc35`, i.e. upstream DS4 rebased onto
  2026-08-09 main `84cc882` with Ivan Fioravanti's exact pre-M5 Metal decode
  fusions, `4e401a1` et al.):

  | Context depth | Prefill (PP) t/s | Decode (TG) t/s |
  |---|---|---:|
  | 1K | 183.6 | 31.7 |
  | 8K | 192.0 | 35.2 |
  | 32K | 111.0 | 15.6* |
  | 128K | 93.2 | 24.5 |

  \*Samples are single-shot unless noted; expect ±a few %. The 32K decode
  sample was visibly stalled (mean 15.6 t/s vs peak 25.0); two same-session
  standard-build samples with the MTP head attached measured 29.96 / 30.46 t/s
  at 32K, so the true 32K decode is ≈28–30 t/s. 8K reproduced identically
  (35.19) across two separate server sessions.

  The upstream long-context decode fix + pre-M5 fusions roughly doubled
  deep-context decode versus the pre-rebase engine (128K TG 11.23 → 24.47,
  +118%); 1K decode is unchanged (~32 t/s) and prefill is somewhat lower on
  this quantization path. Earlier Aug 3/4 numbers (TG 14.7/11.7/11.2/11.5/11.7
  at 1K–128K) are superseded.

## Reproduction

Full recipe (map recovery + GGUF surgery + validation): `docs/REAP25-REPRODUCE.md`
in the [reap-compact-support](https://github.com/ljubomirj/ds4/tree/reap-compact-support)
branch — DESIGN notes + RUNBOOK + scripts (`bexact.py`, `prune_gguf.py`,
`extract_tables.py`, `keep_map_bexact.json`).

## Notes

- ds4's GGUF variant differs from llama.cpp's (u64 string lengths, no size field,
  32-byte data alignment) — this file is for the ds4 engine, not llama.cpp.
- Not an official DeepSeek release; pruning + 2-bit reduce quality. Evaluate before
  production use.
- DSpark speculative decode (`--mtp <drafter> --dspark`) is linked for
  completeness but measures as a **net slowdown on the M2 Max**: the drafters
  predict the pruned model well (~69% acceptance), yet proposal+verify overhead
  exceeds the decode they save at every depth. Run without `--dspark` on this
  class of hardware.

## Credits and acknowledgements

This is small work sitting on top of a very large body of work by many people, and we
want to thank them properly:

- **[DeepSeek](https://huggingface.co/deepseek-ai)** — for the
  [DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
  base model, the DSpark draft stages, and the reference inference implementation.
- **[antirez (Salvatore Sanfilippo)](https://github.com/antirez)** — for the
  [ds4 (DwarfStar) engine](https://github.com/antirez/ds4), its
  `gguf-tools/deepseek4-quantize` toolchain and imatrix, the REAP-compact runtime
  support this file is built for, and the
  [DeepSeek-V4-Flash-DSpark-support.gguf](https://huggingface.co/antirez/deepseek-v4-gguf)
  drafter.
- **[PipeNetwork](https://github.com/PipeNetwork)** — for the
  [DeepSeek-V4-Flash-MLX-REAP25](https://huggingface.co/pipenetwork/DeepSeek-V4-Flash-MLX-REAP25)
  REAP pruning and the from-scratch MLX port of the architecture.
- **[Rednalreden](https://huggingface.co/Rednalreden)** — for the
  [stock 2-bit imatrix GGUF](https://huggingface.co/Rednalreden/DeepSeek-V4-Flash-0731-dwarfstar-q2-gguf)
  we pruned from.
- **[GaelicThunder](https://huggingface.co/GaelicThunder)** — reference 2-bit builds
  of the 0731 that guided the quant recipe.
- **[eouya2](https://huggingface.co/eouya2)** — prior compact REAP25 GGUF work that
  proved the GGUF-level expert-subset approach works.
- **[0xSero](https://huggingface.co/0xSero)** — REAP observation datasets and the
  0731 REAP reference checkpoints we used to sanity-check our map recovery.
- **[bleysg](https://huggingface.co/bleysg)** — for the
  [DSpark-drafter-Q2K-Q8-0731.gguf](https://huggingface.co/bleysg/DeepSeek-V4-Flash-DSpark-drafter-GGUF).
- **[ggerganov / llama.cpp](https://github.com/ggerganov/llama.cpp)** — for the
  IQ2_XXS/Q2_K dequant reference tables used in the map recovery.

If you are one of the people above and we misrepresented your work, please open an
issue or pull request on the [reap-compact-support branch](https://github.com/ljubomirj/ds4)
and we will fix it promptly.
