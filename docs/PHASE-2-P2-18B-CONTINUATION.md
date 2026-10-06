# P2-18b Literal Copy Continuation

## Approval

The repository owner approved continuation of the exact P2-18 v3 step-100 checkpoint through cumulative step 500.

P2-18b changes **cumulative optimization only**.

It preserves:

- the exact 144 P2-18 training records;
- the exact 72 P2-18 evaluation records;
- tokenizer SHA-256 `44756dc5700e4ac4d258403429358c0d4783b55fccb0271d695e29ed0bd54533`;
- the 27,566,080-parameter architecture;
- optimizer state;
- complete-record sampler state;
- seed/RNG continuation;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing Level A/B/C/D P2-18 scoring rules.

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

The approved continuation source is the completed P2-18 v3 first run:

- training complete tasks: **4/144**
- validation loss: **6.8281600873 -> 2.8766768773**
- mean recent loss: **0.5493557507**
- cumulative tokens processed: **132,286**
- tokenizer vocabulary size: **820**
- sampler: `complete-record-v1`
- sampler records: **144**

The run remains underfit at step 100, which is why continuation is justified.

## Runtime source gate

Before any continuation update, the runner verifies:

- the prepared v3 bundle still passes `verify_prepared`;
- candidate SHA, tokenizer SHA, vocabulary size and dataset hashes match the approved identities;
- train/evaluation counts remain 144/72;
- the source run is the completed P2-18 approved experiment at step 100;
- source training metrics match the owner-reviewed values;
- the actual checkpoint SHA matches `trained-candidate-score.json`;
- parameter count remains exactly 27,566,080;
- optimizer state exists;
- sampling RNG state exists;
- CPU and CUDA RNG state exist;
- complete-record sampler metadata still identifies exactly 144 records;
- seed remains 1337.

Each increment uses the existing `resume_pilot` path and must complete exactly 100 additional updates before scoring.

## Run

After pulling the merged changes:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_18b_continuation.py `
  --prepared training\artifacts\experiments\p2-18-literal-copy-prepared-v3 `
  --source-run training\artifacts\experiments\p2-18-literal-copy-run-v3 `
  --output-dir training\artifacts\experiments\p2-18b-literal-copy-continuation-v1
```

There is no CLI option to request more than the four approved +100 increments.

## Scoring

At cumulative steps 200, 300, 400 and 500, report:

### Training /144

- total complete-task passes;
- Level A/B/C/D complete-task passes.

### Tier A /18

- complete task;
- literal exact;
- selector exact /9;
- value exact /9;
- EOS.

### Tier B /18

- complete task;
- format valid;
- label exact;
- literal exact;
- selector/value exact breakdown;
- EOS.

### Tier C /18

- selected-field exact;
- wrong-field retrieval;
- selector/old/new target-field breakdown;
- EOS.

### Tier D /18

- full plan exact;
- format valid;
- selector exact;
- old-value exact;
- new-value exact;
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

If supplied Level A fit becomes strong and held-out Tier A selector/value copying rises materially, exact literal copying is learnable at the current scale.

If supplied Level A reaches near-perfect fit while Tier A remains near zero and validation loss rises, stop adding optimization and move to reference-mediated symbol handling.

If Tier A/B become strong while Tier C accumulates wrong-field retrievals, literal copying is established and variable/reference binding becomes the next isolated target.

The final holdout remains closed.
