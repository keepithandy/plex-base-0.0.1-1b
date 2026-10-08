# P2-46 — Semantic Transfer Failure Diagnostic

## Status

**Diagnostic implementation prepared. No model training is authorized.**

## Purpose

Explain why P2-44 improved strongly on its own validation distribution while P2-45 still failed the unchanged bridge.

The question is:

> What representation or binding failure prevents the 27M Plex Nano model from transferring request understanding to independently worded coding tasks?

## Frozen evidence

P2-44 endpoint:

- checkpoint step: **100**
- checkpoint SHA-256: `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- validation loss: **2.172380618146948**

P2-45:

- responses SHA-256: `ca1e8c8abb8dc419ef2fd2d2c3834964e5baad448b3dd439678decadbf1919a9`
- complete passes: **0 / 18**
- schema-valid: **12 / 18**
- checks passed: **78 / 162**
- targetRole: **0 / 18**
- exact constraints: **0 / 18**
- required hint coverage: **0 / 18**

## Diagnostic questions

P2-46 should measure:

1. What target roles did P2-45 actually emit?
2. Are those roles copied from P2-44 training examples, recombined from familiar atoms, or novel?
3. Which P2-44 constraint atoms appear in failed P2-45 responses?
4. Are search hints grounded in the request but mismatched to the evaluator, or are they unrelated?
5. Which six outputs became schema-invalid, and why?
6. Why did action accuracy fall to **6 / 18**?
7. Which tasks improved, stayed unchanged, or regressed from P2-43 to P2-45?
8. How similar is each P2-45 request/output pair to its nearest P2-44 training example?

## Rules

- No optimizer creation.
- No gradient updates.
- No checkpoint selection.
- No new curriculum until the diagnostic is complete.
- No final-holdout access.
- Do not alter the P2-31 development task set or thresholds.
- Preserve P2-43, P2-44, and P2-45 evidence exactly.

## Completion condition

P2-46 is complete when it produces a concrete failure taxonomy and a narrow recommendation for P2-47.

P2-47 must target **transferable coding understanding**, not simply lower loss on another isolated representation.


## Implemented diagnostic

P2-46 is implemented by:

```text
training/src/plex_training/structured_plan_transfer_diagnostic.py
```

CLI command:

```text
plan-transfer-diagnose
```

It verifies the exact frozen identities before analysis:

- unchanged P2-31 development task set
- P2-42 responses SHA `3a935e10fb8d7deab057c3776446f1151ec3f0945b195c5350f93b6a54af30ee`
- P2-45 responses SHA `ca1e8c8abb8dc419ef2fd2d2c3834964e5baad448b3dd439678decadbf1919a9`
- P2-42 checkpoint SHA `adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc`
- P2-44 checkpoint SHA `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- exact P2-44 curriculum SHA `fc56eca2186e2b7f643af9fbec514c1d5d34248eba2ac380b9f93c482b945c30`

The report contains:

- P2-42 → P2-45 strict field deltas
- per-task improved / regressed / unchanged classification
- exact P2-44 train targetRole / constraint / hint / bundle / full-plan reuse
- P2-44 validation-only reuse
- request-grounding checks for target roles and hints
- whether emitted constraint triples were seen during P2-44 training
- nearest same-language P2-44 training request similarity
- exact schema-failure reason counts
- action correctness by language
- comparison against the P2-43 template-reuse baseline

Loose JSON inspection is diagnostic only. Invalid responses are never repaired or rescored as valid plans.

## Run P2-46

The normal command shape is:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-transfer-diagnose `
  --p242-responses training/artifacts/structured-plan/p2-42-step100/responses.jsonl `
  --p242-manifest training/artifacts/structured-plan/p2-42-step100/run-manifest.json `
  --p245-responses training/artifacts/structured-plan/p2-45-step100/responses.jsonl `
  --p245-manifest training/artifacts/structured-plan/p2-45-step100/run-manifest.json `
  --report training/artifacts/structured-plan/p2-46-semantic-transfer-diagnostic.json
```

For the already-generated October 8 P2-45 artifact that was created before the artifact-root path fix, use its actual nested path instead:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-transfer-diagnose `
  --p242-responses training/artifacts/structured-plan/p2-42-step100/responses.jsonl `
  --p242-manifest training/artifacts/structured-plan/p2-42-step100/run-manifest.json `
  --p245-responses training/artifacts/training/artifacts/structured-plan/p2-45-step100/responses.jsonl `
  --p245-manifest training/artifacts/training/artifacts/structured-plan/p2-45-step100/run-manifest.json `
  --report training/artifacts/structured-plan/p2-46-semantic-transfer-diagnostic.json
```

## Decision boundary

Running P2-46 does not authorize P2-47 data preparation or training.

The generated report must be reviewed first. P2-47 should then make the smallest representation change supported by the measured failure taxonomy.
