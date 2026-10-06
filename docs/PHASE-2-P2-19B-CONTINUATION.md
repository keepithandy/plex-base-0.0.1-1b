# P2-19b Reference Binding Continuation

## Approval

The repository owner approved continuation of the exact P2-19 v1 step-100 checkpoint through cumulative step 500.

P2-19b changes **cumulative optimization only**.

It preserves:

- the exact 144 P2-19 training records;
- the exact 72 P2-19 evaluation records;
- tokenizer SHA-256 `03df6f1a6dce8637f968e498c1bf2522e630f6d04d633b03f8b4d74d1bddf983`;
- the 27,566,080-parameter architecture;
- optimizer state;
- complete-record sampler state;
- seed/RNG continuation;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing Level A/B/C/D P2-19 reference-binding scoring rules.

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

The approved continuation source is the completed P2-19 v1 first run:

- training complete tasks: **51/144**
- validation loss: **6.6869590580 -> 3.0484805703**
- mean recent loss: **0.4593148714**
- cumulative tokens processed: **188,282**
- tokenizer vocabulary size: **667**
- sampler: `complete-record-v1`
- sampler records: **144**

Held-out step-100 reference transfer already exists:

- Tier A reference exact: **4/18**
- Tier B reference exact: **6/18**
- Tier C reference exact: **3/18**
- Tier D full plan exact: **1/18**

## Runtime source gate

Before any continuation update, the runner verifies:

- the prepared P2-19 v1 bundle still passes `verify_prepared`;
- candidate SHA, tokenizer SHA, vocabulary size and dataset hashes match the approved identities;
- sampler index SHA matches the reviewed step-100 source;
- train/evaluation counts remain 144/72;
- the source run is the completed P2-19 approved experiment at step 100;
- source optimization metrics match the owner-reviewed values;
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
uv run --project training --no-sync python training\phase2\run_p2_19b_continuation.py `
  --prepared training\artifacts\experiments\p2-19-reference-binding-prepared-v1 `
  --source-run training\artifacts\experiments\p2-19-reference-binding-run-v1 `
  --output-dir training\artifacts\experiments\p2-19b-reference-binding-continuation-v1
```

There is no CLI option to request more than the four approved +100 increments.

## Scoring

At cumulative steps 200, 300, 400 and 500, report:

### Training /144

- total complete-task passes;
- Level A/B/C/D complete-task passes.

### Tiers A/B/C /18

- complete/reference exact;
- known-reference output;
- wrong-known-reference count;
- unknown/malformed count;
- target-field breakdown;
- EOS.

### Tier D /18

- full plan exact;
- format valid;
- selector-reference exact;
- old-reference exact;
- new-reference exact;
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

The highest-value outcome is not necessarily strong Tier A.

If Tier A remains weak while B/C/D rise materially, deterministic Plex Code prebinding/resolution is strongly supported: tooling should own arbitrary repository literals while Plex Base reasons over references.

If B rises but C remains around chance, explicit reference handling works but semantic role mapping remains the next bottleneck.

If C rises while D remains weak, single-reference semantic selection is viable and multi-reference composition becomes the next isolated target.

If supplied fit becomes strong while B/C/D remain near chance and validation loss rises, reference mediation alone is insufficient at the current scale.

The final holdout remains closed.
