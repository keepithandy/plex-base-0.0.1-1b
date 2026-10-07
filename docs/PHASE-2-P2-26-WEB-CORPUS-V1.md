# P2-26 — Plex Web Corpus v1

## Status

**Active.**

P2-25 closed the ingestion-pipeline milestone. P2-26 scales that pipeline toward the first meaningful Plex Web corpus.

## Immediate target

The first target is **Plex Web 1M**.

Because P2-27 has not frozen the new tokenizer yet, P2-26 uses a byte-scale proxy first:

- roughly **4–6 MiB of accepted normalized HTML/CSS/JavaScript**
- multiple independent repositories
- repository-group train/validation separation
- zero blocked-source contamination
- zero protected-evaluation overlap
- retained license/provenance metadata

The exact token count is measured after P2-27 tokenizer review.

## Starting source pool

The first reviewed expansion pool is recorded in:

`training/pretraining/p2-26-source-candidates.json`

It currently adds six pinned MIT repositories covering:

- HTML email templates
- vanilla JavaScript boilerplate
- CSS teaching/examples
- small HTML document templates
- browser interaction JavaScript
- vanilla JavaScript state-management examples

These are candidates, not automatic training records. Every source still passes the normal Plex Web preflight, corpus filters, grouped split, and contamination gate.

## P2-26 workflow

```text
reviewed pinned source registry
        ↓
web-source-materialize
        ↓
web-source-verify
        ↓
dataset-build
        ↓
web-contamination-check
        ↓
accepted corpus byte/count review
        ↓
expand source pool if needed
        ↓
freeze Plex Web Corpus v1 candidate
```

## Hard rules

- Do not train yet.
- Do not fit the new tokenizer yet.
- Do not use unknown-license repositories.
- Do not accept gated third-party dataset terms automatically.
- Do not add the Plex repository or its task/evaluation material to pretraining.
- Do not promote a corpus with a failing or missing contamination report.
- Keep the current 27.6M architecture unchanged through the first pretraining pilot.

## Exit condition

P2-26 completes when a reproducible, provenance-complete, contamination-clean corpus candidate reaches the agreed first-scale target and is ready for P2-27 tokenizer review.
