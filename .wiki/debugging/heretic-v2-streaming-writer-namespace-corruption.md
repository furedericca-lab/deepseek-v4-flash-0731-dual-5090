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
