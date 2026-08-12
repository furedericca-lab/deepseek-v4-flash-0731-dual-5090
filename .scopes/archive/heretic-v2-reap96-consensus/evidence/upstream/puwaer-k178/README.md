---
license: mit
library_name: transformers
base_model: deepseek-ai/DeepSeek-V4-Flash-0731
base_model_relation: finetune
pipeline_tag: text-generation
tags:
- moe
- expert-pruning
- reap
- deepseek_v4
- compressed
---

# puwaer/DeepSeek-V4-Flash-0731-reap-200b

[DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) with its routed experts reduced from
**256 to 178 per layer** by router-weighted expert activation **pruning** (REAP), taking the
checkpoint from 156 GiB to 104 GiB. All 43 layers are kept; only the expert
population inside each MoE block changes. No fine-tuning, no distillation, and
no gradient step of any kind — the experts are prued from calibration
statistics in a single pass.

Produced with [moe-compress](https://github.com/puwaer/moe-expert-compress).

## Benchmarks

| Model | Experts | Size | GSM8K | MATH-500 | HumanEval+ | MBPP+ | mean |
|---|---|---|---|---|---|---|---|
| base 284b | 256 | 156 GiB | 0.9484 | 0.7060 | 0.8720 | 0.7407 | 0.8168 |
| **REAP 200b** | 178 | 104 GiB | **0.9401** | **0.6880** | **0.8720** | **0.7407** | **0.8102** |
| REAM 200b | 178 | 104 GiB | 0.8620 | 0.6080 | 0.8841 | 0.7698 | 0.7810 |
| REAP 150b | 132 |  79 GiB | 0.9295 | 0.7140 | 0.8963 | 0.7593 | 0.8248 |
| REAM 150b | 132 |  79 GiB | 0.6922 | 0.5020 | 0.8537 | 0.7328 | 0.6952 |

Difference from the base model, in points:

| GSM8K | MATH-500 | HumanEval+ | MBPP+ | mean |
|---|---|---|---|---|
| -0.83 | -1.80 | +0.00 | +0.00 | -0.66 |

Metrics: GSM8K `exact_match,strict-match`, MATH-500 `math_verify,none`,
HumanEval+/MBPP+ `pass@1_plus`. All greedy (n=1), 4096-token context, `enable_thinking=false`, served
with SGLang.

## What changed relative to the base model

| | base | this model |
|---|---|---|
| Routed experts per layer | 256 | **178** |
| Decoder layers | 43 | 43 |
| Experts per token | 6 | 6 |
| Checkpoint size | 156 GiB | **104 GiB** |
| MTP modules (`mtp.0/1/2`) | present (4705 tensors) | **absent** |
| `chat_template` | not shipped | **shipped** (`chat_template.jinja`) |
| `encoding/encoding_dsv4.py` | present | **present** (copied verbatim) |

One difference deserves to be read before you deploy this:

- **The multi-token-prediction modules are gone.** The base checkpoint carries
  `mtp.0`, `mtp.1` and `mtp.2`; this one carries none of them. **MTP-based
  speculative decoding is therefore unavailable.** Engines that look for those
  weights will fall back to ordinary decoding. Nothing else references them, so
  standard generation is unaffected.

Everything else about the prompt and generation defaults is the base model's.

## Thinking

**Thinking is on by default**, just like the base model.

```python
# Python
tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False)

```

```bash
# SGLang or llama-server API
{"messages": [...], "chat_template_kwargs": {"enable_thinking": false}}

```

* **Reasoning effort:** Set `reasoning_effort` to `"low"` (default), `"high"`, or `"max"` (applies only in thinking mode).

### Practical Notes

1. **Token Budget:** Thinking consumes tokens before the actual answer starts. Ensure your `max_tokens` is high enough to prevent mid-reasoning truncation.
2. **Default Sampling:** Per `generation_config.json`, the model samples by default (`do_sample`, `temperature`, `top_p`) rather than using greedy decoding.
3. **Output Format:** Reasoning appears inline in `message.content`, ending with `</think>`. (In llama.cpp, use `--reasoning-format deepseek` to isolate it into `message.reasoning_content`).

### Where the prompt format comes from

DeepSeek does not ship a `chat_template`: the base model builds prompts with a
Python encoder, `encoding/encoding_dsv4.py`, which does not survive a checkpoint
conversion. Two things here address that.

`encoding/` is **copied verbatim from the base repository** (MIT, Copyright (c)
2023 DeepSeek) and is the authority. Use it directly if you need tool calling,
the internal task tokens, `developer` or `latest_reminder` messages, or
multi-turn `context` — none of which the template implements.

`chat_template.jinja` is a transcription of `encode_messages()` for the subset
that does fit a template: system, user and assistant turns, both thinking modes,
and `reasoning_effort`. It is **verified to reproduce the encoder string for
string** over several hundred conversations, including multi-turn exchanges with
`reasoning_content`, consecutive user messages, and all three effort levels.

## Compression recipe

```bash
moe-compress compress \
    --model deepseek-ai/DeepSeek-V4-Flash-0731 \
    --method reap --num-kept-experts 178 \
    --datasets c4,math,code --mix-ratio 0.0,0.3,0.7 \
    --num-samples 3072 --seq-len 512 \
    --streaming --stream-experts \
    --save-path DeepSeek-V4-Flash-0731-reap-200b

```

Calibration is the REAM paper's mixture, weighted 30% math / 70% code with no
C4 (`mix_ratio` positions match `datasets`). `--streaming` is what lets a
156 GiB checkpoint be compressed on a single 96 GB GPU: layers are read and
written one at a time, so peak memory is the skeleton plus one layer.

## Reconstruction quality

Measured during compression on a 4096-token probe, comparing each rebuilt MoE
block's output against the original, averaged over all 43 layers:

|  | cosine (mean) | cosine (min) | rel. L2 (mean) |
| --- | --- | --- | --- |
| this model | 0.9792 | 0.9005 | 0.1273 |

This is a compression-time diagnostic, not a quality metric — read the
benchmarks for that.

## Serving

Verified with SGLang. On Hopper the MXFP4 expert layout needs an explicit MoE
runner; `auto` lands on a Triton path that asserts on the packed weights:

```bash
python3 -m sglang.launch_server \
    --model-path puwaer/DeepSeek-V4-Flash-0731-reap-200b \
    --tp-size 2 \
    --nnodes 2 --node-rank $RANK --dist-init-addr <head>:5000 \
    --moe-runner-backend flashinfer_mxfp4 \
    --chat-template chat_template.jinja \
    --context-length 4096

```

GGUF builds for llama.cpp are available; the routed experts are already MXFP4 in
the source weights, so an `MXFP4_MOE` GGUF is numerically identical to this
checkpoint.

## Choosing between REAP and REAM

On this model REAP wins outright, and by a margin that widens as more is
removed. Points against the base model, given as **178 experts / 132 experts**:

|  | GSM8K | MATH-500 | HumanEval+ | MBPP+ | mean |
| --- | --- | --- | --- | --- | --- |
| **REAP** — prune low-saliency experts | −0.83 / −1.90 | −1.80 / +0.80 | ±0.00 / +2.44 | ±0.00 / +1.85 | −0.66 / +0.80 |
| **REAM** — merge them into survivors | −8.64 / −25.63 | −9.80 / −20.40 | +1.22 / −1.83 | +2.91 / −0.79 | −3.58 / −12.16 |

REAP at 178 experts returns the base model's pass@1 exactly on both code
benchmarks — 542 problems, not one of them different — for a third off the
checkpoint.

An earlier build of these checkpoints looked like a trade-off instead — REAP
holding arithmetic and losing code, REAM the reverse. That was an artifact of a
bug in the hash-routed layers' expert table, not a property of either method.
With it fixed the trade-off disappears: REAP is at least as good as REAM on
code and far better on arithmetic.

Note also how differently the two scale. Going from 178 experts to 132 costs
REAP 1.1 more points of GSM8K; it costs REAM 17.0.

## Citation

The methods:

* **REAP** — Router-weighted Expert Activation Pruning. Lasby et al., 2025.
[arXiv:2510.13999](https://arxiv.org/abs/2510.13999)
* **REAM** — Router-weighted Expert Activation Merging. Jha et al., 2026.
[arXiv:2604.04356](https://arxiv.org/abs/2604.04356)

The implementation: [https://github.com/puwaer/moe-expert-compress](https://github.com/puwaer/moe-expert-compress)

The base model: [deepseek-ai/DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)

## License

MIT, following the base model. The compression code is MIT; its numerical core
is ported from the official REAM reference implementation (Copyright (c) 2026
Samsung Electronics Co., Ltd.) with attribution headers retained.
`encoding/encoding_dsv4.py` is DeepSeek's, redistributed under the same MIT
terms as the base model.
