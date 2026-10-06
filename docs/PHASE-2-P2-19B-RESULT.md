# P2-19b Reference Binding Continuation Result

## Status

**Complete and closed.**

The exact P2-19 v1 step-100 checkpoint was continued through cumulative step 500 in four isolated +100-update CUDA increments.

No training beyond step 500 was authorized or performed.

The final holdout remained closed.

## Learning curve

| Step | Training /144 | A /36 | B /36 | C /36 | D /36 | Tier A /18 | Tier B /18 | Tier C /18 | Tier D full /18 | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 51 | 18 | 12 | 17 | 4 | 4 | 6 | 3 | 1 | 3.0485 | 0.4593 |
| 200 | 116 | 28 | 26 | 27 | 35 | 6 | 5 | 2 | 12 | 3.2406 | 0.2613 |
| 300 | 129 | 36 | 29 | 29 | 35 | 8 | 4 | 4 | 11 | 3.5489 | 0.1274 |
| 400 | 137 | 32 | 35 | 34 | 36 | 8 | 6 | 2 | 11 | 3.9792 | 0.0776 |
| 500 | 143 | 36 | 36 | 35 | 36 | 6 | 6 | 2 | 14 | 4.2772 | 0.0665 |

## Decisive findings

### Reference vocabulary and output structure transfer

Across Tiers A, B and C, Plex consistently learned to emit known symbolic references rather than malformed arbitrary text.

At step 500:

- Tier A known-reference output: **18/18**
- Tier B known-reference output: **18/18**
- Tier C known-reference output: **18/18**

Tier D remained structurally strong:

- format valid: **17/18**
- full plan exact: **14/18**
- selector-reference exact: **14/18**
- old-reference exact: **14/18**
- new-reference exact: **14/18**

This is materially better than P2-18 raw-literal reproduction.

### Semantic reference selection does not generalize reliably

Training Level C reached **35/36** by step 500.

Held-out Tier C ended at only **2/18**:

- selector: **0/6**
- old: **0/6**
- new: **2/6**

The model therefore learned the supplied semantic-reference mappings without demonstrating reliable held-out semantic role selection.

### Explicit role-to-reference selection also remains weak

Training Level B reached **36/36**.

Held-out Tier B remained:

```text
step 100: 6/18
step 200: 5/18
step 300: 4/18
step 400: 6/18
step 500: 6/18
```

The symbolic output space is learned, but held-out binding remains unreliable.

### Tier D is a structured symbolic-copy success

Tier D rose from **1/18** full-plan exact at step 100 to **14/18** at step 500.

However, Tier D is supplied explicit bindings and asked to reproduce the complete symbolic plan. It demonstrates that Plex can preserve and emit a pre-bound symbolic plan; it does **not** by itself establish semantic inference of those bindings.

## Optimization behavior

Validation loss worsened after step 100 while recent training loss continued falling:

```text
validation:
3.0485 -> 3.2406 -> 3.5489 -> 3.9792 -> 4.2772

recent training loss:
0.4593 -> 0.2613 -> 0.1274 -> 0.0776 -> 0.0665
```

Supplied fit reached **143/144** while held-out B/C remained weak.

Additional optimization on the unchanged P2-19 representation is therefore **not justified**.

## Conclusion

P2-19/P2-19b is closed.

Reference mediation solved an important representation problem:

> Plex is much better at manipulating stable symbolic references than reproducing arbitrary repository literals.

But the experiment still conflated two primitives:

1. understanding which semantic role is requested;
2. retrieving the reference assigned to that role.

P2-20 decomposes those primitives directly.

## Next experiment

P2-20 removes raw literals entirely and tests:

- **A:** semantic wording -> role label;
- **B:** explicit role label + binding table -> reference;
- **C:** semantic wording + binding table -> reference.

That decomposition will identify whether the remaining failure is semantic classification, symbolic lookup, or their composition.
