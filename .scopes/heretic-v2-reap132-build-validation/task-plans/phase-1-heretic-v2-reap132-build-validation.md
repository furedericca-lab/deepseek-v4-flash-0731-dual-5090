---
description: Task list for heretic-v2-reap132-build-validation phase 1.
---

# Tasks: heretic-v2-reap132-build-validation Phase 1

## Input
- Canonical sources:
  - `README.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-scope-milestones.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-brainstorming.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-implementation-research-notes.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-technical-documentation.md`
  - `.scopes/heretic-v2-reap132-build-validation/heretic-v2-reap132-build-validation-contracts.md`

## Canonical architecture / Key constraints
- The plan file and its mask logic are immutable.
- Use squanchyzx HERETIC v2 commit `e7efd043...3bad9` only.
- Use deterministic `--plan --streaming`; calibration and saliency are forbidden.
- Source/output live on `/data/linux-fast`; project Python runs only in `.venv`.
- Do not start pruning before the build code has a truthful commit identity and
  a real quantized Layer 0 naming preflight passes.

## Format
- [ID] [P?] [Component] Description
- [P] means parallelizable.
- Valid components: Backend, Frontend, Agentic, Docs, Config, QA, Security, Infra.
- Every task must have a clear DoD.

## Phase 1: Freeze, Source Verification, and Deterministic Prune
Goal: Freeze every build input, verify the complete source snapshot, and produce the native HERETIC-v2-REAP132 checkpoint exactly once.

Definition of Done: The frozen plan and build code are immutable, source provenance/content manifests pass, and `--plan --streaming` finishes without calibration to a complete native output whose writer reports zero duplicate/unknown names, 792 expert tensors per layer, and 40,325 indexed tensors.

Tasks:
- [x] T001 [QA] Freeze and recheck the plan identity
  - DoD: Full SHA `b43a1078...84b04`, logical SHA `082e51d2...f7b17`, both repo/commit pairs, 43 layer maps, and three hash tables match the contract without rewriting the JSON.
- [x] T002 [Config] Record the executable build-code commit
  - DoD: Root and vendor commit SHAs containing the exact extractor, provenance gate, plan-mode validation, and tests are recorded; executed worktrees are clean or their deliberate diff is fully captured.
- [x] T003 [Infra] Complete and inventory the fixed source download
  - DoD: The user-started `hf download` exits zero, no transfer process remains, all indexed shards exist under the NVMe source directory, and no partial/temp file is treated as complete.
- [x] T004 [Security] Generate and verify source provenance
  - DoD: `scripts/write_checkpoint_source_manifest.py` writes `.checkpoint-source.json` matching repo `squanchyzx/...HERETIC-Abliterated-FP8`, revision `e7efd043...3bad9`, and local config/index hashes.
- [x] T005 [Backend] Implement the canonical checkpoint content manifest
  - DoD: `scripts/checkpoint_content_manifest.py` and focused tests implement the v1 schema, hash every source file sequentially, and produce a stable canonical manifest SHA without including itself.
- [x] T006 [QA] Run pre-prune validation
  - DoD: Full vendor tests pass; plan load, source manifest, source content manifest, free space, and output non-existence/overwrite policy pass.
- [x] T007 [Infra] Capture clean runtime baselines
  - DoD: `free -h`, `nvidia-smi`, `df -hT`, swap, and relevant process snapshots are logged, and no wiki/doctor scan is reading model files.
- [ ] T008 [Backend] Execute deterministic streaming pruning
  - DoD: `uv run moe-compress compress --model <source> --plan squanchyzx-puwaer-reap132-mask.json --streaming --save-path <native-output>` exits zero with no calibration/saliency dataset access, no duplicate/unknown checkpoint names, and the exact 40,325-tensor structural inventory.
- [ ] T009 [QA] Quarantine and record the native output
  - DoD: Output index/config/shards exist, run command/timestamps/exit status/peak memory are recorded, and the artifact remains unapproved until Phase 2 passes.

Checkpoint: A structurally complete but quarantined native checkpoint exists;
Phase 2 owns the full classification and byte-exact acceptance.

## Dependencies & Execution Order
- Phase 1 blocks all others.
- This phase must complete before any later phase starts.
- Tasks marked [P] within this phase may run concurrently only when they do not touch the same files.
