# P2-32 — Structured-Plan Representation Curriculum

## Status

**Preparation candidate ready for review — October 7, 2026. Model training is not authorized.**

P2-32 responds directly to the P2-31 failure mode. P2-31 generated all 18 responses without truncation, but **0/18** responses were valid JSON. Because the parser failed before semantic fields could be scored, the next experiment teaches the strict structured-plan representation itself before asking Plex Nano to cross the Phase-3 bridge again.

## Goal

Teach the fixed P2-30 endpoint to emit the `plex-structured-edit-plan-v1` contract reliably while preserving the existing architecture boundary:

- **Plex Nano:** language, semantic action, target kind, target role, normalized constraints, bounded search hints
- **Plex Code:** exact repository lookup, current-state resolution, mutation, validation, and diff generation

P2-32 does not train exact file paths, selectors, symbols, or repository bytes.

## Base checkpoint

Preparation is pinned to the official P2-30 endpoint:

- step: **100**
- checkpoint SHA-256: `28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`

The descriptive P2-30 step-50 validation minimum remains ineligible for post-hoc checkpoint selection.

## Frozen tokenizer

P2-32 reuses the frozen 16K tokenizer:

- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- source bundle manifest SHA-256: `7753b1518b737e7f6b8e0b64f4f829b027ed3aad5b33a7613b3715481448eec5`
- tokenizer refit: **forbidden**

## Candidate curriculum

`training/phase2/drafts/p2-32-structured-plan-candidate-v1.jsonl`

Canonical SHA-256:

`608cf988b96e8578fa2c7948a12e298c4ed25c640098a2bf3710f3b3cc6802d3`

The candidate contains **96 records** arranged into **24 semantic concept groups**.

### Split

| | Train | Validation |
|---|---:|---:|
| HTML | 24 | 8 |
| CSS | 24 | 8 |
| JavaScript | 24 | 8 |
| **Total** | **72** | **24** |

All four records belonging to one semantic concept stay in the same split.

There are:

- **18 train groups**
- **6 validation groups**

No semantic concept group crosses train/validation.

## Curriculum levels

Every concept group contains exactly four variants:

### Level A — serialization

One record gives the plan fields explicitly and asks Plex to serialize exactly one strict JSON object.

Purpose: isolate format learning.

### Level B — field binding

One record supplies semantic fields in prose and requires Plex to bind them into the strict schema.

Purpose: combine labels with the output representation.

### Level C — semantic composition

Two distinct natural-language repository-style requests require the full semantic plan.

Purpose: test request → structured plan composition without exact repository lookup.

Per group:

- A: **1**
- B: **1**
- C: **2**

## Leakage controls

P2-32 is separate from P2-31 development evidence.

The reviewer requires:

- zero exact P2-31 request overlap
- zero P2-31 target-role overlap
- whole concept groups contained in one split
- all 96 candidate solutions parse under the strict P2-31 plan schema
- final project holdout remains closed
- P2-01b and P2-31 development examples remain excluded from gradients

Validation concepts use target roles not present in the P2-31 development set.

## Preparation review command

Static review can run directly after pulling the repository:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-curriculum-review
```

For the required local frozen-tokenizer roundtrip/context preflight:

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-curriculum-review `
  --bundle-dir training/artifacts/task-finetune/p2-30-request-v3-16k
```

The tokenizer preflight verifies:

- exact frozen tokenizer identity
- exact roundtrip for every rendered training record
- maximum complete-record context <= the 512-token model context plus EOS accounting
- train/validation token counts

It performs **zero optimizer updates**.

## Machine-readable preparation contract

`training/pretraining/p2-32-structured-plan-preparation-contract.json`

Current status:

- data preparation: allowed
- model training: **not authorized**
- automatic extension: **false**
- training command: **none**

The contract contains a draft-only proposed first-run envelope for later review, but those settings do not authorize execution.

## Exit gate before any P2-32 training

Before a first optimizer update can be authorized:

1. candidate and review hashes must match
2. static curriculum review must pass
3. local frozen-tokenizer roundtrip/context preflight must pass
4. a weights-only P2-32 stage transition must be implemented and tested
5. a dedicated contract-enforcing P2-32 training command must be implemented and tested
6. a separate bounded training authorization must be explicitly reviewed and committed

Until then, P2-32 is preparation only.
