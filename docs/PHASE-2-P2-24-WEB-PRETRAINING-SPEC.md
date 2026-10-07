# P2-24 — Plex Web Pretraining Specification

## Status

**Active specification milestone.**

P2-24 starts Plex's first genuine domain-pretraining program.

The training strategy is now:

```text
permissively licensed HTML/CSS/JavaScript corpus
                    ↓
        scratch domain pretraining
                    ↓
             Plex Web Base
                    ↓
      Phase 2 task-format fine-tuning
                    ↓
       structured edit planning
```

The purpose of this milestone is to freeze what is allowed into the pretraining corpus before building a large ingestion system.

## Why this changes the plan

The existing Phase 2 experiments were intentionally tiny and controlled. They proved that the 27,566,080-parameter scratch model can learn supplied semantic formats and some held-out classification behavior.

They did **not** provide a broad HTML/CSS/JavaScript prior.

The existing task datasets are therefore reclassified as:

- fine-tuning curricula
- development/evaluation sets
- architecture diagnostics

They are not a substitute for domain pretraining.

## Initial language scope

Plex Web v1 accepts only the web-code family:

- HTML: `.html`, `.htm`
- CSS: `.css`
- JavaScript: `.js`, `.mjs`, `.cjs`

JSON, Markdown, TypeScript, JSX/TSX, frameworks, build configuration, and other languages are **not** part of the first corpus unless a later reviewed revision explicitly adds them.

## License policy

P2-24 uses a deliberately conservative allowlist.

Initially allowed SPDX identifiers:

- `MIT`
- `Apache-2.0`
- `BSD-2-Clause`
- `BSD-3-Clause`
- `ISC`
- `0BSD`
- `CC0-1.0`
- `Unlicense`

Everything else is excluded by default, including:

- no detected license
- unknown/ambiguous license
- custom licenses
- GPL-family licenses
- AGPL
- LGPL
- MPL
- EPL
- source records whose provenance cannot be recovered

This is a project policy, not a legal determination. Any expansion of the allowlist requires a recorded review before ingestion.

## Candidate source families

### Repository sources

The preferred pretraining material is human-authored repository code with retained repository identity.

Potential source mechanisms include:

- approved public repositories with pinned revisions and explicit allowed licenses
- permissively licensed code datasets that retain original source provenance and license identifiers
- selected educational code sources whose sample-code license is separately verified

A dataset being described as "permissively licensed" is not enough. Plex must still retain and honor the underlying source license/provenance.

### The Stack / BigCode

BigCode datasets are candidates for a later ingestion adapter, not automatically approved corpus content.

The adapter must preserve:

- original source/repository identity where available
- license metadata
- dataset/version identity
- removal/update requirements applicable to the dataset version
- source hashes

If access requires the dataset user to accept terms or share account/contact information, that step belongs to the repository owner. Plex tooling must not accept such terms automatically.

### MDN code samples

MDN code samples may be considered as a high-quality educational supplement only if the extractor can preserve the sample's licensing basis.

Do not ingest general MDN prose as Plex Web code pretraining merely because a page contains code.

## Provenance contract

Every retained file record must be traceable.

Minimum fields:

```text
sourceKind
sourceDataset
sourceDatasetVersion
repositoryUrl
repositoryRevision
path
language
spdxLicense
licenseEvidence
sourceSha256
normalizedSha256
byteLength
splitGroup
split
```

If a source does not support the relevant field, the record must state why rather than inventing metadata.

## Repository-level split rule

Training/validation separation is by repository (or an equally strong source family key), **never by individual file**.

If these files come from one repository:

```text
index.html
styles.css
app.js
```

all three belong to the same split.

This prevents project-local structure from leaking between train and validation.

## Quality filters

Reject or quarantine:

- binary or undecodable files
- empty files
- source maps
- minified/bundled artifacts
- `node_modules`
- vendor directories
- generated build output
- lock files
- files marked generated
- extremely large files
- trivially tiny/no-content files
- obvious secrets, private keys, tokens, or credentials
- duplicate and near-duplicate content
- records missing required provenance/license information

The exact thresholds belong to P2-25 and must be recorded in the build manifest.

## Deduplication

Plex Web must perform at least:

1. normalized exact-content deduplication
2. repository-aware duplicate accounting
3. near-duplicate detection before serious pretraining scale

Deduplication decisions must be reproducible and reported.

## Contamination protection

Before corpus promotion, fingerprint all protected development/evaluation material, including:

- P2-01b
- P2-14
- P2-21
- P2-22
- P2-23
- future P2-30/P2-31 held-out sets
- the final project holdout when it exists

At minimum check:

- exact record/content hashes
- normalized exact matches
- suspicious long substring overlap
- source/repository overlap where applicable

A build must emit a contamination report. Matching records are excluded from training unless explicitly classified as non-protected training material.

## Corpus ladder

Do not jump directly to the largest build.

Target ladder:

| Corpus | Approximate training-token target | Purpose |
|---|---:|---|
| **Plex Web 1M** | 1 million | pipeline validation |
| **Plex Web 10M** | 10 million | tokenizer/training behavior |
| **Plex Web 100M** | 100 million | meaningful domain-pretraining experiment |
| **Plex Web Large** | 500M+ candidate | serious 27.6M pretraining, only after earlier gates |

These are target scales, not automatic authorizations. Actual counts come from the frozen tokenizer/build.

## Tokenizer rule

The serious Plex Web tokenizer must be fitted on the **pretraining training split only**.

P2-27 compares tokenization efficiency and preservation across:

- HTML
- CSS
- JavaScript
- ordinary task instructions
- existing Plex task formats

No validation or protected held-out material may be used for tokenizer fitting.

## Model-size rule

Keep the existing **27,566,080-parameter** architecture for the first domain-pretraining pilot.

Do not simultaneously change corpus strategy, tokenizer, and model scale in the same first experiment.

The larger 0.5B–1.5B direction remains a later decision based on measured pretraining and task-tuning results.

## Owner participation

The repository owner participates at explicit promotion gates.

Owner review is required for:

- adding a new license identifier to the allowlist
- adding a new source family with materially different terms
- accepting third-party gated-dataset terms
- promoting the first serious corpus to P2-29 pretraining
- opening the final project holdout

Routine deterministic filtering of already-approved sources does not require per-file manual approval.

## P2-24 completion check

P2-24 is complete when:

- this specification is committed
- the machine-readable source/license policy is committed
- the pretraining workspace documents the corpus ladder and provenance contract
- roadmap/README/changelog reflect the new pretraining-first strategy

P2-24 does **not** itself download or train on a large corpus.

The next implementation milestone is **P2-25 — Corpus Ingestion Pipeline**.
