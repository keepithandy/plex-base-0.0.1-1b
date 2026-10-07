# P2-23 Target-Kind Classification — First Run Result

## Status

**First bounded run complete at cumulative step 100.**

The run reached the authorized 100-update ceiling without interruption. It did not automatically continue.

## Fixed source identity

- candidate SHA: `3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08`
- tokenizer SHA: `4a476b8671591da259fd0e7f5180c845726d22153e492b63b35cee445d88644a`
- actual vocabulary size: **1,091**
- parameter count: **27,566,080**
- seed: **1337**
- training JSONL SHA: `0e22327d9f8e54cf38f9467e87bd74fdb6bb962b13c68cea5ca26cb603db9d54`
- validation JSONL SHA: `e052ba467be729534429d7d455277ac191fdd68addc9064cf87d7333adf9c626`
- training tokens SHA: `8d3be291f0f442533c712c40bf6a20ad3db4c642a1b81148136a34c184d683c3`
- validation tokens SHA: `816b073a0ae74a9d43a20ffcab8aaa01c547d3670a6afae328fbb2e82c461c7c`
- dataset manifest SHA: `73f179ffead7ab3355269c313e2f8416cf436caf422c40fa7090801500508c88`
- sampler index SHA: `d19a15fc252e545a50e3e470ba3453b5e86f2ecd1a7ea0a301f2a215c0688de4`

## Step-100 learning state

| Measure | Result |
|---|---:|
| supplied fit | **46 / 144** |
| Level A | **20 / 48** |
| Level B | **12 / 48** |
| Level C | **14 / 48** |
| Tier A | **4 / 24** |
| Tier B | **3 / 24** |
| Tier C | **6 / 24** |

Six-way chance is **4/24 per tier**.

Held-out transfer at step 100 is therefore not yet interpretable as a final target-kind result because the supplied curriculum remains substantially underfit.

## Training target-kind totals

Across 24 supplied examples per target kind:

| Target kind | Exact /24 |
|---|---:|
| CSS_SELECTOR | **10** |
| CSS_PROPERTY | **19** |
| HTML_ELEMENT | **0** |
| HTML_ATTRIBUTE | **4** |
| JS_IDENTIFIER | **4** |
| JS_PROPERTY | **9** |

The early learning curve is strongly class-asymmetric. CSS_PROPERTY is learned fastest; HTML_ELEMENT remains completely collapsed at step 100.

This is not yet enough evidence to call HTML_ELEMENT a representation failure because total supplied fit is only 46/144.

## Optimization state

- validation loss before: **7.138363922343535**
- validation loss after: **3.493942849776324**
- mean recent training loss: **0.33622351228259506**
- cumulative tokens processed: **177,579**
- steps this run: **100**
- interrupted: **false**
- learning rate: **0.0003 constant**

Validation loss dropped substantially while supplied fit remained incomplete. The correct next experiment is therefore continued optimization of the unchanged representation, not a target-kind redesign.

## Development sets

- P2-14: **0/12**
- P2-01b: **0/30**

Both remain excluded from gradients.

## Decision

Proceed with **P2-23b** as four isolated +100-update continuations:

```text
100 -> 200 -> 300 -> 400 -> 500
```

Score after every increment.

No continuation beyond cumulative step 500 is authorized.

The final project holdout remains closed.
