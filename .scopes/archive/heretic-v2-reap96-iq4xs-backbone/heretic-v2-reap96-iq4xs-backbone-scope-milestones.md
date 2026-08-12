---
description: Scope boundaries and milestones for the K96 Profile A IQ4_XS release.
---

# heretic-v2-reap96-iq4xs-backbone Scope and Milestones

## In Scope

- Add quantizer direct-I/O input and atomic direct-I/O output support to the
  pinned llama.cpp fork.
- Run one Profile A dry-run with the K96 Golden as immutable input.
- Produce one Profile A `MXFP4exp-IQ4XSbb` GGUF if the dry-run and clean-boot
  gates pass.
- Verify metadata, unchanged routing data, and byte-identical MXFP4 expert
  payloads through aligned direct I/O.
- Run the single artifact through the established dual-5090 acceptance suite.

## Out of Scope

- Editing, replacing, or rebuilding the K96 MXFP4 Golden.
- Reopening K96 consensus scoring, survivor selection, or `tid2eid` generation.
- Profile B, `--pure`, imatrix, IQ3, Q2, or any alternative quantization.
- Comparing Profile A against another quantization profile.
- Treating this artifact as a fix for the known K96 semantic quality loss.
- Changing the canonical K132 deployment artifact unless this independent
  release completes every gate and the user makes a separate promotion decision.

## Decisions

| Decision | Result |
|---|---|
| Input source | Immutable K96 MXFP4 Golden only |
| Expert handling | 129 MXFP4 payloads preserved byte-for-byte |
| Shared Expert | No override; IQ4_XS default mixed policy |
| Core Backbone | IQ4_XS default mixed policy |
| Router / `tid2eid` / norms | Source type, unchanged |
| Strict profile | Prohibited; no `--pure` fallback |
| Importance matrix | Not used |
| Size gate | `< 60,000,000,000` bytes; stop on miss |
| Large-file I/O | Aligned direct I/O only |
| Runtime comparison | Profile A against recorded K96 Golden baseline only |

## Decision Log

| Boundary / Decision | Evidence Source | Evidence Strength | Conflict | Confidence | Confidence Reason | Result |
|---|---|---:|---|---:|---|---|
| Run Profile A only | Explicit user direction | 5 | None | 5 | No profile A/B is permitted | Accepted |
| Preserve only Routed Experts | Golden inventory and user tensor classification | 5 | Shared Expert naming contains FFN terms | 5 | Exact regex matches 43 x 3 routed tensors only | Accepted |
| Default-mix Shared Expert and Core Backbone | llama.cpp dry-run type selection | 5 | Sensitive tensors auto-promote | 5 | This is the intended non-pure mixed policy | Accepted |
| Require post-build expert finalization | Two rejected provenance reports | 5 | Adds one full O_DIRECT rewrite | 5 | Stable sparse expert drift otherwise violates the release contract | Accepted |
| Keep K132 deployed | Recorded K96 semantic baseline | 5 | IQ4_XS runtime itself passes | 5 | Compression does not repair K96 survivor quality | Accepted |

## Milestones

### M1 - Scope and DIO quantizer

Create the independent release branch and scope, implement direct-I/O input and
atomic direct-I/O output for `llama-quantize`, and pass focused fixture tests.

Exit: rebuilt quantizer exposes both DIO flags; fixture quantization proves
direct input, direct staging, synchronization, atomic publication, and dry-run
non-creation behavior.

### M2 - Profile A production artifact

Run the Profile A dry-run. If it predicts a result under the size gate, execute
the formal clean-boot quantization with no concurrent payload scans.

Exit: quantizer exits zero, the current boot remains clean, the final output is
published atomically, and its size is under the required limit.

### M3 - Provenance and runtime release gate

Create the O_DIRECT content manifest and strict acceptance report, including
129/129 byte-identical expert payload checks, then run the established dual-GPU
runtime suite.

Exit: all structural, payload, routing, metadata, numerical, runtime, memory,
and kernel-health gates pass. Otherwise preserve evidence and do not promote.

All three milestones are complete. The accepted release is
`59,256,121,472` bytes with O_DIRECT SHA256
`845a0b91d17fddd6990068b995c8af031945af55f5bff94acc5a1c08389c63c3`.
It is a validated independent K96 release, not the deployed K132 replacement.

## Stop Conditions

- The Golden path, size, SHA256, or permissions differ from the immutable input
  contract.
- Current boot contains BAD_PAGE, compound-head corruption, Oops, GPF, Xid, or
  an unexplained process SIGSEGV.
- Dry-run predicts `>= 60,000,000,000` bytes.
- Fewer or more than 129 expert tensors match the lock regex.
- Any expert tensor changes type or payload.
- Quantizer DIO output cannot guarantee failure-safe atomic publication.
