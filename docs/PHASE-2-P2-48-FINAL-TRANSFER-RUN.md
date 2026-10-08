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
