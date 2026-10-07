# P2-26 — Source Batch #2

## Status

**Completed and promoted as the corrected P2-26 corpus candidate.**

Batch #1 proved the full P2-26 path with 69 accepted records and a clean contamination report. Batch #2 is intentionally much larger so Plex can test the first meaningful corpus-size target.

## Candidate size

Pinned-tree screening estimates:

- **5,849,962 bytes** of HTML/CSS/JavaScript before Plex content filtering
- **3,322 candidate files** before Plex content filtering
- 6 repositories
- 3 split groups because the 4 MDN repositories are intentionally treated as one source family

These are discovery estimates only. The authoritative numbers come from `web-source-verify`.

The completed local run produced:

- **3,142 Web-preflight accepted files**
- **5,463,479 accepted normalized source bytes**
- **3,140 final dataset records** after two additional invalid-JavaScript syntax rejects
- **3,071 train / 69 validation**
- dataset manifest SHA-256 `2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`
- contamination result: **passed**
- blocked origins: **0**
- exact protected matches: **0**
- long substring matches: **0**

The final project holdout remained closed.

## Sources

| Source | License | Pinned commit | Estimated eligible bytes | Estimated eligible files | Split group |
|---|---|---|---:|---:|---|
| mdn/dom-examples | CC0-1.0 | `f49fdb84422425b24c716d1eeaf8d408b9d7f710` | 1,335,054 | 458 | MDN family |
| mdn/css-examples | CC0-1.0 | `8cfcea69111e8bbacc9c92e3b04ead512693b937` | 2,318,030 | 672 | MDN family |
| mdn/interactive-examples | CC0-1.0 | `13024db581b08fae11a0ca229497198b9b0534e7` | 962,839 | 1,776 | MDN family |
| mdn/learning-area | CC0-1.0 | `d55e1c2e3ff401519811b64e5b2a7d3643b43d0f` | 522,644 | 254 | MDN family |
| BulmaTemplates/bulma-templates | MIT | `188672e66bccc5e2e946440ebc6214d600860969` | 451,234 | 70 | repository |
| soyaine/JavaScript30 | MIT | `a934c4adecbf8cc8ff2650a05a434892ad8e58d2` | 260,161 | 92 | repository |

## Why the MDN family shares one split group

The MDN repositories are separate Git repositories but share a strong source family, writing style, and example ecosystem. Treating them as independent train/validation groups could create overly optimistic validation through related examples.

All four therefore use:

```text
source-family-mdn-web-examples
```

## Local workflow

Materialize only the pinned revisions:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-materialize `
  --registry training\pretraining\p2-26-source-batch-2.json `
  --manifest-output training\pretraining\sources.p2-26-batch-2.local.json
```

Verify the resulting source pool:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-verify `
  --source-manifest training\pretraining\sources.p2-26-batch-2.local.json
```

The verifier reported `readyForDeterministicBuild: true`. The corrected corpus was then built with `web-dataset-build`; the earlier generic v1 build is not the promoted corpus.

## Promotion gates

Batch #2 must still pass:

1. source/license/provenance preflight
2. Plex content filtering and exact deduplication
3. repository/source-family grouped corpus build
4. contamination scan against protected Plex evaluation material
5. accepted-byte review against the 4–6 MiB P2-26 target

No tokenizer fitting or model training occurs in this batch.


## Closeout

Batch #2 met the P2-26 first-scale target and passed the contamination gate. It is frozen as the local corpus candidate used by P2-27 tokenizer review.

See [P2-26 closeout](PHASE-2-P2-26-CLOSEOUT.md).
