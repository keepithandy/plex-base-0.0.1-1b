# P2-20 Semantic Role + Reference Lookup Decomposition — First Run Result

## Status

The owner-approved first P2-20 CUDA run completed at the 100-update ceiling from a fresh seed-1337 initialization.

The final holdout remained closed.

## Step-100 optimization state

- supplied complete-task passes: **45/144**
- validation loss: **6.5795933117 -> 3.2708642700**
- mean recent training loss: **0.1827663374**
- cumulative tokens processed: **120,293**
- tokenizer vocabulary size: **597**
- tokenizer SHA-256: `bd9f01238f6ecc82871a2a3a7aa1b7527f353fface791847040c1358b5c0da63`
- step: **100**
- interrupted: **false**

Validation loss fell by roughly 50% while the supplied curriculum remained substantially underfit.

## Supplied training fit

| Level | Complete /48 |
|---|---:|
| A — semantic wording -> role label | **30** |
| B — explicit role + bindings -> reference | **8** |
| C — semantic wording + bindings -> reference | **7** |

All three training levels reached EOS on every supplied row.

### Training Level A

- exact role: **30/48**
- known-role output: **48/48**
- wrong known role: **18/48**
- malformed/unknown role: **0/48**

By target role:

- SELECTOR: **15/16**
- OLD: **13/16**
- NEW: **2/16**

### Training Level B

- exact reference: **8/48**
- known-reference output: **48/48**
- wrong known reference: **40/48**

By target role:

- SELECTOR: **2/16**
- OLD: **2/16**
- NEW: **4/16**

### Training Level C

- exact reference: **7/48**
- known-reference output: **48/48**
- wrong known reference: **41/48**

By target role:

- SELECTOR: **1/16**
- OLD: **2/16**
- NEW: **4/16**

## Held-out transfer at step 100

### Tier A — semantic role classification

- exact role: **6/24**
- known-role output: **16/24**
- wrong known role: **10/24**
- malformed/unknown role: **8/24**
- EOS: **24/24**

By target role:

- SELECTOR: **0/8**
- OLD: **5/8**
- NEW: **1/8**

The simple three-way chance expectation is 8/24. Step-100 Tier A is not yet evidence of semantic-role generalization.

### Tier B — explicit symbolic lookup

- exact reference: **4/24**
- known-reference output: **24/24**
- wrong known reference: **20/24**
- malformed/unknown reference: **0/24**
- EOS: **24/24**

By target role:

- SELECTOR: **1/8**
- OLD: **2/8**
- NEW: **1/8**

The simple six-way chance expectation is 4/24, exactly matching the observed result.

Because supplied Level B is only 8/48, this is still an underfit optimization state rather than a decisive lookup failure.

### Tier C — semantic + lookup composition

- exact reference: **6/24**
- known-reference output: **24/24**
- wrong known reference: **18/24**
- malformed/unknown reference: **0/24**
- EOS: **24/24**

By target role:

- SELECTOR: **2/8**
- OLD: **2/8**
- NEW: **2/8**

The six-way chance expectation is 4/24. The observed 6/24 is not enough to establish compositional transfer while supplied Level C remains only 7/48.

## Development suites

P2-14 remained **0/12** complete tasks.

P2-01b remained **0/30** complete tasks.

P2-01b EOS reached **10/10** for CSS, **10/10** for HTML and **10/10** for JavaScript after training.

## Interpretation

P2-20 has successfully separated three primitives, but step 100 is too early for a final diagnosis.

The important step-100 result is:

- Level A is learning faster than B/C;
- B/C have learned the symbolic output vocabulary but not yet the lookup operation;
- validation loss is still falling strongly;
- recent training loss remains nontrivial;
- the total supplied fit is only 45/144.

A controlled continuation is therefore justified before concluding whether the remaining bottleneck is semantic classification, symbolic lookup, or composition.

## Next step

P2-20b is owner-approved to continue this exact step-100 checkpoint through cumulative steps 200, 300, 400 and 500 in isolated +100-update increments.

No automatic continuation beyond 500 is authorized.
