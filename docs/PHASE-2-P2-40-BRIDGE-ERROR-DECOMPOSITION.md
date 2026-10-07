# P2-40 — Bridge Error Decomposition

## Status

**Read-only diagnostic prepared — October 7, 2026. No model training is authorized.**

P2-39 failed the unchanged structured-plan development gate:

- complete plans: **0 / 18**
- schema-valid plans: **5 / 18**
- checks: **54 / 162**
- HTML schema-valid: **3 / 6**
- CSS schema-valid: **1 / 6**
- JavaScript schema-valid: **1 / 6**

The five schema-valid outputs still missed every targetRole, exact constraint set, and required hint set.

P2-40 inspects the exact P2-39 raw responses to determine whether the dominant failure after P2-38 is:

1. continued memorized-role collapse,
2. new P2-38 concept collapse,
3. residual JSON/schema instability,
4. or a different semantic substitution pattern.

## Fixed inputs

Task set:

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

Task-set SHA-256:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

P2-39 responses:

`training/artifacts/structured-plan/p2-39-step100/responses.jsonl`

Responses SHA-256:

`e9aca13ac5fed3286ad00294dc6fc87960ea66e7f22a9abd9cce375e0c92a3e6`

Contract:

`training/pretraining/p2-40-bridge-error-decomposition-contract.json`

## Command

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-bridge-diagnose `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-39-step100/responses.jsonl `
  --contract training/pretraining/p2-40-bridge-error-decomposition-contract.json `
  --report training/artifacts/structured-plan/p2-39-step100/bridge-error-diagnostic.json
```

Expected safety fields:

- `trainingPerformed: false`
- `researchOptimizerUpdates: 0`
- `finalHoldoutOpened: false`

Do not authorize more training until this diagnostic identifies the actual semantic substitutions and remaining structural failure modes.
