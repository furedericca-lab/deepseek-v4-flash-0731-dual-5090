---
title: Maintenance Log
type: maintenance-log
status: current
updated: 2026-08-10T18:16:02Z
---

# Maintenance Log

Append-only history for wiki updates caused by scope work, implementation closeout, or knowledge refresh.

## 2026-08-10T18:26:53Z [deepseek-v4-flash-0731-dual-5090]

- Summary: Recorded dual-5090 deployment architecture, model placement, and first-boot recipe from host inventory.
- Pages: decisions/dual-5090-q2-k-full-gpu-with-ram-f16-kv.md, implementation/model-placement-and-disk-strategy.md, how-to/first-boot-llama-server-recipe.md
- Verification: wiki-note decision/add + rebuild/lint
- Residual risk: Host RAM only ~46 GiB; model still on Toshiba NTFS source path pending NVMe copy.

## 2026-08-11T06:38:38Z [deepseek-v4-flash-0731-dual-5090]

- Summary: Recorded immutable REAP-132 plan identity and mandatory local checkpoint manifest verification.
- Pages: implementation/reap132-plan-checkpoint-provenance.md
- Verification: uv run pytest vendor/moe-expert-compress/tests -q, uv run python scripts/extract_puwaer_plan.py -o puwaer-reap132-mask.json
- Residual risk: Base checkpoint is not downloaded yet; manifest and streaming compression remain pending.

## 2026-08-11T07:17:33Z [deepseek-v4-flash-0731-dual-5090]

- Summary: Switched mapped REAP132 base provenance to squanchyzx HERETIC v2 and recorded the generated artifact identity.
- Pages: implementation/reap132-plan-checkpoint-provenance.md, implementation/model-placement-and-disk-strategy.md
- Verification: uv run python scripts/extract_puwaer_plan.py, uv run pytest vendor/moe-expert-compress/tests -q
- Residual risk: The fixed v2 checkpoint has not been downloaded; manifest generation and streaming compression remain pending.

## 2026-08-11T07:28:12Z [heretic-v2-reap132-build-validation]

- Summary: Opened the phased HERETIC v2 REAP132 build, byte-verification, native smoke, golden GGUF, and controlled A/B scope.
- Pages: implementation/heretic-v2-reap132-build-validation.md, implementation/reap132-plan-checkpoint-provenance.md, implementation/model-placement-and-disk-strategy.md
- Verification: python3 /home/build/.codex/skills/ok-skill repo-task-driven check --scope heretic-v2-reap132-build-validation --decision --json
- Residual risk: Source download is active and current build-code changes are uncommitted; pruning is blocked until both identities are frozen.

## 2026-08-11T07:30:14Z [heretic-v2-reap132-build-validation]

- Summary: Corrected source download state after the initial process exited with no target directory.
- Pages: implementation/heretic-v2-reap132-build-validation.md
- Verification: findmnt -T /data/linux-fast/models, ps -u build -o pid,etime,cmd
- Residual risk: Fixed-revision source download must be restarted and its terminal result captured before Phase 1 can proceed.

## 2026-08-11T09:53:35Z [heretic-v2-reap132-build-validation]

- Summary: Verified the fixed HERETIC v2 source snapshot, added canonical checkpoint content manifests, and recorded the pre-prune build-commit blocker.
- Pages: implementation/heretic-v2-reap132-build-validation.md
- Verification: uv run pytest vendor/moe-expert-compress/tests -q; repo-task-driven check; wiki-note rebuild/lint/doctor
- Residual risk: Pruning remains blocked until root and vendor build changes have truthful commit identities.

## 2026-08-11T10:05:49Z [heretic-v2-reap132-build-validation]

- Summary: Corrected build identities and added checkpoint-native passthrough for all 4,705 model-ignored MTP tensors before pruning.
- Pages: implementation/heretic-v2-reap132-build-validation.md
- Verification: uv run pytest vendor/moe-expert-compress/tests -q
- Residual risk: Native output remains unverified until deterministic pruning and Phase 2 byte checks complete.

## 2026-08-11T10:32:10Z [heretic-v2-reap132-build-validation]

- Summary: Recorded the rejected first REAP132 output: 396 layerless expert scales plus 41 malformed KV norm names, 16632 lost per-layer scale keys, root-cause boundary, and mandatory preflight gates.
- Pages: debugging/heretic-v2-streaming-writer-namespace-corruption.md, implementation/heretic-v2-reap132-build-validation.md
- Verification: source/output index comparison; safetensors header inspection; real quantized layer naming reproduction
- Residual risk: Naming conversion remains unfixed; failed output is quarantined and pruning must be rerun after a zero-unknown one-layer preflight.

## 2026-08-11T11:33:49Z [heretic-v2-reap132-build-validation]

- Summary: Recorded five source shard mutations, fixed-revision repair, read-only snapshot enforcement, pread streaming isolation, and post-preflight manifest stability.
- Pages: debugging/heretic-v2-streaming-writer-namespace-corruption.md, implementation/heretic-v2-reap132-build-validation.md
- Verification: live HF 96-file comparison; official hf repair; pread Layer 0 preflight; full source manifest check
- Residual risk: NVMe kernel logs are clean and reads are stable; complete SMART data remains unchecked without read-only sudo authorization.

## 2026-08-11T12:16:51Z [heretic-v2-reap132-build-validation]

- Summary: Recorded the exit-139 rerun, five additional source SHA256 mismatches, fixed-revision repair, 96/96 verification tool, read-only freeze, and clean SMART evidence.
- Pages: debugging/heretic-v2-streaming-writer-namespace-corruption.md, implementation/heretic-v2-reap132-build-validation.md
- Verification: uv run python tools/verify_hf_checkpoint_sha256.py; uv run python scripts/checkpoint_content_manifest.py --check
- Residual risk: The process responsible for the second same-size source drift is not proven; do not rerun pruning until the remaining mutation path and exit 139 are isolated.

## 2026-08-12T04:41:23Z [heretic-v2-reap132-build-validation]

- Summary: Recorded deterministic O_DIRECT A/B byte reproducibility, noMTP NextN config correction, CPython 3.13 GPF forensics, bounded RAM/O_DIRECT diagnostics, PCIe topology, and the Python 3.12 faulthandler recovery gate.
- Pages: debugging/heretic-v2-streaming-writer-namespace-corruption.md, implementation/heretic-v2-reap132-build-validation.md
- Verification: 23 tests passed; 32 GiB x4 native memory patterns passed; 16 GiB O_DIRECT source/copy SHA256 matched; AER/NVMe/MCE counters clean
- Residual risk: Exact invalid-PyObject corruptor remains unproven; reboot before the Python 3.12 config-correct full rebuild.

## 2026-08-12T09:05:39Z [heretic-v2-reap132-build-validation]

- Summary: Identified and fixed direct GGUF output zeroing lazy ordinary tensors; quarantined the first full GGUF and retained MXFP4 as the sole deployment target.
- Pages: implementation/heretic-v2-reap132-build-validation.md
- Verification: 7 direct-I/O writer tests passed; 90 MXFP4 samples passed; 9 nonexpert provenance samples failed on quarantined artifact
- Residual risk: Replacement full GGUF must complete direct provenance and dual-5090 semantic runtime acceptance.

## 2026-08-12T14:20:26Z [heretic-v2-reap96-consensus]

- Summary: Archived completed REAP132 delivery, created the isolated K96 consensus scope, and aligned entry points with immutable K132 release policy.
- Pages: implementation/heretic-v2-reap96-consensus.md, implementation/heretic-v2-reap132-build-validation.md, decisions/reap96-k132-subset-consensus.md
- Verification: repo-task-driven archive/scaffold; wiki-note rebuild/lint/doctor
- Residual risk: External mask schemas and immutable revisions must be verified before any K96 plan is generated.

## 2026-08-12T16:51:48Z [heretic-v2-reap96-consensus]

- Summary: Expanded the frozen K96 plan record with source provenance, scoring and tie-break semantics, corrected histograms, semantic-rank boundary statistics, plan hashes, regenerated hash-routing invariants, and Phase 3 quality risks.
- Pages: implementation/heretic-v2-reap96-consensus.md, decisions/reap96-k132-subset-consensus.md
- Verification: uv run python scripts/verify_reap96_plan.py
- Residual risk: K96 remains an unbuilt aggressive pruning candidate; K132 stays canonical until all Phase 3 O_DIRECT, provenance, GGUF, and dual-5090 semantic gates pass.

## 2026-08-12T23:19:02Z [heretic-v2-reap96-iq4xs-backbone]

- Summary: Archived completed K96 Profile A IQ4_XS release scope and aligned repository entry points.
- Pages: implementation/k96-profile-a-iq4xs-non-routed-release.md
- Verification: repo-task-driven archive; wiki-note rebuild/lint/doctor
- Residual risk: K96 semantic limitation remains; K132 remains deployed.

## 2026-08-12T23:38:30Z [heretic-v2-reap132-mixed-expert-quant]

- Summary: Opened fixed 17/26 K132 mixed routed-expert quantization scope and froze structural and activation score formulas.
- Pages: implementation/k132-fixed-ratio-mixed-expert-quantization.md
- Verification: repo-task-driven scaffold/check; wiki-note rebuild/lint/doctor
- Residual risk: Phase 1 imatrix coverage has not run; no layer assignment or quantized artifact exists yet.
