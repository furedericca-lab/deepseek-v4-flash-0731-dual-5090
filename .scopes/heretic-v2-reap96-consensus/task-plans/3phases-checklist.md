---
description: Execution and verification checklist for the K96 consensus candidate.
---

# Phases Checklist: heretic-v2-reap96-consensus

## Input

- `.scopes/heretic-v2-reap96-consensus/` contract, milestones, and research notes
- immutable `squanchyzx-puwaer-reap132-mask.json`
- archived REAP132 delivery audit record

## Rules

- This is the active K96 audit hub; update after each evidence or implementation batch.
- K132 remains immutable and deployable until a separate K96 release passes.
- Do not mark work complete without stored command output/report paths.

## Global Status Board

| Phase | Status | Completion | Health | Blockers |
|---|---|---:|---|---|
| Phase 1 | Complete | 100% | Healthy | Six normalized sources; REAP25 map recovered from its linked ds4 source branch |
| Phase 2 | Complete | 100% | Healthy | Frozen deterministic plan and independently verified hash routing |
| Phase 3 | In progress | 50% | Healthy | Native A/B accepted; GGUF and runtime gates remain |

## Phase Entry Links

1. [Phase 1](phase-1-heretic-v2-reap96-consensus.md)
2. [Phase 2](phase-2-heretic-v2-reap96-consensus.md)
3. [Phase 3](phase-3-heretic-v2-reap96-consensus.md)

## Phase Execution Records

### Phase 1

- Completed: authenticated `hf` retrieval; revision and digest lock for all
  inspected small files; normalized K216, Blivion K192, REAP37 K163, native
  K160, native K178, and REAP25 K192 masks; six-source overlap report; focused schema and
  extraction tests pass.
- Evidence: `evidence/upstream/`, `evidence/normalized/`, and
  `evidence/reap96-phase1-overlap.json`. No external model shard or GGUF
  payload was downloaded.
- Native evidence: K160 completed 43/43 exact base-to-pruned router recoveries
  at logical SHA `ccb46a9f...25596`; K178 completed 43/43 at
  `09f66d74...82200`. The extractor uses official `HfFileSystem` bounded
  reads with fsspec read-ahead disabled and atomic layer fragments, preserving
  the exact matching algorithm while making Xet request stalls resumable.
- Nesting result: `K132 subset K178` and `K160 subset K216` both hold on
  43/43 layers. K132/K160 intersection is 116-127 experts per layer
  (mean 121.14). REAP25 is accepted for Layers 3-42 from the linked ds4
  `reap-compact-support` branch's published 64.8KB B-exact recovery map.
- Phase 1 handoff: the evidence lock and overlap report were accepted as the
  immutable inputs to the now-complete Phase 2. No external model weights or
  GGUF payloads were used.

### Phase 2

- Completed: deterministic scoring is stored at
  `evidence/reap96-phase2-score-report.json`. It selects 96 candidates per
  layer. The 96/97 score boundary ties in 42/43 layers; three resolve through
  the evidence vector and 39 through K216's complete published semantic rank.
  No actual boundary uses expert ID.
- Frozen plan: `evidence/heretic-v2-reap96-consensus-plan.json`, file SHA
  `578adbbd4ac13bec75f5ab726e6406f9bec50ec8154f6d773d9c5bd83105be11`,
  logical SHA `e82c3649af2607e798b88e39ac0dd9a4b71dc3b31b5f4f17b60fc12aa74c01cf`.
- New Layer 0-2 routing tables are `[129280,6]` int64, range `0..95`, use all
  96 experts, and all 129,280 token rows contain six distinct IDs. Independent report
  `evidence/reap96-phase2-plan-verification.json` is PASS; a second generation
  was byte-identical.
- Final pre-build gates: score report contains exactly 4,128 selected experts
  (`5:1969, 4:1867, 3:277, 2:15`) and 1,548 deleted experts
  (`4:309, 3:913, 2:293, 1:31, 0:2`). The earlier 4,171 summary was a reporting
  bug that counted one boundary row per layer twice; the frozen JSON and plan
  were not changed. All three hash tables pass shape, dtype, range, row-wise
  six-ID distinctness, and 96/96 coverage gates.
- Routing closeout: normalized cosine is canonical and raw L2 is preserved only
  as superseded audit evidence. Raw L2 versus cosine changed 89/108 primary
  replacements and 481,044 actual slots. Cosine global assignment improved the
  deterministic greedy objective by only 0.0225%, so greedy remains frozen.

### Phase 3

- Native build/provenance complete. The accepted K132 manifest re-check passed
  at `9175b915...e5d`. Builds A and B were independently verified and their 22
  manifest entries matched path/size/SHA256 at `62e40f7c...574ed`, covering
  `63,989,574,313` bytes. Build B is the read-only canonical K96 native source at
  `/data/linux-fast/models/DeepSeek-V4-Flash-0731-HERETIC-v2-REAP96-noMTP`;
  Build A was deleted after A/B acceptance.
- GGUF conversion/provenance complete. The read-only K96 MXFP4 candidate is
  `64,340,873,568` bytes with O_DIRECT SHA256 `697309d1...ff31`; metadata reports
  `deepseek4`, 43 blocks, 96 experts, six active experts, 1,328 tensors, and
  `MOSTLY_MXFP4_MOE`. Expert, nonexpert, and FP8-backbone provenance passed
  108 of 108, 7 of 7, and 104 of 104. Dual-5090 runtime acceptance remains
  pending.

## Final Release Gate

- K96 plan is a fully explained 96-of-132 subset in every layer.
- K96 does not reuse K132 hash routing.
- The separate K96 artifact passes the existing O_DIRECT, provenance, and
  dual-5090 runtime gates.
- K132 remains canonical if any K96 gate fails.
