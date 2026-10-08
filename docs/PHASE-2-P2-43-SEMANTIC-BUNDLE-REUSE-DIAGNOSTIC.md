# P2-43 — Semantic Bundle Reuse Diagnostic

## Status

**Diagnostic prepared — October 8, 2026. No model training is authorized.**

P2-43 investigates why the fixed P2-41 step-100 model produces structurally valid plans while still binding unseen requests to the wrong `targetRole`, constraints, and search hints.

## Why P2-43 exists

P2-41 substantially improved structured-plan serialization.

The P2-42 response set shows that nearly every output is now shaped like one strict semantic plan rather than malformed JSON. The remaining problem is no longer primarily serialization.

Instead, the outputs repeatedly contain P2-41-shaped semantic values such as:

- `p241-pricing-table-target`
- `p241-card-layout-primary`
- `p241-score-average-target`
- `p241-unique-records-target`

Preliminary inspection of the 18 P2-42 rows found that **14 / 18 emitted target roles exactly match roles exposed in the P2-41 training split**. None of those 14 were validation-only roles.

That is strong motivation to measure training-bundle reuse directly rather than extend the same 108-record curriculum.

## Research question

When Plex receives an unseen P2-31 request, is it:

1. composing `targetRole`, constraints, and hints from evidence in the current request, or
2. retrieving/recombining semantic components that were exposed during P2-41 training?

P2-43 is designed to separate those behaviors.

## Diagnostic dimensions

For every strict P2-42 response, P2-43 measures:

- P2-31 field correctness
  - language
  - action
  - targetKind
  - targetRole
  - exact constraints
  - required hint coverage
- exact P2-41 **training** targetRole reuse
- exact P2-41 training constraint-set reuse
- exact P2-41 training search-hint reuse
- exact P2-41 training semantic-bundle reuse
- exact P2-41 training full-plan reuse
- validation-only role/bundle reuse
- repeated output-role collapse
- lexical overlap between the current P2-31 request and the P2-41 request that owned a reused bundle
- coverage of expected semantic tokens in the produced plan

The core semantic-bundle signature is:

```text
targetRole
+ exact constraint set
+ exact search-hint list
```

This lets P2-43 distinguish an exact remembered bundle from looser component recombination.

## Fixed inputs

P2-43 accepts only the unchanged P2-31 development set:

```text
training/phase2/evaluation/p2-31-plan-dev-v1.json
```

Task-set SHA-256:

```text
8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5
```

It compares against the frozen P2-41 candidate:

```text
training/phase2/drafts/p2-41-request-conditioned-plan-binding-v1.jsonl
```

Candidate SHA-256:

```text
20f309181adbd4c86ff0c5a7ad833792d754e3a9102000003922696a237b64ba
```

The P2-42 run manifest must prove that the responses came from:

- P2-41 step-100 checkpoint SHA `adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc`
- frozen tokenizer SHA `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- P2-41 bundle manifest SHA `a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a`
- 18 unchanged development tasks
- zero optimizer updates
- closed final holdout

The response SHA is read from and verified against the deterministic P2-42 run manifest. P2-43 does not require generated artifacts to be committed.

## Run the diagnostic

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-binding-diagnose `
  --responses training/artifacts/structured-plan/p2-42-step100/responses.jsonl `
  --p242-manifest training/artifacts/structured-plan/p2-42-step100/run-manifest.json `
  --report training/artifacts/structured-plan/p2-42-step100/p2-43-binding-diagnostic.json
```

The defaults already point to the frozen P2-31 task set, P2-41 candidate, and P2-43 contract.

## Interpretation boundary

P2-43 is deliberately descriptive.

It does **not** define a new pass/fail threshold after seeing P2-42 outputs. It records exact reuse rates and field behavior so the next curriculum decision can be based on measured evidence.

A high rate of wrong target roles or whole semantic bundles that exactly match P2-41 training examples would support the hypothesis that Plex is retrieving learned semantic templates rather than composing plans from current-request evidence.

A low exact-reuse rate with the same semantic failures would point instead toward a more distributed representation/generalization problem.

## Training decision

Do **not** continue P2-41 on the unchanged 108 records.

P2-41 already reached very low training loss while unseen `targetRole`, exact constraints, and hint binding remained poor. Additional optimization would risk strengthening the same template-retrieval behavior.

Any replacement curriculum or new optimizer run is a separate milestone after P2-43 is measured.

## Safety accounting

- model training authorized: **false**
- gradient updates: **0**
- response repair: **none**
- checkpoint selection: **none**
- retrospective step-25 promotion: **prohibited**
- final project holdout: **closed**
