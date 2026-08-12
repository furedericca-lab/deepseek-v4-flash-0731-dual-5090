---
description: Execution checklist for the K96 Profile A IQ4_XS release.
---

# Phases Checklist: heretic-v2-reap96-iq4xs-backbone

| Phase | Status | Exit evidence |
|---|---|---|
| Phase 1 | Complete | DIO quantizer implementation and focused tests |
| Phase 2 | Complete | Profile A dry-run and 59,256,121,472-byte artifact |
| Phase 3 | Complete | Strict provenance, SHA256, and dual-5090 runtime acceptance |

## Locked Rules

- One immutable K96 Golden input.
- One Profile A output.
- No Profile B, `--pure`, imatrix, or quantization-profile A/B.
- No changes to K96 experts, routing, or Golden payloads.
- No full buffered access to model files.

## Release Result

- Canonical output is read-only and has O_DIRECT SHA256
  `845a0b91d17fddd6990068b995c8af031945af55f5bff94acc5a1c08389c63c3`.
- 129/129 routed experts and 46/46 routing tensors are byte-identical to the
  Golden after the required O_DIRECT expert finalizer.
- Dual-5090 64K startup, OpenAI API, Chinese, JSON, Python, and 32,767-token
  prefill passed without kernel or NVIDIA faults.
- The known K96 France-prompt quality failure remains. K132 remains deployed.

## Closeout Evidence Boundary

- The accepted candidate has the same tensor namespace as the immutable K96
  Golden, so the zero-MTP/DSpark namespace result is directly inherited and
  verified by the final acceptance report.
- The quantizer validated every newly quantized row and the candidate passed
  the full 64K runtime probe set without non-finite runtime behavior. A separate
  exhaustive post-quantization NaN/Inf payload-scan report was not retained;
  this is an evidence-granularity limitation, not an observed artifact defect.
- Runtime evidence used the fork whose release changes were pushed at
  `2abf1748cc91d64f6ead12ed535a71cb05fd6d3d`; the binary's embedded upstream
  build metadata remains `1e17097be2c19c7ae4ff4f635fef25f24f25dbd2`.
- Archived REAP132 rules that excluded IQ3/Q2 remain preserved for the original
  REAP132 delivery scope. This independent K96 release extended quantization
  work without changing the K132 deployment artifact.
- The archived K96 consensus record is preserved as upstream evidence. This
  release does not reopen its survivor scoring or hash-routing decisions.


## Archive Record

- Archived on 2026-08-13 under `.scopes/archive/heretic-v2-reap96-iq4xs-backbone/`.
- Archive purpose: preserve the completed heretic-v2-reap96-iq4xs-backbone audit trail.
- Future enhancements should use a new `repo-task-driven` scope under `.scopes/<enhancement-scope>/`.
- Archived docs should only change for factual errata or path-maintenance updates.
