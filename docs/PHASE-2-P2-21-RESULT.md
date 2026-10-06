# P2-21 Semantic Role Generalization — First Run Result

## Status

The owner-approved first P2-21 CUDA run completed at the 100-update ceiling from a fresh seed-1337 initialization.

The final holdout remained closed.

## Step-100 optimization state

- supplied complete-task passes: **68/144**
- validation loss: **6.9496481235 -> 3.3556300860**
- mean recent training loss: **0.3088514040**
- cumulative tokens processed: **143,854**
- tokenizer vocabulary size: **890**
- tokenizer SHA-256: `28c513c3887d6eba0680e448443358ac04f812abbb4d2ab23c2d1bf004d0b4ef`
- step: **100**
- interrupted: **false**

Validation loss fell sharply while the supplied semantic curriculum remained substantially underfit.

## Supplied training fit

| Level | Complete /48 |
|---|---:|
| A — clean paraphrases | **21** |
| B — minimal semantic contrasts | **21** |
| C — repository-style language | **26** |

All three supplied levels produced known role labels and EOS on every row after training.

### Training role breakdown

| Level | SELECTOR /16 | OLD /16 | NEW /16 |
|---|---:|---:|---:|
| A | **6** | **0** | **15** |
| B | **6** | **2** | **13** |
| C | **13** | **2** | **11** |

The strongest step-100 asymmetry is the near-collapse of `OLD` relative to `NEW`.

## Held-out transfer at step 100

| Tier | Exact /24 | SELECTOR /8 | OLD /8 | NEW /8 |
|---|---:|---:|---:|---:|
| A | **6** | 1 | 0 | 5 |
| B | **8** | 1 | 0 | 7 |
| C | **10** | 3 | 1 | 6 |

The simple three-way chance expectation is **8/24**.

At step 100:

- Tier A is below that expectation;
- Tier B equals it;
- Tier C is modestly above it;
- all three tiers produce known labels on 24/24 rows and reach EOS on 24/24 rows.

Because supplied fit is only 68/144, these held-out results are not yet a final semantic-transfer diagnosis.

## Development suites

P2-14 remains **0/12** complete tasks.

P2-01b remains **0/30** complete tasks.

After P2-21 training, P2-01b reaches EOS on all CSS, HTML and JavaScript development tasks.

## Interpretation

The first-run result isolates two useful facts:

1. the three-label output grammar is learned cleanly;
2. semantic class selection is still underfit and highly asymmetric, especially for `OLD`.

The combination of:

- 68/144 supplied fit;
- validation loss falling from 6.94965 to 3.35563;
- recent training loss still at 0.30885;

supports a controlled continuation before changing the curriculum or architecture.

## Next step

P2-21b is owner-approved to continue this exact step-100 checkpoint through cumulative steps 200, 300, 400 and 500 in isolated +100-update CUDA increments.

No automatic continuation beyond step 500 is authorized.
