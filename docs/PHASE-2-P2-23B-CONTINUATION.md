# P2-23b Target-Kind Continuation

## Status

**Owner approved.**

P2-23b continues the exact P2-23 v1 step-100 checkpoint through cumulative step 500.

Fixed schedule:

```text
100 -> 200 -> 300 -> 400 -> 500
```

Each transition is one isolated +100-update CUDA continuation.

No continuation beyond cumulative step 500 is authorized.

## Preserved state

- 144 training records / 72 evaluation records
- tokenizer SHA `4a476b8671591da259fd0e7f5180c845726d22153e492b63b35cee445d88644a`
- 27,566,080 parameters
- optimizer state
- complete-record sampler state
- CPU/CUDA RNG trajectory
- seed 1337
- ordinary next-token complete-record objective
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- existing A/B/C target-kind scorer

P2-14 and P2-01b remain excluded from gradients. The final project holdout remains closed.

## Reviewed step-100 source

- supplied fit: **46/144**
- Level A/B/C: **20/48, 12/48, 14/48**
- Tier A/B/C: **4/24, 3/24, 6/24**
- training target-kind totals:
  - CSS_SELECTOR **10/24**
  - CSS_PROPERTY **19/24**
  - HTML_ELEMENT **0/24**
  - HTML_ATTRIBUTE **4/24**
  - JS_IDENTIFIER **4/24**
  - JS_PROPERTY **9/24**
- validation loss: **7.1383639223 -> 3.4939428498**
- mean recent loss: **0.3362235123**
- cumulative tokens: **177,579**

## Source identities

```text
candidate:
3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08

tokenizer:
4a476b8671591da259fd0e7f5180c845726d22153e492b63b35cee445d88644a

training JSONL:
0e22327d9f8e54cf38f9467e87bd74fdb6bb962b13c68cea5ca26cb603db9d54

validation JSONL:
e052ba467be729534429d7d455277ac191fdd68addc9064cf87d7333adf9c626

training tokens:
8d3be291f0f442533c712c40bf6a20ad3db4c642a1b81148136a34c184d683c3

validation tokens:
816b073a0ae74a9d43a20ffcab8aaa01c547d3670a6afae328fbb2e82c461c7c

dataset manifest:
73f179ffead7ab3355269c313e2f8416cf436caf422c40fa7090801500508c88

sampler index:
d19a15fc252e545a50e3e470ba3453b5e86f2ecd1a7ea0a301f2a215c0688de4
```

## Scoring

At cumulative steps 200, 300, 400 and 500 retain:

- supplied fit /144
- Level A/B/C /48
- Tier A/B/C /24
- per-kind exact results for:
  - CSS_SELECTOR
  - CSS_PROPERTY
  - HTML_ELEMENT
  - HTML_ATTRIBUTE
  - JS_IDENTIFIER
  - JS_PROPERTY
- known target-kind output counts
- malformed/unknown target-kind counts
- EOS
- validation loss
- recent training loss
- cumulative tokens
- P2-14
- P2-01b
- checkpoint identity

The three pairwise distinctions of special interest remain:

```text
CSS_SELECTOR   <-> CSS_PROPERTY
HTML_ELEMENT   <-> HTML_ATTRIBUTE
JS_IDENTIFIER  <-> JS_PROPERTY
```

## Run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_23b_continuation.py `
  --prepared training\artifacts\experiments\p2-23-target-kind-prepared-v1 `
  --source-run training\artifacts\experiments\p2-23-target-kind-run-v1 `
  --output-dir training\artifacts\experiments\p2-23b-target-kind-continuation-v1
```

The runner exposes no step or duration override for extending the fixed schedule.

Do not automatically continue after step 500.
