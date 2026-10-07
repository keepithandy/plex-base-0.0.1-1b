# P2-35 — Serialization Stability Curriculum

## Status

**Preparation candidate ready for review — October 7, 2026. Model training is not authorized.**

P2-35 responds directly to the P2-34 finding that all 18 development responses learned the outer JSON boundary but corrupted the interior key/value grammar.

## Goal

Teach stable local JSON transitions before asking Plex Nano to compose a full semantic plan.

The curriculum is intentionally narrower than P2-32.

P2-32 concentrated heavily on complete plans.

P2-35 decomposes one complete plan into six linked syntax stages so the model repeatedly learns the punctuation and nesting transitions that failed in P2-34.

## Candidate

`training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl`

Canonical SHA-256:

`2abd94ee05da241848e06500b0df43fd0f70e19af75c199ef6d73181fa8a1bad`

The candidate contains:

- **144 records**
- **24 concept groups**
- **108 train**
- **36 validation**
- **18 train groups**
- **6 validation groups**

Per language:

| Language | Train | Validation |
|---|---:|---:|
| HTML | 36 | 12 |
| CSS | 36 | 12 |
| JavaScript | 36 | 12 |

## Six stages per group

Each concept group contains exactly one record at every stage.

### A — Flat JSON prefix

Target shape:

```json
{"schemaVersion":1,"language":"html","action":"modify"}
```

Purpose: stabilize quote/key/colon/value/comma transitions at the exact prefix already attempted by P2-34.

### B — Full top-level identity

Adds:

- `targetKind`
- `targetRole`

Purpose: keep top-level keys and values distinct before nesting begins.

### C — One constraint object

Target shape:

```json
{"kind":"attribute","key":"aria-label","value":"Account"}
```

Purpose: repeatedly train the exact `kind → key → value` grammar that was heavily corrupted in P2-34.

### D — Nested arrays

Target shape contains only:

- `constraints`
- `searchHints`

Purpose: stabilize object/array boundaries and comma transitions.

### E — Full explicit serialization

All semantic fields are supplied directly; Plex serializes the complete strict plan.

Purpose: bridge local grammar into the final schema without requiring semantic inference.

### F — Production request-to-plan

Uses the exact production structured-plan prompt template and requires the same full plan as level E.

Purpose: transfer stable grammar back into the real P2-31/P2-33 inference surface.

## Group consistency

For every group, the reviewer requires:

- A matches the full plan's schemaVersion/language/action
- B matches its full top-level identity
- C equals its first full-plan constraint
- D equals its complete constraints/searchHints arrays
- E and F are the same strict plan
- all six stages stay in the same train/validation split
- all six stages use the same language, action, target kind and target role

## Leakage controls

P2-35 excludes:

- all exact P2-31 development requests
- all P2-31 development target roles
- all P2-33 response strings from gradient data
- P2-01b development data
- the final project holdout

Validation groups remain separate from training groups.

After the first clean-checkout review caught repeated micro-prompts, levels A-E were concept-labeled rather than relaxing the uniqueness gate. The reviewed candidate now has **144 / 144 unique prompts**, so no exact prompt crosses the train/validation boundary.

## Frozen tokenizer

P2-35 keeps the existing frozen 16K tokenizer:

`2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

No tokenizer refit is allowed.

## Review command

Static review:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-serialization-review
```

Frozen-tokenizer/context preflight:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-serialization-review `
  --bundle-dir training/artifacts/structured-plan/p2-32-training-bundle
```

The command performs **zero optimizer updates**.

## Governance

Preparation contract:

`training/pretraining/p2-35-serialization-stability-preparation-contract.json`

Current state:

- data preparation authorized: **true**
- model training authorized: **false**
- automatic extension: **false**
- training command: **none**
- final holdout opened: **false**

A later P2-35 run requires separate weights-only staging, contract-enforcing training tooling, local preflight, and explicit owner authorization.
