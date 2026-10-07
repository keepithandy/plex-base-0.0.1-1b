# P2-27 — Web Tokenizer Review

## Status

**Active.**

P2-27 reviews tokenizer behavior on the frozen P2-26 Plex Web corpus before any new model weights are initialized or trained.

The frozen dataset manifest for this review is:

`2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`

If that dataset identity changes, the P2-27 review must be restarted against the new corpus identity.

## Goal

Choose and freeze a tokenizer configuration that gives the 27.6M scratch Plex model a reasonable representation of:

- HTML structure and attributes
- CSS selectors, properties, values, and punctuation
- JavaScript identifiers, expressions, functions, and operators
- ordinary request text
- Plex task/plan formatting

P2-27 is tokenizer work only. It does not train model weights.

## Candidate set

The first review compares fresh byte-level BPE tokenizers with requested vocabulary sizes:

- 4,096
- 8,192
- 12,288
- 16,384

All candidates use the existing Plex byte-level BPE implementation and the same special-token contract.

The 16,384 value is the current model vocabulary capacity; P2-27 does not change the 27.6M architecture.

## Fit boundary

Every fresh candidate must be fitted **only on the P2-26 training split**.

Validation may be encoded and measured after fitting, but it must not influence BPE merge learning.

The final project holdout is not part of tokenizer fitting or review.

## Measurements

The `tokenizer-review` command records for each candidate:

- requested vocabulary size
- actual vocabulary size
- tokenizer SHA-256
- train text bytes and token count
- validation text bytes and token count
- bytes per text token
- tokens per KiB
- exact roundtrip count
- representative HTML/CSS/JavaScript/Plex-task sample compression
- exact roundtrip of those representative samples
- bundle size

An existing Plex tokenizer can optionally be measured as a baseline with `--baseline-tokenizer`, but baseline weights or vocabulary are never reused to fit a candidate.

## Selection rule

P2-27 does not automatically promote the numerically largest or most compressed tokenizer.

A tokenizer may be frozen only after reviewing:

1. exact roundtrip behavior
2. train/validation compression
3. representative web-code and Plex-format behavior
4. actual vocabulary size
5. compatibility with the unchanged 16,384 model vocabulary capacity

The command reports informational compression leaders, but `automaticPromotion` remains false.

## Scratch-training boundary

For every P2-27 candidate:

- fresh tokenizer fit: **yes**
- fit data: **P2-26 train split only**
- pretrained tokenizer reused for fitting: **no**
- pretrained model checkpoint loaded: **no**
- model weights initialized: **no**
- model training performed: **no**

Plex therefore remains on the scratch-training path.

## First local review command

From the Plex repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli tokenizer-review `
  --dataset-dir training\artifacts\datasets\p2-26-web-batch-2-v2 `
  --output-dir tokenizer-reviews\p2-27-web-v1 `
  --vocab-sizes 4096 8192 12288 16384 `
  --min-frequency 2
```

The command writes its artifacts beneath `training/artifacts/` and prints a compact candidate comparison.

Do not run `initialize`, `pilot`, or any other model-training command from the P2-27 output until the tokenizer review is explicitly closed.

## Exit condition

P2-27 completes when:

- the frozen P2-26 corpus identity is confirmed
- candidate tokenizers are fitted on training text only
- all corpus and representative-sample roundtrip checks pass
- compression/size results are reviewed
- one tokenizer configuration is explicitly frozen for P2-28
- its tokenizer hash and bundle identity are recorded

**Next after completion:** P2-28 — fresh 27.6M scratch domain-pretraining pilot.
