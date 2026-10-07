# Plex Web pretraining workspace

This directory is the control surface for Plex's HTML/CSS/JavaScript domain-pretraining program.

## Current milestone

**P2-24 — specification.**

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
