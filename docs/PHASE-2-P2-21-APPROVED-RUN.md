# P2-21 Semantic Role Generalization — Approved First Run

## Status

**Owner approved. Preparation and one bounded first CUDA run are authorized.**

Candidate:

`p2-21-semantic-role-generalization-candidate-v1`

Approved candidate SHA-256:

`8206798467f74bda9867c0179495b535eade3849ca1d8a5d3147de00f27e5584`

## Fixed first-run policy

- 144 training records
- 72 evaluation-only records
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
- final holdout closed

The 72 P2-21 evaluation records must not be used for tokenizer fitting or gradient training.

## Scoring

All three tiers use the same semantic-role metrics:

- complete task / exact role
- known-role output
- wrong-known-role output
- unknown/malformed role
- target-role breakdown for SELECTOR / OLD / NEW
- EOS

### Tier A

Clean unseen semantic paraphrases.

### Tier B

Minimal semantic contrasts.

### Tier C

Repository-style edit language.

The simple chance baseline is 1/3 for every tier.

## Preparation

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_21_approved_experiment.py `
  --output training\artifacts\experiments\p2-21-semantic-role-prepared-v1
```

Then verify:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_21_approved_experiment.py `
  --output training\artifacts\experiments\p2-21-semantic-role-prepared-v1 `
  --verify-only
```

## First CUDA run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_21_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-21-semantic-role-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-21-semantic-role-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The wrapper rejects requests above 100 updates or 10 minutes and rejects non-CUDA execution.

## Interpretation

| Result | Interpretation |
|---|---|
| A/B/C strong | semantic-role normalization transfers across all intended language regimes |
| A strong, B/C weak | basic paraphrases transfer, but contrast/repository semantics remain weak |
| A/B strong, C weak | canonical semantics work; repository-style wording is the remaining gap |
| All weak after strong supplied fit | current semantic curriculum does not generalize sufficiently |

## Gate after step 100

Do not automatically continue.

Do not increase model size on the basis of this run alone.

The final holdout remains closed.
