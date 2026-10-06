# P2-19 Reference-Mediated Symbol Binding — First Run Result

## Status

The owner-approved first P2-19 CUDA run completed at the 100-update ceiling from a fresh seed-1337 initialization.

The final holdout remained closed.

## Step-100 optimization state

- supplied complete-task passes: **51/144**
- validation loss: **6.6869590580 -> 3.0484805703**
- mean recent training loss: **0.4593148714**
- cumulative tokens processed: **188,282**
- tokenizer vocabulary size: **667**
- tokenizer SHA-256: `03df6f1a6dce8637f968e498c1bf2522e630f6d04d633b03f8b4d74d1bddf983`
- step: **100**
- interrupted: **false**

Validation loss fell by roughly 54% while the supplied curriculum remained substantially underfit.

## Supplied training fit

| Level | Complete /36 |
|---|---:|
| A — raw literal -> reference | **18** |
| B — explicit field -> reference | **12** |
| C — semantic role -> reference | **17** |
| D — three-reference plan | **4** |

All four training levels reached **36/36 EOS**.

## Held-out transfer at step 100

### Tier A — raw literal -> reference

- complete/reference exact: **4/18**
- known-reference outputs: **18/18**
- wrong known reference: **14/18**
- unknown/malformed: **0/18**
- EOS: **18/18**

By target field:

- selector: **2/6**
- old: **1/6**
- new: **1/6**

### Tier B — explicit field -> reference

- complete/reference exact: **6/18**
- known-reference outputs: **18/18**
- wrong known reference: **12/18**
- unknown/malformed: **0/18**
- EOS: **18/18**

By target field:

- selector: **1/6**
- old: **2/6**
- new: **3/6**

This is the strongest step-100 held-out reference-selection tier.

### Tier C — semantic role -> reference

- complete/reference exact: **3/18**
- known-reference outputs: **18/18**
- wrong known reference: **15/18**
- unknown/malformed: **0/18**
- EOS: **18/18**

By target field:

- selector: **1/6**
- old: **1/6**
- new: **1/6**

The overall 3/18 result equals the simple six-way chance expectation and is not yet evidence of semantic binding generalization.

### Tier D — three-reference plan

- format valid: **17/18**
- full plan exact: **1/18**
- selector reference exact: **4/18**
- old reference exact: **7/18**
- new reference exact: **4/18**
- selector/old/new used known references on **17/18** rows each
- EOS: **18/18**

The model already transfers the symbolic plan structure strongly even while exact field selection remains weak.

## Development suites

P2-14 remained **0/12** complete tasks.

P2-01b remained **0/30** complete tasks.

P2-01b EOS reached **10/10** for CSS, **10/10** for HTML and **10/10** for JavaScript after training.

## Interpretation

P2-19 differs materially from P2-18.

P2-18 could increasingly fit supplied literal-copy mappings while held-out exact literal behavior remained zero. P2-19 shows nonzero held-out reference selection while supplied fit is still only 51/144.

This is not yet decisive proof that reference mediation solves binding. Tier C is still at chance and training is incomplete.

The combination of:

- strong validation-loss reduction;
- incomplete supplied fit;
- 18/18 valid known-reference outputs on Tiers A/B/C;
- nonzero held-out A/B/C/D exact behavior;

justifies a controlled optimization continuation before changing representation or model scale.

## Next step

P2-19b is owner-approved to continue this exact step-100 checkpoint through cumulative steps 200, 300, 400 and 500 in isolated +100-update increments.

No automatic continuation beyond 500 is authorized.
