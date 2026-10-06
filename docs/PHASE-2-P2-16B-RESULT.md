# P2-16b Optimization Continuation Result

## Status

P2-16b completed the owner-approved learning curve from cumulative step 100 through step 500 in four isolated +100-update CUDA continuations.

No automatic continuation beyond step 500 occurred. P2-14 and P2-01b remained excluded from gradient training. The final holdout remained closed.

## Learning curve

| Step | Training complete /120 | Training syntax-valid /120 | Tier A /24 | Tier B /12 | Tier C /12 | Tier D /12 | Validation loss |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 3 | 45 | 0 | 0 | 0 | 0 | 3.387112 |
| 200 | 98 | 118 | 0 | 0 | 0 | 0 | 3.945704 |
| 300 | 105 | 112 | 0 | 0 | 0 | 0 | 4.084458 |
| 400 | 116 | 119 | 0 | 0 | 0 | 0 | 4.657675 |
| 500 | 114 | 120 | 0 | 0 | 0 | 0 | 4.620283 |

P2-14 remained 0/12 and P2-01b remained 0/30 at every scored continuation point.

Mean recent training loss fell from 0.328863 at step 100 to approximately 0.0454 at step 500 while held-out validation loss rose after its step-100 minimum. This is clear evidence that further optimization on the unchanged P2-16 curriculum primarily increased fitting/memorization rather than semantic edit generalization.

## Structural transfer

Although complete held-out edits remained zero, CSS syntax validity improved strongly on the easier tiers.

At step 500:

- Tier A syntax-valid: 24/24
- Tier B syntax-valid: 12/12
- Tier C syntax-valid: 6/12
- Tier D syntax-valid: 3/12

The model therefore learned bounded CSS-shaped output substantially better than it learned the exact requested transformation.

## Step-500 failure pattern

Tier A was the most diagnostic because all 24 outputs were syntactically valid while all 24 complete edits failed.

Tier A failure counts included:

- requested edit not applied: 24/24
- unexpected selector or declaration: 24/24
- correct property, wrong value: 17/24
- preservation failure: 10/24
- malformed CSS: 0/24

Manual inspection showed the model often emitted a semantically related **training selector** and **training value** instead of copying the literal selector/value from the current task.

Examples included:

- a held-out border-radius request answered with a remembered `.p216-train-border-radius-09` rule;
- a held-out border-radius add request preserving unrelated declarations correctly but substituting a remembered training selector and `2px` value;
- held-out opacity requests answered with remembered `.p216-train-opacity-*` selectors;
- a width request answered with a remembered padding example.

This indicates a binding/retrieval failure: the model recognizes the semantic neighborhood and output grammar but does not reliably bind the current selector and literal values into the edit.

## Conclusion

P2-16/P2-16b is closed as an optimization-only line.

Additional updates on the same raw request-to-final-CSS curriculum are not justified by these results.

The next experiment should change the **semantic representation**, not model size or training duration. P2-17 therefore separates:

1. source+request -> canonical edit-plan extraction;
2. source+explicit edit plan -> deterministic CSS application;
3. held-out composition of extraction + application with no direct chain examples in training.

The final holdout remains closed.
