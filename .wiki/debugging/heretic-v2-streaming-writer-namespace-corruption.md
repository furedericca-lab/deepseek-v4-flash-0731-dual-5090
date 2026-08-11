---
title: HERETIC v2 streaming writer namespace corruption
type: debugging
status: current
scope: heretic-v2-reap132-build-validation
related_scopes:
  - deepseek-v4-flash-0731-dual-5090
related_files:
  - path: vendor/moe-expert-compress/src/moe_compress/streaming/naming.py
    role: owner
  - path: vendor/moe-expert-compress/src/moe_compress/streaming/writer.py
    role: caller
  - path: vendor/moe-expert-compress/tests/test_naming.py
    role: test
  - path: squanchyzx-puwaer-reap132-mask.json
    role: config
  - path: tools/verify_hf_checkpoint_sha256.py
    role: verification
  - path: tests/test_verify_hf_checkpoint_sha256.py
    role: test
code_anchors:
  - id: checkpoint-name-reversal
    kind: function
    file: vendor/moe-expert-compress/src/moe_compress/streaming/naming.py
    symbol: to_checkpoint_names
    role: defines
  - id: source-namespace-gate
    kind: function
    file: vendor/moe-expert-compress/src/moe_compress/streaming/naming.py
    symbol: verify_against_source
    role: defines
  - id: writer-source-cross-check
    kind: method
    file: vendor/moe-expert-compress/src/moe_compress/streaming/writer.py
    symbol: StreamingCheckpointWriter.finalize
    role: defines
source_docs:
  - .scopes/heretic-v2-reap132-build-validation/task-plans/3phases-checklist.md
tags:
  - deepseek-v4
  - fp4
  - safetensors
  - streaming
  - namespace
last_checked: 2026-08-11
updated: 2026-08-11T12:16:32Z
---

# HERETIC v2 streaming writer namespace corruption

## Symptom

The first deterministic REAP132 streaming run exited `0`, did not trigger the
memory guard, wrote 18 shards, and produced a stable content manifest. It was
still structurally invalid. `StreamingCheckpointWriter.finalize()` reported 437
names absent from the source index:

- 396 names such as `.experts.0.w1.weight`, with no layer or FFN prefix;
- 41 names such as `layers.42.attn.norm.weight`, where the source namespace is
  `layers.42.attn.kv_norm.weight`.

The output index contained 23,693 tensors, of which 23,256 existed in the
source namespace and 437 did not. The source index contains 72,317 tensors.
Every output layer had only 396 correctly named expert tensors, corresponding
to 132 experts times the three packed weights. The matching 396 scale tensors
per layer were not correctly preserved.

## Proven impact

The 396 top-level expert names are the E8M0 scale payloads, not legitimate
expert-renumbering names. Their shapes identify them as scales, for example:

```text
.experts.0.w1.weight                  [2048, 128] F8_E8M0
layers.42.ffn.experts.0.w1.weight     [2048, 2048] I8
source layers.42.ffn.experts.0.w1.scale [2048, 128] F8_E8M0
```

Because all 43 layers emitted the same 396 malformed top-level names, later
layers overwrote earlier entries in the writer dictionaries. The checkpoint is
short by 16,632 distinct per-layer scale keys: `43 * 396 - 396`. The expected
post-prune index size is therefore 40,325, not 23,693. The 41 bad attention norm
names are namespace errors without an additional count loss.

This output cannot load correctly in a serving engine and cannot be repaired by
classifying the 437 names as expected remaps. It must remain quarantined and
must not enter native smoke, GGUF conversion, or deployment.

## Root cause boundary

The failure occurs in `to_checkpoint_names()` when it reverses the installed
Transformers DeepSeek-V4 conversion mapping for a complete real quantized layer.
After pruning, the fused routed-expert state includes both
`gate_up_proj`/`down_proj` and their `_scale_inv` tensors. Reversing the full
state produces correct per-layer packed-weight names but malformed scale names.
The generic reverse `.norm.` mapping also turns the attention KV norm into
`attn.norm` instead of the checkpoint-native `attn.kv_norm` spelling.

The existing naming tests did not catch this because their tiny DeepSeek-V4
fixture is unquantized. Testing single synthetic names also passes; the defect
appears on the complete fused weight-plus-scale state of a real FP4 layer.

## Detection procedure

Do not use process exit or a content manifest as a semantic checkpoint gate.
The content manifest correctly hashes whatever files exist, including an
invalid namespace. Before accepting any future streaming output:

1. Compare every output index key against the source index. Unknown names must
   be a hard failure, not a warning.
2. Require 792 expert tensors per layer: 132 experts times `w1/w2/w3` times
   `weight/scale`.
3. Require 40,325 total tensors for this frozen source, plan, and MTP-preserving
   build unless a documented source or plan identity changes.
4. Open representative safetensors headers and verify scale shapes and dtypes,
   not only key counts.
5. Run the direct-safetensors verifier before native loading or GGUF conversion.

## Required fix and regression gate

The naming layer must explicitly preserve the decoder-layer prefix and map the
real quantized expert scale payloads to
`layers.L.ffn.experts.E.w{1,2,3}.scale`. It must also restore
`layers.L.attn.kv_norm.weight`. Add a regression fixture built from the same
fused packed-weight and E8M0 scale state shape the writer receives after
`apply_keep()`.

The writer source cross-check must reject any unknown output name before an
artifact is reported as successfully compressed. A one-layer real-checkpoint
preflight must produce zero unknown names before the full 43-layer rerun.

After the fix, preserve the failed output and logs as evidence, create a fresh
output directory, rerun deterministic pruning with the frozen plan, and require:

```text
unknown source names: 0
expert tensors per layer: 792
total indexed tensors: 40325
unclassified tensors: 0
```

Only the subsequent byte-exact verifier can establish final correctness.

## Source snapshot mutation discovered during repair

The namespace investigation also invalidated the assumption that the source
directory had remained immutable. The canonical 97-file content manifest had
recorded the correct fixed-revision bytes, but a later live comparison against
Hugging Face found same-size SHA drift in shards 2, 41, 43, 44, and 46. Shard 2
appeared only after an explicit `sync`, consistent with a delayed dirty-page
writeback from the old mmap loading path.

All five shards were downloaded again with the logged-in official `hf` CLI at
revision `e7efd043c5e072da4d40f0f98ade554c5713bad9`. After replacement, a fresh
remote comparison proved:

```text
paths and sizes: 96/96
LFS SHA256: 50/50
Git blob SHA1: 46/46
writable remote files: 0
mismatches: 0
```

The old streaming loader used safetensors mmap-backed slices. Vendor commit
`7fae3000e321fde32a4a010171b9480e22148ba0` changes the single-file index,
per-layer load, and MTP passthrough paths to `backend="pread"`, and regression
tests require source safetensors hashes to remain unchanged. The 96 repository
files plus `.checkpoint-source.json` and `checkpoint-content-manifest.json` are
now read-only.

A real Layer 0 preflight through pread passed 792/792 expert tensors, zero
unknown names, and zero byte/dtype/shape provenance mismatches. A subsequent
full manifest check remained stable at
`815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98`.

Repeated reads of a bad shard were stable around `sync`, and the kernel log had
no NVMe I/O, media, data-integrity, or EXT4 errors. A subsequent authorized SMART
read reported `PASSED`, zero critical warnings, zero media/data-integrity errors,
and zero error-log entries. The SSD has historical unsafe-shutdown and elevated
temperature counters, but there is no current evidence of media failure.

## Follow-up full-run source gate

The next deterministic run wrote 18 output shards but exited `139` after the
save message; the memory guard did not trigger. The output is not releasable
because the process did not exit cleanly, and its 90 GiB directory was deleted
under the standing unusable-artifact cleanup authorization. A complete post-run comparison against
the fixed Hugging Face revision then found five same-size SHA256 mismatches:

```text
model-00005-of-00048.safetensors
model-00040-of-00048.safetensors
model-00042-of-00048.safetensors
model-00047-of-00048.safetensors
model-00048-of-00048.safetensors
```

Their recorded mtimes predate the 19:34 run, so the evidence does not establish
that the `pread` rerun created the drift. It does establish that mode `0444` and
a prior manifest result are not substitutes for a fresh remote hash gate at the
moment a source artifact is consumed.

The five files were downloaded to an isolated repair directory with the logged-in
official `hf` CLI at revision
`e7efd043c5e072da4d40f0f98ade554c5713bad9`. Each replacement matched its remote
LFS SHA256 before atomic replacement. A complete second pass then proved:

```text
remote files: 96
paths: 96/96
LFS SHA256: 50/50
Git files by downloaded remote SHA256: 46/46
mismatches: 0
writable remote files: 0
content manifest: 97 files PASS
manifest SHA256: 815f75dd1198597d823af439456a7dbd141c19855df277437a0751b925c7bb98
```

`tools/verify_hf_checkpoint_sha256.py` now implements this gate. It continues
after individual failures, records every file result, emits a `mismatches`
collection plus missing/extra path collections, and exits nonzero only after the
complete comparison. LFS objects use the revision metadata SHA256; ordinary Git
files are downloaded at the fixed revision and hashed remotely and locally.

The historical 40,325 tensor count in this page describes the rejected
MTP-preserving policy. The release policy now deliberately drops all 4,705
`mtp.*` tensors, so `scripts/derive_reap132_inventory.py` derives a 35,620-tensor
noMTP target. The naming fix remains required independently of this policy.

## 2026-08-11 page-cache BAD_PAGE incident

After the noMTP build, a full buffered SHA/manifest pass twice triggered Linux
`7.0.0-28-generic` reports from `kswapd0` and `page_cache_ra_order`:
`Bad page state`, `corrupted mapping in tail page`, and
`compound_head not consistent`. One shard temporarily hashed differently through
the normal page cache while the same bytes read with `O_DIRECT` matched the
remote SHA256. NVMe SMART remained clean (zero media/data-integrity errors).

The issue recurred after reboot while zram held only tens of KiB, so zram is not
the leading cause. It is currently an unresolved kernel/RAM/EXPO stability
issue triggered by large sequential page-cache pressure. BIOS is now `1.S2` with
EXPO1 and DDR5-6000 configured. A complete 96-file remote SHA pass and source
manifest check passed in that boot, but the full tensor verifier was stopped when
the kernel emitted another `BAD_PAGE`; no post-prune PASS report may be frozen
from that run.

`verify_reap132_checkpoint.py` uses chunked reads with
`POSIX_FADV_DONTNEED` to bound page-cache growth. Reboot into the alternate
`6.17.0-23-generic` kernel, or disable EXPO and repeat the stress pass, before
accepting the verifier report as final evidence.

## 2026-08-12 5800 MT/s follow-up

After reducing DDR5 from 6000 to 5800 MT/s, a clean 6.17 boot (`tainted=4096`)
completed a full direct-safetensors read without reproducing `BAD_PAGE`,
`compound_head`, MCE, or I/O errors. This materially improves the host
stability signal, but does not validate the checkpoint built while the system
was still at 6000 MT/s.

The verifier initially reported 49 failures. Reclassifying `gate.bias` as a
router tensor removed 41 false positives. Eight expert byte mismatches remained
stable on repeat reads, plus one stable `layers.3.attn.wo_a.weight` mismatch;
these are treated as invalid-artifact evidence. The old read-only `noMTP` and
`rerun-6.17` model directories were deleted after quarantine; logs and reports
remain under `.artifacts/`.

A new deterministic rebuild is running under 5800 MT/s in the isolated
`DeepSeek-V4-Flash-0731-HERETIC-v2-REAP132-rerun-5800` directory. It must pass
the manifest and byte verifier before any smoke or GGUF work.

The 5800 MT/s rebuild completed and its 20-file manifest passed twice, but the
first full verifier attempt triggered a `kswapd0` general-protection Oops at
`23:59:42` on 6.17. The kernel taint changed to include `DIE`; verification was
stopped and no post-prune PASS report exists. This confirms that 5800 improves
the threshold but does not establish host stability. The new output remains
read-only and quarantined.

## 2026-08-12 5600 MT/s final A/B result

With `7.0.0-28-generic` and DDR5-5600, a fresh rebuild completed, its manifest
passed twice, and the complete verifier finished without any kernel error
(`tainted=4096`). The verifier still reported five expert weight byte
mismatches. The mismatch set differs from the previous 5800-built artifact,
while router, scales, shared experts, tid2eid, HERETIC overlay, MTP absence,
and dangling-ID checks all pass.

Because the mismatches move to different experts on each rebuild despite a
fixed source and fixed plan, the remaining defect is a non-deterministic FP4
expert-weight mutation in the CUDA/streaming writer path (or its tensor
conversion), not an explained plan remap. Do not keep rebuilding or promote an
artifact until the writer preserves the raw packed weight bytes or fails hard
on any mutation.

## 2026-08-12 CPU-only control

For a direct control, the same frozen source and plan were rebuilt with
`--streaming --device cpu`, avoiding CUDA entirely. The manifest passed twice,
and the host stayed clean, but nine packed expert-weight mismatches remained.
This disproves a CUDA-only explanation: the Transformers fused expert
merge/split/reverse conversion itself is not a byte-exact representation for
these packed FP4 tensors. The fix must bypass that conversion and slice the
source safetensors payloads directly on CPU by expert ID.

The first independent raw-payload builder attempt copied about 53 GB before
the host reproduced a kernel Oops during ext4 buffered output and page
migration (`anon_vma_interval_tree_iter_first` -> `rmap_walk_anon` ->
`migrate_pages` -> `ext4_buffered_write_iter`). The raw output has no index and
is incomplete; it is quarantined. This is a separate host-stability blocker
from the FP4 conversion defect and must be resolved before trusting a large
raw rewrite.

## 2026-08-12 I/O verification gate

The raw builder's bounded writer is deliberately a chunked buffered write with
`POSIX_FADV_DONTNEED`; its helper is not an `O_DIRECT` writer because
safetensors payload offsets and lengths are not generally 4096-byte aligned.
The helper was renamed from `_direct_write` to `_chunk_write` so this distinction
is explicit.  Do not cite the builder as evidence that direct I/O was used.

`tools/verify_io_paths.py` provides the independent read-path check.  For each
regular file it computes SHA256 through an unbuffered sequential read and an
`O_DIRECT` read using aligned 4 MiB buffers; only a final unaligned tail falls
back to buffered I/O.  A file is accepted only when both digests match.  The
tool reports every missing, error, and mismatch path before returning nonzero.

The required evidence order for a future build is:

1. clean kernel boot and no `BAD_PAGE`, MCE, AER, or NVMe errors;
2. fixture and Layer 0 raw-builder preflight (`792/792`, zero mutation);
3. buffered/direct SHA256 agreement for every completed shard after `fsync`;
4. full direct provenance verifier and two byte-identical deterministic builds.

An I/O-path mismatch is an artifact/host failure, not a reason to trust the
ordinary page-cache hash or continue to native smoke/GGUF.

## 2026-08-12 current run blocked before preflight

The requested validation was not started because the first host gate already
failed on the active `7.0.0-28-generic` boot: `/proc/sys/kernel/tainted` is
`4256`, and `journalctl -k -b` contains fresh `BUG: Bad page state` entries,
`kswapd0` failures, and a kernel Oops involving `nvme_irq`.  The fixed source
directory remains read-only on ext4.  No Layer 0 or full-model read was started
under this tainted boot; otherwise its hashes would not be admissible evidence.

After a clean reboot, the Layer 0 preflight passed at `792/792`.  The first raw
Build A exposed two builder defects through the independent verifier: expert
headers used the old source name instead of the remapped output name, and router
tensors copied the first 132 contiguous rows instead of gathering the frozen
`kept_experts` rows.  The namespace bug was fixed and reduced the verifier from
33,871 failures to 86; 83 of the remaining failures were the router gather bug.
Both defects are now fixed in the builder.

The same second verifier run reported three expert-weight mismatches, but the
kernel simultaneously emitted fresh `BAD_PAGE` / `compound_head not consistent`
events and taint changed to `4128`.  Those three mismatches are not admissible
builder evidence.  Build B and further full-model reads remain blocked until a
new clean boot; the current Build A is quarantined and must not be deployed.

As a diagnostic on the already-tainted boot, MGLRU was changed from `0x0007`
to `0x0000`.  All 22 approximately 4 GB shards then passed buffered versus
`O_DIRECT` SHA256 comparison, representing roughly 170 GB of aggregate reads,
with no new `BAD_PAGE`, `compound_head`, Oops, MCE, AER, or I/O-error message.
This strongly identifies MGLRU/folio eviction as the path that exposes the bad
folio state, but does not prove that MGLRU created that state.  It is not formal
artifact evidence because the boot was already tainted `4128`.  The formal
rerun still requires a clean reboot followed by MGLRU disablement before any
large model read.

The observed `dead000000000400` mapping must not be interpreted as direct
use-after-free evidence.  Linux defines the tail-page mapping sentinel as
`TAIL_MAPPING = (void *)0x400 + POISON_POINTER_DELTA`; on this architecture that
can render exactly as `dead000000000400`.  For a valid tail page that value is
expected, while `free_tail_page_prepare()` reports corruption when the page and
folio relationship or required tail metadata do not agree.

The current causal hypotheses therefore remain separate:

1. MGLRU eviction incorrectly handles the folio lifecycle;
2. page cache, ext4 large-folio, split/free/refcount, or another MM path corrupts
   the metadata before MGLRU later discovers it;
3. RAM/IMC or DMA corrupts metadata and reclaim merely detects it.

The first two are now the leading software class.  Linux 6.16 and later include
ext4 regular-file large-folio support, matching this workload's large buffered
ext4 reads and writes.  Upstream MM/hugetlb fixes and syzbot reports have also
demonstrated that software-only folio/tail-page bugs can produce the same
`page does not match folio` and `corrupted mapping in tail page` symptom family.
These precedents support the software hypothesis but are not proof that this
host has the same upstream bug.

A stronger upstream precedent is a syzbot/KASAN reproducer from the Linux 6.18
development cycle running in a virtual Google Compute Engine environment.  Its
failure passed through `kswapd0` -> `evict_folios` -> `shrink_folio_list` ->
`filemap_release_folio` / `try_to_free_buffers` before `BAD_PAGE` and a general
protection fault.  Earlier syzbot work also reproduced the
`drop_buffers` / `try_to_free_buffers` / `shrink_folio_list` / `evict_folios`
family.  This proves that Linux MM/filesystem folio lifecycle defects can create
this class of failure without unstable physical DDR5.

It still does not prove bug identity on this host: the local stack reaches
`free_unref_folios` and `free_tail_page_prepare`, and no matching reproducer or
kernel bisect has been completed.  The evidence now makes a post-6.15 MM/ext4
large-folio reclaim regression the leading hypothesis.  The highest-value
control is Ubuntu's 6.8 GA kernel, which predates ext4 regular-file large-folio
enablement, tested first with MGLRU enabled and then disabled only if needed.
