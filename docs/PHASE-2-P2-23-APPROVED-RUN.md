# P2-23 Target-Kind Classification — Approved First Run

## Status

**Owner approved. Preparation and one bounded first CUDA run are authorized.**

Candidate:

`p2-23-target-kind-classification-candidate-v1`

Approved candidate SHA-256:

`3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08`

## Fixed first-run policy

- 144 training records
- 72 evaluation-only records
- A/B/C = 48 training + 24 evaluation each
- fresh tokenizer fitted on training text only
- fresh seed 1337 initialization
- unchanged 27,566,080-parameter architecture
- ordinary next-token complete-record loss
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- CUDA
- matched step-zero scoring
- maximum 100 updates
- maximum 10 minutes
- no automatic extension
- P2-14 excluded from gradient training
- P2-01b excluded from gradient training
- final project holdout closed

The 72 P2-23 evaluation records must not be used for tokenizer fitting or gradient training.

## Legal model outputs

```text
CSS_SELECTOR
CSS_PROPERTY
HTML_ELEMENT
HTML_ATTRIBUTE
JS_IDENTIFIER
JS_PROPERTY
```

Simple six-way chance is **4/24 = 16.7% per evaluation tier**.

## Scoring

All three tiers report:

- exact target-kind classification
- known target-kind output
- wrong known target-kind
- unknown/malformed target-kind
- per-kind breakdown for all six target kinds
- EOS

### Tier A

Clean unseen target-kind paraphrases.

### Tier B

Six-way minimal semantic contrasts.

### Tier C

Repository-style CSS/HTML/JavaScript target language.

Key pairwise distinctions:

- CSS_SELECTOR vs CSS_PROPERTY
- HTML_ELEMENT vs HTML_ATTRIBUTE
- JS_IDENTIFIER vs JS_PROPERTY

## Preparation

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_23_approved_experiment.py `
  --output training\artifacts\experiments\p2-23-target-kind-prepared-v1
```

Then verify:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_23_approved_experiment.py `
  --output training\artifacts\experiments\p2-23-target-kind-prepared-v1 `
  --verify-only
```

## First CUDA run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_23_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-23-target-kind-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-23-target-kind-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner rejects requests above 100 updates or 10 minutes and rejects non-CUDA execution.

## Interpretation

The first run should answer whether flat target-kind semantics learn cleanly at the existing 27.6M scale.

Do not automatically continue after step 100.

Do not increase model size from this run alone.

The final project holdout remains closed.
