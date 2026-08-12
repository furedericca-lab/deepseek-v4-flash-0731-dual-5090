---
description: Data contracts and validation rules for the K96 consensus plan.
---

# heretic-v2-reap96-consensus Contracts

## Evidence Contract

Each external evidence record must contain its Hugging Face repository,
immutable revision, source URL, retrieval timestamp, SHA256, declared K,
covered layers, original-ID recovery method, and lineage.

The target first round is puwaer K178, 0xSero K160/K216, Blivion K192, and
REAP25 K192. A target is not an accepted input merely because its model card
claims a plan exists. For every native checkpoint whose published metadata lacks
a complete survivor map, run the project's byte-exact base-to-pruned router-row
extractor; K160 and K178 both completed 43/43 exact recovery through this
path. K216, Blivion K192, and optional REAP37 K163 are normalized. The current
REAP25 is accepted for Layers 3-42 through its linked, revision-pinned ds4
source branch's published B-exact recovery map. Any source that cannot prove
original IDs in `0..255` is excluded from scoring.

## Consensus Input Schema

Normalized masks use JSON with `schema: reap-expert-mask-v1`, a `source` object,
and `layers["0".."42"].kept_experts`. Each list is sorted, unique, has the
source-declared K, and contains original IDs in `0..255`.

## Consensus Output Schema

The K96 plan uses `schema: heretic-reap96-consensus-v1`, references the K132
file and logical SHA256, declares 256 input and 96 output routed experts, and
stores exactly 96 sorted original IDs for every layer. It includes the
source-evidence digests, per-expert score/tie-break provenance, and newly
generated compressed `tid2eid` blobs for Layers 0-2.

Selection order is consensus score, full evidence vector, K216's complete
published per-layer semantic rank, then original expert ID only as a stable
fallback. The frozen result uses no expert-ID fallback at a 96/97 boundary.
K216 semantic rank is not an additional lineage vote: it is finer-grained
ordering from the same 0xSero lineage and is consulted only after all discrete
evidence is tied.

## Validation and Compatibility Rules

- Every K96 keep set is a subset of its K132 keep set.
- Every layer has exactly 96 unique IDs in `0..255`.
- Evidence revisions and payload SHA256 values must match the provenance lock.
- Normalization rejects incomplete layers, compact IDs without recovery proof,
  unexpected K, duplicate IDs, and mixed lineage labels.
- K96 hash routing must have shape `[129280, 6]`, map only to compact IDs
  `0..95`, have six distinct IDs within every token row, cover all 96 compact
  experts across the table, and be regenerated rather than
  copied from K132.
- The plan remains a candidate until a new deterministic builder, O_DIRECT
  verifier, GGUF provenance checks, and llama.cpp runtime acceptance pass.

## Requirement Boundary Notes

No external model or GGUF weights are evidence inputs. No calibration, new
saliency run, puwaer A/B, IQ3, Q2, or native CUDA root-cause debugging is in
scope. The canonical REAP132 release is not a test fixture to overwrite.
