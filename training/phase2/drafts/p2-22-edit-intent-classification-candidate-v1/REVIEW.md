# P2-22 Edit Intent Classification Candidate

## Status

**Pending owner review. Candidate-only.**

This candidate does not authorize tokenizer fitting, model initialization, or training.

Candidate:

`p2-22-edit-intent-classification-candidate-v1`

SHA-256:

`592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0`

## Why P2-22 exists

P2-21/P2-21b demonstrated that the 27.6M Plex Base can learn semantic-role normalization above chance when the request is framed with enough structure.

The strongest held-out P2-21b results were:

- Tier B minimal contrasts: **15/24**
- Tier C repository-style language: **14/24**
- Tier A clean paraphrases: **9/24**

P2-22 tests the next primitive required by a semantic edit planner:

```text
request language
  ->
canonical edit intent
```

The model's only legal outputs are:

```text
REPLACE
INSERT
DELETE
RENAME
TOGGLE
```

## Canonical intent definitions

### REPLACE

Change an existing value or state while preserving the target's presence and identity.

### INSERT

Add a new construct or entry that was not previously present.

### DELETE

Remove an existing construct or entry entirely.

### RENAME

Change an identifier or name while preserving the underlying logical entity.

### TOGGLE

Flip a binary or two-state setting to its opposite state.

These definitions intentionally separate `TOGGLE` from arbitrary replacement and `RENAME` from changing stored content.

## Candidate structure

The candidate contains **225 original records**:

- **150 training records**
- **75 evaluation-only records**
- three semantic bands
- **50 training + 25 evaluation records per band**

Every band is intent-balanced.

Training per band:

- REPLACE: 10
- INSERT: 10
- DELETE: 10
- RENAME: 10
- TOGGLE: 10

Evaluation per band:

- REPLACE: 5
- INSERT: 5
- DELETE: 5
- RENAME: 5
- TOGGLE: 5

The simple five-way chance baseline is **20%**, or **5/25** per tier.

## Level A — clean unseen paraphrases

Level A tests direct edit-intent wording without repository identifiers or exact source values.

Example:

```text
SEMANTIC QUESTION:
The edit keeps the same source slot and changes only what occupies it.
Which intent applies?

VALID LABELS:
REPLACE | INSERT | DELETE | RENAME | TOGGLE
```

Expected:

```text
REPLACE
```

Training and evaluation requests are disjoint.

## Level B — minimal semantic contrasts

Level B uses five-way contrast groups.

Each group defines the operation space once, then asks separately about:

```text
existing value changes        -> REPLACE
missing item becomes present  -> INSERT
present item becomes absent   -> DELETE
entity keeps identity/new name -> RENAME
binary state flips            -> TOGGLE
```

Counts:

- 10 training contrast groups × 5 intents = 50 records
- 5 evaluation contrast groups × 5 intents = 25 records

Training and evaluation contexts are disjoint.

## Level C — repository-style language

Level C places the same classification problem inside CSS, HTML, JavaScript and general repository-edit language.

Examples include requests to:

- update an existing declaration or option;
- add a missing attribute or configuration entry;
- remove an existing field;
- rename a source symbol or configuration key;
- toggle a boolean feature flag.

The model is **not** asked to reproduce:

- selectors;
- identifiers;
- values;
- source code;
- patches;
- reference IDs.

It emits only the canonical intent label.

Counts:

- 10 training repository contexts × 5 intents = 50 records
- 5 evaluation repository contexts × 5 intents = 25 records

## Anti-memorization controls

Pinned candidate properties:

- 225 unique requests;
- zero exact train/evaluation request overlap;
- zero train/evaluation contrast-context overlap;
- zero same-intent train/evaluation near-duplicates at word-Jaccard >= 0.65;
- A/B/C intent distributions perfectly balanced;
- no reference vocabulary requirement;
- no raw repository-literal reproduction;
- no code generation;
- no final project holdout data;
- P2-14 and P2-01b remain development-only.

Prior-task prompt audit:

| Prior set | Exact overlap | Max word-Jaccard |
|---|---:|---:|
| P2-21 | 0 | 0.468750 |
| P2-20 | 0 | 0.289474 |
| P2-19 | 0 | 0.127660 |
| P2-18 | 0 | 0.162162 |
| P2-17 | 0 | 0.157143 |
| P2-14 | 0 | 0.153846 |
| P2-01b | 0 | 0.142857 |

## Evaluation interpretation

### Tier A weak, B/C strong

This would replicate the P2-21 pattern: structured and repository-style semantic framing works better than unconstrained paraphrase transfer.

### A/B/C strong

The 27.6M Plex Base has demonstrated a second useful semantic primitive: canonical edit-intent normalization across clean, contrastive and repository-style language.

### One intent remains weak

Inspect per-intent results before changing the architecture. A persistent class-specific failure could indicate ambiguous definitions or a representation conflict, especially:

- REPLACE vs TOGGLE;
- REPLACE vs RENAME;
- INSERT vs DELETE.

### All tiers weak after strong supplied fit

The five-way operation representation does not generalize sufficiently. The next move should be data/representation analysis rather than more identical optimization.

## Proposed first run after owner approval

If the repository owner later approves this exact candidate SHA, the proposed first-run policy is:

- fresh training-only tokenizer;
- fresh seed-1337 initialization;
- unchanged **27,566,080-parameter** architecture;
- ordinary next-token complete-record loss;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- matched step-zero scoring;
- maximum **100 updates / 10 minutes**;
- no automatic extension;
- all 75 P2-22 evaluation records excluded from tokenizer fitting and gradients;
- P2-14 and P2-01b excluded from gradients;
- final holdout closed.

## Gate

Do not increase model size yet.

P2-22 should determine whether the semantic operation primitive can join P2-21's semantic-role primitive in the future Plex Base -> Plex Code interface.
