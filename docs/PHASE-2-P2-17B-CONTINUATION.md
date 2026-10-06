# P2-17b Semantic Binding Continuation

## Approval

The repository owner approved continuation of the exact P2-17 v2 step-100 checkpoint through cumulative step 500.

P2-17b changes **cumulative optimization only**.

It preserves:

- the exact 120 P2-17 v2 training records;
- the exact 60 P2-17 v2 evaluation records;
- tokenizer SHA-256 `48fca8786e8dd5d8158f4874283b256b87195bb74b6b08cfad605c8eea68c29c`;
- the 27,566,080-parameter architecture;
- AdamW optimizer state;
- seed/RNG continuation;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing P2-17 field-level scoring rules.

The fixed schedule is:

```text
step 100 source checkpoint
  -> +100 -> score step 200
  -> +100 -> score step 300
  -> +100 -> score step 400
  -> +100 -> score step 500
```

No automatic continuation beyond step 500 is authorized. P2-14 and P2-01b remain excluded from gradient training. The final holdout remains closed.

## Runtime source gate

Before any optimizer update, the runner verifies:

- the prepared v2 bundle still passes `verify_prepared`;
- candidate SHA, tokenizer SHA, vocabulary size and dataset hashes match the approved v2 identities;
- the source run is the completed P2-17 approved experiment at step 100;
- the source training metrics match the owner-reviewed values;
- the actual local checkpoint SHA matches `trained-candidate-score.json`;
- parameter count is still exactly 27,566,080;
- optimizer state exists;
- sampling RNG state exists;
- CPU and CUDA RNG state exist;
- `complete-record-v1` remains the sampler;
- seed remains 1337.

Each increment uses the existing `resume_pilot` path and must complete exactly 100 additional updates before scoring.

## Run

After pulling the merged changes:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_17b_continuation.py `
  --prepared training\artifacts\experiments\p2-17-semantic-binding-prepared-v2 `
  --source-run training\artifacts\experiments\p2-17-semantic-binding-run-v2 `
  --output-dir training\artifacts\experiments\p2-17b-semantic-binding-continuation-v1
```

There is no CLI option to request more than the four approved +100 increments.

## Scoring

At cumulative steps 200, 300, 400 and 500, report:

### Training extraction /60
- full-plan exact
- format valid
- selector exact
- operation exact
- property exact
- old-value exact
- new-value exact

### Training application /60
- complete-task pass
- syntax valid
- selector exact
- requested edit applied
- unrelated declarations preserved

### Tier A /20
The same field-level extraction metrics.

### Tier B /20
Explicit-plan application metrics.

### Tier C /20
Request-to-CSS composition metrics.

Also track:

- validation loss before/after each increment;
- mean recent training loss;
- cumulative tokens processed;
- P2-14 passes;
- P2-01b passes and language breakdown;
- checkpoint SHA-256.

## Decision rule

Do not automatically continue after step 500.

If supplied training fit becomes strong while Tier A selector/new-value binding remains near zero, stop adding compute and redesign the representation. If held-out binding begins to rise with training fit, P2-17 is producing genuine literal-binding transfer. If validation loss reverses while training fit continues upward, treat that as overfitting pressure.

The final holdout remains closed.
