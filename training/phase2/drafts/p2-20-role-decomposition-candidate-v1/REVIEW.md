# P2-20 Semantic Role + Reference Lookup Decomposition Candidate

## Status

**Pending owner review. This candidate does not authorize tokenizer fitting, checkpoint initialization, or model training.**

Candidate:

`p2-20-role-decomposition-candidate-v1`

SHA-256:

`8d7c54ceed8a0c90a437626e504e2ba39582f0ca5c57c243db5c564e2c02985d`

## Why P2-20 exists

P2-19/P2-19b established two useful facts:

1. stable symbolic references are a much better output representation than arbitrary repository literals;
2. semantic reference selection still does not generalize reliably.

By step 500, P2-19 training fit reached **143/144**. Tier D structured symbolic-copy performance reached **14/18**, but held-out Tier B explicit reference selection remained **6/18** and Tier C semantic reference selection fell to **2/18**.

That means P2-19 still mixed two separate operations:

```text
understand which semantic role is requested
+
look up the reference assigned to that role
```

P2-20 separates those operations directly.

## Candidate structure

The candidate contains **216 original records**:

- **144 training records**
- **72 evaluation-only records**
- three levels
- 48 training + 24 evaluation records per level

There are no repository selectors, CSS values, or arbitrary raw literals in P2-20.

The canonical role vocabulary is:

```text
SELECTOR
OLD
NEW
```

The symbolic reference vocabulary is:

```text
R0 R1 R2 R3 R4 R5
```

## Level A — semantic wording -> role label

Example:

```text
REQUEST: Which role represents the replacement value?

Choose exactly one role:
SELECTOR
OLD
NEW
Return the role label only.
```

Expected:

```text
NEW
```

This level contains **no reference lookup at all**.

It asks only:

> Can Plex generalize the semantics of selector/current-value/replacement-value language into a canonical role label?

Training and evaluation use disjoint semantic phrases.

### Balance

Training:

- SELECTOR: 16
- OLD: 16
- NEW: 16

Evaluation:

- SELECTOR: 8
- OLD: 8
- NEW: 8

The simple three-way chance baseline is **33.3%**.

## Level B — explicit role label + bindings -> reference

Example:

```text
BINDINGS:
SELECTOR=R0
OLD=R2
NEW=R4

ROLE: NEW
Return the reference assigned to ROLE.
```

Expected:

```text
R4
```

This removes semantic classification.

The requested role is already canonical. Plex only has to retrieve the reference assigned to that role.

This isolates:

> Can Plex generalize a tiny symbolic key/value lookup?

### Balance

Training target roles:

- SELECTOR: 16
- OLD: 16
- NEW: 16

Training target references:

- each of R0-R5: exactly 8

Evaluation target roles:

- SELECTOR: 8
- OLD: 8
- NEW: 8

Evaluation target references:

- each of R0-R5: exactly 4

The six-way reference chance baseline is **16.7%**.

Training and evaluation use disjoint binding-pattern families, so an evaluation request cannot be solved by exact prompt memorization.

## Level C — semantic wording + bindings -> reference

Example:

```text
BINDINGS:
SELECTOR=R0
OLD=R2
NEW=R4

REQUEST: Which role represents the replacement value?
Return the reference assigned to the requested role.
```

Expected:

```text
R4
```

This recombines the two primitives.

Success on A and B but failure on C would establish a **composition bottleneck**.

Failure on A with success on B would establish a **semantic classification bottleneck**.

Success on A with failure on B would establish a **symbolic lookup bottleneck**.

## Anti-memorization controls

Pinned candidate properties:

- training/evaluation semantic phrase overlap: **0**
- training/evaluation exact request overlap: **0**
- duplicate requests: **0**
- no raw repository literals
- no selectors
- no CSS values
- no split/tier marker in model-visible text
- candidate IDs are metadata only
- reference vocabulary is intentionally shared
- role vocabulary is intentionally shared
- B/C role frequencies are balanced
- B/C target-reference frequencies are balanced
- training and evaluation use disjoint binding-pattern families

The point is to test **role semantics and symbolic lookup**, not new token generation.

## Interpretation matrix

| Result | Interpretation |
|---|---|
| A strong, B strong, C strong | Role semantics + lookup + composition all transfer at 27.6M |
| A weak, B strong | Semantic role classification is the bottleneck |
| A strong, B weak | Symbolic key/value lookup is the bottleneck |
| A strong, B strong, C weak | Individual primitives work; composition is the bottleneck |
| A/B/C weak after strong supplied fit | Current model/data regime still does not generalize even these isolated primitives |

## Why this experiment matters for Plex Code

If B is strong, deterministic Plex Code can safely expose compact bindings such as:

```text
SELECTOR=R0
OLD=R2
NEW=R4
```

If A is also strong, Plex Base can classify repository-edit language into canonical roles.

If C is strong, Plex Base can directly turn semantic wording plus a deterministic symbol table into the right reference.

That would give Plex a clean model/tool boundary:

```text
Plex Code:
raw repository bytes -> stable references

Plex Base:
task semantics -> canonical role/reference decision

Plex Code:
reference -> exact repository bytes -> validated edit
```

## Proposed first run after approval

If the repository owner later approves this **exact SHA**, prepare one bounded first run with:

- fresh training-only tokenizer
- fresh seed-1337 initialization
- unchanged **27,566,080-parameter** architecture
- ordinary next-token complete-record loss
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- CUDA
- matched step-zero scoring
- maximum **100 updates / 10 minutes**
- no automatic extension
- all 72 P2-20 evaluation records excluded from tokenizer fitting and gradient training
- P2-14 and P2-01b excluded from training
- final holdout closed

## Decision gate

Do **not** increase model size yet.

The first question is no longer whether Plex can emit valid symbols. P2-19 already showed that it can.

P2-20 asks exactly which remaining primitive fails:

- semantic role classification;
- symbolic lookup;
- or composition.
