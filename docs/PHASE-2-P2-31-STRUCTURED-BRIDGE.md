# P2-31 — Structured Coding Bridge

## Status

**Evaluation complete — October 7, 2026. Gate failed: 0/18 complete plans and 0/18 schema-valid plans. Phase 3 is not authorized.**

P2-31 follows the P2-30 result that sharply improved task-text loss and eliminated truncation but still passed **0/30** complete P2-01b coding tasks. Rather than immediately extending the same fine-tuning run, P2-31 tests a narrower capability boundary:

> Can the fixed P2-30 step-100 Plex Nano checkpoint convert unseen repository-style requests into a bounded, machine-readable semantic edit plan that deterministic Plex Code can resolve and apply?

## Model boundary

### Plex Nano owns

- requested language
- semantic action: create / modify / remove
- target kind
- target role
- normalized semantic constraints
- bounded semantic search hints

### Plex Code owns

- repository enumeration
- exact file lookup
- exact symbol / selector / element resolution
- current-state inspection
- stale-state handling
- mutation
- validation
- diff generation

P2-31 therefore does **not** require Plex Nano to guess file paths, exact selectors, or exact repository symbols.

## Structured plan schema

A valid model response is one JSON object with exactly these fields:

```json
{
  "schemaVersion": 1,
  "language": "html",
  "action": "modify",
  "targetKind": "html-element",
  "targetRole": "primary-navigation",
  "constraints": [
    {
      "kind": "attribute",
      "key": "aria-label",
      "value": "Main"
    }
  ],
  "searchHints": [
    "primary navigation",
    "active page"
  ]
}
```

Rules are intentionally strict:

- no Markdown fences
- no extra fields
- duplicate JSON keys rejected
- target kind must match language
- 1–8 unique normalized constraints
- 1–5 unique semantic search hints
- search hints cannot be file paths
- malformed or truncated responses cannot pass

The evaluator scores parse/schema validity separately from semantic correctness.

## Development set

P2-31 introduces:

`training/phase2/evaluation/p2-31-plan-dev-v1.json`

It contains **18 development-only tasks**:

- HTML: 6
- CSS: 6
- JavaScript: 6

These are new repository-style requests, separate from P2-01b and separate from the sealed final project holdout.

The development task-set SHA-256 is:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

This identity is computed from UTF-8 text with line endings canonically normalized to LF, so the same checked-out JSON has the same authorized identity on Windows (CRLF) and Unix-like systems. `.gitattributes` also pins the P2-31 task set and contract to LF for stable repository bytes.

## Predeclared development gate

Before generation, the gate is fixed at:

- **12 / 18** complete semantic plans overall
- at least **3 / 6** complete plans in each language
- at least **15 / 18** schema-valid JSON plans

This is a development bridge gate, not the sealed Phase 2 final holdout.

## Fixed evaluation checkpoint

P2-31 uses the official P2-30 endpoint only:

- checkpoint step: **100**
- checkpoint SHA-256: `28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

The lower step-50 validation loss is recorded as descriptive P2-30 evidence but is not selected post hoc for P2-31.

## Machine-readable contract

`training/pretraining/p2-31-structured-bridge-contract.json`

The contract explicitly sets:

- `modelTrainingAuthorized: false`
- deterministic temperature 0
- seed 1337
- maximum 256 generated tokens
- final project holdout closed
- zero gradient updates

## Commands

After this implementation is merged and the local checkout is updated, generate plans from the fixed P2-30 endpoint:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-generate `
  --checkpoint training/artifacts/task-finetune/p2-30-first-run/checkpoints/step-0100.pt `
  --bundle-dir training/artifacts/task-finetune/p2-30-request-v3-16k `
  --output-dir structured-plan/p2-31-step100 `
  --device cuda
```

Then score them:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-evaluate `
  --responses training/artifacts/structured-plan/p2-31-step100/responses.jsonl `
  --report training/artifacts/structured-plan/p2-31-step100/evaluation.json
```

No training command is added by P2-31.

## Interpretation

A pass would show that the current small model is more useful as a semantic planner than as a direct code generator and would justify wiring that plan into deterministic Plex Code resolution.

A fail still provides actionable evidence: parse/schema failures indicate representation-format weakness; correct structure with wrong semantic fields indicates instruction-binding weakness; correct semantic plans with later repository-resolution failures would belong to Plex Code rather than Plex Nano.


## Result and closeout

The fixed P2-30 step-100 checkpoint generated all **18/18** responses without truncation, but every response failed strict JSON parsing. The evaluator recorded **0/18 complete plans**, **0/18 schema-valid plans**, and **36/162 checks passed**. HTML, CSS, and JavaScript each scored **0/6**.

See [P2-31 result](PHASE-2-P2-31-RESULT.md) and the machine-readable `training/pretraining/p2-31-structured-bridge-result.json`.

Because parsing failed before semantic fields could be scored, the result is classified as a representation-format failure rather than evidence that every semantic field is wrong. Repository resolution was not reached.

Next: [P2-32 Structured-Plan Representation Curriculum](PHASE-2-P2-32-STRUCTURED-PLAN-CURRICULUM.md).
