# P2-21 Semantic Role Generalization Candidate

## Status

**Pending owner review. Candidate-only.**

This candidate does not authorize tokenizer fitting, model initialization, or training.

Candidate:

`p2-21-semantic-role-generalization-candidate-v1`

SHA-256:

`8206798467f74bda9867c0179495b535eade3849ca1d8a5d3147de00f27e5584`

## Why P2-21 exists

P2-20/P2-20b separated semantic classification from symbolic lookup.

By cumulative step 500:

- supplied Level A semantic classification reached **48/48**;
- held-out Tier A reached **12/24**;
- supplied Level B symbolic lookup reached **27/48**;
- held-out Tier B ended at **3/24**, near the six-way chance baseline;
- supplied Level C reached **39/48**;
- held-out Tier C ended at **5/24**, also near chance.

The cleanest conclusion is that semantic role classification shows real transfer potential, while learned role-to-reference lookup does not.

P2-21 therefore removes reference lookup entirely.

The model's only legal outputs are:

```text
SELECTOR
OLD
NEW
```

## Candidate structure

The candidate contains **216 original records**:

- **144 training records**
- **72 evaluation-only records**
- three semantic bands
- **48 training + 24 evaluation records per band**

Every band is role-balanced.

Training per band:

- SELECTOR: 16
- OLD: 16
- NEW: 16

Evaluation per band:

- SELECTOR: 8
- OLD: 8
- NEW: 8

The simple three-way chance baseline is **33.3%**.

## Level A — clean semantic paraphrases

Level A tests direct unseen semantic wording without reference tables or repository literals.

Example:

```text
SEMANTIC QUESTION:
Which role identifies the source target rather than either value?

VALID LABELS: SELECTOR | OLD | NEW
Answer with exactly one label.
```

Expected:

```text
SELECTOR
```

Training and evaluation requests are disjoint.

The P2-21 prompt frame is intentionally different from P2-20's Level A framing.

## Level B — minimal semantic contrasts

Level B uses contrast triplets.

Each group presents the same semantic edit model three times while changing only which component is being queried.

Example conceptual triplet:

```text
A normalized edit contains:
- a target
- a before state
- an after state
```

Then the three records ask separately for:

```text
where the edit applies     -> SELECTOR
the state being left       -> OLD
the state being entered    -> NEW
```

This is designed to punish shallow prompt-template memorization.

Counts:

- 16 training contrast groups x 3 roles = 48 records
- 8 evaluation contrast groups x 3 roles = 24 records

Training and evaluation contexts are disjoint.

## Level C — repository-style semantic language

Level C asks the same role-classification question inside repository-edit language.

The prompts mention normal coding concepts such as:

- stylesheet rule
- CSS declaration
- HTML element or attribute
- JavaScript object/configuration field

But the model is **not** asked to reproduce selectors, values, identifiers, or exact repository bytes.

Example:

```text
Repository request:
update a stylesheet declaration on the affected rule
from its present state to the requested state.

QUESTION:
Which role identifies the CSS construct that owns the change?
```

Expected:

```text
SELECTOR
```

Counts:

- 16 training repository-context groups x 3 roles = 48 records
- 8 evaluation groups x 3 roles = 24 records

## What P2-21 intentionally removes

P2-21 contains no learned:

- R0-R5 lookup;
- symbol table resolution;
- selector copying;
- literal copying;
- arbitrary value reproduction;
- plan assembly.

Those operations should not obscure the semantic-role question.

The proposed architecture is:

```text
task language
   |
   v
Plex Base
   |
SELECTOR / OLD / NEW
   |
   v
Plex Code deterministic resolver
   |
exact repository bytes
```

## Anti-memorization controls

Pinned candidate properties:

- 216 unique requests;
- zero exact train/evaluation request overlap;
- zero train/evaluation contrast-context overlap;
- A/B/C role distributions perfectly balanced;
- no reference vocabulary;
- only three legal target labels;
- no final project holdout data;
- P2-14 and P2-01b remain development-only.

Prior-task prompt audit:

| Prior set | Exact overlap | Max word-Jaccard |
|---|---:|---:|
| P2-20 | 0 | 0.478261 |
| P2-19 | 0 | 0.152174 |
| P2-18 | 0 | 0.200000 |
| P2-17 | 0 | 0.184615 |
| P2-14 | 0 | 0.142857 |
| P2-01b | 0 | 0.133333 |

P2-20 has the highest expected overlap because both experiments discuss the same three semantic roles, but no P2-20 request is reused exactly.

## Evaluation interpretation

### Tier A strong, B/C weak

Basic paraphrases transfer, but contrast handling or repository-style semantics remain weak.

### Tier A/B strong, C weak

Canonical role semantics are learned, but repository-style wording is the remaining representation gap.

### Tier A/B/C strong

The 27.6M Plex Base has demonstrated useful semantic-role normalization across clean, contrastive, and repository-style language.

At that point, reference resolution should remain deterministic in Plex Code rather than being relearned by the model.

### All tiers weak after strong supplied fit

The current semantic curriculum does not generalize sufficiently, and the next move should be data/representation analysis rather than more identical optimization.

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
- all 72 P2-21 evaluation records excluded from tokenizer fitting and gradients;
- P2-14 and P2-01b excluded from gradients;
- final holdout closed.

## Gate

Do not increase model size yet.

P2-21 is intended to determine whether the one primitive that showed real promise in P2-20 can become reliable enough to use in the Plex Base -> Plex Code interface.
