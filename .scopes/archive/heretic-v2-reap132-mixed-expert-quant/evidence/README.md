---
description: Evidence index for K132 fixed-ratio mixed expert quantization.
---

# Evidence

Phase reports, plan files, dry-run logs, and runtime acceptance records are
added here only after their commands complete with explicit exit status. Large
model, corpus, and imatrix payloads remain outside Git under
`/data/linux-fast/models/` and are referenced by immutable identity.

## Phase 1 Evidence

- `reap132-structural-prior.json`: accepted T001 structural-prior report built
  from archived K96 score-report SHA256
  `ae090c1b70b476d7f116827d9342f8d2a7ff68ee36996912ce33a42735c47bfa`.
  It contains 43 layers and has logical SHA256
  `4493d0e9917aa66da70454d68a1b88e8ba0fd5d9730f6a58d8a19d7291a7e64f`.
  Two independent CLI generations were byte-identical, and the focused test
  suite passed `2/2` tests.
- `reap132-calibration-corpus.json`: accepted T002 corpus contract and published
  artifact identity. Two generations were byte-identical; the 205,333-token
  corpus SHA256 is `aa7a2c175055ea390043928316aedd2c3bb86f70be2a44cd19ac06ff38b65688`,
  its manifest SHA256 is
  `17e589258527dab5337d3764e0932ec849e0362783688537a0ff1b9adb9e6cb3`,
  and focused tests passed `3/3`.
- `reap132-imatrix-audit.json`: accepted 100/200-stage coverage and stability
  audit. The accepted 200-chunk external GGUF is
  `/data/linux-fast/models/calibration/reap132-imatrix-200-full-iq4.gguf`, size
  `251,942,912`, mode `0444`, SHA256
  `f528ab31b7167cfbbdcb65995b77d6c7ffa3115fac70f64874b340bf607897f2`.
- `reap132-imatrix-old-vs-corrected-comparison.json` and
  `reap132-imatrix-corrected-golden-ranking-decision.json`: same-corpus,
  same-200-chunk comparison against a fresh corrected-Golden imatrix. Raw-I
  Spearman is `1.0`; all 43 Rank-I and Rank-P positions are identical; both
  Top17 churn values are zero. The accepted imatrix and frozen 17/26 plan are
  retained. The corrected-Golden comparison imatrix is read-only at
  `/data/linux-fast/models/calibration/reap132-imatrix-200-corrected-golden.gguf`,
  SHA256 `affa578a...75b7`.

## Phase 2 Evidence

- `reap132-golden-mxfp4-exponent-audit.json`: rejection evidence for the old
  K132 GGUF, including three tensors and six abnormal exponent blocks.
- `reap132-mxfp4-full-provenance.json`: full routed-provenance rejection of the
  fresh converter intermediate after a separate 64-byte mutation.
- `reap132-mxfp4-full-routed-rebuild-provenance.json`: accepted 100% byte-exact
  routed provenance for the corrected Golden: 129 tensors, 17,028
  projection-expert comparisons, and 75,884,396,544 compared bytes.
- `reap132-corrected-golden-acceptance.json`: combined corrected Golden PASS;
  path ends in `full-routed-rebuild.gguf`, O_DIRECT SHA256 `752a0146...cfdd`.

- `reap132-mixed-quant-plan.json` and
  `reap132-mixed-quant-tensor-ftypes.txt`: frozen deterministic 17/26 assignment
  bound to hardened llama.cpp
  `efb81abc6a261dcceb014e853beb0ffc5e4a49a0`. Current plan SHA256 is
  `9f87f453...c3ef7`; logical SHA256 is `49b9c651...88d2`. The tensor-ftype SHA256 remains
  `db05988dd60a8262f353e70360a1a85a7ebb585bec9539fb7f70fe73f7c0269e`;
  only the executable provenance changed.
- `reap132-mixed-quant-plan-verification.json`: independent plan PASS.
- `reap132-mixed-quant-corrected-golden-dry-run.log`: complete DIO dry-run from
  the corrected Golden under the pinned binary. Predicted output size is
  `55,348,319,104` bytes.
- `reap132-mixed-quant-dry-run-verification.json`: complete 1,328-tensor
  inventory PASS, including 51 IQ3_XXS, 73 Q2_K, five Q4_K routed promotions,
  43 Q5_K attention-KV promotions, and 62 unchanged compressor APE tensors.
- `reap132-mixed-quant-hardened-dry-run.log` and
  `reap132-mixed-quant-hardened-dry-run-verification.json`: post-reboot dry-run
  and independent PASS under build `264 (5b0c905)`. The predicted size and all
  type counts are unchanged from the frozen plan.
- `reap132-mixed-quant-cpu-nvme-dry-run.log` and its verification JSON: final
  `efb81ab` CPU-attached-NVMe dry-run PASS with the same exact size and types.

## Removed Payloads

The old K132 canonical GGUF, the mutated full-converter intermediate, K96 MXFP4,
and K96 IQ4_XS GGUF were deleted from `/data/linux-fast/models` on 2026-08-13
with explicit user authorization. Their reports remain historical evidence only.

## Interrupted Production Evidence

- `reap132-mixed-quant-production-interrupted-boot-20260813T1129.log`: the first
  corrected-Golden production run reached tensor 943/1328 before an unclean
  host restart. The 39.2 GB staging file was never atomically published and was
  deleted. Sysstat showed 27-28% RAM use, 32-33 GiB available, and zero swap;
  neither kernel OOM killer nor systemd-oomd fired. The prior boot did contain
  a separate `codex-main` SIGSEGV, so no artifact from that boot is admissible.
- `reap132-mixed-quant-production-clean-retry.log`: the second run rejected a
  transient NaN in `blk.4.ffn_down_shexp.weight` and exited 1. Sixteen seconds
  later the kernel reported `list_del` corruption in `free_pcppages_bulk`, then
  a `0xdead000000000122` GPF in the same allocator path and a CPU hard lockup.
  There was no OOM action, swap use, NVMe error, MCE, or EDAC report. The exact
  failed block reread byte-identically after reboot, so this is a host/kernel
  memory-lifecycle incident rather than persistent GGUF corruption.

## CPU-NVMe Production Candidate

- `reap132-mixed-quant-production-cpu-nvme.log`: final `efb81ab` production run
  completed `1328/1328`, exited zero, and published exactly `55,348,319,104`
  bytes on the CPU-attached root NVMe.
- `reap132-mixed-quant-cpu-nvme-acceptance.json`: independent full inventory
  PASS with 51 IQ3_XXS, 73 Q2_K, five Q4_K routed tensors, 600 unchanged tensor
  comparisons over `63,307,072` bytes, zero unstable reads, and zero failures.
- `reap132-mixed-quant-cpu-nvme-odirect-sha256.txt`: root-NVMe candidate
  O_DIRECT SHA256 `67e6990f35db44711c881aee2b55ca789144bec2c0063df2e78957555ea77ab3`.
- The post-production boot has zero OOM, BAD_PAGE, compound-head, page-list,
  Oops, GPF, hard-lockup, I/O/AER/hardware-error, or NVIDIA Xid signatures.
- The direct-I/O copy to the final `/data/linux-fast` path matched this hash,
  passed the final verifier, and was made mode `0444` before runtime testing.

## Phase 4 Runtime Decision

- `reap132-mixed-quant-final-acceptance.json` and
  `reap132-mixed-quant-final-odirect-sha256.txt`: final-path structural PASS and
  immutable identity.
- `reap132-mixed-quant-runtime-acceptance.json`, short probes, long-prefill
  response, and runtime log: infrastructure PASS but semantic FAIL. Chat,
  Chinese, JSON, Python, and 32K-prefill decode showed empty final content or
  repeated `<` output.
- `reap132-mixed-vs-mxfp4-runtime-ab.json`: controlled same-commit/runtime A/B.
  Corrected MXFP4 produced coherent Chinese, valid JSON, and valid Python under
  the same flags and requests, isolating the collapse to the mixed weights.
- Regional ftype selection, packed-expert imatrix order, MXFP4 CPU
  dequantization, and CUDA `MUL_MAT_ID` with 132 experts/top-6 were audited; no
  implementation defect was found. The mixed artifact is rejected for
  deployment and corrected K132 MXFP4 is the sole runtime target.
