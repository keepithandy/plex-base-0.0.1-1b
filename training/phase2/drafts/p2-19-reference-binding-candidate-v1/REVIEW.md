# P2-19 Reference-Mediated Symbol Binding Candidate

## Status

**Pending owner review. This candidate does not authorize tokenizer fitting, checkpoint initialization, or model training.**

Candidate:

`p2-19-reference-binding-candidate-v1`

SHA-256:

`e96d6b8edd2a756a03d285f1081491232df7f79886a47d6ab02efcdb29211fa1`

## Why P2-19 exists

P2-18/P2-18b isolated literal copying from CSS editing. By cumulative step 500, supplied-task fit reached **129/144** while every held-out literal-copy tier remained at **0 complete passes**. The simplest held-out direct-copy tier stayed at:

- literal exact: **0/18**
- selector exact: **0/9**
- value exact: **0/9**

At the same time, validation loss rose after its step-100 minimum while recent training loss continued falling. This closes P2-18 as a representation failure rather than an optimization shortage.

P2-19 asks a different question:

> If arbitrary repository literals are represented by stable short references, can the current 27.6M Plex model generalize the semantic selection and composition of those references?

The experiment deliberately distinguishes **raw-literal lookup** from **reasoning over already-bound references**.

## Candidate structure

The candidate contains **216 original records**:

- **144 training records**
- **72 evaluation-only records**
- four levels
- 36 training + 18 evaluation records per level

The stable reference vocabulary is:

```text
R0 R1 R2 R3 R4 R5
```

Every row contains three distinct references assigned to:

- selector
- old value
- new value

All role-to-reference assignments are balanced across the six reference tokens.

Every raw selector and value in evaluation is held out from training.

### Level A — raw literal → reference lookup

Example:

```text
REFERENCE TABLE:
R0=.unit-4fc68f3e
R2=2.037ch
R4=8.056px

TARGET LITERAL:
.unit-4fc68f3e

Return only the reference name whose literal matches the target.
```

Expected:

```text
R0
```

This is the only level that requires Plex itself to match an arbitrary unseen raw literal against the reference table.

If Level A fails while later levels succeed, Plex Code should perform raw-literal prebinding deterministically.

### Level B — explicit field → reference

Example:

```text
REFERENCE TABLE:
R0=.unit-...
R2=2.037ch
R4=8.056px

BINDINGS:
selector_ref=R0
old_ref=R2
new_ref=R4

COPY FIELD: new_ref
Return the exact reference name only.
```

Expected:

```text
R4
```

This removes arbitrary-string reproduction entirely. Plex only selects a short reference from explicit bindings.

### Level C — semantic role → reference

Example:

```text
REFERENCE TABLE:
R0=.unit-...
R2=2.037ch
R4=8.056px

BINDINGS:
selector_ref=R0
old_ref=R2
new_ref=R4

REQUEST: Return the reference for the replacement value.
Return the exact reference name only.
```

Expected:

```text
R4
```

The semantic phrases are intentionally repeated across train and evaluation. P2-19 is **not** testing paraphrase generalization yet; it is testing whether unseen raw payloads stop breaking semantic reference selection.

### Level D — three-reference plan

Example:

```text
REFERENCE TABLE:
R0=.unit-...
R2=2.037ch
R4=8.056px

BINDINGS:
selector_ref=R0
old_ref=R2
new_ref=R4

Return exactly these three reference fields in this order:
selector_ref=...
old_ref=...
new_ref=...
```

Expected:

```text
selector_ref=R0
old_ref=R2
new_ref=R4
```

This is the smallest model-side representation of a future deterministic edit plan.

## Balance controls

For Levels A/B/C:

- training target fields: selector 12 / old 12 / new 12
- evaluation target fields: selector 6 / old 6 / new 6
- training target references: each of R0-R5 appears exactly 6 times
- evaluation target references: each of R0-R5 appears exactly 3 times

For every level and every role:

- training role-reference assignment: each reference appears 6 times
- evaluation role-reference assignment: each reference appears 3 times

This prevents a fixed-reference majority baseline.

## Anti-memorization controls

Pinned candidate properties:

- training/evaluation selector overlap: **0**
- training/evaluation old/new literal overlap: **0**
- reference vocabulary intentionally shared: **R0-R5**
- no split/tier marker appears in raw literals
- candidate IDs are not part of the model prompt
- raw selectors use neutral hash-like names
- values use short CSS-like numeric/unit literals

The shared reference vocabulary is deliberate. P2-19 tests transfer through a stable symbolic interface, not unseen reference-name generation.

## Interpretation matrix

| Result | Interpretation |
|---|---|
| A strong, B/C/D strong | Model can both resolve unseen literals and reason over references |
| A weak, B/C/D strong | **Best architectural signal:** deterministic tooling should pre-bind raw literals; model reasoning over references is viable |
| B strong, C weak | Explicit symbolic binding works; semantic role mapping remains weak |
| C strong, D weak | Single-reference selection works; multi-reference composition is the next bottleneck |
| B/C/D weak after strong training fit | Reference mediation alone does not solve contextual binding at this scale |

## Proposed first run after approval

If the repository owner later approves this **exact SHA**, prepare a bounded first run with:

- fresh training-only tokenizer
- fresh seed-1337 initialization
- unchanged **27,566,080-parameter** architecture
- ordinary next-token loss over complete records
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- CUDA
- matched step-zero scoring
- maximum **100 updates / 10 minutes**
- no automatic extension

All 72 P2-19 evaluation records must remain excluded from tokenizer fitting and gradient training.

P2-14 and P2-01b remain development-only.

The final project holdout remains closed.

## Decision gate

Do **not** increase model size yet.

The key P2-19 question is whether Levels B/C/D can transfer when the output payload is reduced to familiar symbolic references. If they do, the next engineering step is to make Plex Code create and resolve those references around the model deterministically.
