# P2-22b Edit Intent Continuation Result

## Status

**Complete and closed.**

P2-22b continued the exact P2-22 v1 step-100 checkpoint through cumulative step 500 and stopped at the authorized ceiling. The final holdout remained closed.

## Learning curve

| Step | Training /150 | Train A /50 | Train B /50 | Train C /50 | Tier A /25 | Tier B /25 | Tier C /25 | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 64 | 24 | 22 | 18 | 6 | 2 | 7 | 3.3213 | 0.4386 |
| 200 | 91 | 30 | 24 | 37 | 11 | 5 | 7 | 3.3905 | 0.1455 |
| 300 | 145 | 50 | 46 | 49 | 17 | 12 | 17 | 3.7242 | 0.0935 |
| 400 | 141 | 46 | 49 | 46 | 12 | 14 | 14 | 4.0683 | 0.0805 |
| 500 | **150** | **50** | **50** | **50** | **16** | **16** | **18** | 3.9323 | **0.0728** |

Five-way chance is 5/25 per held-out tier.

Step 500 is the best measured checkpoint by total held-out exact classification: **50/75**.

## Final held-out intent accuracy

Across all three evaluation tiers, each intent has 15 held-out examples.

| Intent | Correct /15 |
|---|---:|
| REPLACE | **12** |
| INSERT | **2** |
| DELETE | **10** |
| RENAME | **15** |
| TOGGLE | **11** |

RENAME generalized perfectly. REPLACE recovered strongly from its step-100 collapse.

INSERT remained the single class-specific defect despite perfect 150/150 supplied fit.

## INSERT confusion at step 500

The 15 held-out INSERT predictions were:

| Predicted label | Count |
|---|---:|
| DELETE | **6** |
| REPLACE | **3** |
| RENAME | **2** |
| TOGGLE | **2** |
| INSERT | **2** |

Tier A is especially diagnostic: all five clean INSERT paraphrases were classified as DELETE.

This supports the hypothesis that Plex has learned a general presence-changing concept but does not reliably preserve the transition direction:

```text
INSERT = ABSENT -> PRESENT
DELETE = PRESENT -> ABSENT
```

## Conclusion

P2-22/P2-22b demonstrated a strong edit-intent primitive:

- clean paraphrases: 16/25
- minimal contrasts: 16/25
- repository-style language: 18/25
- total held-out exact: 50/75

The five-way representation is viable, but INSERT has a specific presence-transition polarity generalization defect.

Additional identical optimization is not justified because supplied fit is already 150/150.

## Next experiment

P2-22c should be evaluation-only.

It should use the existing step-500 checkpoint and ask whether explicit before/after state structure resolves the defect:

```text
ABSENT -> PRESENT = INSERT
PRESENT -> ABSENT = DELETE
PRESENT -> PRESENT with changed content = REPLACE
```

No tokenizer fitting, initialization, gradient training, or model-weight modification is authorized for P2-22c.
