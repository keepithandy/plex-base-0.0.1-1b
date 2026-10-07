# P2-37 — Bridge Error Decomposition Result

## Status

**Diagnostic complete — October 7, 2026.**

P2-37 inspected the exact P2-36 response artifact without repairing, rescoring, or training.

## Result

The 18 development responses decomposed into:

- **7** invalid JSON
- **6** parseable JSON objects that violated the strict plan schema
- **5** schema-valid plans with semantic mismatches

Schema-valid coverage:

- HTML: **0 / 6**
- CSS: **2 / 6**
- JavaScript: **3 / 6**

Across the five schema-valid plans:

- language: **5 / 5 correct**
- action: **5 / 5 correct**
- targetKind: **5 / 5 correct**
- targetRole: **0 / 5 correct**
- exact constraints: **0 / 5**
- required hint coverage: **0 / 5**

## Concept-collapse evidence

Every schema-valid plan reused a targetRole from the P2-35 serialization curriculum:

- `modal-state`: **2**
- `keyed-dedupe`: **2**
- `range-normalizer`: **1**

This is strong evidence that Plex is completing familiar P2-35 semantic templates instead of deriving the target identity from the new request.

Representative examples:

- focus treatment request → `modal-state`
- unique-by-id request → `keyed-dedupe`
- USD formatting request → `range-normalizer`
- sum-by-property request → `keyed-dedupe`

## Remaining structural instability

The 13 non-schema-valid outputs still show representation failures, including:

- constraint arrays emitted under `targetRole`
- a constraint array emitted under `targetKind`
- missing required top-level fields
- nested/repeated `searchHints` fragments
- malformed local key/value transitions

So P2-35 did improve serialization, but the next problem is not solved by repeating the same six-stage curriculum.

## Diagnosis

Primary failure:

**request-conditioned semantic binding / memorized concept collapse**

Secondary failure:

**residual JSON and strict-schema instability**

## Decision

Do not extend P2-35 training.

Proceed to **P2-38 — Semantic-Binding Contrast Curriculum**.

Machine-readable result:

`training/pretraining/p2-37-bridge-error-decomposition-result.json`
