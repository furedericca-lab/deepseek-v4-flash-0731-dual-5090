---
description: Produce and verify one DIO K132 heterogeneous quantization artifact.
---

# Tasks: K132 Mixed Expert Quantization Phase 3

## Input

- Corrected immutable K132 Golden, accepted imatrix, frozen plan, full routed
  provenance PASS, and tensor-ftype file.
- Pinned DIO quantizer and clean-boot contract.

## Canonical architecture / Key constraints

- One production candidate only.
- Base ftype is non-pure IQ4_XS; routed overrides are plan-owned.
- Full input/output/hash/provenance access is direct-I/O only.

## Phase 3: Production Artifact

Goal: Build one structurally correct, stable, direct-verified mixed candidate.

Definition of Done: Quantizer exits zero on a clean boot and the candidate
passes structure, type, routing, source, hash, and kernel gates.

Tasks:

- [x] T041 [Infra] Pass production clean-boot preflight
  - DoD: Kernel/Xid/process/RAM/swap, corrected source identity, full-routed provenance report, free-space, plan, imatrix, binary commit, and command are captured before payload work.
- [x] T042 [Infra] Run atomic DIO production quantization
  - DoD: The one authorized quantizer invocation exits zero, publishes only the final atomic output, and post-run kernel gate remains clean.
- [x] T043 [Backend] Implement mixed-candidate verifier
  - DoD: Direct-only verifier checks metadata, namespace, 51 IQ3-recipe tensors, 78 Q2_K_S-recipe tensors against the pinned selector, non-routed IQ4_XS policy inventory, and byte-identical router/`tid2eid`/structural payloads.
- [ ] T044 [QA] Produce direct-only content identity
  - DoD: Candidate has stable O_DIRECT SHA256, read-only mode, zero unstable reads, no MTP/DSpark, and explicit file-size evidence without a size threshold.
  - Current evidence: root-NVMe staging hash, size, namespace, noMTP/DSpark,
    and zero-unstable-read gates pass. Final-path hash equality and mode `0444`
    remain pending.
- [ ] T045 [Docs] Record artifact acceptance or rejection
  - DoD: Reports distinguish intended lossy routed quantization from forbidden routing/metadata drift and identify K132 as rollback baseline.

Checkpoint: Phase 4 starts only with an accepted T045 artifact and clean boot.

## Rejected Input Incident

The first production attempt correctly failed on a non-finite Q2_K block. Full
investigation found six abnormal exponent blocks in three routed tensors of the
old K132 GGUF. A fresh whole-file converter output introduced a separate 64-byte
routed mutation. Neither file is admissible. The final input replaces all 129
complete routed payloads from accepted native K132 and passed 100% byte-exact
verification before the frozen plan was regenerated.

A later corrected-Golden run was interrupted by an unclean host restart after
tensor 943/1328. It was not a system RAM OOM: sysstat recorded 27-28% memory
use, 32-33 GiB available, zero swap, and no kernel/systemd OOM action. The
unpublished staging file was removed. A same-corpus corrected-Golden imatrix
comparison then produced Spearman `1.0`, zero Rank-I/Rank-P changes, and zero
Top17 churn, so the accepted imatrix and frozen plan remain unchanged.

The next retry rejected a transient NaN while reading
`blk.4.ffn_down_shexp.weight`; sixteen seconds later the kernel reported a
per-CPU page-list corruption in `free_pcppages_bulk`, followed by a GPF and hard
lockup. A clean-boot O_DIRECT reread of the exact failed block matched the
accepted native reconstruction byte-for-byte, excluding persistent corruption
at that location. The quantizer input path now uses position-independent,
bounded 1 MiB O_DIRECT reads with reusable aligned buffers and compares two
independent reads of every chunk before exposing bytes to the quantizer. The new
reader passed 25 root-filesystem
fixtures, 50 target-NVMe fixtures, and 100 repeated reads of the exact 8.5 MiB
historical failure tensor with unchanged kernel gates. Production remains
fail-closed on any read mismatch, short read, non-finite tensor, or kernel
event.

The final hardened reader at `efb81abc6a261dcceb014e853beb0ffc5e4a49a0`
detected and rejected a transient mismatch at file offset `24,064,782,336` on
the chipset-attached NVMe; no candidate was published. The same 8 MiB range then
passed 100 repeated reads with clean kernel and NVMe gates.

The controlled storage-path A/B copied byte-identical read-only Golden and
imatrix inputs to the CPU-attached root NVMe. Production completed all 1,328
tensors and atomically published `/home/build/work/reap132-direct-quant/reap132-mixed.gguf`,
size `55,348,319,104`. The independent verifier passed: 51 IQ3_XXS, 73 Q2_K,
five Q2_K_S Q4_K promotions, 600 unchanged tensors, `63,307,072` unchanged
bytes compared, zero unstable reads, and zero failures. Its O_DIRECT SHA256 is
`67e6990f35db44711c881aee2b55ca789144bec2c0063df2e78957555ea77ab3`.
The post-run kernel/Xid signature count is zero. T041-T043 pass; T044 has passed
its root-NVMe hash and verifier sub-gates. T044-T045 remain open until the
candidate is copied with direct I/O to the frozen final path, rehash-equal, made
read-only, and recorded as Phase 3 accepted.

## Dependencies & Execution Order

- Phase 3 depends on frozen Phase 2 evidence.
- T041 blocks T042; T042 blocks T043-T045.
