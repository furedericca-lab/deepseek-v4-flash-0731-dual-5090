---
description: Scope boundaries and milestones for heretic-v2-reap132-build-validation.
---

# heretic-v2-reap132-build-validation Scope and Milestones

## In Scope

- Freeze the exact plan, source repos/commits, build-code commit, and provenance.
- Complete and validate the squanchyzx HERETIC v2 source snapshot on NVMe.
- Produce `HERETIC-v2-REAP132` through deterministic plan application.
- Implement and run byte-exact post-prune verification.
- Create source/output content manifests with distinct hashes from the plan hash.
- Run native HF smoke tests before conversion.
- Produce and validate one MXFP4-preserving golden GGUF.
- Run dual-5090 llama.cpp validation and a controlled puwaer/HERETIC A/B.
- Maintain scope and wiki evidence after every gate.

## Out of Scope

- Re-running REAP calibration or changing the survivor mask.
- Editing, regenerating, or normalizing the frozen plan JSON.
- IQ3, Q2_K, or other further quantization before the golden GGUF passes.
- Public or LAN serving; all smoke endpoints remain on `127.0.0.1`.
- Multi-user throughput tuning or context targets above the validated baseline.
- Committing model checkpoints, GGUF files, or large verification payloads to git.

## Decision Log

| Boundary / Decision | Evidence Source | Evidence Strength | Conflict | Confidence | Confidence Reason | Result |
|---|---|---:|---|---:|---|---|
| Treat plan JSON as immutable input | Full file/logical SHA and user instruction | 5 | None | 5 | Proven 43-layer mapping is the scope foundation | Accepted |
| Use existing puwaer survivor set | Exact router/tid2eid comparison | 5 | Fresh calibration explicitly deferred | 5 | Enables controlled A/B | Accepted |
| Require byte-exact verifier | Native FP4 preservation requirement | 5 | More implementation work | 5 | Geometry alone cannot prove preservation | Accepted |
| Separate plan and output hashes | Artifact identity model | 5 | None | 5 | They cover different payloads | Accepted |
| Native HF smoke before GGUF | User-defined gate | 5 | Runtime resource uncertainty | 4 | Correct failure isolation | Accepted |
| Golden MXFP4 GGUF before IQ3/Q2 | User-defined ordering | 5 | None | 5 | Establishes clean baseline | Accepted |

## Milestones

### M0 - Scope and frozen input record

- New phased scope passes placeholder and decision checks.
- Plan full SHA, logical SHA, repo/commit pair, 43/43 mapping, and three routing
  blobs are recorded.
- Exit: frozen plan record is complete except for the explicitly blocked build
  code commit, which must be resolved before pruning.

### M1 - Verified source snapshot

- Fixed HERETIC v2 revision is fully downloaded to NVMe.
- `.checkpoint-source.json` and a complete source content manifest pass.
- File inventory agrees with `model.safetensors.index.json`; no partial files.
- Exit: source can be opened layer-by-layer and provenance is immutable.

### M2 - Native deterministic REAP132 output

- `--plan --streaming` completes without calibration/saliency.
- Output is written under
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132/`.
- Exit: native checkpoint, logs, and run metadata exist with no write errors.

### M3 - Post-prune byte-exact verification

- `post-prune-verification.json` reports every required PASS category.
- Output content manifest and manifest SHA are generated.
- Exit: 43/43 expert mappings, router, FP4 weights/scales, shared experts,
  HERETIC overlay, MTP, and `tid2eid` are proven.

### M4 - Native HF smoke

- Chat, reasoning, coding, tool-call, and longer-context probes complete.
- No NaN, routing overflow, tokenizer/config fault, or obvious degeneration.
- Exit: native checkpoint is accepted as the conversion source.

### M5 - Golden GGUF and dual-5090 runtime

- Pinned llama.cpp converter produces an MXFP4-preserving GGUF.
- GGUF SHA, metadata, two-GPU visibility, localhost boot, `/v1/models`, and one
  completion pass.
- Exit: golden GGUF is frozen before further quantization.

### M6 - Controlled A/B

- puwaer REAP-150B and HERETIC-v2 + identical REAP132 use the same harness,
  prompts, runtime flags, and scoring.
- Exit: results isolate the HERETIC attention overlay as the intended variable.

## Dependencies

- M0 blocks all build actions.
- M1 depends on M0 and blocks pruning.
- M2 depends on M1 and blocks verifier execution.
- M3 depends on M2 and blocks native smoke.
- M4 depends on M3 and blocks GGUF conversion.
- M5 depends on M4 and blocks A/B and further quantization.
- M6 depends on a verified comparison artifact and M5.

## Exit Criteria

- Frozen plan and both content manifests have full hashes recorded.
- Build-code commit identity is recorded and matches the executed worktree.
- Native output passes all structural and byte-exact checks.
- Native smoke and golden GGUF dual-5090 smoke pass.
- Controlled A/B report is stored without conflating plan and output hashes.
- Residual risks and skipped checks are explicit; no model binary is in git.

## Escalation Triggers

- Escalate only when code/runtime evidence, authoritative wiki, and scope docs materially conflict and the conflict cannot be resolved from local evidence.
- Escalate for data deletion, permission semantics, production access model, or public API compatibility decisions outside the stated boundaries.
- Escalate when user-specified boundaries cannot be satisfied together.
- Escalate if the source revision or frozen plan hash changes.
- Escalate if any retained FP4 weight/scale, shared expert, HERETIC overlay, MTP,
  or `tid2eid` byte comparison fails.
- Escalate before deleting/replacing a completed source or output checkpoint.
- Escalate if the converter cannot preserve MXFP4 experts without requantization.
