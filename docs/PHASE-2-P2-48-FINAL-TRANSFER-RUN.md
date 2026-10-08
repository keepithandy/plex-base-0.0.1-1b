# P2-48 — Final Bounded Phase 2 Transfer Run

## Status

**Bundle preparation and zero-update sampler preflight implemented. Checkpoint staging and model training are not authorized yet.**

## Purpose

P2-48 is the final bounded Phase 2 training experiment.

It will test whether the P2-47 representation improves the missing behavior identified by P2-46:

> familiar coding knowledge should be selected because the current coding request asks for it.

P2-47 changed the learning target from semantic-plan labels to:

```text
exact request evidence
        ↓
concrete coding intent
```

Before any weight update, P2-48 freezes the exact data/tokenizer/sampler packet.

## Frozen P2-47 candidate

- representation: `plex-request-grounded-change-v1`
- candidate SHA-256: `6e39259cc8fc1646fb7a16d2056706312f8736d330f94a642690aaf9d1c1489a`
- bytes: **81,032**
- records: **108**
- train: **72**
- validation: **36**
- P2-31 exact request overlap: **0**

Train/validation transfer boundary:

- exact request overlap: **0**
- exact solution overlap: **0**
- exact non-empty binding-set overlap: **0**
- validation targets seen in train: **18 / 18**
- validation binding intents seen in train: **18 / 18**
- validation actions seen in train: **3 / 3**

## Frozen tokenizer review

The real P2-47 review passed against the P2-44 tokenizer bundle:

- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- source bundle manifest SHA-256: `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`
- maximum record size: **286 / 512 tokens**
- train tokens: **19,377**
- validation tokens: **9,763**

## Proposed bounded run

The proposed P2-48 experiment remains:

- seed: **1337**
- micro-batch: **1**
- gradient accumulation: **16**
- maximum optimizer updates: **100**
- maximum wall time: **600 seconds**
- examples at 100 updates: **1,600**
- validation: **0 / 25 / 50 / 75 / 100**
- checkpoints: **25 / 50 / 75 / 100**
- device: **CUDA**
- resume: **disabled**
- automatic continuation: **disabled**

These settings are a proposal only until the bundle and sampler identities are frozen.

## Source model

The proposed source model is the fixed P2-44 step-100 endpoint:

- checkpoint SHA-256: `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- step: **100**

P2-48 does not reuse the P2-44 optimizer or sampler state.

## Step 1 — Pack the P2-48 bundle

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-bundle-prepare
```

Expected status:

```text
training-bundle-prepared-zero-update
```

The bundle is written under:

```text
training/artifacts/request-grounded/p2-48-training-bundle
```

This command does not create an optimizer or checkpoint and performs no gradient updates.

## Step 2 — Replay the proposed sampler

Run:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-bundle-preflight `
  --report training/artifacts/request-grounded/p2-48-bundle-preflight.json
```

Expected status:

```text
bundle-preflight-passed-awaiting-stage-decision
```

The preflight must show:

- all **72** training records selected
- deterministic minimum/maximum record selection counts
- exact expected real target positions for 100 updates
- exact train/validation JSONL hashes
- exact token-file hashes
- exact index hashes
- training still unauthorized
- checkpoint staging still unauthorized
- final holdout still closed

## What happens after the preflight

The actual local bundle/preflight JSON is frozen in the repository first.

Only then may a separate P2-48 stage decision be added. That later stage must:

1. verify the exact P2-44 step-100 source checkpoint,
2. preserve model weights bit-for-bit,
3. reset P2-48 step/tokens to zero,
4. create a fresh empty optimizer state only for stage serialization,
5. reset sampler state,
6. keep model training unauthorized until the final training preflight/approval packet is reviewed.

## Decision boundary

This milestone currently authorizes:

- deterministic bundle packing
- bundle inspection
- deterministic sampler replay

It does **not** authorize:

- checkpoint staging
- optimizer creation for training
- gradient updates
- automatic continuation
- P2-49 evaluation
- final project holdout access


## Real bundle and sampler preflight

The local P2-48 bundle/preflight passed and is frozen.

Bundle identities:

- bundle manifest SHA-256: `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`
- source dataset manifest SHA-256: `6cab42b964f4d11680c4109cf4787f9074ba62a9cbff23f92b301d497f77771c`
- train JSONL SHA-256: `39879c1199e975096ba962fcad023b3b112c2c8b6444c0a3a9f35971a945d530`
- validation JSONL SHA-256: `9f9514e0feda3e29eb63ee4308e87b94666f05229cfbd26a619a5a35a9708226`
- train token SHA-256: `2aa8cb0d7970ae8ac329f71fd5d2df00df2345181ae9e8e79534f44409b46785`
- validation token SHA-256: `8e8307953e2c1c4afcb7dc20c32f5a797611bf2371912a2480312f2094fc004c`
- train index SHA-256: `5d94bf9c3f0a0867cf945abd965f763c800444cba7162d6cbc522d5de049235f`
- validation index SHA-256: `2151edd14d340377feb42e2f1baa8fcbefe02aad070429e2dbf9ba519a79f52a`

Sampler replay:

- seed: **1337**
- examples: **1,600**
- records selected: **72 / 72**
- minimum selections: **12**
- maximum selections: **33**
- expected real target positions: **429,375**

No training occurred.

## Step-zero stage

P2-48 now authorizes one non-training step-zero stage from the exact P2-44 endpoint:

- source checkpoint SHA-256: `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- source step: **100**
- source tokens processed: **565,641**
- source stage kind: `plex-evidence-first-semantic-composition-stage-transition-v1`
- source training kind: `p2-44-authorized-evidence-composition-training-v1`

Run the read-only source check:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-stage-source-preflight
```

Then create the stage:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-stage
```

The stage must preserve the model weights exactly, reset P2-48 step/tokens to zero, reset sampler state, serialize a fresh empty optimizer state, and keep training settings/schedule null.

P2-48 model training remains unauthorized after stage creation.


## Final CUDA training preflight

The zero-update stage passed locally and is frozen:

- stage checkpoint SHA-256: `52aabd0c3d07125dfd89eafd1cd9ecfbb79cbf8a89dfa15c8f8334ead3f2dd60`
- model weights preserved: **true**
- optimizer state empty: **true**
- sampler reset: **true**
- P2-48 stage step: **0**
- P2-48 stage tokens: **0**
- training performed: **false**

The next step is the final read-only CUDA preflight:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-training-preflight `
  --report training/artifacts/request-grounded/p2-48-training-preflight.json
```

It verifies:

- exact stage SHA
- exact bundle/data/token/index identities
- exact request-grounded prompt prefix
- deterministic 1,600-example sampler replay
- **429,375** expected real target positions
- CUDA availability
- step-zero validation loss
- no optimizer step
- no checkpoint write
- no training authorization
- final holdout closed

Expected status:

```text
training-preflight-passed-awaiting-owner-authorization
```

After the preflight result is frozen, P2-48 can be presented as one final bounded 100-update training decision.


## Frozen training authorization packet

The final CUDA preflight passed with:

- baseline validation loss: **6.505710401033101**
- baseline validation batches: **19**
- expected examples: **1,600**
- expected real target positions: **429,375**
- stage checkpoint SHA-256: `52aabd0c3d07125dfd89eafd1cd9ecfbb79cbf8a89dfa15c8f8334ead3f2dd60`
- bundle manifest SHA-256: `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`

The bounded runner is implemented and guarded by:

```text
training/pretraining/p2-48-first-run-contract.json
```

The checked-in authorization state is intentionally:

```text
status: owner-approval-required
modelTrainingAuthorized: false
approvedBy: null
approvedDate: null
```

Running the command below before explicit owner approval must fail before the training preflight or optimizer can run:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-run
```

After explicit owner authorization, only the authorization fields may change. The frozen stage, data, sampler, baseline, schedule, limits, evaluation policy, and continuation rule must remain identical.

The approved run remains bounded to:

- **100** optimizer updates maximum
- **600** seconds maximum
- validation at **0 / 25 / 50 / 75 / 100**
- checkpoints at **25 / 50 / 75 / 100**
- no resume
- no automatic continuation
- fixed step-100 endpoint policy unless the run stops early
- P2-31 development evaluation only after the final completed step
- final project holdout closed

No P2-48 gradient update is authorized by the current repository state.


## Actual bounded training result

P2-48 completed the full authorized run.

- completed optimizer updates: **100 / 100**
- elapsed time: **20.2421 seconds**
- examples: **1,600**
- real target positions: **429,375**
- padding target positions: **0**
- all training records selected: **72 / 72**
- selection range: **12–33**
- final checkpoint SHA-256: `fd86d11375e547f05b2fab7a36188ca30a7ecd0b0f38198de62bcddbfba489b7`
- final holdout opened: **false**
- continuation authorized: **false**

Validation curve:

| Step | Mean loss |
|---:|---:|
| 0 | **6.505710401033101** |
| 25 | **2.7775440717998303** |
| 50 | **2.913108511974937** |
| 75 | **3.1200873851776123** |
| 100 | **3.233508963333933** |

### Interpretation

P2-48 clearly learned the P2-47 request-grounded representation: validation loss fell sharply by step 25.

The validation curve then worsened from step 25 through step 100, which is an overfitting signal.

The frozen evaluation policy does **not** permit retrospective checkpoint selection. Therefore:

- step 25 is recorded as the best measured internal validation point,
- step 100 remains the fixed P2-48 endpoint,
- P2-49 evaluates **only** step 100,
- no P2-48 continuation is authorized.

Internal validation alone does not establish coding-request transfer. P2-49 is the unchanged external development gate.
