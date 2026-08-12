---
license: mit
language:
- en
- zh
base_model:
- deepseek-ai/DeepSeek-V4-Flash-0731
tags:
- deepseek-v4
- mixture-of-experts
- reap
- pruning
- mxfp4
- dgx-spark
pipeline_tag: text-generation
---

# DeepSeek-V4-Flash-0731 REAP K160

This is an experimental, structurally validated REAP expert-pruned checkpoint of [`deepseek-ai/DeepSeek-V4-Flash-0731`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731). It keeps 160 of 256 routed experts in every MoE scope while preserving top-6 routing, shared experts, attention, embeddings, output head, mHC, compressor, and indexer tensors.

The checkpoint is intended for memory-constrained DeepSeek-V4 research and inference. It is not an official DeepSeek release, and pruning can reduce quality. Evaluate it on your own coding, reasoning, tool-use, and long-context workloads before production use.

## What was pruned

| Item | Value |
|---|---:|
| Source revision | `9e165c30e2704aec5d9d593cce3eebd58bbef1cb` |
| Original routed experts | 256 per MoE scope |
| Retained routed experts | 160 per MoE scope |
| Routed experts removed | 37.5% |
| Router top-k | 6, unchanged |
| Backbone MoE layers | 43 |
| DSpark MTP blocks | 3, mapped to backbone layers 40, 41, and 42 |
| Safetensors shards | 48 |
| Tensor payload | 107,803,320,952 bytes |

Each retained expert is physically compacted into a contiguous 160-expert tensor. Learned router weights and biases are sliced to the same retained IDs. For the first three hash-routed layers, token-to-expert tables are remapped to the nearest retained current-revision router row by cosine similarity.

## Observation provenance

This release transfers expert rankings from a prior DeepSeek-V4-Flash REAP observation run; it is **not** a fresh observation of the `0731` weights.

- Observation dataset: [`0xSero/deepseek-v4-flash-reap-observations-v2`](https://huggingface.co/datasets/0xSero/deepseek-v4-flash-reap-observations-v2)
- Snapshot: `partial-v2-21289`
- Rows used: 21,289
- Prior source revision: `deepseek-ai/DeepSeek-V4-Flash@60d8d70770c6776ff598c94bb586a859a38244f1`
- Coverage: coding, math, science, tool calling, and agentic tool trajectories; every expert was observed

Before transferring the ranking, all 43 old router matrices were aligned against the `0731` checkpoint. Every old expert row had the same expert ID as its nearest current-revision row. The weakest layer-mean same-index cosine was `0.9923683405`; the weakest individual row was `0.9460793734`. All three hash-routing tables were bit-identical. These results support identity transfer, but they do not make it equivalent to a fresh `0731` observation.

## Validation

Structural validation passed with:

- 48/48 readable safetensors shards
- 45,821 tensors and exact index coverage
- 46/46 MoE scopes at K160
- 92 exact router-tensor comparisons
- 552 exact retained-expert old-to-new comparisons
- 12 exact protected-tensor comparisons
- zero structural failures

The machine-readable build and validation records are included as `REAP_MANIFEST.json`, `reap_plan.json`, and files under `validation/`.

Runtime validation was performed on one NVIDIA DGX Spark / GB10 using the Anemll DeepSeek-V4 vLLM preview image, with CUDA graphs enabled. The bundled CUDA `sqrtsoftplus` router supports only a fixed set of expert counts, so K160 requires routing unsupported expert counts through vLLM's included pure-Torch router fallback. Expert execution remains on the B12X MXFP4 MoE backend.

The backbone-only API smoke passed at 8,192-token configured context: `/v1/models` became ready, the exact-answer probe returned `PRUNED_OK` in 6.19 seconds, and the coding probe returned `return a + b` in 1.60 seconds. Both stopped normally. The requests intentionally had no output-token cap. DSpark MTP was not enabled for this smoke.

## Serving notes

Use a DeepSeek-V4-capable runtime. Generic Transformers releases may not understand the model's custom MXFP4, sparse-attention, tokenizer, and DSpark MTP components. The exact runtime smoke configuration and result are recorded under `validation/`.

For the tested vLLM preview lineage, patch `vllm_topk_softplus_sqrt` so expert counts outside the fused kernel's supported set `(16, 32, 64, 128, 192, 256, 320, 384, 512)` call the adjacent `_topk_softplus_sqrt_torch` implementation. Do not change the checkpoint back to 256 experts: that would invalidate the tensors and routing map.

## Limitations

- Expert importance came from a closely aligned earlier checkpoint, not a fresh `0731` observation.
- Structural and smoke validation do not establish benchmark parity with the unpruned model.
- This is an aggressive 37.5% routed-expert prune. Coding preservation is plausible because coding and agentic data were included, but must be measured rather than assumed.
- The included three DSpark MTP blocks were pruned consistently; MTP runtime compatibility should be validated separately from backbone generation.

## Credits and license

Thanks to [DeepSeek](https://huggingface.co/deepseek-ai) for the base model, [Cerebras Research](https://github.com/CerebrasResearch/reap) for REAP, the [vLLM](https://github.com/vllm-project/vllm) contributors, and the Anemll/DGX Spark community for the DeepSeek-V4 Spark runtime work.

This derivative follows the source repository's MIT license. See `LICENSE` for the full text.
