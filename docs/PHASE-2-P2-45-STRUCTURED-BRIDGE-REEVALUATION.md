# P2-45 — Structured Bridge Re-evaluation

## Status

**Complete. Gate failed. No continuation is authorized.**

P2-45 re-runs the unchanged P2-31 structured-plan development gate on the fixed P2-44 step-100 endpoint.

## Frozen endpoint

- P2-44 checkpoint: `training/artifacts/structured-plan/p2-44-first-run/checkpoints/step-0100.pt`
- checkpoint SHA-256: `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- checkpoint step: **100**
- stage kind: `plex-evidence-first-semantic-composition-stage-transition-v1`
- training settings kind: `p2-44-authorized-evidence-composition-training-v1`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- tokenizer bundle manifest SHA-256: `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`

## Why this gate matters

P2-43 showed that P2-41 had largely solved serialization but still failed semantic composition:

- **17 / 18** schema-valid
- **0 / 18** semantic passes
- targetRole correct: **0**
- exact constraints: **0**
- required hint coverage: **0**
- **14** responses reused a P2-41 training targetRole
- **8** reused an exact P2-41 semantic bundle
- **7** reproduced an exact P2-41 training full plan

P2-44 changed the representation to evidence-first composition and then produced a healthier bounded training curve:

- baseline validation loss: **3.3981438778542183**
- step 25: **2.2757347886626786**
- step 50: **2.2634602172954663**
- step 75: **2.2411495543814994**
- step 100: **2.172380618146948**

The fixed step-100 endpoint is therefore the endpoint under evaluation.

## Unchanged P2-31 gate

P2-45 does not change the evaluation task set, prompt, schema, inference settings, or thresholds.

- tasks: **18**
- HTML / CSS / JavaScript: **6 / 6 / 6**
- temperature: **0**
- seed: **1337**
- max new tokens: **256**
- minimum complete passes: **12 / 18**
- minimum per language: **3 / 6**
- minimum schema-valid: **15 / 18**

The final project holdout stays closed.

## Commands

Generate deterministic P2-45 responses:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --checkpoint training/artifacts/structured-plan/p2-44-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-44-training-bundle `
  --contract training/pretraining/p2-45-structured-bridge-contract.json `
  --output-dir structured-plan/p2-45-step100 `
  --device cuda
```


> `--output-dir` is interpreted under the default artifact root `training/artifacts`.
> Use `structured-plan/p2-45-step100` rather than repeating the artifact-root prefix.

Then evaluate:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-45-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-45-step100/evaluation.json
```

P2-45 performs **0** optimizer updates and authorizes no continuation.


## Result

P2-45 generated all **18** deterministic development responses from the fixed P2-44 step-100 endpoint.

Response SHA-256:

`ca1e8c8abb8dc419ef2fd2d2c3834964e5baad448b3dd439678decadbf1919a9`

Evaluation:

| Metric | Result |
|---|---:|
| Complete semantic passes | **0 / 18** |
| Schema-valid | **12 / 18** |
| Checks passed | **78 / 162** |
| HTML complete passes | **0 / 6** |
| CSS complete passes | **0 / 6** |
| JavaScript complete passes | **0 / 6** |
| Gate passed | **No** |

Field-level result:

| Field | Correct |
|---|---:|
| response present | **18 / 18** |
| not truncated | **18 / 18** |
| schema valid | **12 / 18** |
| language | **12 / 18** |
| action | **6 / 18** |
| target kind | **12 / 18** |
| target role | **0 / 18** |
| exact constraints | **0 / 18** |
| required hint coverage | **0 / 18** |

Six responses were schema-invalid. The observed failure modes included duplicate constraints, malformed constraint objects, and a target-kind/language mismatch.

### Interpretation

P2-44 produced a strong internal validation curve, but the unchanged P2-31 bridge shows that the learned representation still does not transfer reliably to independently worded coding requests.

This is now classified as a **semantic transfer failure**.

Do not continue the unchanged P2-44 training curriculum. The next milestone is **P2-46 — Semantic Transfer Failure Diagnostic**, which is diagnostic-only and performs no training.
