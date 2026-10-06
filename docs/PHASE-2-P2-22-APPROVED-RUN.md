# P2-22 Edit Intent Classification — Approved First Run

## Status

**Owner approved. Preparation and one bounded first CUDA run are authorized.**

Candidate:

`p2-22-edit-intent-classification-candidate-v1`

Approved candidate SHA-256:

`592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0`

## Fixed first-run policy

- 150 training records
- 75 evaluation-only records
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

The 75 P2-22 evaluation records must not be used for tokenizer fitting or gradient training.

## Legal model outputs

```text
REPLACE
INSERT
DELETE
RENAME
TOGGLE
```

The simple five-way chance expectation is **5/25 per evaluation tier**.

## Scoring

All three tiers use the same edit-intent metrics:

- complete task / exact intent
- known-intent output
- wrong-known-intent output
- unknown/malformed intent
- target-intent breakdown for REPLACE / INSERT / DELETE / RENAME / TOGGLE
- EOS

### Tier A

Clean unseen edit-intent paraphrases.

### Tier B

Five-way minimal semantic contrasts.

### Tier C

Repository-style edit language.

## Preparation

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_22_approved_experiment.py `
  --output training\artifacts\experiments\p2-22-edit-intent-prepared-v1
```

Then verify:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_22_approved_experiment.py `
  --output training\artifacts\experiments\p2-22-edit-intent-prepared-v1 `
  --verify-only
```

## First CUDA run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_22_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-22-edit-intent-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-22-edit-intent-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The wrapper rejects requests above 100 updates or 10 minutes and rejects non-CUDA execution.

## Interpretation

| Result | Interpretation |
|---|---|
| A/B/C strong | edit-intent normalization transfers across all intended language regimes |
| A weak, B/C strong | P2-21 pattern repeats: structured framing is useful, free paraphrase remains weak |
| one intent weak | inspect class ambiguity before changing architecture |
| all weak after strong supplied fit | five-intent representation does not generalize sufficiently |

Special attention should be paid to:

- REPLACE vs TOGGLE
- REPLACE vs RENAME
- INSERT vs DELETE

## Gate after step 100

Do not automatically continue.

Do not increase model size on the basis of this run alone.

The final holdout remains closed.
