# P2-21b Semantic Role Continuation Result

## Status

**Complete and closed.**

The exact P2-21 v1 step-100 checkpoint was continued through cumulative step 500 in four isolated +100-update CUDA increments.

No continuation beyond step 500 was authorized or performed.

The final holdout remained closed.

## Learning curve

| Step | Training /144 | Train A /48 | Train B /48 | Train C /48 | Tier A /24 | Tier B /24 | Tier C /24 | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 68 | 21 | 21 | 26 | 6 | 8 | 10 | 3.3556 | 0.3089 |
| 200 | 70 | 28 | 20 | 22 | 8 | 9 | 9 | 3.5949 | 0.1173 |
| 300 | 113 | 41 | 34 | 38 | 9 | 13 | 12 | 3.8441 | 0.0935 |
| 400 | 135 | 47 | 42 | 46 | 10 | **15** | **15** | 3.7209 | 0.0827 |
| 500 | **144** | **48** | **48** | **48** | 9 | **15** | **14** | 4.1354 | **0.0752** |

## Decisive findings

### Tier A — clean paraphrases

Tier A ended at **9/24**, close to the simple three-way chance expectation of 8/24.

Step-500 role breakdown:

- SELECTOR: **6/8**
- OLD: **1/8**
- NEW: **2/8**

This does not demonstrate reliable generalization to unconstrained paraphrases.

### Tier B — minimal semantic contrasts

Tier B ended at **15/24**.

Step-500 role breakdown:

- SELECTOR: **4/8**
- OLD: **5/8**
- NEW: **6/8**

This is materially above the 8/24 chance expectation and shows genuine transfer under a structured contrastive framing.

### Tier C — repository-style language

Tier C ended at **14/24**.

Step-500 role breakdown:

- SELECTOR: **5/8**
- OLD: **4/8**
- NEW: **5/8**

This also materially exceeds chance and is especially relevant to the intended Plex Code workflow.

## OLD-role diagnosis

The first run showed a severe OLD asymmetry:

- Tier A: 0/8
- Tier B: 0/8
- Tier C: 1/8

By step 500:

- Tier A: 1/8
- Tier B: 5/8
- Tier C: 4/8

OLD therefore is not a fundamental semantic blind spot. It catches up when the task supplies stronger semantic structure.

## Optimization behavior

Supplied fit reached **144/144**, while validation loss worsened from the step-100 minimum:

```text
validation:
3.3556 -> 3.5949 -> 3.8441 -> 3.7209 -> 4.1354

recent training loss:
0.3089 -> 0.1173 -> 0.0935 -> 0.0827 -> 0.0752
```

The step-400 checkpoint is the strongest operational point in the measured curve:

- training: 135/144
- Tier A: 10/24
- Tier B: 15/24
- Tier C: 15/24
- validation loss: 3.7209

Step 500 reaches perfect supplied fit but does not improve held-out transfer overall.

Additional optimization on the unchanged P2-21 representation is not justified.

## Architecture conclusion

P2-21/P2-21b demonstrates that the 27.6M Plex Base can learn semantic-role normalization above chance when the request is framed with enough structure.

The useful boundary is:

```text
arbitrary/free paraphrase
  -> weak

structured semantic contrast
  -> useful transfer

repository-style edit language
  -> useful transfer
```

Plex Code should therefore provide a stable semantic frame and continue to resolve exact repository bytes deterministically.

## Next experiment

P2-22 should test **Edit Intent Classification** with five canonical operations:

```text
REPLACE
INSERT
DELETE
RENAME
TOGGLE
```

The experiment should preserve the successful P2-21 pattern:

1. clean unseen wording;
2. hard minimal contrasts;
3. repository-style language.

No selector copying, literal copying, reference lookup, or code generation should be part of P2-22.

Do not increase model size yet.

The final holdout remains closed.
