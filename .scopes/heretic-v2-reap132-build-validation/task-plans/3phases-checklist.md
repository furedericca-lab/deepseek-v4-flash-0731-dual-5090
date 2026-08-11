---
description: Execution and verification checklist for heretic-v2-reap132-build-validation 3-phase plan.
---

# Phases Checklist: heretic-v2-reap132-build-validation

## Input
- Canonical docs under:
  - `.scopes/heretic-v2-reap132-build-validation`
  - `.scopes/heretic-v2-reap132-build-validation/task-plans`

## Rules
- Use this file as the single progress and audit hub.
- Update status, evidence commands, and blockers after each implementation batch.
- Do not mark a phase complete without evidence.

## Global Status Board
| Phase | Status | Completion | Health | Blockers |
|---|---|---|---|---|
| Phase 1 | In progress | 90% | Blocked | noMTP build and structural gate pass; host kernel emits BAD_PAGE during full reads |
| Phase 2 | In progress | 25% | Blocked | verifier and output manifest are implemented, but full report cannot be trusted after BAD_PAGE |
| Phase 3 | Not started | 0% | Unknown | Phase 2 native verification/smoke not complete |

## Phase Entry Links
1. [phase-1-heretic-v2-reap132-build-validation.md](phase-1-heretic-v2-reap132-build-validation.md)
2. [phase-2-heretic-v2-reap132-build-validation.md](phase-2-heretic-v2-reap132-build-validation.md)
3. [phase-3-heretic-v2-reap132-build-validation.md](phase-3-heretic-v2-reap132-build-validation.md)

## Phase Execution Records

### 2026-08-11 scope creation and input freeze record

- Phase: 1
- Completed tasks:
  - created the three-phase build/verification scope
  - recorded full plan SHA, logical SHA, repo/commit identities, 43/43 mapping,
    and three exact routing tables
  - confirmed source tensor inventory and verifier naming surface
  - confirmed `/data/linux-fast` ext4 has about 870 GiB available
- Evidence commands:
  - `sha256sum squanchyzx-puwaer-reap132-mask.json`
  - `jq` geometry/provenance inspection of the frozen plan
  - fixed-revision Hugging Face index inspection
  - `git rev-parse HEAD` and submodule HEAD/status inspection
  - `df -hT /data/linux-fast`
- Issues/blockers:
  - user-started fixed-revision source download exited; a later check found no
    download process and no target directory
  - root and vendor worktrees contain uncommitted build changes, so the current
    extractor/compressor cannot yet be identified by a truthful commit SHA
- Resolutions:
  - re-run the fixed-revision command and capture its terminal error if it exits
    again; do not run pruning until download, manifests, tests, and build-code
    commit identity pass Phase 1 gates
- Checkpoint confirmed: scope/input evidence recorded; native build gate remains closed

### 2026-08-11 verified source and pre-prune record

- Phase: 1
- Completed tasks:
  - T001 rechecked the immutable plan full/logical hashes, both repo commits,
    43 layer maps, 132 experts per layer, and three hash-routing tables
  - T003 completed the official logged-in `hf` CLI fixed-revision confirmation;
    all 96 remote files match, including 50/50 LFS SHA256 checks and 46/46
    byte comparisons after repairing `tokenizer.json`
  - T004 wrote and verified `.checkpoint-source.json` against the fixed remote
    config and index
  - T005 implemented and tested `scripts/checkpoint_content_manifest.py`; the
    97-entry source manifest is stable at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - T006 passed focused tests and the full vendor suite
  - T007 captured the pre-prune RAM/swap/GPU/disk/process baseline
  - T002 froze root build commit
    `41888983bf304b234d6414ce74abf117322d8b5c` and vendor build commit
    `0645265700b0c8325c2ac141b02873f3cd0ab474`
  - pre-start review found and fixed silent omission of 4,705 model-ignored MTP
    tensors; checkpoint-native passthrough preserves 10,862,838,300 source bytes
- Evidence commands/results:
  - `sha256sum squanchyzx-puwaer-reap132-mask.json` ->
    `b43a1078f905157cbdbe976530d96b6c41730ccd3ef6feac4d598a15a9d84b04`
  - `uv run hf download ... --revision e7efd043...3bad9 --local-dir ...` -> exit 0
  - source remote comparison -> 96/96 paths and sizes, 50/50 LFS SHA256,
    46/46 small files byte-identical
  - `scripts/write_checkpoint_source_manifest.py` plus
    `verify_checkpoint_source()` -> PASS
  - `scripts/checkpoint_content_manifest.py ... --artifact-role source` and
    `--check` -> 97 files, stable manifest SHA above
  - focused manifest/provenance tests -> `68 passed`; final full vendor tests ->
    `216 passed, 5 skipped`
  - baseline -> 46 GiB RAM, 47 GiB swap, 714 GiB NVMe free, dual RTX 5090
    visible, native output absent, no model/wiki/doctor scan active
- Issues/blockers:
  - no Phase 1 entry blocker remains
  - legacy `puwaer-reap132-mask.json` was deleted; the only executable plan is
    committed `squanchyzx-puwaer-reap132-mask.json`
- Checkpoint confirmed: verified source snapshot and executable build identities are frozen; T008 deterministic pruning is authorized to start

### 2026-08-11 rejected first output and naming-fix record

- Phase: 1
- Completed work:
  - the first streaming process exited zero without OOM, but its output was
    rejected after the source-namespace cross-check found 437 unknown names
  - 396 layerless E8M0 scale names collided across 43 layers, losing 16,632
    distinct scale keys; 41 attention KV norm names were also malformed
  - fixed quantized expert scale and KV norm reverse naming in vendor commit
    `5439fba8071467d8b2bb113046cd4e488ac14f5f`
  - a live comparison against the fixed Hugging Face revision then proved that
    source shards 2, 41, 43, 44, and 46 had drifted after the previously correct
    content manifest was generated; all five were replaced from the official
    logged-in `hf` CLI and the repair directory was deleted
  - changed every streaming safetensors read to the `pread` backend in vendor
    commit `7fae3000e321fde32a4a010171b9480e22148ba0`, preventing model tensors from
    sharing an mmap-backed source storage
  - made duplicate tensor names and source-index unknown names fatal writer errors
  - added full fused FP4 weight/scale, two-layer collision, KV norm, duplicate,
    and unknown-name regressions
- Evidence commands/results:
  - failed output index -> 23,693 total, 23,256 source-known, 437 unknown
  - expected fixed inventory -> 40,325 total and 792 expert tensors per layer
  - focused naming/streaming tests -> `23 passed`
  - full vendor suite -> `222 passed, 5 skipped`
  - fixed-revision live comparison after repair -> 96/96 paths and sizes,
    50/50 LFS SHA256, 46/46 Git blob SHA1, and 96/96 remote files read-only
  - real source Layer 0 after `apply_keep()` -> 821 converted tensors, 792
    expert tensors, 396 weights, 396 scales, zero unknown names, zero byte/dtype/
    shape provenance mismatches
  - full 97-file source manifest check after the pread Layer 0 run -> PASS at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - repeated shard reads around `sync` were stable and kernel logs contained no
    NVMe I/O, media, data-integrity, or EXT4 errors; a later authorized SMART
    read passed with zero critical warnings, media/data-integrity errors, and
    error-log entries
- Resolution:
  - user explicitly authorized deleting the unusable first model output to avoid
    operator confusion; timestamped run logs and Wiki evidence remain
  - rerun only from the frozen plan, read-only source snapshot, and committed
    pread/naming implementation
- Checkpoint confirmed: the failed artifact is not T008 completion; Layer 0
  preflight passes and a clean full rerun is authorized

### 2026-08-11 rejected exit-139 rerun and source re-verification

- Phase: 1
- Completed work:
  - the clean rerun wrote 18 shards but exited `139` after the save message;
    memory guard remained clear, so T008/T009 are not complete
  - a full fixed-revision comparison continued across all 96 files and found
    five same-size LFS SHA256 mismatches in shards 5, 40, 42, 47, and 48
  - downloaded those five files with the logged-in official `hf` CLI into an
    isolated repair directory, verified 5/5 SHA256 values, atomically replaced
    the bad files, and deleted the repair directory
  - added `tools/verify_hf_checkpoint_sha256.py`; it compares every LFS file to
    remote SHA256 metadata, downloads and hashes each fixed-revision Git file,
    continues after mismatches, and emits complete mismatch/missing/extra sets
  - deleted the 90 GiB exit-139 output under the standing authorization to
    remove unusable model artifacts
- Evidence commands/results:
  - pre-repair comparison -> 91/96 matched; five exact mismatch records saved
    under repo-ignored `logs/`
  - post-repair tool comparison -> 96/96 matched, 50/50 LFS SHA256, 46/46 Git
    files by downloaded remote SHA256, zero missing/extra paths
  - all 96 repository files plus `.checkpoint-source.json` and
    `checkpoint-content-manifest.json` -> mode `0444`
  - source content manifest check -> 97 files PASS at
    `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - verifier/manifest tests -> `11 passed`
- Issues/blockers:
  - shard mtimes predate the 19:34 rerun, so current evidence does not identify
    which process caused the second drift; do not attribute it to `pread`
  - isolate the remaining mutation path and exit `139` before another full run
- Checkpoint confirmed: source is repaired, remotely verified, and read-only;
  deterministic pruning is blocked pending root-cause isolation

### 2026-08-11 noMTP build-policy decision

- Phase: 1-2 contract update
- Decision:
  - keep squanchyzx HERETIC v2 as the immutable source and apply the frozen
    puwaer REAP132 plan exactly
  - retain the generic ignored-tensor passthrough capability, but select the
    explicit project policy `--drop-mtp`
  - write the new artifact only as
    `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-noMTP/`
- Derived inventory gate:
  - old MTP-preserving structural count -> 40,325
  - classified source MTP/DSpark tensors -> 4,705 totaling 10,862,838,300 bytes
  - current noMTP structural count -> 35,620
  - derive the count from source/plan classification during verification rather
    than accepting the hard-coded number alone
- Required verification:
  - 43/43 layers, 792 expert tensors per layer, 396 weights and 396 scales
  - exact frozen survivor/router/three-table `tid2eid` provenance
  - all 66 HERETIC v2 `attn.wo_b.{weight,scale}` tensors source-identical
  - MTP/DSpark tensors -> 0; unknown/unclassified tensors -> 0
- Executable identities:
  - root build -> `8071c7c64101f16ea0959881b86d180862bd514b`
  - vendor build -> `56137d189fd36c1c8881ca99233614b177442425`
- Checkpoint confirmed: the earlier 40,325 gate remains historical evidence for
  the rejected MTP-preserving build and is superseded for the release artifact

### 2026-08-11 noMTP artifact and host-stability record

- Phase: 1-2
- Completed work:
  - deterministic `--plan --streaming --drop-mtp` completed with exit 0,
    memory guard clear, 15 shards, 35,620 indexed tensors, and zero MTP tensors
  - post-build fixed-revision source comparison passed `96/96`; source manifest
    passed at `815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`
  - output content manifest passed twice: 20 files at
    `1e1cad5a73adb26215a94a323de66e38b34b406eea0d8f519cbe7250da9a2846`
  - implemented `scripts/verify_reap132_checkpoint.py` and adversarial fixture
    tests; project tests pass `18 passed`
  - output directory was made read-only and remains quarantined
- Issues/blockers:
  - full direct tensor verification was interrupted after the host emitted
    `BAD_PAGE` and `compound_head not consistent` from `kswapd0` at 22:56:30
  - zram was effectively unused; current evidence points to unresolved
    kernel/RAM/EXPO stability under page-cache pressure, not model semantics
  - no `post-prune-verification.json` PASS report exists; native smoke and GGUF
    remain blocked
- Next gate:
  - boot `6.17.0-23-generic` or disable EXPO, confirm a clean `journalctl -k -b`,
    then rerun the cache-bounded verifier

### 2026-08-11 6.17 rerun result

- A fresh deterministic `--plan --streaming --drop-mtp` rebuild was completed
  under `6.17.0-23-generic` in the isolated directory
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-rerun-6.17/`.
- Structural output gate passed: 15 shards, 35,620 indexed tensors, and zero
  MTP/DSpark tensors. The output manifest passed twice with manifest SHA256
  `18de33ba67182a9a8d34b242a22d4681bc5659d5ccf8d0a72a60ea0020000456`.
- The output was made read-only before verification.
- During the cache-bounded direct verifier, the 6.17 boot reproduced
  `BUG: Bad page state` / `compound_head not consistent` in `kswapd0` at
  `23:30:01`; verification was stopped immediately and no PASS report exists.
- `cat /proc/sys/kernel/tainted` changed from `4096` to `4128` after this event.
  Native smoke, GGUF conversion, and deployment remain blocked. The new rerun
  is quarantined separately from the earlier failed artifact.

### 2026-08-12 5800 MT/s verification result

- After changing memory to 5800 MT/s, a clean `6.17.0-23-generic` boot started
  with `tainted=4096` and no kernel memory errors.
- The complete verifier finished without another `BAD_PAGE`, `compound_head`,
  MCE, or I/O error; this is evidence that 5800 MT/s materially improves the
  host stability gate compared with 6000 MT/s.
- The checkpoint is still not releasable: the verifier report contains 49
  semantic failures. Router rows, scales, shared experts, tid2eid, HERETIC
  overlay, MTP absence, and dangling IDs pass, but expert byte provenance has
  8 mismatches and the current report flags 41 untouched/router-related names.
- No native smoke or GGUF work is authorized until the verifier contract is
  corrected for the expected router bias/overlay namespace and the remaining
  expert mismatches are independently explained or eliminated.

### 2026-08-12 5600 MT/s writer diagnosis

- A fresh rebuild and full verifier under `7.0.0-28-generic` with DDR5-5600
  completed without kernel errors (`tainted=4096`).
- Manifest passed twice; structural counts remained 15 shards and 35,620
  tensors with MTP/DSpark absent.
- Five FP4 expert weight byte mismatches remained. Their expert IDs differ from
  the previous rebuilds, while scales and all non-expert gates/overlays pass.
- Root-cause gate: the streaming writer materializes fused FP4 tensors on CUDA,
  then converts them back through `revert_weight_conversion()` and CPU writes.
  This path is not byte-exact for packed FP4 storage. The next implementation
  must read source safetensors bytes on CPU and slice survivors directly,
  bypassing GPU round-trip and fused reverse conversion.

## Final Release Gate
- Scope constraints preserved.
- Quality/security gates passed.
- Remaining risks documented.
- Frozen plan has not changed.
- Native checkpoint byte verification and smoke passed before GGUF conversion.
- Golden GGUF and controlled A/B identities/results are recorded separately.
