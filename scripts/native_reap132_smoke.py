#!/usr/bin/env python3
"""Run a bounded native DeepSeek V4 forward with O_DIRECT checkpoint reads."""

from __future__ import annotations

import argparse
import json
import os
import resource
from pathlib import Path
from typing import Any

import torch
from torch.nn import functional as F
from transformers import AutoTokenizer
from transformers.masking_utils import create_sliding_window_causal_mask
from transformers.models.deepseek_v4 import modeling_deepseek_v4 as deepseek_v4

from moe_compress.streaming import LayerStreamer, build_skeleton


def gib(value: int) -> float:
    return round(value / 2**30, 3)


def rss_gib() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3)


def tensor_metadata(
    tensor: torch.Tensor,
    *,
    trace_values: bool = False,
    mask_semantics: bool = False,
) -> dict[str, Any]:
    pointer = tensor.data_ptr()
    metadata = {
        "shape": list(tensor.shape),
        "dtype": str(tensor.dtype),
        "stride": list(tensor.stride()),
        "storage_offset": tensor.storage_offset(),
        "is_contiguous": tensor.is_contiguous(),
        "device": str(tensor.device),
        "data_ptr": pointer,
        "data_ptr_mod_16": pointer % 16,
        "data_ptr_mod_128": pointer % 128,
        "data_ptr_mod_256": pointer % 256,
    }
    if not trace_values:
        return metadata

    if mask_semantics:
        metadata["nan_count"] = int(torch.isnan(tensor).sum().item())
        metadata["positive_infinity_count"] = int(torch.isposinf(tensor).sum().item())
        metadata["negative_infinity_count"] = int(torch.isneginf(tensor).sum().item())
    else:
        metadata["finite"] = bool(torch.isfinite(tensor).all().item())
        metadata["min"] = float(tensor.min().item())
        metadata["max"] = float(tensor.max().item())
    return metadata


def append_trace(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def install_attention_trace(
    layer_index: int,
    trace_path: Path,
    *,
    trace_values: bool = False,
    qk_layout: str = "original",
) -> None:
    original = deepseek_v4.eager_attention_forward

    def traced_attention(
        module,
        query,
        key,
        value,
        attention_mask,
        scaling,
        dropout=0.0,
        **kwargs,
    ):
        if module.layer_idx != layer_index:
            return original(
                module,
                query,
                key,
                value,
                attention_mask,
                scaling,
                dropout=dropout,
                **kwargs,
            )

        key_states = deepseek_v4.repeat_kv(key, module.num_key_value_groups)
        value_states = deepseek_v4.repeat_kv(value, module.num_key_value_groups)
        key_transposed = key_states.transpose(2, 3)
        qk_key_operand = (
            key_transposed.contiguous()
            if qk_layout == "key-transposed-contiguous"
            else key_transposed
        )
        torch.cuda.synchronize(query.device)
        append_trace(
            trace_path,
            {
                "event": "before_qk_matmul",
                "layer": layer_index,
                "trace_values": trace_values,
                "qk_layout": qk_layout,
                "query": tensor_metadata(query, trace_values=trace_values),
                "key_states_original": tensor_metadata(key_states, trace_values=trace_values),
                "key_states_transposed": tensor_metadata(
                    key_transposed, trace_values=trace_values
                ),
                "qk_key_operand": tensor_metadata(
                    qk_key_operand, trace_values=trace_values
                ),
                "value_states": tensor_metadata(value_states, trace_values=trace_values),
                "attention_mask": (
                    tensor_metadata(
                        attention_mask,
                        trace_values=trace_values,
                        mask_semantics=True,
                    )
                    if isinstance(attention_mask, torch.Tensor)
                    else None
                ),
            },
        )
        torch.cuda.synchronize(query.device)
        attn_weights = torch.matmul(query, qk_key_operand) * scaling
        torch.cuda.synchronize(query.device)
        append_trace(
            trace_path,
            {
                "event": "after_qk_matmul",
                "layer": layer_index,
                "trace_values": trace_values,
                "attn_weights": tensor_metadata(attn_weights, trace_values=trace_values),
            },
        )
        if attention_mask is not None:
            attn_weights = attn_weights + attention_mask
        sinks = module.sinks.reshape(1, -1, 1, 1).expand(
            query.shape[0], -1, query.shape[-2], -1
        )
        combined_logits = torch.cat([attn_weights, sinks], dim=-1)
        combined_logits = combined_logits - combined_logits.max(dim=-1, keepdim=True).values
        probs = F.softmax(combined_logits, dim=-1, dtype=combined_logits.dtype)
        scores = probs[..., :-1]
        attn_weights = F.dropout(scores, p=dropout, training=module.training).to(
            value_states.dtype
        )
        torch.cuda.synchronize(query.device)
        append_trace(
            trace_path,
            {
                "event": "before_av_matmul",
                "layer": layer_index,
                "trace_values": trace_values,
                "attn_weights": tensor_metadata(attn_weights, trace_values=trace_values),
                "value_states": tensor_metadata(value_states, trace_values=trace_values),
            },
        )
        torch.cuda.synchronize(query.device)
        attn_output = torch.matmul(attn_weights, value_states)
        torch.cuda.synchronize(query.device)
        append_trace(
            trace_path,
            {
                "event": "after_av_matmul",
                "layer": layer_index,
                "trace_values": trace_values,
                "attn_output": tensor_metadata(attn_output, trace_values=trace_values),
            },
        )
        return attn_output.transpose(1, 2).contiguous(), attn_weights

    deepseek_v4.eager_attention_forward = traced_attention


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--prompt", default="Hello")
    parser.add_argument("--max-input-tokens", type=int, default=512)
    parser.add_argument("--require-input-tokens", type=int)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trace-attention-layer", type=int)
    parser.add_argument("--attention-trace", type=Path)
    parser.add_argument(
        "--trace-values",
        action="store_true",
        help="include CUDA value reductions in attention traces; disabled by default",
    )
    parser.add_argument(
        "--qk-layout",
        choices=("original", "key-transposed-contiguous"),
        default="original",
        help="controlled Layer 2 QK key-layout diagnostic",
    )
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("native smoke requires CUDA")
    cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
    if cuda_visible_devices != "0":
        raise RuntimeError("native smoke requires CUDA_VISIBLE_DEVICES=0")
    if torch.cuda.device_count() != 1:
        raise RuntimeError(
            "native smoke requires exactly one visible CUDA device, got "
            f"{torch.cuda.device_count()}"
        )
    device = torch.device(args.device)
    if device.type != "cuda" or device.index is None or device.index >= torch.cuda.device_count():
        raise ValueError(f"invalid CUDA smoke device: {args.device}")

    checkpoint = args.checkpoint.resolve()
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
    encoded = tokenizer(args.prompt, return_tensors="pt", add_special_tokens=False)
    if args.max_input_tokens < 1:
        raise ValueError("--max-input-tokens must be positive")
    input_ids = encoded.input_ids[:, : args.max_input_tokens]
    if input_ids.numel() < 1:
        raise ValueError("the bounded smoke requires at least one input token")
    if args.require_input_tokens is not None and input_ids.shape[1] < args.require_input_tokens:
        repeats = (args.require_input_tokens + input_ids.shape[1] - 1) // input_ids.shape[1]
        input_ids = input_ids.repeat(1, repeats)[:, : args.require_input_tokens]
    if (
        args.require_input_tokens is not None
        and input_ids.shape[1] != args.require_input_tokens
    ):
        raise ValueError(
            f"expected {args.require_input_tokens} input tokens, got {input_ids.shape[1]}"
        )

    torch.cuda.set_device(device)
    torch.cuda.reset_peak_memory_stats(device)
    if (args.trace_attention_layer is None) != (args.attention_trace is None):
        raise ValueError("attention tracing requires both trace arguments")
    if args.trace_values and args.trace_attention_layer is None:
        raise ValueError("--trace-values requires attention tracing")
    if args.qk_layout != "original" and args.trace_attention_layer is None:
        raise ValueError("non-original --qk-layout requires attention tracing")
    if args.trace_attention_layer is not None:
        install_attention_trace(
            args.trace_attention_layer,
            args.attention_trace.resolve(),
            trace_values=args.trace_values,
            qk_layout=args.qk_layout,
        )

    skeleton = build_skeleton(str(checkpoint), device="cpu")
    streamer = LayerStreamer(
        skeleton,
        device="cpu",
        keep_shared_on=str(device),
        io_backend="direct",
    )
    streamer.load_shared()

    model = skeleton.model
    placements = {str(index): str(device) for index in streamer.layer_indices}
    with torch.inference_mode():
        current = device
        ids = input_ids.to(current)
        inputs_embeds = model.model.embed_tokens(ids)
        position_ids = torch.arange(input_ids.shape[1], dtype=torch.long, device=current).unsqueeze(0)
        causal_mask = create_sliding_window_causal_mask(
            config=model.config,
            inputs_embeds=inputs_embeds,
            attention_mask=None,
            past_key_values=None,
            position_ids=position_ids,
        )
        hidden_states = inputs_embeds.unsqueeze(2).expand(
            -1, -1, model.config.hc_mult, -1
        ).contiguous()
        position_embeddings = {
            "main": model.model.rotary_emb(inputs_embeds, position_ids=position_ids, layer_type="main"),
            "compress": model.model.rotary_emb(
                inputs_embeds, position_ids=position_ids, layer_type="compress"
            ),
        }

        for layer_index in streamer.layer_indices:
            target = torch.device(placements[str(layer_index)])
            if target != current:
                hidden_states = hidden_states.to(target)
                ids = ids.to(target)
                position_ids = position_ids.to(target)
                causal_mask = causal_mask.to(target) if causal_mask is not None else None
                position_embeddings = {
                    key: tuple(item.to(target) for item in value)
                    for key, value in position_embeddings.items()
                }
                current = target
            layer = streamer.load_layer(layer_index, device=str(target))
            hidden_states = layer(
                hidden_states,
                position_embeddings=position_embeddings,
                position_ids=position_ids,
                attention_mask=causal_mask,
                input_ids=ids,
                past_key_values=None,
            )
            torch.cuda.synchronize(target)
            streamer.free_layer(layer_index)
            if not torch.isfinite(hidden_states).all():
                raise ValueError(f"non-finite hidden state after layer {layer_index}")
            print(
                f"forward layer {layer_index:02d} on {current} "
                f"rss_peak={rss_gib()} GiB",
                flush=True,
            )

        hidden_states = hidden_states.to(device)
        hidden_states = model.model.norm(model.model.hc_head(hidden_states))
        logits = model.lm_head(hidden_states[:, -1:, :])
        if not torch.isfinite(logits).all():
            raise ValueError("non-finite final logits")
        next_token = int(torch.argmax(logits[0, -1]).item())
        torch.cuda.synchronize(device)

    report = {
        "schema": "native-reap132-direct-prefill-smoke-v2",
        "checkpoint": str(checkpoint),
        "io_backend": "direct",
        "cuda_visible_devices": cuda_visible_devices,
        "cuda_launch_blocking": os.environ.get("CUDA_LAUNCH_BLOCKING"),
        "trace_attention_layer": args.trace_attention_layer,
        "trace_values": args.trace_values,
        "qk_layout": args.qk_layout,
        "attention_trace": str(args.attention_trace.resolve()) if args.attention_trace else None,
        "torch_cuda_device_count": torch.cuda.device_count(),
        "device": str(device),
        "device_name": torch.cuda.get_device_name(device),
        "device_uuid": str(torch.cuda.get_device_properties(device).uuid),
        "input_tokens": [int(token) for token in input_ids[0].tolist()],
        "input_token_count": int(input_ids.shape[1]),
        "next_token": next_token,
        "next_token_text": tokenizer.decode([next_token]),
        "placements": placements,
        "layers_completed": len(streamer.layer_indices),
        "rss_peak_gib": rss_gib(),
        "gpu_peak_gib": {str(device.index): gib(torch.cuda.max_memory_allocated(device))},
        "finite_logits": True,
        "status": "PASS",
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
