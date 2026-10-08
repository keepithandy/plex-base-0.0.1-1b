# P2-49 — Unchanged Bridge Re-evaluation

## Status

**Complete. Gate failed. No training or checkpoint reselection is authorized.**

## Purpose

P2-49 asks one narrow question:

> Did the P2-47 request-grounded representation improve transfer to independently worded coding requests?

It re-runs the original P2-31 structured-plan development gate without changing the task set, prompt, schema, inference settings, or thresholds.

## Endpoint under evaluation

P2-48 completed all 100 authorized optimizer updates.

The internal request-grounded validation curve was:

| Step | Mean loss |
|---:|---:|
| 0 | 6.505710401033101 |
| 25 | **2.7775440717998303** |
| 50 | 2.913108511974937 |
| 75 | 3.1200873851776123 |
| 100 | 3.233508963333933 |

Step 25 was the best measured internal validation point, but the predeclared checkpoint policy forbids retrospective selection.

P2-49 therefore evaluates the fixed endpoint only:

- checkpoint: `training/artifacts/request-grounded/p2-48-first-run/checkpoints/step-0100.pt`
- step: **100**
- SHA-256: `fd86d11375e547f05b2fab7a36188ca30a7ecd0b0f38198de62bcddbfba489b7`
- stage kind: `plex-request-grounded-coding-stage-transition-v1`
- training settings kind: `p2-48-authorized-request-grounded-training-v1`

## Unchanged P2-31 gate

- tasks: **18**
- HTML / CSS / JavaScript: **6 / 6 / 6**
- temperature: **0**
- seed: **1337**
- max new tokens: **256**
- minimum complete passes: **12 / 18**
- minimum per language: **3 / 6**
- minimum schema-valid: **15 / 18**

Comparison baseline from P2-45:

- complete semantic passes: **0 / 18**
- schema-valid: **12 / 18**
- checks passed: **78 / 162**
- language correct: **12 / 18**
- action correct: **6 / 18**
- target kind correct: **12 / 18**
- target role / exact constraints / hint coverage: **0 / 18**

The final project holdout remains closed.

## Generate P2-49 responses

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --checkpoint training/artifacts/request-grounded/p2-48-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/request-grounded/p2-48-training-bundle `
  --contract training/pretraining/p2-49-structured-bridge-contract.json `
  --output-dir structured-plan/p2-49-step100 `
  --device cuda
```

Expected properties:

- **18** responses
- checkpoint SHA matches the fixed P2-48 endpoint
- training performed: **false**
- optimizer updates: **0**
- final holdout opened: **false**

## Evaluate

Then run:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-49-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-49-step100/evaluation.json
```

## Decision rule

Use the original P2-31 gate unchanged.

Do not:

- lower thresholds,
- switch to step 25 after seeing P2-49,
- continue P2-48 training,
- open the final holdout.

P2-50 closes Phase 2 after this evaluation whether the gate passes or fails.


## Result

P2-49 evaluated the fixed P2-48 step-100 endpoint against the unchanged P2-31 development gate.

Response SHA-256:

`b9ba75d9c058d26299c22950b0cfd0e9248011f5663886b96d96006ccda1cb06`

Evaluation:

| Metric | Result |
|---|---:|
| Complete semantic passes | **0 / 18** |
| Schema-valid | **0 / 18** |
| Checks passed | **36 / 162** |
| HTML complete passes | **0 / 6** |
| CSS complete passes | **0 / 6** |
| JavaScript complete passes | **0 / 6** |
| Gate passed | **No** |

Field-level result:

| Field | Correct |
|---|---:|
| response present | **18 / 18** |
| not truncated | **18 / 18** |
| schema valid | **0 / 18** |
| language | **0 / 18** |
| action | **0 / 18** |
| target kind | **0 / 18** |
| target role | **0 / 18** |
| exact constraints | **0 / 18** |
| required hint coverage | **0 / 18** |

Observed schema failure shape:

- **15 / 18** responses reached the structured-plan parser but used a field set that did not match the P2-31 schema.
- **3 / 18** responses were not valid JSON.

Compared with P2-45:

| Metric | P2-45 | P2-49 | Delta |
|---|---:|---:|---:|
| complete passes | 0 | 0 | 0 |
| schema-valid | 12 | 0 | **-12** |
| checks passed | 78 | 36 | **-42** |
| language | 12 | 0 | **-12** |
| action | 6 | 0 | **-6** |
| target kind | 12 | 0 | **-12** |
| target role | 0 | 0 | 0 |
| exact constraints | 0 | 0 | 0 |
| hint coverage | 0 | 0 | 0 |

### Interpretation

P2-48 strongly learned the new request-grounded representation on its own held-out distribution, but that learning did not transfer back into the legacy P2-31 structured-plan output contract.

This result does **not** justify selecting the better-looking P2-48 step-25 checkpoint after the fact. Step 100 remains the predeclared endpoint.

P2-49 therefore fails the unchanged legacy transfer gate.

No additional Phase 2 training is authorized. P2-50 closes Phase 2 and carries the unresolved transfer limitation into Phase 3.
