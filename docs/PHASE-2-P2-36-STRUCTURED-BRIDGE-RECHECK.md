# P2-36 — Structured Bridge Re-evaluation

## Status

**Evaluation authorized — October 7, 2026. No model training is authorized.**

P2-36 re-runs the exact P2-31 structured-plan development gate against the official P2-35 step-100 endpoint.

The purpose is narrow:

> Did P2-35 serialization-stability training convert the previous malformed-JSON failure into valid, semantically usable structured plans on unchanged development requests excluded from P2-35 gradients?

## Fixed checkpoint

- path: `training/artifacts/structured-plan/p2-35-first-run/checkpoints/step-0100.pt`
- step: **100**
- SHA-256: `1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0`

The generator also verifies:

- stage kind: `plex-serialization-stability-stage-transition-v1`
- stage milestone: `P2-35`
- training settings kind: `p2-35-authorized-serialization-stability-training-v1`

## Unchanged development set

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

SHA-256:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

The same 18 tasks are used again.

## Unchanged gate

- **12 / 18** complete plans overall
- at least **3 / 6** HTML
- at least **3 / 6** CSS
- at least **3 / 6** JavaScript
- at least **15 / 18** schema-valid JSON plans

The thresholds are not changed after observing P2-35 training behavior.

## Comparison baseline

P2-33 on the pre-P2-35 endpoint scored:

- complete plans: **0 / 18**
- schema-valid plans: **0 / 18**
- checks: **36 / 162**

## Commands

Generate deterministic responses:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --checkpoint training/artifacts/structured-plan/p2-35-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-35-training-bundle `
  --contract training/pretraining/p2-36-structured-bridge-contract.json `
  --output-dir structured-plan/p2-36-step100 `
  --device cuda
```

Score responses:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-36-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-36-step100/evaluation.json
```

Both commands perform **zero optimizer updates** and keep the final project holdout sealed.
