# P1-14 dataset pipeline

P1-14 implements a local, reproducible curation path. It does not download a dataset or decide whether a license permits training. A source is included only after its catalog entry records the pinned revision, license evidence, and an explicit owner rights review.

The first approved sources, pinned versions, selected file counts, split, build hashes, and verification are in [DATASET-SOURCE-REVIEW.md](DATASET-SOURCE-REVIEW.md). The separate `plex_training.source_fetch` helper downloads only files listed in [training/dataset-source-lock.json](../training/dataset-source-lock.json), checks upstream Git blob hashes, retains licenses, and limits selected downloads to 20 MiB. It never sets rights approval. The `dataset-build` command remains offline.

## Add a reviewed source

Copy [`training/dataset-sources.example.json`](../training/dataset-sources.example.json) to the ignored local file `training/dataset-sources.local.json`. Put the checked-out source beneath `training/data/raw/<source-id>/`. In the catalog, replace every placeholder and set:

- `id`: a stable short identifier.
- `localPath`: a path relative to the catalog file, contained under the catalog directory.
- `origin` and `revision`: the source location and immutable commit or release used.
- `licenseId` and `licenseEvidence`: the declared license and its authoritative evidence. A local evidence file is relative to the source root; it must exist, be contained within that root, and be no larger than 1 MiB. Its original bytes are copied under the dataset's `licenses/` directory and hashed in the manifest. A URL can record evidence for other sources, but a URL alone does not package the notice; use local license files for the proposed MIT sources.
- `rightsReviewStatus`: set to `approved` only after reviewing the source license and relevant terms; record an ISO-8601 UTC timestamp in `rightsReviewedAtUtc`.
- `groupId`: the repository or related repository family. Sources that share examples or history must share a group so they cannot cross the train/validation split.
- `includeExtensions`: the file types to consider. Omit it to use the built-in allowlist.

The pipeline reads local files only. It does not run source programs, change source files, or include absolute source paths in the output manifest. Keep machine-specific local catalogs and raw source snapshots out of Git. The approved starter catalog [training/dataset-sources.starter-v1.json](../training/dataset-sources.starter-v1.json) contains only reviewed public metadata and relative paths; it can be committed with the source lock and pipeline so the corpus is reproducible.

## Build the dataset

From the repository root in PowerShell, after reviewed files and catalog entries are ready:

```powershell
uv run --project training python -m plex_training.cli dataset-build `
  --source-manifest training\dataset-sources.local.json `
  --output-dir datasets\p1-14 `
  --validation-percent 10 `
  --seed 1337
```

The output is written beneath `training/artifacts` and counts against the owner's 200 GiB allocation. Choose a fresh output directory for each build; existing output is never overwritten. The pipeline creates `train.jsonl`, `validation.jsonl`, and a deterministic `manifest.json` containing source/license metadata, hashes, filters, skipped relative paths and reason codes, and split details. The source catalog hash, immutable revisions, seed, and grouped split method make the build traceable and repeatable.

## Curation behavior and limits

The pipeline accepts UTF-8 source and explanation files from its extension allowlist, excludes common generated/vendor/dependency directories, caps each file at 1 MiB, strips a UTF-8 BOM, normalizes line endings and Unicode NFC, and removes exact normalized-content duplicates. It rejects invalid UTF-8, binary-like text, empty/very short files, detected credential patterns, invalid Python syntax, invalid JSON, and invalid JavaScript syntax when Node's `--check` is available. `node --check` parses syntax and does not execute the source. JavaScript is skipped if Node validation is unavailable. Other languages and Markdown are checked for text and credential patterns but are not parser-validated; the manifest records which validators ran.

Credential patterns are a defense-in-depth filter, not a guarantee that secrets are absent. Review sources before inclusion and inspect the filter counts and resulting examples. False positives may be removed by curating the local source files or narrowing `includeExtensions`; the pipeline intentionally does not redact content silently.

Exact duplicates are removed before splitting. A stable SHA-256 ranking of `seed` and `groupId` assigns complete repository groups to validation or training; at least two eligible groups are required. This reduces source leakage but does not identify every related repository automatically. Assign related sources the same `groupId` in the catalog.

The output remains a text corpus for P1-14. P1-15 will train Plex's tokenizer using only `train.jsonl`, then encode both splits. No pretrained weights or external tokenizer checkpoints are used.
