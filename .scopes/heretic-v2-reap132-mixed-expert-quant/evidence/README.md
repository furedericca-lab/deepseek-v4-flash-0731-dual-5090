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
