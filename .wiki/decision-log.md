---
title: Decision Log
type: decision-log
status: current
generated_by: /home/build/.codex/skills/wiki-note/scripts/wiki_note.py
updated: 2026-08-12T18:34:14Z
---



















































































# Decision Log

<!-- BEGIN AUTO -->
- Last rebuilt: 2026-08-12T18:34:14Z
- Decision count: 2

## Draft Decisions

- None.

## Accepted Decisions

- 2026-08-12 | [Derive K96 only as a REAP132 subset](decisions/reap96-k132-subset-consensus.md) | scope: heretic-v2-reap96-consensus
- 2026-08-11 | [Dual 5090 Q2_K full-GPU with RAM F16 KV](decisions/dual-5090-q2-k-full-gpu-with-ram-f16-kv.md) | scope: deepseek-v4-flash-0731-dual-5090

## Current Decisions

- None.

## Superseded Decisions

- None.

## Stale Decisions

- None.
<!-- END AUTO -->

## Manual Review Notes

Keep this section concise. The script preserves text outside the auto block.

- 2026-08-12: Retain the corrected MXFP4 GGUF as an unpromoted candidate. Its
  sampled routed-expert, nonexpert, and FP8-backbone payload contracts pass;
  an exact native/GGUF 11-token prompt has the same first greedy token. Finish
  multi-token behavior quality before promotion.
