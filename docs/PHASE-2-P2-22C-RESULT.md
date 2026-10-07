# P2-22c Presence Transition Diagnostic Result

## Status

**Complete and closed.**

P2-22c evaluated the unchanged P2-22b cumulative step-500 checkpoint on 45 new explicit state-transition records. No tokenizer fitting, initialization, gradient training, optimizer updates, or model-weight changes occurred. The final project holdout remained closed.

## Overall result

| Metric | Result |
|---|---:|
| Exact classification | **12 / 45** |
| Chance baseline | **15 / 45** |
| Tier A | **5 / 15** |
| Tier B | **5 / 15** |
| Tier C | **2 / 15** |
| Presence polarity exact | **3 / 30** |
| Direct INSERT<->DELETE reversals | **3** |

The diagnostic performed below its three-way chance baseline overall.

## Per-intent result

| Intent | Exact /15 |
|---|---:|
| INSERT | **2** |
| DELETE | **1** |
| REPLACE | **9** |

Explicit before/after state structure did not recover INSERT or DELETE.

## Confusion pattern

INSERT and DELETE produced the same aggregate prediction distribution:

| Predicted | INSERT rows | DELETE rows |
|---|---:|---:|
| REPLACE | 2 | 2 |
| INSERT | 2 | 2 |
| DELETE | 1 | 1 |
| RENAME | 9 | 9 |
| TOGGLE | 0 | 0 |
| OTHER | 1 | 1 |

The dominant attractor was **RENAME**, not a simple INSERT/DELETE reversal.

Tier C was the strongest negative signal: INSERT and DELETE were both **0/5**, with four of five examples for each predicted as RENAME.

## Conclusion

The P2-22b INSERT defect is not solved by exposing explicit:

```text
ABSENT -> PRESENT
PRESENT -> ABSENT
```

state transitions.

The current 27.6M Plex Base does not reliably preserve direction across existence-state transitions. In contrast, REPLACE remains substantially easier, indicating that in-place mutation semantics are more accessible than relational presence-direction reasoning.

P2-22c therefore does **not** validate before/after state reasoning as a model-side intermediate representation.

## Architectural consequence

Keep Plex Base focused on flat semantic normalization primitives that have shown transfer.

Move exact relational/state logic into deterministic Plex Code unless a later dedicated experiment proves otherwise.

## Next milestone

P2-23 should test **Target-Kind Classification** as another flat semantic primitive.

No P2-22d is planned.
