# P2-17b Semantic Binding Continuation Result

## Status

P2-17b completed the approved continuation from cumulative step 100 through step 500 in four isolated +100-update CUDA increments.

No automatic continuation beyond step 500 occurred. P2-14 and P2-01b remained excluded from gradient training. The final holdout remained closed.

## Learning curve

| Step | Training complete /120 | Tier A full plan /20 | Tier B complete /20 | Tier C complete /20 | Validation loss |
|---:|---:|---:|---:|---:|---:|
| 100 | 1 | 0 | 0 | 0 | 2.574477 |
| 200 | 109 | 0 | 0 | 0 | 2.909547 |
| 300 | 114 | 0 | 0 | 0 | 3.109528 |
| 400 | 118 | 0 | 0 | 0 | 3.206422 |
| 500 | **120** | **0** | **0** | **0** | **3.369034** |

Mean recent training loss fell from 0.373338 at step 100 to 0.040778 at step 500 while held-out validation loss worsened after its step-100 minimum.

This is a decisive memorization/overfitting curve for the unchanged P2-17 representation.

## Field-level extraction

At step 500, supplied extraction fit reached 60/60 on every tracked field:

- selector: 60/60
- operation: 60/60
- property: 60/60
- old value: 60/60
- new value: 60/60
- full five-field plan: 60/60

Held-out Tier A remained:

- format valid: 19/20
- operation exact: 13/20
- property exact: 15/20
- old value exact: 6/20
- new value exact: 3/20
- selector exact: **0/20**
- full plan exact: **0/20**

The model therefore generalized categorical edit semantics substantially better than arbitrary literal binding.

## Explicit-plan application

Tier B supplied the correct edit plan directly, so natural-language extraction was removed from the task.

At step 500:

- syntax valid: 18/20
- selector exact: 0/20
- requested edit applied: 5/20
- unrelated declarations preserved: 4/20
- complete task: 0/20

The selector result is especially important: the model memorized 60/60 supplied application selectors while reproducing 0/20 held-out selectors exactly.

This shows the remaining bottleneck is not only request interpretation. It is exact contextual literal copying/reference binding.

## Composition

Tier C remained 0/20 complete. At step 500 only 1/20 outputs were syntax-valid, with 0/20 selector exact, 0/20 requested edits applied, and 0/20 preservation passes.

Because extraction and explicit-plan application both fail on unseen literals, Tier C composition is not yet a useful next target.

## Broader development

P2-14 remained 0/12 and P2-01b remained 0/30 at every scored continuation point.

P2-17/P2-17b therefore did not establish broader coding-task transfer.

## Conclusion

P2-17/P2-17b is closed as an optimization line.

Additional updates on the same representation are not justified.

The measured capability split is:

- **learned:** output format, EOS behavior, operation category, property category, supplied literal mappings;
- **not established:** exact copying of unseen selectors/values from current context, reference binding, full held-out edit application.

The next experiment is **P2-18 Literal Copy Primitive**. It removes CSS transformation and tests direct unseen copying, labeled copying, selected-field binding, and tiny multi-field plan assembly before any return to full CSS editing.

Model size remains unchanged at 27,566,080 parameters. The final holdout remains closed.
