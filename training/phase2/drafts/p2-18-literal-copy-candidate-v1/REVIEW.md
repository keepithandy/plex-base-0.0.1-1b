# P2-18 Literal Copy Primitive Candidate

## Status

**Pending owner review. No tokenizer fitting, checkpoint initialization, or model training is authorized by this candidate work.**

Candidate:

`p2-18-literal-copy-candidate-v1`

SHA-256:

`9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6`

## Why P2-18 exists

P2-17/P2-17b reached **120/120 complete supplied-task passes** by cumulative step 500, but held-out literal binding remained weak:

- Tier A selector exact: **0/20**
- Tier A new-value exact: **3/20**
- Tier A old-value exact: **6/20**
- Tier A operation exact: **13/20**
- Tier A property exact: **15/20**
- Tier A full plan: **0/20**
- Tier B complete: **0/20**
- Tier C complete: **0/20**

Validation loss was best at step 100 and then worsened as training fit approached 120/120. Additional optimization on P2-17 is therefore not justified.

P2-18 removes almost all CSS semantics and asks a narrower question:

> Can the current 27.6M Plex model copy and bind exact **unseen literals from context**?

If this primitive does not transfer, returning directly to full CSS transformation would confound semantic reasoning with a lower-level literal-copy failure.

## Candidate structure

The candidate contains **216 original records**:

- 144 training records;
- 72 evaluation-only records.

Each of four levels contributes:

- 36 training records;
- 18 evaluation records.

Training and evaluation use completely disjoint selectors and source/target values.

### Level A — direct copy

Input contains one literal:

```text
COPY EXACTLY:
.unit-711fa889
Return the copied text only.
```

Expected:

```text
.unit-711fa889
```

Training: 18 selector literals + 18 value literals.

Evaluation: 9 selector literals + 9 value literals.

### Level B — labeled copy

Example:

```text
INPUT:
selector=.unit-711fa889

Return exactly one line in the form selector=<copied literal>.
```

Expected:

```text
selector=.unit-711fa889
```

This checks whether adding a small structural label breaks copying.

### Level C — selected-field binding

Example:

```text
INPUT:
selector=.unit-711fa889
old=12.375px
new=37.125px

COPY FIELD: new
Return the exact literal value only.
```

Expected:

```text
37.125px
```

The target field is balanced across selector/old/new:

- training: 12/12/12;
- evaluation: 6/6/6.

This is the first true binding test: multiple literals are present, but Plex must return the literal associated with the requested field.

### Level D — tiny structured plan

Example:

```text
INPUT:
selector=.unit-711fa889
old=12.375px
new=37.125px

Return exactly these three fields in this order, copying every literal exactly:
selector=...
old=...
new=...
```

Expected:

```text
selector=.unit-711fa889
old=12.375px
new=37.125px
```

This tests multi-literal binding without requiring CSS parsing or edit application.

## Anti-memorization controls

The candidate pins:

- train/evaluation selector overlap: **0**
- train/evaluation old/new literal overlap: **0**
- exact duplicate requests: **0**
- exact duplicate IDs: **0**

Selectors use a neutral hash-derived grammar and contain no `train`, `eval`, or tier marker.

Values remain CSS-like numeric/unit literals while being disjoint across the split.

## Scoring intent

### Tier A /18

- exact output;
- literal exact;
- selector/value breakdown;
- EOS.

### Tier B /18

- exact output;
- label exact;
- literal exact;
- selector/value breakdown;
- EOS.

### Tier C /18

- exact selected literal;
- target-field breakdown for selector/old/new;
- wrong-field retrieval rate;
- EOS.

### Tier D /18

- full three-field plan exact;
- format valid;
- selector exact;
- old exact;
- new exact;
- EOS.

## Proposed first run

If the owner later approves this exact candidate, the first run should keep the current model scale and optimizer family so the changed variable is the **literal-copy curriculum**:

- fresh training-only tokenizer;
- fresh seed-1337 initialization;
- unchanged 27,566,080-parameter architecture;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- matched step-zero evaluation;
- maximum 100 updates / 10 minutes;
- no automatic extension.

The P2-18 evaluation records must remain excluded from tokenizer fitting and gradient training. P2-14 and P2-01b remain development-only. The final holdout remains closed.

## Decision rule

P2-18 is a primitive gate.

- If Tier A/B unseen literal copying rises strongly, proceed to Level C/D binding and later reattach deterministic edit execution.
- If training fits but Tier A unseen copying remains near zero, stop adding CSS examples and evaluate architectural support for reference-mediated symbol handling.
- Do not increase the model toward 0.5B–1.5B merely to hide an unresolved copy/binding primitive.
