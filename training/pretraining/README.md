# Plex Web pretraining workspace

This directory is the control surface for Plex's HTML/CSS/JavaScript domain-pretraining program.

## Current milestone

**P2-25 — corpus ingestion pipeline (started).**

P2-24's specification and machine-readable source policy are committed. The first P2-25 slice adds a local-source preflight verifier before any corpus copying or training.

No large corpus is stored in Git.

## Pipeline

```text
approved source
    ↓
license/provenance gate
    ↓
HTML/CSS/JS file gate
    ↓
quality + secret/generated/minified filters
    ↓
hashing + deduplication
    ↓
repository-grouped train/validation split
    ↓
contamination check
    ↓
immutable corpus manifest/shards
    ↓
training-only tokenizer
    ↓
scratch domain pretraining
```

## Corpus ladder

- Plex Web 1M — pipeline validation
- Plex Web 10M — tokenizer/training behavior
- Plex Web 100M — meaningful pretraining experiment
- Plex Web Large — 500M+ candidate after earlier gates

## Important rules

- Publicly visible code is **not** automatically approved training data.
- Unknown or ambiguous licenses are rejected by default.
- Source provenance must survive every transformation.
- Repository families stay in one split.
- Protected Phase 2 development/evaluation content must not leak into pretraining.
- Gated dataset terms must be accepted by the repository owner directly, not by automation.
- The first pilot keeps the current 27.6M architecture.

See:

- [P2-24 specification](../../docs/PHASE-2-P2-24-WEB-PRETRAINING-SPEC.md)
- [source policy](source-policy.json)


## Verify reviewed local sources

Copy `source-manifest.example.json` to a working manifest beside your local source snapshots, replace the placeholders with pinned provenance/license information, then run:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-verify `
  --source-manifest training\pretraining\sources.local.json
```

The verifier is read-only. It does not copy files or train the model.

It rejects sources outside the committed license allowlist and filters candidate HTML/CSS/JavaScript files for:

- disallowed paths such as `node_modules`, vendor/build output and caches
- minified suffixes
- generated-file markers
- binary/invalid UTF-8
- known credential/secret patterns
- exact normalized duplicates

At least two independent repository/source groups are required so later train/validation splitting can remain leak-resistant.

P2-25 is not complete until the verified source set can be promoted into a deterministic corpus build with provenance and contamination reports.
