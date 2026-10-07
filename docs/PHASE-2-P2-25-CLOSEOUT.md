# P2-25 — Plex Web Corpus Ingestion Closeout

## Status

**Complete.** P2-26 is now the active milestone.

P2-25 established the reproducible, license-gated path from reviewed web repositories to Plex Web corpus artifacts.

## Seed-corpus evidence

The owner ran the first real Plex Web source preflight against two pinned MIT repositories.

Results:

- 2 independent source groups
- 21 accepted HTML/CSS/JavaScript files
- 91,214 accepted source bytes at preflight
- 9 HTML files
- 6 CSS files
- 6 JavaScript files
- 0 exact duplicates
- 3 files rejected by the secret-pattern filter
- `readyForDeterministicBuild: true`

The seed dataset build produced:

- 21 records
- 3 train records
- 18 validation records
- 107,419 total artifact bytes
- the same 3 secret-pattern rejections

The owner repeated the build with the same source manifest, seed 1337 and 50% repository-group validation split. The repeated manifest SHA-256 was identical:

```text
16C16741A62DF39EEC23AB1C7C87B81E24F565C3F3E80D4174038C109B9195F3
16C16741A62DF39EEC23AB1C7C87B81E24F565C3F3E80D4174038C109B9195F3
```

This closes the reproducibility requirement for the P2-25 seed build.

## Contamination gate

P2-25 now includes `web-contamination-check`.

The gate protects:

- `training/phase2/evaluation`
- `training/phase2/data/authored`
- the Plex repository itself as a blocked source origin
- the still-closed final holdout by policy

The checker records exact normalized matches, long protected substrings and blocked source origins into `contamination-report.json`.

**Important:** the historical seed corpus was built before this checker existed. It remains a pipeline-validation corpus, not a pretraining-authorized corpus. P2-26 corpus promotion requires a fresh passing contamination report. This avoids claiming an unrun content scan.

## P2-25 exit condition

P2-25 is closed because the repository now has:

- explicit source/license policy
- provenance-gated source manifests
- secret/generated/minified/binary filtering
- exact deduplication
- repository-group train/validation splitting
- deterministic repeated corpus construction
- a mandatory contamination-report gate before promotion

The next milestone is **P2-26 — Plex Web Corpus v1**.
