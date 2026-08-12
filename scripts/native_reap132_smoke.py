#!/usr/bin/env python3
"""Run a bounded native DeepSeek V4 forward with O_DIRECT checkpoint reads."""

from __future__ import annotations

import argparse
import json
import resource
from pathlib import Path

import torch
from transformers import AutoTokenizer
from transformers.masking_utils import create_sliding_window_causal_mask

from moe_compress.streaming import LayerStreamer, build_skeleton


def gib(value: int) -> float:
    return round(value / 2**30, 3)


def rss_gib() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--prompt", default="Hello")
    parser.add_argument("--max-input-tokens", type=int, default=512)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("native smoke requires CUDA")
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
            try:
                hidden_states = layer(
                    hidden_states,
                    position_embeddings=position_embeddings,
                    position_ids=position_ids,
                    attention_mask=causal_mask,
                    input_ids=ids,
                    past_key_values=None,
                )
            finally:
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

    report = {
        "schema": "native-reap132-direct-smoke-v1",
        "checkpoint": str(checkpoint),
        "io_backend": "direct",
        "input_tokens": [int(token) for token in input_ids[0].tolist()],
        "input_token_count": int(input_ids.shape[1]),
        "next_token": next_token,
        "next_token_text": tokenizer.decode([next_token]),
        "placements": placements,
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
