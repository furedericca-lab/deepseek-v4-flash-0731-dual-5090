---
description: Canonical architecture for the K96 consensus candidate pipeline.
---

# heretic-v2-reap96-consensus Technical Documentation

## Canonical Architecture

```text
immutable K132 plan
        +
small pinned external masks/plans
        |
        v
normalized original-ID evidence store
        |
        v
lineage-aware overlap and score report
        |
        v
K96 subset plan + regenerated hash routing
        |
        v
existing deterministic O_DIRECT builder and verifier
        |
        v
separate K96 MXFP4 candidate and dual-5090 acceptance
```

## Key Constraints and Non-Goals

K132 source/release files are immutable. The K96 plan must contain original
expert IDs until the existing raw-copy builder compacts them. `tid2eid` is the
only special routing payload and uses K96 compact IDs. No full buffered scan,
external weight download, fresh calibration, or alternate quantization is
allowed.

## Major Decisions and Trade-offs

- Preserve K132 as the candidate universe. This sacrifices the possibility of
  recovering a K132-pruned expert, but keeps K96 causally comparable to the
  accepted release.
- Prefer published mask/plan provenance over model payload inspection. This
  reduces evidence collection to small, reviewable files and avoids unsafe
  large buffered reads or unnecessary external-weight downloads.
- Keep consensus selection transparent instead of using a raw intersection.
  Exact K96 cardinality requires a deterministic score/tie-break report, while
  source nesting is verified before a source is treated as an ordinal tier.
- Regenerate hash routing for K96. Reusing K132 routing would create dangling
  compact expert IDs and is invalid even if the 96 original experts are valid.

## Module Boundaries and Data Flow

The implemented Phase 1/2 scripts own evidence normalization, overlap
reporting, consensus scoring, K96 plan/hash-routing construction, and
independent plan verification. Existing production scripts continue to own
source manifest creation, O_DIRECT build, byte verification, GGUF conversion,
provenance, and runtime startup. The evidence lock is tracked JSON; model
artifacts remain under `/data/linux-fast` and outside git.

The frozen plan selects 4,128 experts (`43 x 96`) from 5,676 K132 candidates.
Selection sorts by total score, the ordered evidence vector, K216's complete
semantic rank, and only theoretically by original expert ID. Forty-two layers
have a score tie at the 96/97 boundary: three resolve by evidence vector and 39
by K216 semantic rank. No boundary reaches expert ID. K216 rank is a secondary
ordering from the existing 0xSero lineage, not an additional vote.

The Layer 0-2 routing generator preserves surviving assignments and replaces a
deleted K132 compact expert with the nearest available K96 router row by squared
L2 distance, excluding IDs already present in the same token row. The resulting
tables are `[129280, 6]` int64, range `0..95`, row-wise distinct, and cover all
96 compact experts.

## Interfaces and Contracts

The normalized evidence and K96 plan contracts are defined in
`heretic-v2-reap96-consensus-contracts.md`. Scripts must emit JSON reports with
input digests and no implicit network state. A non-passing report prevents plan
generation or downstream build work.

## Security and Reliability

Use the authenticated `hf` CLI only for authorized Hugging Face retrieval.
Pin revisions before downloading small files; reject HTML/error bodies and
verify SHA256. Never place credentials, full model data, or GGUF data in the
repository. Require the existing clean-boot and direct-I/O gates before any
large build or verification.

## Test Strategy

Run focused pytest for new consensus scripts, schema and synthetic routing
fixtures, repo-task scope checks, wiki rebuild/lint/doctor, and `git diff
--check`. Candidate release work additionally inherits the existing full
O_DIRECT checkpoint, GGUF provenance, and llama.cpp API/runtime acceptance
matrix.
