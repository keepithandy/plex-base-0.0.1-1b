# P2-42 — Structured Bridge Re-evaluation

## Status

Evaluation gate prepared. No model training is authorized.

P2-42 re-runs the unchanged P2-31 structured-plan development gate against the fixed P2-41 step-100 endpoint.

## Fixed endpoint

- checkpoint: `training/artifacts/structured-plan/p2-41-first-run/checkpoints/step-0100.pt`
- checkpoint SHA-256: `adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc`
- tokenizer bundle: `training/artifacts/structured-plan/p2-41-training-bundle`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- bundle manifest SHA-256: `a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a`

Checkpoint provenance is pinned to:

- stage kind: `plex-request-conditioned-plan-binding-stage-transition-v1`
- stage milestone: `P2-41`
- training settings kind: `p2-41-authorized-request-binding-training-v1`

## Unchanged development gate

P2-42 uses the original P2-31 development set and original gate:

- tasks: **18**
- HTML / CSS / JavaScript: **6 / 6 / 6**
- minimum complete passes: **12 / 18**
- minimum per language: **3 / 6**
- minimum schema-valid responses: **15 / 18**
- temperature: **0**
- seed: **1337**
- max new tokens: **256**

P2-39 remains the comparison baseline:

- complete plans: **0 / 18**
- schema-valid: **5 / 18**
- checks passed: **54 / 162**
- targetRole correct among schema-valid: **0 / 5**
- exact constraints: **0 / 5**
- hint coverage: **0 / 5**

## Generate P2-42 responses

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --checkpoint training/artifacts/structured-plan/p2-41-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/structured-plan/p2-41-training-bundle `
  --contract training/pretraining/p2-42-structured-bridge-contract.json `
  --output-dir structured-plan/p2-42-step100 `
  --device cuda
```

## Evaluate

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --task-set training/phase2/evaluation/p2-31-plan-dev-v1.json `
  --responses training/artifacts/structured-plan/p2-42-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-42-step100/evaluation.json
```

P2-42 performs no optimizer updates, does not inspect the final project holdout, and does not authorize any P2-41 continuation.
