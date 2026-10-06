# P2-21b Semantic Role Continuation

## Approval

The repository owner approved continuation of the exact P2-21 v1 step-100 checkpoint through cumulative step 500.

P2-21b changes **cumulative optimization only**.

It preserves:

- the exact 144 P2-21 training records;
- the exact 72 P2-21 evaluation records;
- tokenizer SHA-256 `28c513c3887d6eba0680e448443358ac04f812abbb4d2ab23c2d1bf004d0b4ef`;
- the 27,566,080-parameter architecture;
- optimizer state;
- complete-record sampler state;
- seed/RNG continuation;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing P2-21 A/B/C semantic-role scoring rules;
- per-role SELECTOR / OLD / NEW reporting.

The fixed schedule is:

```text
step 100 source checkpoint
  -> +100 -> score step 200
  -> +100 -> score step 300
  -> +100 -> score step 400
  -> +100 -> score step 500
```

No automatic continuation beyond step 500 is authorized. P2-14 and P2-01b remain excluded from gradient training. The final holdout remains closed.

## Step-100 source state

The approved continuation source is the completed P2-21 v1 first run:

- training complete tasks: **68/144**
- Level A: **21/48**
- Level B: **21/48**
- Level C: **26/48**
- Tier A: **6/24**
- Tier B: **8/24**
- Tier C: **10/24**
- validation loss: **6.9496481235 -> 3.3556300860**
- mean recent loss: **0.3088514040**
- cumulative tokens processed: **143,854**
- tokenizer vocabulary size: **890**
- sampler: `complete-record-v1`
- sampler records: **144**

## Runtime source gate

Before any continuation update, the runner verifies:

- the prepared P2-21 v1 bundle still passes `verify_prepared`;
- candidate SHA, tokenizer SHA, vocabulary size and dataset hashes match the approved identities;
- sampler index SHA matches the reviewed step-100 source;
- train/evaluation counts remain 144/72;
- Level/Tier counts remain 48/24 for A/B/C;
- the source run is the completed P2-21 approved experiment at step 100;
- source optimization metrics match the owner-reviewed values;
- source training fit remains 68/144 with A/B/C = 21/21/26;
- source held-out Tier A/B/C remain 6/8/10;
- the actual checkpoint SHA matches `trained-candidate-score.json`;
- parameter count remains exactly 27,566,080;
- optimizer state exists;
- sampling RNG state exists;
- CPU and CUDA RNG states exist;
- complete-record sampler metadata still identifies exactly 144 records;
- seed remains 1337.

Each increment uses the existing `resume_pilot` path and must complete exactly 100 additional updates before scoring.

## Run

After pulling the merged changes:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_21b_continuation.py `
  --prepared training\artifacts\experiments\p2-21-semantic-role-prepared-v1 `
  --source-run training\artifacts\experiments\p2-21-semantic-role-run-v1 `
  --output-dir training\artifacts\experiments\p2-21b-semantic-role-continuation-v1
```

There is no CLI option to request more than the four approved +100 increments.

## Scoring

At cumulative steps 200, 300, 400 and 500, report:

### Training /144

- total complete-task passes;
- Level A/B/C complete-task passes.

### Tier A/B/C /24

For each tier:

- exact role;
- known-role output;
- wrong-known-role output;
- unknown/malformed role;
- SELECTOR exact count;
- OLD exact count;
- NEW exact count;
- EOS.

Also track:

- validation loss before/after each increment;
- mean recent training loss;
- cumulative tokens processed;
- P2-14 passes;
- P2-01b passes and language breakdown;
- checkpoint SHA-256.

## Decision rule

Do not automatically continue after step 500.

The continuation is intended to resolve the central P2-21 question:

- does `OLD` catch up as supplied fit becomes strong?
- do A/B/C rise materially above the 8/24 chance expectation?
- or does the model memorize the supplied curriculum while held-out semantic transfer remains weak?

If supplied fit becomes strong while validation worsens and held-out A/B/C remain near chance, close P2-21 and redesign the semantic representation rather than optimizing further.

The final holdout remains closed.
