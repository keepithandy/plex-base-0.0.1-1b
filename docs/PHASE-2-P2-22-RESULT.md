# P2-22 Edit Intent Classification — First Run Result

## Status

The owner-approved first P2-22 CUDA run completed at the 100-update ceiling from a fresh seed-1337 initialization.

The final holdout remained closed.

## Step-100 optimization state

- supplied complete-task passes: **64/150**
- validation loss: **7.0730092866 -> 3.3212734972**
- mean recent training loss: **0.4386107448**
- cumulative tokens processed: **151,505**
- tokenizer vocabulary size: **1,074**
- tokenizer SHA-256: `8f09812c2165cb928c1908f7a81ef59d5e8b6f3f8acb185e083bf1324ed23e5a`
- step: **100**
- interrupted: **false**

Validation loss fell sharply while the supplied edit-intent curriculum remained substantially underfit.

## Supplied training fit

| Level | Complete /50 |
|---|---:|
| A — clean paraphrases | **24** |
| B — minimal semantic contrasts | **22** |
| C — repository-style language | **18** |

All three supplied levels produced known intent labels and EOS on every row after training.

### Training intent totals

| Intent | Exact /30 |
|---|---:|
| REPLACE | **1** |
| INSERT | **8** |
| DELETE | **20** |
| RENAME | **21** |
| TOGGLE | **14** |

The strongest step-100 asymmetry is the near-collapse of `REPLACE`, with `INSERT` also materially weaker than DELETE/RENAME.

## Held-out transfer at step 100

| Tier | Exact /25 | REPLACE /5 | INSERT /5 | DELETE /5 | RENAME /5 | TOGGLE /5 |
|---|---:|---:|---:|---:|---:|---:|
| A | **6** | 0 | 0 | 3 | 2 | 1 |
| B | **2** | 0 | 0 | 0 | 1 | 1 |
| C | **7** | 0 | 0 | 3 | 4 | 0 |

The simple five-way chance expectation is **5/25**.

Because supplied fit is only 64/150, these held-out scores are not yet a final edit-intent transfer diagnosis.

## Development suites

P2-14 remains **0/12** complete tasks.

P2-01b remains **0/30** complete tasks.

After P2-22 training, P2-01b reaches EOS on all CSS, HTML and JavaScript development tasks.

## Interpretation

The first-run result isolates two useful facts:

1. the five-label output grammar is learned cleanly;
2. semantic intent selection is still underfit and strongly asymmetric, especially for `REPLACE` and `INSERT`.

The combination of:

- 64/150 supplied fit;
- validation loss falling from 7.07301 to 3.32127;
- recent training loss still at 0.43861;

supports a controlled continuation before changing the intent vocabulary or architecture.

## Next step

P2-22b is owner-approved to continue this exact step-100 checkpoint through cumulative steps 200, 300, 400 and 500 in isolated +100-update CUDA increments.

No automatic continuation beyond step 500 is authorized.
