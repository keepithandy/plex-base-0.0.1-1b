# P2-26 — Plex Web Corpus v1

## Status

**Complete.**

P2-25 closed the ingestion-pipeline milestone. P2-26 then scaled that pipeline to the first meaningful Plex Web corpus and is now closed. The final corrected candidate is documented in [P2-26 closeout](PHASE-2-P2-26-CLOSEOUT.md).

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
web-dataset-build
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

## Final result

The corrected verifier-locked batch #2 corpus contains:

- **3,140 records**
- **3,071 train / 69 validation**
- **5,463,479 accepted normalized source bytes**
- dataset manifest SHA-256 `2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`
- zero blocked-origin contamination matches
- zero exact protected-content matches
- zero long-substring matches

The final project holdout remained closed.

## Exit condition

P2-26 required a reproducible, provenance-complete, contamination-clean corpus candidate at the agreed first-scale target and ready for P2-27 tokenizer review.

**Met. P2-26 is complete and P2-27 is active.**
