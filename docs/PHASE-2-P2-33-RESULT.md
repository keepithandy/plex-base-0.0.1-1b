# P2-33 — Structured Bridge Re-evaluation Result

## Status

**Gate failed — October 7, 2026.**

P2-33 re-ran the unchanged P2-31 structured-plan development set against the fixed P2-32 step-100 checkpoint after representation training.

The result did not improve the structured-plan gate.

## Result

| Metric | Result |
|---|---:|
| Complete plans | **0 / 18** |
| Schema-valid plans | **0 / 18** |
| Checks passed | **36 / 162** |
| Partial tasks | **18 / 18** |
| HTML | **0 / 6** |
| CSS | **0 / 6** |
| JavaScript | **0 / 6** |
| Gate | **FAIL** |

Every response was present and untruncated, but every response failed strict JSON parsing before semantic fields could be scored.

The response artifact SHA-256 was:

`ff7d199607030935b39b6b21a924958e43ac1583b9a02de170bab6ebcccf32d6`

The development task set remained:

`8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5`

No model training occurred during P2-33 and the final project holdout remained sealed.

## Interpretation

P2-32 materially improved held-out next-token loss on its own structured-plan validation split, but that improvement did **not** transfer into valid free-generated JSON on the untouched development requests.

The failure therefore remains at the output/representation boundary. P2-33 still does not establish whether the underlying semantic choices would have been correct, because the evaluator could not parse a plan object.

Do not authorize more optimizer updates from this result alone.

The next milestone is **P2-34 — Output-Boundary Diagnostic**, which inspects the raw P2-33 response strings without repairing, rescoring, or training.

Machine-readable result:

`training/pretraining/p2-33-structured-bridge-result.json`
