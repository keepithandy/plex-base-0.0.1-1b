# P2-34 — Structured-Plan Output-Boundary Diagnostic

## Status

**Read-only diagnostic prepared — October 7, 2026. No model training is authorized.**

P2-31 and P2-33 both produced the same gate result:

- **0 / 18** complete plans
- **0 / 18** schema-valid plans
- **36 / 162** checks
- all 18 responses present
- all 18 responses untruncated

P2-32 reduced its structured-plan validation loss substantially, but that did not change the free-generation gate.

P2-34 therefore pauses training and inspects the raw P2-33 outputs.

## Purpose

The diagnostic answers questions such as:

- does the response ever begin with `{`?
- does it contain an opening/closing JSON object at all?
- does `"schemaVersion"` appear?
- is there Markdown fencing?
- is a valid plan embedded inside extra prose?
- is there a parseable JSON object with the wrong schema?
- is the model producing malformed JSON-like text?
- is it producing no JSON object at all?
- are many tasks collapsing to the same repeated output/prefix?

The command does **not** repair responses and does **not** rescore them.

## Fixed inputs

Task set:

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

Task-set SHA-256:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

P2-33 responses:

`training/artifacts/structured-plan/p2-33-step100/responses.jsonl`

Responses SHA-256:

`ff7d199607030935b39b6b21a924958e43ac1583b9a02de170bab6ebcccf32d6`

Contract:

`training/pretraining/p2-34-output-boundary-contract.json`

## Classifications

Each response is assigned one diagnostic class:

- `strict-valid-plan`
- `markdown-fenced`
- `extra-text-around-valid-plan`
- `embedded-json-wrong-schema`
- `malformed-json-candidate`
- `no-json-object-start`

These classifications are diagnostic only. They do not alter the original P2-33 score.

## Command

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-diagnose `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-33-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-33-step100/output-boundary-diagnostic.json
```

Expected safety fields:

- `trainingPerformed: false`
- `researchOptimizerUpdates: 0`
- `finalHoldoutOpened: false`

The next training/data decision must be based on this diagnostic rather than another blind continuation.
