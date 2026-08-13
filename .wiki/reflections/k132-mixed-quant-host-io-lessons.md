---
title: K132 mixed quant host and direct IO lessons
type: reflection
status: current
scope: heretic-v2-reap132-mixed-expert-quant
related_scopes:
  - heretic-v2-reap132-build-validation
related_files:
  - path: vendor/llama.cpp/src/llama-mmap.cpp
    role: owner
  - path: vendor/llama.cpp/tests/test-llama-file.cpp
    role: test
  - path: scripts/verify_reap132_mixed_quant_gguf.py
    role: test
  - path: .scopes/heretic-v2-reap132-mixed-expert-quant/evidence
    role: doc
source_docs:
  - .scopes/heretic-v2-reap132-mixed-expert-quant/task-plans/phase-3-heretic-v2-reap132-mixed-expert-quant.md
tags:
  - reap132
  - direct-io
  - kernel
  - quantization
  - incident-response
last_checked: 2026-08-13
updated: 2026-08-13T14:10:00+08:00
---

# K132 mixed quant host and direct IO lessons

This note preserves the reusable lessons from the corrected K132 Golden and
mixed-quant production incidents. It separates proven facts from hypotheses so
future artifact work does not regress to weaker gates or misclassify host faults.

## Diagnose OOM from evidence, not from a restart

The interrupted production run was not a system RAM OOM. Sysstat showed only
27-28% RAM use, 32-33 GiB available, zero swap, and no kernel OOM killer or
systemd-oomd action. A later failure produced a transient non-finite tensor read,
then `list_del` corruption in `free_pcppages_bulk`, a `0xdead...` general
protection fault, and a CPU hard lockup. These signatures point to page lifecycle
corruption, not capacity exhaustion.

Correlate process exit, memory history, swap, OOM journal entries, and the first
kernel corruption signature on the same boot. Do not label a crash as OOM merely
because it happened during a large model job.

## Separate payload mutation from transient read corruption

The old K132 GGUF contained six abnormal MXFP4 exponent blocks across three
routed tensors. Full comparison against accepted native K132 proved real stored
payload drift. A fresh whole-file converter output then showed another local
64-byte routed mutation. These were artifact defects and required a complete
routed-payload rebuild, not a quantizer tolerance change.

By contrast, the failed shared-expert block and a later direct-read mismatch
reread byte-identically after reboot and repeated cleanly. NVMe SMART had zero
media errors and zero error-log entries. That excludes persistent media
corruption at those locations, but does not prove whether RAM/IMC, kernel
direct-I/O plumbing, DMA, or another host component caused the transient.

Never use an exponent-only scan as complete provenance. It catches extreme
MXFP4 exponent damage but misses legal-looking exponent changes and quant nibble
mutations. Golden acceptance requires complete byte-exact routed provenance.

## Double-read fail-closed direct IO is an integrity boundary

The hardened reader uses position-independent `pread`, fixed reusable aligned
buffers, bounded 1 MiB windows, and two independent reads of every window. The
buffers must match before bytes become visible to the quantizer. Short,
unaligned, beyond-EOF, or mismatched reads fail immediately; there is no retry
that silently accepts the second value.

This gate detected a transient mismatch at offset `24,064,782,336` while reading
`blk.13.ffn_down_exps.weight`. The process stopped without publishing a
candidate. One hundred later rereads of the same range passed. Ordinary
successful reads, one whole-file hash, and clean media counters are therefore
not sufficient integrity evidence on this host.

Reuse bounded buffers instead of allocating and freeing large aligned buffers
for every tensor. This reduces page allocation/free churn around the kernel
failure surface, although it does not establish root cause.

## Atomic publication is mandatory

Every failed or interrupted run left only an unpublished staging file. No final
candidate path was exposed until all 1,328 tensors completed and the writer
performed atomic publication. Finite checks, direct-read comparisons, and
kernel monitoring remain fail-closed. Do not clamp non-finite values, ignore
mismatches, patch a few bytes in place, or promote a partial file to recover
elapsed compute time.

## Storage-path A/B must change one variable

`/data/linux-fast` is on the chipset-attached aigo NVMe. The root filesystem is
on the CPU-attached WD SN540 NVMe. Moving byte-identical read-only Golden and
imatrix copies, plus output staging, to the root NVMe provided a topology A/B
without changing quantizer, plan, corpus, or model bytes.

The root-NVMe production run completed all 1,328 tensors at the exact dry-run
size `55,348,319,104` bytes. This proves the selected path can complete under the
hardened reader. It does not prove that the chipset NVMe, controller, IOMMU,
DMA, RAM, or kernel was the unique cause of earlier faults.

## Rebuild from authoritative native bytes

When routed mutation is confirmed, rebuild complete packed tensors from
accepted native K132 bytes. Do not seek-patch the old GGUF. The corrected Golden
replaced all 129 routed tensors, then compared 17,028 projection-experts and
75,884,396,544 bytes with zero failures.

The imatrix was also regenerated from the corrected Golden with the same
200-chunk corpus. Its raw-I Spearman correlation with the accepted imatrix was
`1.0`, every Rank-I and Rank-P position matched, and Top17 churn was zero. Only
because there was no meaningful ranking change was the frozen 17/26 plan kept.

## Production acceptance order

1. Require a clean boot: no BAD_PAGE, compound-head error, page-list corruption,
   Oops, GPF, hard lockup, unexplained SIGSEGV, or NVIDIA Xid.
2. Freeze source, imatrix, plan, binary commit, command, output name, and free
   space before payload work.
3. Keep inputs read-only; use verified aligned O_DIRECT reads and atomic direct
   output.
4. Stop on read mismatch, short read, non-finite data, or kernel event. Do not
   retry within the same boot as acceptance evidence.
5. After exit zero, independently verify namespace, types, and every tensor
   contractually required to remain unchanged.
6. Record O_DIRECT whole-file SHA256 and make the accepted output read-only.
7. Copy to another device only through direct I/O, then require destination
   size and O_DIRECT SHA256 equality.
8. Only then run dual-GPU 64K startup, behavior, 32K prefill, resource, and
   post-runtime kernel/Xid gates.

## Current boundary

The CPU-attached root-NVMe candidate completed quantization, passed the
1,328-tensor verifier, preserved 600 unchanged tensors byte-for-byte, and has
O_DIRECT SHA256
`67e6990f35db44711c881aee2b55ca789144bec2c0063df2e78957555ea77ab3`.
It remains staging until copied and rehashed on `/data/linux-fast`, made
read-only, and accepted by the dual-5090 runtime matrix.
