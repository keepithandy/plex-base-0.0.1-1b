# P2-41 — Request-Conditioned Plan Binding

## Status

**Preparation milestone opened — October 7, 2026. No model training is authorized.**

## Why P2-41 exists

P2-40 showed two distinct failure families in the fixed P2-39 bridge responses:

1. structural serialization instability
2. request-conditioned semantic binding failure

The measured P2-40 decomposition was:

- invalid JSON: **9 / 18**
- parseable JSON but invalid strict plan schema: **4 / 18**
- schema-valid semantic mismatch: **5 / 18**

Among the five schema-valid outputs:

- language: **5 / 5**
- action: **3 / 5**
- targetKind: **5 / 5**
- targetRole: **0 / 5**
- exact constraints: **0 / 5**
- required hint coverage: **0 / 5**

Plex is therefore showing emerging broad-category recognition without reliable request-conditioned binding.

## Research question

Can a contrastive full-plan curriculum teach Plex to use the specific request to select the correct semantic plan fields instead of reusing a familiar plan bundle from the same language or target kind?

## Design principle

P2-41 must make template reuse insufficient.

Training groups should deliberately share superficial structure while requiring different semantic outputs.

Required contrast families include:

### Same language + same target kind + different target role

The model cannot solve the group by learning only the language or target kind.

### Same language + same target kind + same action + different constraints

The model must condition on the request details that determine the constraint set.

### Similar request wording + different action

The model must distinguish create/modify-style intent instead of selecting a familiar action template.

### Same output skeleton + different semantic field values

The serialized shape stays constant while the semantic content changes.

### Similar domain vocabulary + different search hints

The model must derive bounded search concepts from the current task rather than copying neighboring hints.

## Serialization track

P2-41 also needs to reinforce the canonical strict-plan boundary:

- exactly one `schemaVersion`
- exactly one `language`
- exactly one `action`
- exactly one `targetKind`
- exactly one `targetRole`
- one valid `constraints` array
- one valid `searchHints` array
- no duplicate keys
- no malformed nested constraint objects
- no prose outside the JSON object
- all required fields present

Serialization is necessary but must not become the only learning objective.

## Semantic track

Diagnostic emphasis should be placed on:

- `targetRole`
- exact `constraints`
- required `searchHints`

while retaining independent measurement of:

- `language`
- `action`
- `targetKind`

## Evaluation

Any later bridge re-evaluation must preserve the exact P2-39/P2-40 baseline:

- complete plans: **0 / 18**
- schema-valid plans: **5 / 18**
- checks passed: **54 / 162**

Among schema-valid outputs:

- language: **5 / 5**
- action: **3 / 5**
- targetKind: **5 / 5**
- targetRole: **0 / 5**
- constraints exact: **0 / 5**
- hint coverage: **0 / 5**

Report structural and semantic measurements separately.

## Leakage restrictions

P2-41 preparation must not:

- train on P2-31 development answers
- copy P2-31 expected plans into the curriculum
- create trivial paraphrases of individual P2-31 tasks that expose their expected plans
- inspect or score the final project holdout

Use independently constructed semantic families and preserve existing contamination/overlap checks.

## Architecture boundary

Plex Nano should learn semantic normalization and bounded plan selection.

Plex Code should continue to own deterministic repository lookup, exact literal resolution, mutation, validation, and diff generation.

P2-41 should not move deterministic repository resolution back into the model simply to improve a benchmark.

## Preparation acceptance checks

Before any bounded P2-41 training authorization, the repository should demonstrate:

- deterministic candidate generation
- valid structured-plan targets
- no duplicate task IDs
- intact contrast groups
- train/validation group separation
- no prohibited P2-31 target leakage
- frozen tokenizer identity
- token/context bounds
- reproducible candidate hashes
- explicit starting checkpoint identity
- explicit fixed-step training contract
- no automatic continuation
- final holdout protection

## Training authorization

**None yet.**

Do not perform P2-41 optimizer updates until a separate reviewed authorization contract records the exact candidate, tokenizer, starting checkpoint, step/time bounds, checkpoint schedule, and owner approval.

The fixed P2-39/P2-40 development baseline must remain unchanged for later comparison.


## Preparation tooling

The first P2-41 preparation tooling now exists and performs no model training.

It deterministically generates:

- **108** strict full-plan records
- **36** intact three-record contrast groups
- **72 train / 36 validation** records
- **24 train / 12 validation** records per language
- **9 groups / 27 records** for each contrast family:
  - `role`
  - `constraints`
  - `action`
  - `hints`

Within every language, each contrast family has exactly **2 train groups and 1 validation group**.

The reviewer enforces:

- exact P2-31 development-set identity
- zero exact P2-31 request overlap
- zero P2-31 targetRole overlap
- zero exact P2-31 expected-plan overlap
- strict production-plan parsing
- intact group/split topology
- isolation of the intended contrast dimension
- optional frozen-tokenizer roundtrip/context preflight
- zero optimizer updates
- closed final holdout

### Generate the candidate

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-generate
```

This creates:

```text
training/phase2/drafts/p2-41-request-conditioned-plan-binding-v1.jsonl
training/phase2/drafts/p2-41-request-conditioned-plan-binding-v1.review.json
```

Generation refuses to overwrite existing candidate/review outputs.

### Review the generated candidate

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-review
```

For frozen-tokenizer preflight, add the verified tokenizer bundle:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-review `
  --bundle-dir <verified-frozen-tokenizer-bundle>
```

No P2-41 training command exists yet. Candidate generation and review must pass before a separate bounded-run packet is designed.


## Frozen candidate and tokenizer preflight

Owner verification passed with:

- candidate SHA-256: `20f309181adbd4c86ff0c5a7ad833792d754e3a9102000003922696a237b64ba`
- candidate bytes: **91,551**
- records / groups: **108 / 36**
- train / validation: **72 / 36**
- unique requests: **108**
- unique target roles: **54**
- P2-31 exact-request overlap: **0**
- P2-31 targetRole overlap: **0**
- P2-31 exact expected-plan overlap: **0**
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- maximum record length: **374 tokens including EOS**
- train tokens: **25,599**
- validation tokens: **12,798**
- focused tests: **5 passed**
- full training suite: **281 passed**
- training performed: **false**
- research optimizer updates: **0**
- final holdout opened: **false**

Machine-readable evidence:

`training/pretraining/p2-41-preparation-result.json`

## Zero-update execution path

P2-41 now has three preparation commands and deliberately has **no training command**.

### Step 1 — pack the frozen candidate

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-prepare `
  --source-bundle-dir training/artifacts/structured-plan/p2-35-training-bundle
```

Expected output:

`training/artifacts/structured-plan/p2-41-training-bundle`

### Step 2 — create the weights-only P2-41 stage

P2-41 stages from the fixed P2-38 step-100 endpoint:

`training/artifacts/structured-plan/p2-38-first-run/checkpoints/step-0100.pt`

Pinned SHA-256:

`9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6`

Run:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-stage `
  --base-checkpoint training/artifacts/structured-plan/p2-38-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-41-training-bundle
```

Expected output:

`training/artifacts/structured-plan/p2-41-stage0/stage-checkpoint.pt`

The stage must preserve the P2-38 weights exactly while resetting optimizer state, sampler state, P2-41 step, and P2-41 token accounting.

### Step 3 — read-only CUDA preflight

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-request-binding-preflight `
  --bundle-dir training/artifacts/structured-plan/p2-41-training-bundle `
  --stage-checkpoint training/artifacts/structured-plan/p2-41-stage0/stage-checkpoint.pt
```

This reports the exact bundle/stage hashes, JSONL/index hashes, complete-record sampler identity, expected 100-step real-target count, and stage-zero validation loss.

It still reports:

- `authorized=false`
- `modelTrainingAuthorized=false`
- `trainingPerformed=false`
- `researchOptimizerUpdates=0`
- `finalHoldoutOpened=false`

Only after those identities are measured may a separate P2-41 first-run authorization contract be prepared.


## Measured zero-update preflight

The P2-41 zero-update CUDA preflight passed with the fully measured packet:

- base P2-38 checkpoint SHA-256: `9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6`
- P2-41 bundle manifest SHA-256: `a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a`
- P2-41 stage checkpoint SHA-256: `763920474516488e5bc68d00e77320916c95d9c67253752c03f48f9da36b67fd`
- train JSONL SHA-256: `458de009e4ef227361e2813c7380bfa2d42739f36335ed333ea3b6a250800db3`
- validation JSONL SHA-256: `020324cb8d4b5d4fc0737fd741e498640d3636c326a58d25428db88279a3bd16`
- train index SHA-256: `0ab27caccc5ba11d9d321660197794cff8d2c074fdb843f0149204234a328104`
- validation index SHA-256: `70f546c7d3b9c3a99c0e2efc4d16335ea7d1e9fdab90ee7e4f7d1017a8d29c5a`
- baseline validation loss: **3.0144005020459494**
- baseline validation batches: **24**
- expected examples at 100 steps: **1,600**
- expected real target positions at 100 steps: **567,311**
- device: **CUDA**
- training performed: **false**
- research optimizer updates: **0**
- final holdout opened: **false**

Machine-readable evidence:

`training/pretraining/p2-41-stage-preflight-result.json`

A draft first-run contract now exists at:

`training/pretraining/p2-41-first-run-contract.json`

The draft uses the measured packet above and proposes:

- maximum optimizer updates: **100**
- maximum wall time: **600 seconds**
- micro-batch: **1**
- gradient accumulation: **16**
- seed: **1337**
- validation: **0 / 25 / 50 / 75 / 100**
- checkpoints: **25 / 50 / 75 / 100**
- no resume
- no automatic continuation

The draft is intentionally still unauthorized:

- `modelTrainingAuthorized=false`
- `approvedBy=null`
- `approvedDate=null`
- `command=null`

No P2-41 training runner should be used until the current test suite passes against this packet and the owner explicitly authorizes the bounded first run.
