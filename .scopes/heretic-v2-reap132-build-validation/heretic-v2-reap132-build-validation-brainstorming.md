---
description: Brainstorming and decision framing for heretic-v2-reap132-build-validation.
---

# heretic-v2-reap132-build-validation Brainstorming

## Problem

Build a native Hugging Face checkpoint that combines the immutable squanchyzx
HERETIC v2 attention overlay with puwaer's published REAP-132 survivor set,
then prove the output before any GGUF conversion or further quantization.

## Scope

- Freeze `squanchyzx-puwaer-reap132-mask.json` as an immutable build input.
- Apply the existing plan with streaming deterministic pruning; do not run
  calibration or recompute saliency.
- Produce byte-level post-prune evidence and a deterministic output manifest.
- Run native HF smoke tests before creating the first MXFP4-preserving GGUF.
- Validate the GGUF on dual RTX 5090 and run a controlled puwaer-versus-HERETIC
  A/B with the same survivor set.

## Constraints

- Base repo: `squanchyzx/DeepSeek-V4-Flash-0731-HERETIC-Abliterated-FP8`.
- Base commit: `e7efd043c5e072da4d40f0f98ade554c5713bad9` (HERETIC v2).
- Plan file SHA256:
  `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`.
- Plan logical SHA256:
  `082e51d268052f8b26be63d7fe6edc7881c385644e12f6ee5dc763719d0f7b17`.
- The plan has 43/43 exact router matches and three exact `tid2eid` blobs.
- Source and output checkpoints live under `/data/linux-fast/models/`, never in
  git. The project-local `.venv` is the only Python runtime.
- The host has about 46 GiB RAM; streaming is mandatory for pruning.
- Mask logic and saliency are frozen. A fresh REAP calibration is out of scope.

## Options

1. Apply the existing plan and verify every retained tensor.
   - Preserves the controlled A/B and avoids calibration drift.
2. Re-run REAP calibration on HERETIC v2.
   - Could optimize for altered hidden states, but changes the expert set and
     defeats the current controlled comparison.
3. Convert to GGUF before native verification.
   - Saves one validation step but mixes pruning defects with conversion defects.
4. Verify only shapes/configuration.
   - Fast but insufficient for the required FP4 and overlay provenance.

## Decision Summary

| Decision | Options Considered | Rationale | Research Note Link |
|---|---|---|---|
| Expert selection | Existing puwaer plan vs fresh calibration | Preserve the proven 43-layer mapping and controlled A/B | [Research notes](heretic-v2-reap132-build-validation-implementation-research-notes.md#selected-design) |
| Validation depth | Geometry-only vs byte-exact | Native FP4 preservation is a core requirement | [Research notes](heretic-v2-reap132-build-validation-implementation-research-notes.md#validation-plan) |
| Conversion order | GGUF first vs native HF first | Isolate pruning failures before conversion | [Milestones](heretic-v2-reap132-build-validation-scope-milestones.md#milestones) |
| First GGUF | MXFP4 baseline vs IQ3/Q2 | Keep routed experts closest to native bytes | [Technical docs](heretic-v2-reap132-build-validation-technical-documentation.md#major-decisions-and-trade-offs) |

## Decision

Use deterministic `--plan --streaming` pruning, generate an independently
verifiable native output, run native smoke tests, and only then convert the
verified checkpoint to a golden MXFP4-preserving GGUF. Further quantization is
deferred until that baseline passes dual-5090 runtime and controlled A/B gates.

## Risks

- The current extractor and compressor changes are uncommitted, so an extractor
  commit cannot yet be honestly recorded in the frozen build record.
- A 156 GiB-class source download may be incomplete or corrupted despite a
  successful process exit; file inventory and content manifests are required.
- A shape-correct output can still contain reordered expert bytes, wrong scales,
  altered shared experts, lost HERETIC tensors, or invalid hash routing.
- Native HF smoke may expose runtime support or memory limits unrelated to the
  deterministic surgery.
- GGUF conversion can change layout or precision and must not be used as proof
  that the native checkpoint was correct.

## Open Questions

- Phase 1 must record the first commit that actually contains the frozen
  extractor, plan-mode verifier, and associated tests; current root HEAD
  `f1f31e4e6dc12abc965c937ede7a51269996d977` predates those worktree changes.
- Phase 3 must pin the exact llama.cpp converter commit after confirming that
  its current DeepSeek-V4 path preserves the intended MXFP4 expert representation.
- Native smoke batch/context settings must be selected from measured host memory
  after the output checkpoint exists; they must not weaken the validation set.
