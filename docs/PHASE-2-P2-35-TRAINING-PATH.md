# P2-35 — Serialization-Stability Training Path

## Status

**First bounded run owner-approved — October 7, 2026. No P2-35 optimizer update has been executed yet.**

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

The run command now defaults to the sole owner-approved contract:

`training/pretraining/p2-35-first-run-contract.json`

That contract pins the exact stage, bundle, dataset, sampler, target-count, and baseline identities from the frozen preflight packet. It authorizes one bounded first run only.

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


## Complete local approval packet

The final read-only CUDA preflight pinned every value required for a later owner-approved first run:

- stage checkpoint SHA-256: `735554ac725acdcf063c2bb7ab27c71fafe187b82751c6b951c38900501a198d`
- bundle manifest SHA-256: `17f02f7f0b786be770f964b445854684fee0a010793672149e7fcc6c611aae5d`
- train JSONL SHA-256: `b921dd54657e77619835c5d9bce7a92c12c3a8f388d8ebe8ab8f6a9550ad69f3`
- validation JSONL SHA-256: `e48d45b81e7431180990224ed50b6b097b38bac705966e7524f54d1ac5d0d0ce`
- train index SHA-256: `e10af50b9b2f9dd3f4d67a3a772122be15d82c472db3f2e87469ba9904a79f44`
- validation index SHA-256: `cd93cc1d4ec62f400115b225b4bf090da99ff9c5eda9b46e7e2d134570eb6703`
- expected examples at 100 steps: **1,600**
- expected real target positions at 100 steps: **299,958**
- baseline validation loss: **4.335327882033128**
- baseline validation batches: **13**
- train/validation records: **108 / 36**
- train/validation tokens: **20,427 / 6,727**
- research optimizer updates: **0**
- final holdout opened: **false**

Machine-readable evidence:

`training/pretraining/p2-35-stage-preflight-result.json`

The approved contract contains these exact values and sets `approvalPacketComplete=true` with:

- `status: owner-approved-first-run`
- `modelTrainingAuthorized: true`
- `approvedBy: keepithandy`
- `approvedDate: 2026-10-07`

The authorization is limited to the single bounded first run. Resume, overwrite, automatic continuation, and any second run remain unauthorized.
