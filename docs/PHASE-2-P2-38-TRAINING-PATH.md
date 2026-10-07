# P2-38 — Locked Semantic-Binding Execution Path

## Status

**Candidate review complete; zero-update bundle/stage/preflight path prepared. Model training remains unauthorized.**

P2-38 uses the reviewed semantic-binding contrast candidate:

- candidate SHA-256: `137e2ccf8e015ba74a109ce53f3c7adf502262a4d2a79382e21bfc69a1ea7ab8`
- records: **108**
- contrast groups: **36**
- train / validation: **72 / 36**
- unique requests: **108**
- unique target roles: **108**
- P2-31 exact-request overlap: **0**
- P2-31 target-role overlap: **0**
- P2-35 target-role overlap: **0**
- strict full-plan solutions: **108**
- maximum record length: **395 tokens including EOS**
- train / validation token counts: **24,793 / 12,409**

Preparation evidence is recorded in:

`training/pretraining/p2-38-preparation-result.json`

## Fixed base checkpoint

P2-38 stages only from the official P2-35 step-100 endpoint:

`training/artifacts/structured-plan/p2-35-first-run/checkpoints/step-0100.pt`

SHA-256:

`1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0`

The stage loader also requires:

- P2-35 stage kind: `plex-serialization-stability-stage-transition-v1`
- P2-35 training settings kind: `p2-35-authorized-serialization-stability-training-v1`
- frozen tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

## Execution boundary

P2-38 now has isolated commands:

- `plan-semantic-binding-prepare`
- `plan-semantic-binding-stage`
- `plan-semantic-binding-preflight`
- `plan-semantic-binding-run`

The run command exists only so the path can be tested. Its default contract is:

`training/pretraining/p2-38-first-run-contract.draft.json`

That draft explicitly has:

- `approvalPacketComplete=false`
- `modelTrainingAuthorized=false`
- `approvedBy=null`
- stage SHA: **null**
- bundle SHA: **null**
- train/validation JSONL SHAs: **null**
- sampler: **null**
- expected 100-step target count: **null**
- baseline validation loss: **null**
- command: **null**

Therefore real P2-38 training is still blocked.

## Step 1 — pack the P2-38 bundle

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-semantic-binding-prepare `
  --source-bundle-dir training/artifacts/structured-plan/p2-35-training-bundle
```

Expected output:

`training/artifacts/structured-plan/p2-38-training-bundle`

This repacks the 72/36 reviewed full-plan candidate with the frozen tokenizer and performs zero optimizer updates.

## Step 2 — create the weights-only P2-38 stage

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-semantic-binding-stage `
  --base-checkpoint training/artifacts/structured-plan/p2-35-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-38-training-bundle
```

Expected output:

`training/artifacts/structured-plan/p2-38-stage0/stage-checkpoint.pt`

The stage must:

- preserve model weights exactly
- reset optimizer state
- reset sampler state
- start P2-38 at step 0
- reset P2-38 tokens processed to 0
- perform zero optimizer updates

## Step 3 — run read-only CUDA preflight

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-semantic-binding-preflight `
  --bundle-dir training/artifacts/structured-plan/p2-38-training-bundle `
  --stage-checkpoint training/artifacts/structured-plan/p2-38-stage0/stage-checkpoint.pt
```

The preflight will report:

- exact P2-38 bundle manifest SHA
- exact stage checkpoint SHA
- train/validation JSONL SHA-256
- train/validation index SHA-256
- complete-record sampler identity
- expected examples at 100 steps
- exact expected real target positions at 100 steps
- stage-zero validation loss on CUDA
- train/validation token counts
- `authorized=false`
- `trainingPerformed=false`
- `researchOptimizerUpdates=0`
- `finalHoldoutOpened=false`

## Proposed first-run envelope

The draft currently mirrors the proven bounded P2-35 envelope:

- AdamW
- learning rate: **0.0003**
- betas: **0.9 / 0.95**
- epsilon: **1e-8**
- weight decay: **0.1**
- gradient clipping: **1.0**
- micro-batch: **1**
- gradient accumulation: **16**
- maximum steps: **100**
- maximum wall time: **600 seconds**
- seed: **1337**
- CUDA
- validation: **0 / 25 / 50 / 75 / 100**
- checkpoints: **25 / 50 / 75 / 100**
- no resume
- no overwrite
- no automatic continuation
- fixed endpoint reporting; no retrospective lowest-validation checkpoint selection

These settings are **proposed, not authorized**.

## Governance

After local pack/stage/preflight, the exact identities must be committed and reviewed before any training authorization:

1. bundle manifest SHA-256
2. train JSONL SHA-256
3. validation JSONL SHA-256
4. train index SHA-256
5. validation index SHA-256
6. stage checkpoint SHA-256
7. exact expected real target positions at 100 steps
8. baseline validation loss
9. unchanged tokenizer/candidate identities
10. zero optimizer updates
11. final holdout still closed

Only a later explicit owner authorization may replace the draft contract with an executable first-run contract.
