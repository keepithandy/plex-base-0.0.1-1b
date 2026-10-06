# P2-18 Approved Literal Copy Run

## Status

P2-18 is owner-approved for one bounded first run against the exact candidate:

`p2-18-literal-copy-candidate-v1`

Candidate SHA-256:

`9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6`

The approval artifact is:

`training/phase2/approvals/p2-18-literal-copy-candidate-v1.json`

## Authorized policy

- 216 total reviewed candidate records
- 144 training records
- 72 evaluation-only records
- Level/Tier A: direct unseen literal copy
- Level/Tier B: labeled unseen literal copy
- Level/Tier C: selected-field binding
- Level/Tier D: three-field plan assembly
- fresh tokenizer fitted on the 144 training records only
- all 72 evaluation records excluded from tokenizer fitting
- all 72 evaluation records excluded from gradient training
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
uv run --project training --no-sync python training\phase2\prepare_p2_18_approved_experiment.py `
  --output training\artifacts\experiments\p2-18-literal-copy-prepared-v1
```

Preparation:

1. reruns the read-only P2-18 candidate verifier;
2. verifies the exact owner approval;
3. materializes the exact 144/72 partition;
4. proves the evaluation source group is the validation partition;
5. fits a fresh Plex byte-level BPE tokenizer on the 144 training records only;
6. verifies every P2-18 prompt/record/answer against the 512-token context and generation budget;
7. checks unchanged P2-14 and P2-01b development prompts with the same tokenizer;
8. instantiates the real `CompleteRecordTokenCorpus` as a sampler preflight;
9. creates a fresh CPU seed-1337 step-zero Plex initialization;
10. verifies the model still has exactly 27,566,080 parameters;
11. records hashes and the complete prepared experiment plan.

Preparation does **not** train the model.

### Windows / OneDrive dataset promotion

The dataset builder writes into a private sibling staging directory and atomically promotes that directory into the final `dataset` path. Windows OneDrive/indexing can briefly hold a directory handle and return `WinError 5` or `WinError 32` during that final rename. The dataset pipeline now retries only those transient Windows promotion errors for a bounded period. It still fails immediately for other permission errors and refuses to overwrite a destination that appears unexpectedly.

Verify the prepared bundle:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_18_approved_experiment.py `
  --output training\artifacts\experiments\p2-18-literal-copy-prepared-v1 `
  --verify-only
```

## Run

Only after preparation and verification succeed:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_18_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-18-literal-copy-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-18-literal-copy-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner refuses CPU execution, runs above 100 updates, runs above ten minutes, reuse of an existing output directory, and any prepared bundle that no longer matches the approved plan.

## Matched scoring

Fresh step-zero and trained checkpoints are both scored on all 216 candidate records.

### Level/Tier A — direct copy

Report:

- complete/exact output
- literal exact
- selector-literal exact
- value-literal exact
- EOS

This is the cleanest unseen-copy primitive.

### Level/Tier B — labeled copy

Report:

- complete task
- format valid
- label exact
- literal exact
- selector/value breakdown
- EOS

This tests whether a small structural wrapper disrupts exact copying.

### Level/Tier C — selected-field binding

Report:

- selected literal exact
- selector/old/new target-field breakdown
- wrong-field retrieval count
- EOS

A wrong-field retrieval means Plex copied a real literal from the current context, but bound the request to the wrong field. This separates binding failure from inability to copy.

### Level/Tier D — three-field plan assembly

Report:

- full plan exact
- format valid
- selector exact
- old-value exact
- new-value exact
- EOS

This tests multiple simultaneous literal bindings without CSS parsing or edit execution.

### Existing development suites

P2-14 /12 and P2-01b /30 are scored at step zero and after training. They remain development-only and are never used for gradients.

## Decision rule

P2-18 is a primitive gate.

Do not automatically extend the run if training is incomplete. First inspect:

- supplied training fit by level;
- Tier A direct-copy transfer;
- Tier B labeled-copy transfer;
- Tier C correct-field versus wrong-field retrieval;
- Tier D per-field binding;
- validation loss;
- P2-14/P2-01b development transfer.

If supplied training fit becomes strong while Tier A/B unseen copying remains near zero, further CSS examples are not justified. The next representation should evaluate reference-mediated symbol handling, with deterministic Plex tooling resolving model-selected references back to exact repository literals.

The final holdout remains closed.
