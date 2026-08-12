---
description: Evidence-backed design choices for the K96 Profile A IQ4_XS release.
---

# K96 Profile A IQ4_XS Implementation Research Notes

## Considered Designs

| Design | Benefits | Cost / Risk | Result |
|---|---|---|---|
| Profile A default mixed policy | One controlled quantization variable | Shared Expert is not specially protected | Selected |
| Profile B with `--pure` | Smaller possible output | User prohibited it and quality protections disappear | Rejected |
| Shared Expert fixed Q8_0 | Conservative per-token path | Adds an unsupported local policy | Rejected |
| Routed Experts allowed to requantize | Simpler CLI | Destroys immutable MXFP4 provenance | Rejected |

## Decision Roundtable

| Decision | Requirement Clarity | Evidence Strength | Evidence Source | Conflict | User-Intent Confidence | Implementation Confidence | Risk/Reversibility | Confidence Reason | Outcome |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| Profile A only | 5 | 5 | Explicit user instruction | None | 5 | 5 | 5 | No A/B or pure fallback is allowed | Accepted |
| Routed Experts remain byte-identical MXFP4 | 5 | 5 | Golden tensor inventory and strict provenance | `--allow-requantize` affects other tensors | 5 | 5 | 5 | Exact 129-tensor regex and payload verifier isolate this class | Accepted |
| Shared Expert uses default mixed policy | 5 | 5 | Dry-run and final type inventory | Five early down tensors promote to Q5_K | 5 | 5 | 5 | Promotion is llama.cpp's built-in quality policy | Accepted |
| Add expert finalizer | 5 | 5 | Two rejected full provenance scans | Adds another bulk pass | 5 | 5 | 4 | Stable sparse drift made a post-build rewrite necessary | Accepted |
| Do not promote over K132 | 5 | 5 | K96 Golden/native France differential | Runtime stability passes | 5 | 5 | 5 | IQ4_XS retains the known K96 semantic limitation | Accepted |

## Selected Design

Quantize the immutable K96 Golden once with non-pure IQ4_XS and an exact MXFP4
override for the 129 Routed Expert tensors. After a clean quantizer exit,
restore those 129 payloads from the Golden through aligned O_DIRECT and run a
stable double-read verifier. Accept the independent artifact only after direct
SHA256 and dual-5090 runtime gates. Keep K132 as the deployment artifact.
