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
