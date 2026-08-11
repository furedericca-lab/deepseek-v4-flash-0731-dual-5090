# puwaer REAP-132 plan extractor

目标：从以下两个公开 Hugging Face checkpoint **精确提取** puwaer REAP-132 决策快照，并生成可交给 `moe-compress --plan` 使用的 JSON。提取结果会记录 Hugging Face resolved commit；无法解析不可变 revision 时脚本会失败，不会生成未锁定来源的 plan。

- Base: `deepseek-ai/DeepSeek-V4-Flash-0731` (256 routed experts/layer)
- Pruned: `puwaer/DeepSeek-V4-Flash-0731-reap-150b` (132 routed experts/layer)

## 安装

在项目根目录执行：

```bash
uv sync
```

项目根目录的 `.venv` 是唯一运行环境；不要使用 `/home/build/torch/.venv`。

## 生成 plan

```bash
uv run python scripts/extract_puwaer_plan.py -o puwaer-reap132-mask.json
```

需要固定远端版本时，显式传入 commit SHA：

```bash
uv run python scripts/extract_puwaer_plan.py \
  --base-revision <base-commit-sha> \
  --pruned-revision <puwaer-commit-sha> \
  -o puwaer-reap132-mask.json
```

如果 Hugging Face 要求 token：

```bash
export HF_TOKEN='hf_...'
uv run python scripts/extract_puwaer_plan.py -o puwaer-reap132-mask.json
```

## Plan 格式

```json
{
  "schema": "puwaer-reap-mask-v1",
  "base_num_routed_experts": 256,
  "kept_num_routed_experts": 132,
  "num_hidden_layers": 43,
  "num_hash_layers": 3,
  "base_revision_sha": "...",
  "pruned_revision_sha": "...",
  "layers": {
    "0": {
      "kept_experts": ["132 个原始 expert ID"],
      "mapping_evidence": "gate.weight-row-sha256-exact"
    }
  },
  "hash_routing": {
    "0": {
      "tensor_name": "layers.0.ffn.gate.tid2eid",
      "dtype": "...",
      "shape": ["..."],
      "encoding": "zlib+base64",
      "sha256": "...",
      "data": "..."
    }
  }
}
```

`layers[N].kept_experts[i]` 表示：REAP 后的 `new expert i` 对应原始模型的
`expert kept_experts[i]`。列表按原始 ID 升序排列。

提取器对 router 行执行 byte-exact 匹配，不使用浮点近似；Layer 3–42 优先
比较 `gate.bias`，有歧义时回退到完整 `gate.weight` 行。前三层的最终
`tid2eid` 直接从 puwaer checkpoint 提取并压缩保存，不重新推算 replacement。

## 下载原始 checkpoint

`--streaming` 的 `LayerStreamer` 需要本地 Transformers checkpoint 目录，不能把
Hugging Face repo ID 当作 `--model` 传入。先固定 commit SHA 下载完整 snapshot 到
NVMe（实际裁剪本来就需要完整原始权重）：

```bash
uv run hf download deepseek-ai/DeepSeek-V4-Flash-0731 \
  --revision <base_revision_sha> \
  --local-dir /data/linux-fast/models/DeepSeek-V4-Flash-0731-base
```

## 应用 plan

`--plan` 路径跳过 calibration 和 saliency 计算，复用现有 DeepSeek-V4 adapter、
`apply_keep()` 和 streaming writer：

```bash
uv run moe-compress compress \
  --model /data/linux-fast/models/DeepSeek-V4-Flash-0731-base \
  --plan puwaer-reap132-mask.json \
  --streaming \
  --save-path output/DeepSeek-V4-Flash-0731-reap132
```

模型 surgery 由 `DeepseekV4Adapter.apply_keep()` 负责，包括 FP4 expert tensors、
router rows 和 hash-layer `tid2eid`。

## 安全与流量

脚本通过 `HfFileSystem` 使用 Hugging Face 官方 Xet/Range 传输，单次读取限制
为 256 MiB，不下载完整模型或完整 shard。实际流量以输出的
`range_mib_downloaded` 为准。

快速检查 survivor ID（不嵌入 `tid2eid`）：

```bash
uv run python scripts/extract_puwaer_plan.py \
  --no-tid2eid -o puwaer-reap132-mask-lite.json
```
