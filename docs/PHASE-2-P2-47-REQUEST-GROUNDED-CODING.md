# P2-47 — Request-Grounded Coding Representation

## Status

**Candidate preparation implemented. No model training is authorized.**

## Purpose

P2-46 showed that Plex learned to recombine familiar semantic components, but the current request still did not reliably control which components were selected.

P2-47 changes the representation so the model must learn a much more direct relationship:

```text
natural coding request
        ↓
exact request evidence
        ↓
concrete coding intent
```

This milestone is about the **27M coding model's understanding**. It does not add file discovery, repository navigation, or application-agent behavior.

## Representation

P2-47 uses:

```text
plex-request-grounded-change-v1
```

Example:

```json
{
  "schemaVersion": 1,
  "language": "css",
  "action": "modify",
  "targetEvidence": "profile card",
  "bindings": [
    {
      "evidence": "use display grid",
      "kind": "declaration",
      "key": "display",
      "value": "grid"
    },
    {
      "evidence": "use a 16px gap",
      "kind": "declaration",
      "key": "gap",
      "value": "16px"
    }
  ]
}
```

The important difference from P2-44 is that every semantic output is attached directly to evidence copied from the request.

### Removed from the primary target

P2-47 does **not** train:

- `targetRole`
- `searchHints`
- milestone-prefixed labels
- arbitrary semantic bundle names
- repository lookup concepts

Those fields were useful diagnostics, but P2-46 showed they could become attractors that the model recombined without obeying the current request.

## Candidate design

The deterministic candidate contains:

- **108 records**
- **72 train**
- **36 validation**
- **36 per language**
- HTML / CSS / JavaScript
- **36 three-record contrast groups**

Contrast families:

1. **target-binding** — same coding behavior, different requested target
2. **requirement-binding** — same target, different coding requirement
3. **action-binding** — create / modify / remove wording
4. **near-neighbor** — very similar requests where one evidence phrase changes the intended coding behavior

## Transfer design

Validation intentionally reuses familiar atoms while holding out combinations.

Required properties:

- every validation target is already seen in training
- every validation coding-intent triple is already seen in training
- create / modify / remove are all seen in training
- validation uses different natural request forms
- **0** train/validation exact request overlap
- **0** train/validation exact solution overlap
- **0** train/validation exact non-empty binding-set overlap
- **0** exact P2-31 development request overlap

That directly tests the P2-46 problem:

> Can familiar coding knowledge be selected because the current request asks for it?

## Frozen candidate identity

The deterministic generator is pinned to:

- candidate ID: `p2-47-request-grounded-coding-v1`
- SHA-256: `6e39259cc8fc1646fb7a16d2056706312f8736d330f94a642690aaf9d1c1489a`
- bytes: **81,032**
- generator: `p2-47-request-grounded-coding-generator-v1`

Any generator drift fails closed.

## Generate candidate

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-coding-generate
```

This creates:

```text
training/phase2/drafts/p2-47-request-grounded-coding-v1.jsonl
training/phase2/drafts/p2-47-request-grounded-coding-v1.review.json
```

No weights are changed.

## Review candidate

Run:

```powershell
uv run --project training --no-sync python -m plex_training.cli request-grounded-coding-review `
  --bundle-dir training/artifacts/structured-plan/p2-44-training-bundle `
  --report training/artifacts/structured-plan/p2-47-candidate-review.json
```

The review checks:

- exact candidate SHA and byte count
- request evidence is actually present in each request
- representation validity
- language balance
- contrast-family balance
- train/validation combination holdout
- P2-31 exact-request exclusion
- frozen tokenizer identity
- tokenizer roundtrip
- 512-token context fit

## Evaluation plan

P2-47 has two distinct evaluation roles.

### Candidate validation

Before training, validate:

- strict representation structure
- exact request evidence
- exact action
- exact target evidence
- exact coding-intent kind/key/value
- combination holdouts
- tokenizer/context fit

### Post-training transfer

P2-49 will still run the unchanged P2-31 development bridge for historical comparison.

That bridge is now explicitly a **regression/transfer comparison**, not the product definition of Plex.

The product direction remains:

```text
coding request + supplied code/file context
                ↓
             Plex Nano
                ↓
         correct code change
```

## Decision boundary

P2-47 authorizes **candidate generation and review only**.

It does not authorize:

- a training bundle
- checkpoint staging
- optimizer creation
- gradient updates
- P2-48
- final-holdout access

P2-48 begins only after the exact P2-47 candidate and tokenizer review are recorded.
