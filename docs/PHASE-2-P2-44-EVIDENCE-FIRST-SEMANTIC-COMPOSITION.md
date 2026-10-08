# P2-44 — Evidence-First Semantic Composition

## Status

**Design/preparation only. No model training is authorized.**

P2-44 replaces the P2-41 semantic-binding representation rather than extending it.

## Problem to solve

P2-43 showed that P2-41 solved much of the output-serialization problem but did not solve request-conditioned semantic composition.

The model frequently emitted exact P2-41 training roles, constraints, hints, semantic bundles, and even full plans on unrelated P2-31 development requests.

The next curriculum must therefore make the semantic fields themselves derivable from current-request evidence.

## Core hypothesis

Plex should generalize better when:

1. semantic atoms are visible or deterministically inferable from the request,
2. the same atoms appear in multiple contexts,
3. training examples recombine those atoms in many ways,
4. validation contains **new combinations of familiar atoms**, and
5. arbitrary milestone-specific semantic labels are eliminated.

The test is not whether Plex can memorize another larger list of roles.

The test is whether Plex can compose a never-seen semantic bundle from familiar request evidence.

## Keep the production output

P2-44 keeps:

- the current structured-plan production prompt
- the strict full-plan JSON schema
- the same HTML/CSS/JavaScript scope
- the frozen 16,384-token tokenizer
- deterministic review and hash pinning

P2-44 does **not** introduce a new micro-JSON inference format merely to make training easier.

Serialization improved substantially in P2-41/P2-42. The representation change should target semantic binding without discarding that progress.

## Remove opaque semantic labels

P2-44 targets may not use arbitrary milestone-specific identifiers such as:

```text
p241-pricing-table-target
p241-score-average-target
p241-card-layout-primary
```

A targetRole must instead be supported by semantic atoms in the request or by a documented deterministic normalization.

For example, a request that clearly describes a profile image upload control might support a normalized role such as:

```text
profile-image-upload
```

The curriculum should not assign a role such as:

```text
p244-control-17-primary
```

because that identifier cannot be composed from request evidence.

## Ground every semantic field

### targetRole

Every meaningful atom must trace to request wording or a deterministic normalization rule.

### constraints

Constraint kind/key/value triples must represent explicit requirements in the request.

Do not inject stable filler constraints simply to make examples share a template.

### searchHints

Hints must be concise lexical anchors derived from the request.

Generic filler tokens such as `requirements`, `primary`, `lifecycle`, or `settings` are not acceptable unless the request genuinely supplies that meaning.

### action

Keep action directly request-conditioned and contrast it independently.

### targetKind

Continue using the language-bound target kind, but do not let targetKind stand in for semantic understanding.

## Composition-first split

The train/validation split must hold out **combinations**, not arbitrary labels.

A semantic atom may appear during training.

A pair or bundle of atoms may then be withheld from training and appear only in validation.

Example concept:

```text
Training:
  profile + card
  profile + image
  account + card
  account + image-upload

Validation:
  profile + image-upload
```

The exact semantic bundle must be unseen even though the underlying pieces are familiar.

That is the behavior P2-44 needs to measure.

## Required contrast families

The candidate should contain balanced contrasts for at least:

1. **role composition**
   - same action/kind, different semantic nouns/modifiers
2. **constraint binding**
   - same role, different explicit requirements
3. **hint grounding**
   - same broad target, different lexical lookup evidence
4. **action discrimination**
   - same semantic target, different lifecycle action
5. **cross-field coherence**
   - role, constraints, and hints must all describe the same request instead of independent familiar templates
6. **near-neighbor discrimination**
   - requests with overlapping vocabulary but different intended semantic bundles

## Required review before training

Before any model-training authorization, record:

- candidate record count
- language balance
- semantic atom inventory by field
- train/validation atom overlap
- exact train/validation targetRole overlap
- exact train/validation constraint-set overlap
- exact train/validation search-hint overlap
- exact train/validation semantic-bundle overlap
- exact train/validation full-plan overlap
- P2-31 exact request overlap
- P2-31 exact targetRole overlap
- P2-31 exact expected-plan overlap
- maximum record length under the frozen tokenizer
- candidate SHA
- review SHA

The desired split is:

- familiar semantic atoms
- novel combinations
- **zero exact semantic-bundle leakage**

## Success question

The next experiment should answer:

> Can Plex produce the correct novel targetRole, constraints, and search-hint combination from current-request evidence when the individual semantic atoms are familiar but the complete bundle was never present in training?

That is substantially stricter than fitting a list of arbitrary semantic templates.

## Protected evaluation

The following remain excluded from P2-44 training:

- exact P2-31 development requests
- exact P2-31 targetRole strings
- exact P2-31 expected plans
- P2-42 generated responses
- P2-43 diagnostic output
- the final project holdout

## Current authorization

P2-44 currently authorizes only:

- curriculum design
- deterministic candidate generation
- deterministic leakage/composition review
- frozen-tokenizer preflight

It does **not** authorize:

- checkpoint staging
- optimizer creation
- gradient updates
- continuation from P2-41
- automatic training


## Implemented candidate topology

The deterministic P2-44 generator now uses:

- **162 total records**
- **54 contrast groups**
- **108 train records / 36 train groups**
- **54 validation records / 18 validation groups**
- **54 records per language**
  - 36 train
  - 18 validation
- six contrast families:
  - role composition
  - constraint binding
  - hint grounding
  - action discrimination
  - cross-field coherence
  - near-neighbor discrimination

Each family has two train groups and one validation group per language.

The role space is built from reusable domain/object atoms. Exact validation target roles are absent from training, while every validation role atom must already be present in training. The same requirement applies to validation constraint atoms and hint atoms.

The reviewer rejects:

- exact train/validation targetRole overlap
- exact train/validation semantic-bundle overlap
- exact train/validation full-plan overlap
- any validation role/constraint/hint atom not already present in training
- any exact P2-31 request, targetRole, or expected-plan overlap
- milestone-prefixed semantic roles
- declared grounding evidence that is not literally present in the request

Constraint-set overlap is measured rather than forbidden because P2-44 intentionally tests recombination of familiar requirement atoms into unseen role/bundle combinations.

## Deterministic tooling

Generate the candidate:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-generate
```

Review grounding, composition, and protected-development leakage:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-review `
  --bundle-dir training/artifacts/structured-plan/p2-41-training-bundle
```

The optional bundle argument performs frozen-tokenizer roundtrip, context-length, train-token, validation-token, tokenizer-SHA, and bundle-manifest checks.

Successful review still leaves:

```text
modelTrainingAuthorized = false
trainingPerformed       = false
researchOptimizerUpdates = 0
finalHoldoutOpened      = false
```

No stage/run command exists for P2-44 at this point.


## Candidate review result

The local deterministic review passed and is now frozen.

Candidate:

- SHA-256: `fc56eca2186e2b7f643af9fbec514c1d5d34248eba2ac380b9f93c482b945c30`
- bytes: **182,492**
- records: **162**
- train / validation: **108 / 54**
- groups: **54**

Protected-development leakage:

- exact P2-31 request overlap: **0**
- exact P2-31 targetRole overlap: **0**
- exact P2-31 expected-plan overlap: **0**

Composition holdout:

- exact train/validation targetRole overlap: **0**
- exact train/validation search-hint overlap: **0**
- exact train/validation semantic-bundle overlap: **0**
- exact train/validation full-plan overlap: **0**
- validation role atoms seen in train: **19 / 19**
- validation constraint atoms seen in train: **18 / 18**
- validation hint atoms seen in train: **22 / 22**

Exact constraint-set overlap is **27**. This is intentional: P2-44 is designed to reuse familiar requirements while withholding the exact role/bundle/full-plan composition.

Frozen-tokenizer preflight:

- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- bundle manifest SHA-256: `a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a`
- maximum record tokens including EOS: **375 / 512**
- train tokens: **38,280**
- validation tokens: **19,186**

The candidate identity and tokenizer accounting are now hard-pinned in the preparation contract and curriculum code. Regeneration or review will fail if they drift.

### Next gate

The next allowed work is a deterministic **training-bundle pack/preflight** step:

```text
reviewed candidate
→ frozen tokenizer pack
→ train/validation JSONL + token/index manifests
→ exact bundle hashes
→ zero-update preflight
```

This does not authorize checkpoint staging or model training.


## Training-bundle packing and zero-update preflight

P2-44 now has a deterministic bundle packer and sampler preflight. These commands do not create a checkpoint, optimizer, or training runner.

Pack the frozen candidate with the exact frozen tokenizer:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-prepare
```

The default output is:

```text
training/artifacts/structured-plan/p2-44-training-bundle
```

The bundle contains:

- `train.jsonl`
- `validation.jsonl`
- `train.tokens.u16le`
- `validation.tokens.u16le`
- `train.index.json`
- `validation.index.json`
- `source-dataset-manifest.json`
- `manifest.json`
- copied frozen tokenizer/model-config files

The packer re-verifies the frozen candidate SHA, tokenizer identity, split counts, token totals, maximum record length, rendered prompt shape, token roundtrips, indices, and all file hashes.

Run the zero-update sampler preflight:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-preflight
```

The preflight:

- re-inspects the entire packed bundle
- loads the complete-record sampler
- replays a **proposal-only** 100-step / micro-batch-1 / accumulation-16 schedule
- reports the 1,600 selected examples
- reports deterministic expected real target positions
- reports record-selection coverage and min/max selection counts
- performs **0** optimizer updates
- creates **0** checkpoints
- does **not** authorize model training

A successful preflight ends at:

```text
bundle-preflight-passed-awaiting-separate-stage-decision
```

Checkpoint staging remains a separate future decision.


## Frozen bundle and sampler result

The real local P2-44 bundle and sampler replay passed and are now frozen.

Bundle identity:

- bundle manifest SHA-256: `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`
- source dataset manifest SHA-256: `18d827d2e6bef3aaee41afacee163f16367dc6fc5198334f321c88f7623515b8`
- train JSONL SHA-256: `0141dbd0209d10e2138a0a90ff688e97b4b1de39f91c28ca367ed7267b309789`
- validation JSONL SHA-256: `8b690e91335aab703a331de41ea0d6d801d68058f0dc1a3eada716d952fede2c`
- train index SHA-256: `5364aef18ff9ce5c702989953bf19268c7f4a8af079e84fc2f90672e8a63fc09`
- validation index SHA-256: `5c409f624474173648d5068fd1961ea3659ceb304dc65fe66382343cff29ea59`

Accounting remains:

- train records: **108**
- validation records: **54**
- train tokens: **38,280**
- validation tokens: **19,186**
- maximum record length: **375 / 512**

The proposal-only complete-record sampler replay used:

- seed: **1337**
- proposed steps: **100**
- micro-batch: **1**
- gradient accumulation: **16**
- examples: **1,600**
- expected real target positions: **565,641**
- records selected: **108 / 108**
- minimum selections per record: **5**
- maximum selections per record: **24**

No optimizer, checkpoint stage, or gradient update was created by this replay.

## Stage-source compatibility gate

P2-44 now has a separate read-only gate for verifying the intended weight source.

The intended source is the fixed P2-41 endpoint:

```text
training/artifacts/structured-plan/p2-41-first-run/checkpoints/step-0100.pt
```

Expected SHA-256:

```text
adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc
```

The verifier checks:

- exact checkpoint SHA
- P2-41 step **100**
- P2-41 total processed targets **567,311**
- model parameter count/config
- scratch-model initialization provenance
- P2-41 stage-transition provenance
- P2-41 authorized-training provenance
- frozen tokenizer identity
- frozen P2-44 bundle compatibility

Run it with:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-stage-preflight
```

A successful result ends at:

```text
stage-source-preflight-passed-awaiting-stage-authorization
```

The command is read-only. It does not create an optimizer or stage checkpoint.

Actual P2-44 stage creation remains a separate future authorization decision.


## Step-zero stage construction

The real stage-source preflight passed against the exact P2-41 step-100 endpoint:

- checkpoint SHA-256: `adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc`
- checkpoint step: **100**
- previous processed targets: **567,311**
- parameters: **27,566,080**
- source stage kind: `plex-request-conditioned-plan-binding-stage-transition-v1`
- source training kind: `p2-41-authorized-request-binding-training-v1`
- P2-44 bundle compatibility: **passed**

P2-44 now authorizes creation of one step-zero stage checkpoint. This authorization is deliberately narrower than training authorization.

Run:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-stage
```

Default output:

```text
training/artifacts/structured-plan/p2-44-stage0
```

The stage creator must prove after reload that:

- every model tensor is bit-identical to the P2-41 base
- the fresh AdamW optimizer has empty state
- P2-41 optimizer state is not reused
- sampler RNG resets to seed **1337**
- P2-41 sampler state is not reused
- P2-44 stage step is **0**
- P2-44 processed targets are **0**
- training settings are null
- schedule state is null
- the exact frozen P2-44 bundle/tokenizer records are attached
- no gradient update occurred

The expected terminal status is:

```text
stage-created-training-not-authorized
```

A successful stage does **not** authorize a training run. Its checkpoint SHA must be frozen first, followed by a separate training preflight/authorization packet.


## Frozen step-zero stage result

The real P2-44 step-zero stage was created successfully and is now frozen.

Stage identity:

- checkpoint: `training/artifacts/structured-plan/p2-44-stage0/stage-checkpoint.pt`
- checkpoint SHA-256: `e454bf4851690d599c88c898a77b7b741b95fe7fbc291f43e98d34bf35807ef4`
- base checkpoint SHA-256: `adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc`
- parameter count: **27,566,080**
- P2-44 stage step: **0**
- P2-44 processed targets: **0**

Verified stage properties:

- model weights preserved bit-for-bit using `torch.equal`
- fresh AdamW object created only for serialization
- optimizer state empty
- prior optimizer state not reused
- sampler RNG reset
- prior sampler state not reused
- training settings null
- schedule state null
- gradient updates: **0**
- final holdout: **closed**

## Training preflight

P2-44 now has a separate read-only training preflight around the exact frozen stage SHA.

The preflight will:

1. re-verify the exact stage checkpoint SHA and zero-update stage semantics
2. re-verify every frozen P2-44 bundle/data/tokenizer hash
3. replay the deterministic **1,600-example** complete-record sampling schedule
4. require the expected **565,641** real target positions
5. require CUDA for the real local run
6. measure the untouched stage's step-zero validation loss
7. report the proposed bounded training/evaluation schedule
8. stop without taking an optimizer step or writing a checkpoint

Run:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-training-preflight
```

The proposed run remains:

- seed: **1337**
- device: **CUDA**
- maximum steps: **100**
- maximum wall time: **600 seconds**
- micro-batch: **1**
- gradient accumulation: **16**
- validation steps: **0, 25, 50, 75, 100**
- checkpoint steps: **25, 50, 75, 100**
- resume: **disabled**
- automatic continuation: **disabled**

A successful preflight ends at:

```text
training-preflight-passed-awaiting-owner-authorization
```

That status still means:

```text
modelTrainingAuthorized  = false
optimizerStepAuthorized  = false
checkpointWriteAuthorized = false
researchOptimizerUpdates = 0
```

The baseline validation loss returned by the real CUDA preflight must be frozen before any P2-44 training authorization packet can exist.


## Frozen CUDA training preflight

The real CUDA training preflight passed.

Frozen baseline:

- validation loss: **3.3981438778542183**
- validation batches: **37**
- stage checkpoint SHA-256: `e454bf4851690d599c88c898a77b7b741b95fe7fbc291f43e98d34bf35807ef4`
- expected examples at 100 steps: **1,600**
- expected real target positions: **565,641**
- device: **CUDA**
- resume: **disabled**
- automatic continuation: **disabled**

The first-run implementation now exists, but the checked-in authorization packet remains deliberately unsigned:

```text
status                  = owner-approval-required
modelTrainingAuthorized = false
approvedBy              = null
approvedDate            = null
```

The runner fails closed before it performs CUDA preflight or creates an optimizer unless the exact frozen packet is explicitly changed to:

```text
status                  = owner-approved-first-run
modelTrainingAuthorized = true
approvedBy              = keepithandy
approvedDate            = 2026-10-08
```

No other scientific field may change at approval time.

The bounded run, once explicitly authorized, is locked to:

- **100** maximum optimizer updates
- **600 seconds** maximum wall time
- micro-batch **1**
- accumulation **16**
- validation at **0 / 25 / 50 / 75 / 100**
- checkpoint saves at **25 / 50 / 75 / 100**
- fixed step-100 endpoint policy
- no retrospective lowest-loss checkpoint selection
- no resume
- no automatic continuation
- final holdout closed
- P2-31 development evaluation only after the bounded run, never for gradients or checkpoint selection

The command is present but cannot run while the packet is unsigned:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evidence-composition-run
```

P2-44 is therefore technically ready for an explicit owner training decision, but **training is not authorized by the repository state yet**.
