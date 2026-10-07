# P2-32 — Training Path Implementation

## Status

**Implementation prepared; real model training remains unauthorized.**

The P2-32 curriculum/tokenizer gate passed locally with:

- candidate SHA-256: `608cf988b96e8578fa2c7948a12e298c4ed25c640098a2bf3710f3b3cc6802d3`
- 96 records / 24 groups
- 72 train / 24 validation
- 96/96 schema-valid target plans
- 0 exact P2-31 request overlap
- 0 P2-31 target-role overlap
- frozen tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- maximum complete record including EOS: **447 tokens**
- train token count: **27,251**
- validation token count: **8,992**
- final holdout remained sealed
- optimizer updates: **0**

The machine-readable evidence is:

`training/pretraining/p2-32-preparation-result.json`

## Dedicated path

P2-32 now has four separate commands:

1. `plan-train-prepare` — pack the reviewed 96-record candidate with the frozen P2-30 tokenizer.
2. `plan-train-stage` — load only the official P2-30 step-100 model weights into a fresh P2-32 stage with empty optimizer state, reset sampler state, step 0, and token count 0.
3. `plan-train-preflight` — verify the packed bundle, stage identity, complete-record sampler, expected 100-step target count, and stage-zero validation loss. This command performs **zero** optimizer updates.
4. `plan-train-run` — the bounded CUDA runner. It refuses to execute while the committed authorization contract remains draft/unapproved.

The P2-32 complete-record sampler is intentionally separate from the P2-30 sampler because the P2-30 sampler verifies the historical `Write a small ... / Request / Output contract` text shape. P2-32 verifies its own structured-plan prompt + JSON answer format instead of weakening the old checks.

## Fixed base

The weights-only stage is pinned to:

`training/artifacts/task-finetune/p2-30-first-run/checkpoints/step-0100.pt`

SHA-256:

`28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`

Step 50 remains diagnostic P2-30 evidence only and is not eligible for post-hoc selection.

## Draft first-run envelope

The implementation supports only the existing draft envelope:

- AdamW
- learning rate 0.0003
- betas 0.9 / 0.95
- epsilon 1e-8
- weight decay 0.1
- gradient clipping 1.0
- constant learning rate
- micro-batch 1
- gradient accumulation 16
- maximum 100 optimizer updates
- maximum wall time 600 seconds
- CUDA
- seed 1337
- context length 512
- validation at 0 / 25 / 50 / 75 / 100
- checkpoints at 25 / 50 / 75 / 100
- complete-record-v1
- no resume
- no overwrite
- no automatic continuation

Those settings are **not authorization**.

The draft contract is:

`training/pretraining/p2-32-first-run-contract.draft.json`

It deliberately leaves the following values unset until local staging/preflight supplies them:

- exact P2-32 stage checkpoint SHA-256
- packed bundle manifest SHA-256
- train/validation JSONL SHA-256
- sampler/index identity
- exact expected real target positions at 100 steps
- stage-zero validation loss

## Local staging sequence

After pulling the merged implementation:

### 1. Pack

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-train-prepare `
  --source-bundle-dir training/artifacts/task-finetune/p2-30-request-v3-16k
```

### 2. Create weights-only stage

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-train-stage `
  --base-checkpoint training/artifacts/task-finetune/p2-30-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-32-training-bundle
```

### 3. Read-only CUDA preflight

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-train-preflight `
  --bundle-dir training/artifacts/structured-plan/p2-32-training-bundle `
  --stage-checkpoint training/artifacts/structured-plan/p2-32-stage0/stage-checkpoint.pt
```

The expected preflight result must still say:

- `authorized: false`
- `trainingPerformed: false`
- `researchOptimizerUpdates: 0`
- `finalHoldoutOpened: false`

The returned stage/bundle/sampler/baseline identities are then eligible for a **separate owner authorization review**.

Do not run `plan-train-run` before that authorization is committed.
