# P2-37 — Bridge Error Decomposition

## Status

**Read-only diagnostic prepared — October 7, 2026. No model training is authorized.**

P2-36 improved structured-plan serialization but still failed the development gate:

- complete plans: **0 / 18**
- schema-valid plans: **5 / 18**
- checks: **56 / 162**
- HTML schema-valid: **0 / 6**
- CSS schema-valid: **2 / 6**
- JavaScript schema-valid: **3 / 6**

The five schema-valid plans all got language, action, and targetKind correct while missing targetRole, exact constraints, and hint coverage.

P2-37 inspects the raw response strings to determine exactly what Plex is substituting for those semantic fields and to separate the remaining 13 failures into JSON syntax versus strict-schema failures.

## Fixed inputs

Task set:

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

Task-set SHA-256:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

P2-36 responses:

`training/artifacts/structured-plan/p2-36-step100/responses.jsonl`

Responses SHA-256:

`7492c8d0158381b979b319a4d3a880c0bbba7d7b4227e300c4c68ff357ae7fbd`

Contract:

`training/pretraining/p2-37-bridge-error-decomposition-contract.json`

## Diagnostic output

For invalid plans, the tool reports:

- `invalid-json`
- `parseable-json-invalid-plan-schema`
- exact strict-parser error
- bounded raw-output preview

For schema-valid plans, it reports the actual and expected:

- language
- action
- targetKind
- targetRole
- constraints
- searchHints / expected hint keywords

It also reproduces the evaluator's field checks without changing the original P2-36 score.

## Command

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-bridge-diagnose `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-36-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-36-step100/bridge-error-diagnostic.json
```

Expected safety fields:

- `trainingPerformed: false`
- `researchOptimizerUpdates: 0`
- `finalHoldoutOpened: false`

No P2-37 training decision should be made until this diagnostic identifies the dominant semantic substitutions and the remaining serialization errors.
