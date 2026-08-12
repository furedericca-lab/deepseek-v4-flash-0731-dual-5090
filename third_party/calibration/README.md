# Calibration Source Snapshots

This directory keeps the small, immutable upstream inputs needed to reproduce
the K132 imatrix calibration corpus without relying on future network access.
Model weights, GGUF files, Hugging Face caches, credentials, and generated
calibration outputs do not belong here.

## eaddario/imatrix-calibration

`eaddario-imatrix-calibration-e87ed55/` is a byte-identical subset of:

```text
dataset:  eaddario/imatrix-calibration
revision: e87ed55dcba9d9c3a3e41539f3e728e981b1daa4
license:  MIT, as declared by the upstream dataset card
```

The five micro parquet files are the actual source inputs for the K132 corpus.
Their upstream data card is preserved as `README.upstream.md`.

## 0xSero REAP metadata

`0xsero-deepseek-v4-flash-0731-reap-ddc04540/` is a byte-identical metadata
subset of:

```text
model:    0xSero/DeepSeek-V4-Flash-0731-REAP
revision: ddc04540efda3d2a0788b129f1fad828ddc19b60
license:  MIT
```

This snapshot records the REAP observation lineage and category composition.
It is not a calibration corpus. The referenced observation dataset
`0xSero/deepseek-v4-flash-reap-observations-v2` returned 401 from the public API
and 404 through the authenticated `hf` dataset download path on 2026-08-13, so
its rows are not used or represented as locally available.

Run `sha256sum -c SHA256SUMS` inside either snapshot directory to validate the
vendored files.
