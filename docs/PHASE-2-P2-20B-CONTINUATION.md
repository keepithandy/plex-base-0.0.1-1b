# P2-20b Role Decomposition Continuation

## Approval

The repository owner approved continuation of the exact P2-20 v1 step-100 checkpoint through cumulative step 500.

P2-20b changes **cumulative optimization only**.

It preserves:

- the exact 144 P2-20 training records;
- the exact 72 P2-20 evaluation records;
- tokenizer SHA-256 `bd9f01238f6ecc82871a2a3a7aa1b7527f353fface791847040c1358b5c0da63`;
- the 27,566,080-parameter architecture;
- optimizer state;
- complete-record sampler state;
- seed/RNG continuation;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing Level A/B/C P2-20 scoring rules.

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

The approved continuation source is the completed P2-20 v1 first run:

- training complete tasks: **45/144**
- Level A: **30/48**
- Level B: **8/48**
- Level C: **7/48**
- Tier A: **6/24**
- Tier B: **4/24**
- Tier C: **6/24**
- validation loss: **6.5795933117 -> 3.2708642700**
- mean recent loss: **0.1827663374**
- cumulative tokens processed: **120,293**
- tokenizer vocabulary size: **597**
- sampler: `complete-record-v1`
- sampler records: **144**

## Runtime source gate

Before any continuation update, the runner verifies:

- the prepared P2-20 v1 bundle still passes `verify_prepared`;
- candidate SHA, tokenizer SHA, vocabulary size and dataset hashes match the approved identities;
- sampler index SHA matches the reviewed step-100 source;
- train/evaluation counts remain 144/72;
- Level/Tier counts remain 48/24 for A/B/C;
- the source run is the completed P2-20 approved experiment at step 100;
- source optimization metrics match the owner-reviewed values;
- source training fit remains 45/144;
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
uv run --project training --no-sync python training\phase2\run_p2_20b_continuation.py `
  --prepared training\artifacts\experiments\p2-20-role-decomposition-prepared-v1 `
  --source-run training\artifacts\experiments\p2-20-role-decomposition-run-v1 `
  --output-dir training\artifacts\experiments\p2-20b-role-decomposition-continuation-v1
```

There is no CLI option to request more than the four approved +100 increments.

## Scoring

At cumulative steps 200, 300, 400 and 500, report:

### Training /144

- total complete-task passes;
- Level A/B/C complete-task passes.

### Tier A /24

- exact role;
- known-role output;
- wrong-known-role output;
- unknown/malformed role;
- target-role breakdown;
- EOS.

### Tier B /24

- exact reference;
- known-reference output;
- wrong-known-reference output;
- unknown/malformed reference;
- target-role breakdown;
- EOS.

### Tier C /24

- exact reference;
- known-reference output;
- wrong-known-reference output;
- unknown/malformed reference;
- target-role breakdown;
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

The decomposition is interpreted as follows:

- A strong, B strong, C strong: semantic classification, symbolic lookup and composition all transfer.
- A weak, B strong: semantic classification is the bottleneck.
- A strong, B weak: symbolic role-to-reference lookup is the bottleneck.
- A strong, B strong, C weak: the individual primitives transfer but composition remains the bottleneck.
- A/B/C weak after strong supplied fit while validation loss rises: the current representation/data regime remains insufficient.

The final holdout remains closed.
