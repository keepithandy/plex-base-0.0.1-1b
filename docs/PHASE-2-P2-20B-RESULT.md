# P2-20b Role Decomposition Continuation Result

## Status

**Complete and closed.**

The exact P2-20 v1 step-100 checkpoint was continued through cumulative step 500 in four isolated +100-update CUDA increments.

No continuation beyond step 500 was authorized or performed.

The final holdout remained closed.

## Learning curve

| Step | Training /144 | Train A /48 | Train B /48 | Train C /48 | Tier A /24 | Tier B /24 | Tier C /24 | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 45 | 30 | 8 | 7 | 6 | 4 | 6 | 3.2709 | 0.1828 |
| 200 | 61 | 34 | 12 | 15 | 2 | 1 | 0 | 3.5760 | 0.1272 |
| 300 | 84 | 44 | 17 | 23 | 8 | 4 | 4 | 3.8266 | 0.1170 |
| 400 | 104 | 48 | 25 | 31 | 8 | 5 | 5 | 4.1647 | 0.1062 |
| 500 | **114** | **48** | **27** | **39** | **12** | **3** | **5** | **3.9009** | **0.0964** |

## Decisive findings

### Level A — semantic role classification

Supplied Level A reached **48/48** by step 400 and remained there at step 500.

Held-out Tier A improved to **12/24** by step 500.

Step-500 target-role breakdown:

- SELECTOR: **3/8**
- OLD: **3/8**
- NEW: **6/8**

The simple three-way chance expectation is 8/24. Tier A therefore shows the first meaningful sign that canonical semantic-role classification can generalize, although transfer remains uneven and is not yet reliable enough for integration.

### Level B — explicit symbolic lookup

Supplied Level B improved from **8/48** at step 100 to **27/48** at step 500.

Held-out Tier B stayed near the six-way chance expectation throughout:

```text
step 100: 4/24
step 200: 1/24
step 300: 4/24
step 400: 5/24
step 500: 3/24
```

At step 500 all **24/24** outputs were known references, but only **3/24** were correct.

The model therefore learns the symbolic output vocabulary without demonstrating a transferable role-to-reference lookup operation.

### Level C — semantic + lookup composition

Supplied Level C improved from **7/48** to **39/48**.

Held-out Tier C remained near chance:

```text
step 100: 6/24
step 200: 0/24
step 300: 4/24
step 400: 5/24
step 500: 5/24
```

Because Level B lookup itself does not transfer, Tier C cannot be interpreted as an independent composition failure. The cleaner diagnosis is that symbolic lookup remains the limiting primitive.

## Optimization behavior

Validation loss worsened after the step-100 minimum while recent training loss continued to fall:

```text
validation:
3.2709 -> 3.5760 -> 3.8266 -> 4.1647 -> 3.9009

recent training loss:
0.1828 -> 0.1272 -> 0.1170 -> 0.1062 -> 0.0964
```

This is the familiar Phase-2 overfitting pattern: supplied fit improves while held-out symbolic lookup remains flat near chance.

Additional optimization on the unchanged P2-20 representation is not justified.

## Architecture conclusion

P2-20/P2-20b supports a cleaner boundary between Plex Base and Plex Code.

Plex Base should learn semantic normalization such as:

```text
"the requested replacement value"
        ->
NEW
```

Plex Code should perform exact symbolic lookup and repository-byte resolution deterministically.

The model should not spend capacity learning a key/value operation that host tooling can perform perfectly.

## Next experiment

P2-21 removes reference lookup entirely and focuses on semantic-role generalization:

```text
language
  ->
SELECTOR / OLD / NEW
```

Three held-out tiers should cover:

1. clean unseen paraphrases;
2. hard minimal contrasts;
3. repository-style edit language.

Do not increase model size yet.

The final holdout remains closed.
