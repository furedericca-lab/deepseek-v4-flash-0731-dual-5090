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
