# P2-18 Literal Copy Primitive — First Run Result

## Status

The owner-approved first P2-18 CUDA run completed at the 100-update ceiling from the fresh v3 preparation.

The run remained substantially underfit:

- supplied complete-task passes: **4/144**
- Level A direct copy: **2/36**
- Level B labeled copy: **1/36**
- Level C selected-field binding: **1/36**
- Level D three-field plan: **0/36**

The final holdout remained closed.

## Optimization state

- validation loss: **6.8281600873 -> 2.8766768773**
- mean recent training loss: **0.5493557507**
- tokens processed: **132,286**
- step: **100**
- interrupted: **false**

The roughly 58% validation-loss reduction while supplied-task fit remained only 4/144 indicates the trajectory is still underfit rather than already in the P2-17-style memorization regime.

## Structural learning

Level B training already showed:

- format valid: **34/36**
- label exact: **33/36**
- literal exact: **1/36**

This separates structural-format learning from exact literal reproduction.

Level D training reached 9/36 format-valid outputs while all three literal-field exact metrics remained zero.

## Held-out evaluation at step 100

### Tier A /18

- complete: 0
- literal exact: 0
- selector exact: 0/9
- value exact: 0/9
- EOS: 18/18

### Tier B /18

- complete: 0
- format valid: 18/18
- label exact: 10/18
- literal exact: 0
- selector exact: 0/9
- value exact: 0/9
- EOS: 18/18

### Tier C /18

- selected-field exact: 0
- wrong-field retrieval: 0
- EOS: 18/18

At this stage Plex was not reliably copying even the wrong contextual literal, so reference-binding errors cannot yet be separated from basic literal-copy failure.

### Tier D /18

- complete/full plan: 0
- format valid: 6/18
- selector exact: 0
- old exact: 0
- new exact: 0
- EOS: 18/18

## Existing development suites

P2-14 remained 0/12.

P2-01b remained 0/30, while EOS reached 10/10 in CSS, 10/10 in HTML and 10/10 in JavaScript. This again shows that stopping/completion behavior transfers earlier than task semantics.

## Conclusion

P2-18 at step 100 is **not a decisive literal-copy failure** because the supplied curriculum is still severely underfit.

The validation-loss drop justifies a controlled optimization continuation before changing the representation.

The owner subsequently approved P2-18b: continuation of this exact v3 step-100 checkpoint in four isolated +100-update increments through cumulative step 500, with scoring at 200/300/400/500 and no automatic extension beyond 500.
