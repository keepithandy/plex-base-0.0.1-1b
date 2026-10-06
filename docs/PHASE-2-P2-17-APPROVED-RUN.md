# P2-17 Approved Semantic Binding Run

## Status

P2-17 is owner-approved for one bounded first run against the exact candidate:

`p2-17-semantic-binding-candidate-v1`

Candidate SHA-256:

`2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5`

The approval artifact is:

`training/phase2/approvals/p2-17-semantic-binding-candidate-v1.json`

## Authorized policy

- 180 total reviewed candidate records
- 120 training records
- 60 evaluation-only records
- Tier A: 20 request -> edit-plan tasks
- Tier B: 20 explicit-plan -> CSS tasks
- Tier C: 20 request -> CSS chain tasks
- fresh tokenizer fitted on the 120 training records only
- all 60 evaluation records excluded from tokenizer fitting
- all 60 evaluation records excluded from gradient training
- fresh seed-1337 model initialization
- unchanged 27,566,080-parameter architecture
- ordinary next-token loss over complete records
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- CUDA
- matched step-zero evaluation
- at most 100 updates
- at most 10 minutes
- no automatic extension
- P2-14 excluded from training
- P2-01b excluded from training
- final holdout closed

## Prepare

From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_17_approved_experiment.py `
  --output training\artifacts\experiments\p2-17-semantic-binding-prepared-v1
```

Preparation:

1. reruns the read-only P2-17 candidate verifier;
2. verifies the exact owner approval;
3. materializes the exact 120/60 partition;
4. proves the evaluation group, not the training group, is the dataset validation split;
5. fits a fresh Plex byte-level BPE tokenizer on the 120 training records only;
6. checks every P2-17 prompt/record/answer against the 512-token context and generation budget;
7. checks unchanged P2-14 and P2-01b development prompts against the same tokenizer/context;
8. creates a fresh CPU seed-1337 step-zero Plex initialization;
9. verifies the model still has exactly 27,566,080 parameters;
10. records hashes and the complete prepared experiment plan.

Preparation does **not** train the model.

Verify the resulting bundle with:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_17_approved_experiment.py `
  --output training\artifacts\experiments\p2-17-semantic-binding-prepared-v1 `
  --verify-only
```

## Run

Only after preparation and verification succeed:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_17_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-17-semantic-binding-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-17-semantic-binding-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner refuses CPU execution, runs above 100 updates, runs above ten minutes, reuse of an existing output directory, and any prepared bundle that no longer matches the approved plan.

## Matched scoring

The fresh step-zero checkpoint and trained checkpoint are both scored on all 180 candidate records.

### Training /120

The 120 supplied training records are reported separately as:

- 60 extraction tasks;
- 60 application tasks.

### Tier A /20 — semantic extraction

Each completion is parsed as exactly five ordered fields:

```text
selector=...
operation=...
property=...
old=...
new=...
```

Report:

- full five-field plan exact;
- selector exact;
- operation exact;
- property exact;
- old-value exact;
- new-value exact;
- format validity;
- EOS.

This is the primary P2-17 diagnostic.

### Tier B /20 — explicit plan application

Report:

- complete-task pass;
- CSS syntax validity;
- exact-string match;
- selector exact;
- requested edit applied;
- unrelated declarations preserved;
- EOS.

### Tier C /20 — composition

Tier C uses the same CSS metrics as Tier B but supplies only source CSS + natural-language request. No direct chain tasks are included in training.

A strong Tier B result with weak Tier C would isolate extraction/chaining as the bottleneck. Strong Tier A and B with weak Tier C would isolate composition. Weak Tier A would mean literal semantic binding is still not learned.

### Existing development suites

P2-14 /12 and P2-01b /30 are scored at step zero and after training. They remain development-only and are never used for gradients.

## Interpretation rule

The major experimental change from P2-16 is **semantic-binding representation**, not model size or optimizer configuration.

Do not automatically extend the run if training is incomplete. First inspect:

- Tier A field-level accuracy;
- Tier B application success;
- Tier C composition success;
- supplied training fit;
- validation loss;
- P2-14/P2-01b development transfer.

Any continuation requires a new owner decision.

The final holdout remains closed.
