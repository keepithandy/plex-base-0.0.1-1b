# P2-35 — Serialization-Stability Training Path

## Status

**Preparation preflight passed; locked execution path prepared. Model training remains unauthorized.**

The owner-reported local P2-35 curriculum/tokenizer preflight reproduced:

- candidate SHA-256: `2abd94ee05da241848e06500b0df43fd0f70e19af75c199ef6d73181fa8a1bad`
- records: **144**
- train / validation: **108 / 36**
- concept groups: **24** (**18 / 6** train/validation)
- every level A-F: **24 records**
- JSON-object solutions: **144 / 144**
- strict full-plan solutions: **48**
- exact P2-31 request overlap: **0**
- P2-31 target-role overlap: **0**
- P2-33 response strings used for training: **false**
- frozen tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- maximum record including EOS: **346 tokens**
- train tokens: **20,427**
- validation tokens: **6,727**
- research optimizer updates: **0**
- final project holdout opened: **false**

Machine-readable evidence:

`training/pretraining/p2-35-preparation-result.json`

## Execution boundary

P2-35 now has its own isolated path:

- `plan-serialization-prepare`
- `plan-serialization-stage`
- `plan-serialization-preflight`
- `plan-serialization-run`

The run command is present only so the complete execution path can be reviewed and tested. Its default contract is:

`training/pretraining/p2-35-first-run-contract.draft.json`

That contract has:

- `status: draft-awaiting-owner-review`
- `modelTrainingAuthorized: false`
- `approvedBy: null`
- no pinned stage SHA yet
- no pinned bundle SHA yet
- no sampler/index identity yet
- no expected 100-step target count yet
- no baseline validation loss yet

Therefore **the run command is hard-blocked** until a later owner-approved contract pins the exact local evidence.

## Fixed base checkpoint

P2-35 stages from the official P2-32 step-100 endpoint:

`training/artifacts/structured-plan/p2-32-first-run/checkpoints/step-0100.pt`

SHA-256:

`707e46f9e3e87cdd9beec705e2bd55701b37a40e79aad7ab93858fa63f8ebcf4`

The P2-35 stage transition:

- loads those model weights
- starts P2-35 at step 0
- creates a fresh AdamW optimizer
- reinitializes sampler state from seed 1337
- resets P2-35 tokens processed to 0
- does not reuse the P2-32 optimizer
- does not reuse P2-32 sampler state
- performs zero optimizer updates

## Step 1 — pack the reviewed P2-35 bundle

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-serialization-prepare `
  --source-bundle-dir training/artifacts/structured-plan/p2-32-training-bundle
```

Expected output directory:

`training/artifacts/structured-plan/p2-35-training-bundle`

This repacks the reviewed 108/36 curriculum with the frozen tokenizer. It does not train.

## Step 2 — create the weights-only stage

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-serialization-stage `
  --base-checkpoint training/artifacts/structured-plan/p2-32-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-35-training-bundle
```

Expected output directory:

`training/artifacts/structured-plan/p2-35-stage0`

The stage command verifies model-weight equality after reload and requires a fresh optimizer/sampler state.

## Step 3 — run read-only CUDA preflight

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-serialization-preflight `
  --bundle-dir training/artifacts/structured-plan/p2-35-training-bundle `
  --stage-checkpoint training/artifacts/structured-plan/p2-35-stage0/stage-checkpoint.pt
```

This command:

- verifies the exact stage and bundle
- replays the complete-record sampler for the proposed 100-step schedule
- computes the exact expected real target positions
- computes the P2-35 validation baseline on CUDA
- confirms the output directory is unused
- reports `authorized: false` while the draft contract remains in force
- performs **zero optimizer updates**

## Proposed bounded run

The draft retains the same bounded first-run envelope used for P2-32:

- objective: ordinary next-token loss
- optimizer: AdamW
- learning rate: **0.0003**
- betas: **0.9 / 0.95**
- weight decay: **0.1**
- gradient clipping: **1.0**
- micro-batch: **1**
- gradient accumulation: **16**
- maximum steps: **100**
- maximum wall time: **600 seconds**
- CUDA
- seed: **1337**
- validation: **0 / 25 / 50 / 75 / 100**
- checkpoints: **25 / 50 / 75 / 100**
- no resume
- no overwrite
- no automatic continuation
- fixed endpoint reporting; no retrospective lowest-validation checkpoint selection

These settings are **proposed, not authorized**.

## Authorization rule

After local prepare/stage/preflight, the exact values below must be reviewed and committed before training:

1. packed bundle manifest SHA-256
2. train and validation JSONL SHA-256
3. complete-record sampler index SHA-256
4. stage checkpoint SHA-256
5. exact 100-step real-target count
6. baseline validation loss
7. unchanged candidate/tokenizer identities
8. `trainingExecuted: false`
9. `researchOptimizerUpdates: 0`
10. `finalHoldoutOpened: false`

Only then may a separate owner-approved contract set `modelTrainingAuthorized: true`.
