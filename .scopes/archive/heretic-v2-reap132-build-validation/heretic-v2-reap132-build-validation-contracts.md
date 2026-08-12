---
description: API and schema contracts for heretic-v2-reap132-build-validation.
---

# heretic-v2-reap132-build-validation Contracts

## API Contracts

This scope adds no public network API. Runtime smoke uses the existing local
OpenAI-compatible endpoint at `http://127.0.0.1:8000/v1` only after native and
GGUF structural gates pass.

## Shared Types / Schemas

### Frozen plan identity

```json
{
  "path": "squanchyzx-puwaer-reap132-mask.json",
  "file_sha256": "b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04",
  "logical_sha256": "082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17",
  "base_repo": "squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8",
  "base_revision": "e7efd043c5e072da4d40f0f98ade554c5713bad9",
  "pruned_repo": "puwaer/DeepSeek-V4-Flash-0731-reap-150b",
  "pruned_revision": "868fa38e2f2964699ad065dc8d9382c136cc60b8",
  "layers": 43,
  "experts_per_layer": 132,
  "hash_tables": 3
}
```

### Checkpoint content manifest

```json
{
  "schema": "checkpoint-content-manifest-v1",
  "artifact_role": "source|native-reap132",
  "files": [
    {"path": "relative/path", "size": 0, "sha256": "64 lowercase hex"}
  ],
  "manifest_sha256": "SHA256 of canonical JSON without this field"
}
```

Files are sorted by relative POSIX path. Canonical JSON uses UTF-8,
`sort_keys=true`, and separators `(',', ':')`. The manifest must not include
itself in `files`. Transfer/cache directories `.cache/` and `.hfd/`, repository
metadata `.git/`, and `__pycache__/` are excluded. A partial or temporary file
outside those directories is an error, not an excluded artifact.

### Post-prune verification report

```json
{
  "schema": "heretic-v2-reap132-post-prune-v1",
  "plan": {"file_sha256": "...", "logical_sha256": "..."},
  "source_manifest_sha256": "...",
  "output_manifest_sha256": "...",
  "summary": {
    "layers": "PASS",
    "router": "PASS",
    "experts": "PASS",
    "scales": "PASS",
    "shared_experts": "PASS",
    "tid2eid": "PASS",
    "heretic_overlay": "PASS",
    "mtp_dspark_absent": "PASS",
    "dangling_expert_ids": "PASS"
  },
  "layer_results": [],
  "failures": []
}
```

The report is successful only when all summary fields are `PASS`, exactly 43
layer results exist, and `failures` is empty.

## Event and Streaming Contracts

- Pruning mode is `--plan --streaming`; calibration dataset access and saliency
  collection are forbidden for this build.
- The source directory is read-only from the compressor's perspective.
- Output shards may appear incrementally but the artifact is not valid until the
  writer finalizes its index/config and the process exits zero.
- Verification reads shards sequentially and emits the report only after all
  checks finish; failed runs may write a separate log but not a PASS report.

## Error Model

| Condition | Required behavior |
|---|---|
| Plan full/logical SHA mismatch | Stop before opening model shards |
| Source repo/revision/config/index mismatch | Stop before pruning |
| Missing or partial shard | Stop and preserve download state for resume |
| Calibration/saliency path invoked | Mark build invalid and stop |
| Unknown output tensor name | Verification failure; do not ignore |
| Weight/scale/router/shared/overlay mismatch | Verification failure; quarantine output |
| Any MTP/DSpark tensor remains in output | Verification failure; quarantine output |
| `tid2eid` mismatch, duplicate, or ID >=132 | Verification failure |
| Native smoke NaN/routing/repetition failure | Block GGUF conversion |
| GGUF expert type is not intended MXFP4 representation | Do not freeze as golden baseline |

## Validation and Compatibility Rules

- Output `config.json` must declare `model_type=deepseek_v4`,
  `n_routed_experts=132`, `num_hidden_layers=43`, `num_hash_layers=3`, and
  `num_experts_per_tok=6`.
- For each layer, output expert `new_id` must equal source expert
  `plan.layers[layer].kept_experts[new_id]` for all packed weights and scales.
- Router output row `new_id` must equal the corresponding source row.
- Shared expert tensors are source-identical.
- Backbone layers 10-42 `attn.wo_b.weight` and `.scale` are source-identical,
  preserving the HERETIC v2 overlay.
- All 4,705 source MTP/DSpark tensors are absent from output.
- Expected tensor count is derived from source classification and the frozen
  plan. For the current identities it is `40,325 - 4,705 = 35,620`; the verifier
  must not rely only on the hard-coded result.
- Hash layers 0-2 `tid2eid` are byte-identical to the frozen plan blobs.
- No router or routing tensor may contain an expert ID outside `0..131`.
- Plan, source, native output, and GGUF identities are reported separately.

## Requirement Boundary Notes

- The plan JSON is not rewritten, normalized, or regenerated in this scope.
- Fresh REAP calibration is explicitly rejected.
- Structural deletion stops at routed expert REAP132 plus MTP/DSpark removal.
  Shared experts, router, `tid2eid`, Lightning Indexer, CSA/HCA, mHC, attention,
  embeddings, LM head, norm, RoPE, and sink tensors remain part of the model.
- Further capacity reduction uses runtime placement or a separately approved
  mixed-quantization design, not additional module deletion in this scope.
- Native checkpoint verification cannot be replaced by GGUF runtime success.
- Further IQ3/Q2 quantization begins only in a new scope or explicit extension
  after the golden GGUF baseline passes.
- Deterministic pruning must execute root build commit
  `8071c7c64101f16ea0959881b86d180862bd514b` with vendor build commit
  `56137d189fd36c1c8881ca99233614b177442425`.
