---
description: Scope boundaries and milestones for heretic-v2-reap96-consensus.
---

# heretic-v2-reap96-consensus Scope and Milestones

## In Scope

- Collect and pin small published mask/plan evidence from the agreed lineages.
- Normalize proven original expert IDs and produce an overlap/agreement report.
- Create a K96 subset plan and new legal hash-layer routing.
- Build, verify, convert, and evaluate a separate no-MTP K96 candidate only
  after its plan is accepted.

## Out of Scope

- Editing or rebuilding the accepted REAP132 plan, checkpoint, or canonical GGUF.
- Re-running REAP calibration, saliency, HERETIC, puwaer A/B, IQ3, Q2, or any
  alternative quantization.
- Downloading external model-weight or GGUF files for consensus evidence.
- Extending native PyTorch/cuBLAS runtime debugging.

## Decision Log

| Boundary / Decision | Evidence Source | Evidence Strength | Conflict | Confidence | Confidence Reason | Result |
|---|---|---:|---|---:|---|---|
| K96 is a K132 subset | User direction and accepted K132 artifact | 5 | None | 5 | Prevents reintroducing already rejected experts | Accepted |
| Use independent masks as rank evidence | User direction | 5 | Schema identity may differ | 4 | Requires strict normalization before scoring | Accepted |
| K160/K216 are one lineage | 43/43 exact K160 recovery plus pinned K216 plan | 5 | None | 5 | K160 is a K216 subset in all layers | Accepted |
| K132/K178 are ordinal puwaer tiers | 43/43 exact K178 recovery plus frozen K132 plan | 5 | None | 5 | K132 is a K178 subset in all layers | Accepted |
| Frozen K96 provenance | Phase 2 score and plan reports | 5 | 0xSero is deliberately dominant | 5 | K132 is the hard universe; 0xSero supplies ordinal evidence; independent sources resolve boundaries | Accepted |
| K132 remains deployment baseline | Existing passed release gates | 5 | None | 5 | K96 native is accepted, but GGUF/runtime gates are pending | Accepted |

## Milestones

## Frozen Plan Risk Classification

- Provenance: K132-constrained, 0xSero-dominant, multi-source boundary
  consensus. Blivion, REAP25, and REAP37 are independent boundary evidence;
  K216 semantic rank is a same-lineage secondary rank, not another vote.
- Pruning depth: aggressive-but-evidence-guided. No 5-score expert is removed,
  but 309 of 1,548 removals score 4 and 36 learned-router layers must remove at
  least one 4-score candidate. Quality loss at K96 may therefore reflect the
  target cardinality rather than a builder defect.
- Hash routing: early static token routing is the largest semantic risk. K96
  rewrites 166,235/775,680 slots in Layer 0 (21.43%), 195,398 in Layer 1
  (25.19%), and 235,655 in Layer 2 (30.38%). Structural validation proves
  range and row-wise distinctness, not semantic equivalence to K132.

### M1 - Evidence lock and normalized masks

Pin approved small artifacts, normalize original expert IDs, and record each
source's coverage, revision, digest, and lineage.

Exit: five-or-fewer evidence masks pass schema and identity validation; sources
without machine-readable proven identity are excluded rather than guessed.

### M2 - Consensus K96 plan

Compute layer-wise overlap reports and select 96 K132-subset experts per layer
with deterministic score and tie-breaking. Regenerate and validate all three
hash-layer routing tables.

Exit: a reviewable K96 plan passes structural, subset, source-digest, and
tid2eid legality checks. This milestone is complete and immutable.

### M3 - Candidate release gates

Build the separate no-MTP K96 checkpoint using production direct-I/O,
independently verify it, generate MXFP4 GGUF, and run the dual-5090 llama.cpp
acceptance suite.

Exit: K96 is promoted only if every gate passes; otherwise K132 remains sole
deployment artifact and the failure is recorded without altering it.

Native sub-gate: complete. Deterministic Builds A/B matched all 22 manifest
entries and passed independent verification. Build B is the read-only canonical
K96 native source.

GGUF sub-gate: complete. The pinned direct-I/O converter produced a read-only
`64,340,873,568`-byte MXFP4 candidate at O_DIRECT SHA256 `697309d1...ff31`.
Metadata and all three payload-provenance classes passed. The runtime sub-gate
remains open, so K132 is still the deployed artifact.

## Dependencies

M1 blocks M2. M2 blocks all large checkpoint work. M3 depends on a reviewed M2
plan and a clean-boot kernel gate.

## Exit Criteria

- Evidence provenance and overlap report are reproducible from pinned files.
- K96 plan is deterministic, legal, and separate from K132.
- Any K96 release uses the existing O_DIRECT and runtime validation policy.

## Escalation Triggers

- An evidence source has no immutable revision, digest, or original-ID proof.
- A required source is unavailable as a small artifact and would require
  downloading model weights.
- Nested-mask assumptions fail or the consensus tie boundary cannot be explained
  by stored scores.
- A K96 plan, verifier, or runtime gate contradicts the immutable K132 baseline.
