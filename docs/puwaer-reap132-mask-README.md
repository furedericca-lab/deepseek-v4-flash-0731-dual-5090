# puwaer REAP-132 plan extractor

目标：以 squanchyzx HERETIC v2 为母本，从以下两个公开 Hugging Face checkpoint
**精确映射** puwaer REAP-132 决策快照，并生成可交给 `moe-compress --plan` 使用的
JSON。默认 revision 已固定为 immutable commit；无法读取对应版本时脚本会失败。

- Base: `squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8`
  (`e7efd043c5e072da4d40f0f98ade554c5713bad9`, v2, 256 routed experts/layer)
- Pruned: `puwaer/DeepSeek-V4-Flash-0731-reap-150b` (132 routed experts/layer)

## 安装

在项目根目录执行：

```bash
uv sync
```

项目根目录的 `.venv` 是唯一运行环境；不要使用 `/home/build/torch/.venv`。

## 生成 plan

```bash
uv run python scripts/extract_puwaer_plan.py
```

需要固定远端版本时，显式传入 commit SHA：

```bash
uv run python scripts/extract_puwaer_plan.py \
  --base-revision <base-commit-sha> \
  --pruned-revision <puwaer-commit-sha> \
  -o squanchyzx-puwaer-reap132-mask.json
```

如果 Hugging Face 要求 token：

```bash
export HF_TOKEN='hf_...'
uv run python scripts/extract_puwaer_plan.py
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

该 artifact 复用 puwaer 已发布的 survivor 集合。43 层 router row 均已证明能从
squanchyzx v2 checkpoint byte-exact 映射到 puwaer REAP-150B；它不是在
squanchyzx v2 hidden states 上重新运行 calibration 得到的新 saliency 排名。

## 下载原始 checkpoint

`--streaming` 的 `LayerStreamer` 需要本地 Transformers checkpoint 目录，不能把
Hugging Face repo ID 当作 `--model` 传入。先固定 commit SHA 下载完整 snapshot 到
NVMe（实际裁剪本来就需要完整原始权重）：

```bash
uv run hf download squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8 \
  --revision e7efd043c5e072da4d40f0f98ade554c5713bad9 \
  --local-dir /data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8
```

下载完成后，为 checkpoint 写入 provenance manifest。脚本会先从固定 commit
读取远端 `config.json` 和 `model.safetensors.index.json`，只有本地 SHA256 与远端
完全一致时才会写文件：

```bash
uv run python scripts/write_checkpoint_source_manifest.py \
  /data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8 \
  --repo squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8 \
  --revision e7efd043c5e072da4d40f0f98ade554c5713bad9
```

生成的 `.checkpoint-source.json` 格式如下：

```json
{
  "repo": "squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8",
  "revision": "<base_revision_sha>",
  "config_file": "config.json",
  "config_sha256": "...",
  "index_file": "model.safetensors.index.json",
  "index_sha256": "..."
}
```

## 应用 plan

`--plan` 路径跳过 calibration 和 saliency 计算，复用现有 DeepSeek-V4 adapter、
`apply_keep()` 和 streaming writer：

```bash
uv run moe-compress compress \
  --model /data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8 \
  --plan squanchyzx-puwaer-reap132-mask.json \
  --streaming \
  --save-path output/DeepSeek-V4-Flash-0731-reap132
```

对 `puwaer-reap-mask-v1`，`moe-compress` 会自动读取 checkpoint 根目录的
`.checkpoint-source.json`，要求其中的 repo/revision 与 plan 一致，并在加载模型前
重新计算 config/index SHA256。缺 manifest、revision 不符或元数据被替换都会拒绝。
`--source-revision` 仍可作为额外的兼容性断言，但不再作为 provenance 证据，也不必
出现在正常命令中。

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
