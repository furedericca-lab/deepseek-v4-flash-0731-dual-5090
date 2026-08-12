---
description: Decision framing for a K96 subset of the immutable REAP132 survivor universe.
---

# heretic-v2-reap96-consensus Brainstorming

## Problem

The completed REAP132 deployment is valid but its 85 GB MXFP4 GGUF leaves about
26 GB of weights in host RAM. The new work seeks a smaller K96 candidate without
re-running REAP calibration or changing the accepted K132 release.

## Scope

For every one of 43 layers, select exactly 96 original expert IDs from that
layer's existing 132 K132 survivors. Rank candidates using independently
published REAP masks/plans, regenerate legal hash-layer routing for the new
set, then build and validate a separate artifact only after the plan passes all
data-contract gates.

## Constraints

- K96 is strictly a subset: `K96(layer) subset K132(layer)`.
- Never redownload or derive alternate model weights for evidence collection.
- External evidence is restricted to immutable small text/JSON plans, masks,
  manifests, and router slices where needed for exact identity recovery.
- K132's plan, native checkpoint, canonical GGUF, and deployment remain
  immutable and deployable throughout this scope.
- K96 hash-layer `tid2eid` cannot reuse K132 routing tables; it must be
  regenerated from the new keep set and prove all IDs are in `0..95` with no
  duplicate row entries.

## Options

| Option | Benefits | Rejected Risk |
|---|---|---|
| Re-run REAP calibration at K96 | Direct task-specific saliency | Violates frozen-plan decision and adds a large calibration variable |
| Choose arbitrary K96 from 256 experts | Maximum search freedom | Reintroduces experts K132 already rejected and loses accepted baseline continuity |
| K132 subset scored by independent masks | Preserves baseline while incorporating independent evidence | Requires schema/lineage audit and explicit tie-breaking |

## Decision Summary

Use the K132-subset consensus method. Treat puwaer K132 as the candidate
universe, 0xSero K160/K216 as one lineage with ordinal tiers, puwaer K178 as a
separate run whose subset relationship must be measured rather than assumed,
and Blivion K192 plus REAP25 K192 as independent supplemental signals. REAP25
only applies to Layers 3-42. True2456 K163 is deferred until the first overlap
report establishes a need for a fifth signal.

## Risks

- Published masks may use compact expert IDs, a non-native schema, or a
  different base revision. Evidence is rejected unless original 0..255 identity
  is proven per layer.
- K160/K216 may not be nested. If not, they are treated as two masks, not
  ranking tiers.
- Consensus support does not prove K96 semantic quality. The final K96 artifact
  requires the same O_DIRECT checkpoint, GGUF provenance, and dual-5090 runtime
  acceptance as K132.

## Open Questions

- Can all four required published evidence sources be obtained as small,
  revision-pinned machine-readable files?
- What per-layer agreement distribution and tie-break rule produce 96 experts
  without an unreviewed arbitrary boundary?
