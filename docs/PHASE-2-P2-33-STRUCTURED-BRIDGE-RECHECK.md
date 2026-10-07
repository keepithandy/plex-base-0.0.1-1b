# P2-33 — Structured Bridge Re-evaluation

## Status

**Evaluation authorized — October 7, 2026. No model training is authorized.**

P2-33 re-runs the exact P2-31 structured-plan development gate against the official P2-32 step-100 endpoint.

This is intentionally a re-evaluation rather than a new task set so the project can answer one narrow question:

> Did P2-32 representation training fix the original 0/18 JSON-plan failure on development requests that were excluded from P2-32 gradients?

## Fixed checkpoint

- path: `training/artifacts/structured-plan/p2-32-first-run/checkpoints/step-0100.pt`
- step: **100**
- SHA-256: `707e46f9e3e87cdd9beec705e2bd55701b37a40e79aad7ab93858fa63f8ebcf4`

The generator also verifies:

- stage transition kind: `plex-structured-plan-stage-transition-v1`
- stage milestone: `P2-32`
- training settings kind: `p2-32-authorized-structured-plan-training-v1`

## Unchanged development set

P2-33 reuses:

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

SHA-256:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

The 18 tasks and expected plans are unchanged.

## Unchanged gate

The original P2-31 gate remains:

- **12 / 18** complete plans overall
- at least **3 / 6** complete plans in HTML
- at least **3 / 6** complete plans in CSS
- at least **3 / 6** complete plans in JavaScript
- at least **15 / 18** schema-valid JSON plans

The threshold is not lowered after seeing P2-32 training behavior.

## Baseline comparison

P2-31 on the pre-P2-32 checkpoint scored:

- complete plans: **0 / 18**
- schema-valid plans: **0 / 18**
- checks: **36 / 162**
- all 18 responses present and untruncated

## Commands

Generate deterministic responses:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --checkpoint training/artifacts/structured-plan/p2-32-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-32-training-bundle `
  --contract training/pretraining/p2-33-structured-bridge-contract.json `
  --output-dir structured-plan/p2-33-step100 `
  --device cuda
```

Score them:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-33-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-33-step100/evaluation.json
```

Both commands perform **zero optimizer updates** and keep the final project holdout sealed.
