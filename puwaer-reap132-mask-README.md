# puwaer REAP-132 mask extractor

目标：从以下两个公开 Hugging Face checkpoint **精确反推** puwaer REAP-132 每层保留的原始 expert ID，并把前三个 hash-routing 层的最终 `tid2eid` 一起写入一个可复用 JSON。提取结果会记录 Hugging Face resolved commit；无法解析不可变 revision 时脚本会失败，不会生成未锁定来源的 mask。

- Base: `deepseek-ai/DeepSeek-V4-Flash-0731` (256 routed experts/layer)
- Pruned: `puwaer/DeepSeek-V4-Flash-0731-reap-150b` (132 routed experts/layer)

## 安装

```bash
uv sync
```

## 生成完整 mask

```bash
uv run python scripts/extract_puwaer_reap132_mask.py -o puwaer-reap132-mask.json
```

如果 Hugging Face 要求 token：

```bash
export HF_TOKEN='hf_...'
uv run python scripts/extract_puwaer_reap132_mask.py -o puwaer-reap132-mask.json
```

## 输出内容

```json
{
  "schema": "puwaer-reap-mask-v1",
  "base_num_routed_experts": 256,
  "kept_num_routed_experts": 132,
  "num_hidden_layers": 43,
  "num_hash_layers": 3,
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

`layers[N].kept_experts[i]` 的含义是：

> REAP 后的 `new expert i` = 原始 256-expert 模型中的 `expert kept_experts[i]`。

因此该列表本身就是每层要保留的原始 expert ID，且按原始 ID 升序排列。

## 为什么是精确反推，不是相似度猜测

puwaer 的 DeepSeek-V4 REAP pruning 对 expert tensors 和 router rows 都是按 `keep_idx` 直接切片；REAP pruning 本身不重新量化存活 expert。提取器用 byte-exact 比较恢复原始行号，不做浮点近似比较。

- Layer 0–2：比较 `gate.weight` 的每个完整 router row。
- Layer 3–42：先比较很小的 `gate.bias`；只要存在重复/歧义，就自动回退到完整 `gate.weight` row 比较。
- Layer 0–2 的 `tid2eid`：直接从 puwaer 最终 checkpoint 读取最终表，zlib 压缩并 base64 内嵌到 JSON。因此以后复现时不需要重新跑 calibration，也不需要重新猜 dropped expert 的 replacement。

## 安全机制

脚本通过 `HfFileSystem` 使用 Hugging Face 官方 Xet/Range 传输，并限制单次读取为 256 MiB；不会下载完整模型或完整 shard。

脚本不会下载完整模型或完整 shard，但完整模式仍会读取所有 router 行以及前三层的 `tid2eid`，实际流量取决于 checkpoint 的 tensor 布局，最终以输出的 `range_mib_downloaded` 为准。

## 快速小测试（不嵌入 tid2eid）

如果只想先确认 43 层 survivor ID 能否正常提取：

```bash
uv run python scripts/extract_puwaer_reap132_mask.py --no-tid2eid -o puwaer-reap132-mask-lite.json
```

完整复现请使用默认模式，保留 `tid2eid`。
