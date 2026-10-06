# P2-16 approved CSS generalization experiment

P2-16 is owner-approved for one bounded first run against the exact candidate:

`p2-16-css-generalization-candidate-v1`

Candidate SHA-256:

`639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc`

The approval artifact is:

`training/phase2/approvals/p2-16-css-generalization-candidate-v1.json`

## Authorized policy

- 180 total reviewed candidate records
- 120 gradient-training records
- 60 evaluation-only records
- Tier A: 24
- Tier B: 12
- Tier C: 12
- Tier D: 12
- fresh tokenizer fit on the 120 training rows only
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
- final owner-controlled holdout remains closed

The committed P2-16 candidate remains marked `pending-owner-review` because it is the immutable reviewed candidate artifact. Authorization is represented by the separate approval artifact that pins its SHA-256 and the exact run policy.

## Prepare

From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_16_approved_experiment.py `
  --output training\artifacts\experiments\p2-16-css-generalization-prepared-v1
```

Preparation:

1. reruns the read-only candidate verifier;
2. verifies the exact owner approval;
3. materializes the approved 120/60 partition;
4. proves the evaluation group, not the training group, is selected as the dataset validation split;
5. fits a fresh Plex byte-level BPE tokenizer on the 120 training rows only;
6. checks every P2-16 prompt/record/answer against the 512-token context and CSS generation budget;
7. creates a fresh CPU seed-1337 step-zero Plex initialization;
8. verifies the model still has exactly 27,566,080 parameters;
9. copies unchanged P2-14 and P2-01b development sets for matched scoring;
10. records hashes and the complete prepared experiment plan.

Preparation does **not** train the model.

Verify the completed preparation bundle with:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_16_approved_experiment.py `
  --output training\artifacts\experiments\p2-16-css-generalization-prepared-v1 `
  --verify-only
```

## Run

Only after preparation and verification succeed:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_16_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-16-css-generalization-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-16-css-generalization-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner refuses CPU execution, runs above 100 updates, runs above ten minutes, reuse of an existing output directory, and any prepared bundle that no longer matches the approved plan.

## Matched scoring

The fresh step-zero checkpoint and trained checkpoint are both scored on:

- 120 supplied P2-16 training edits;
- Tier A /24 — same operation, unseen selector/value;
- Tier B /12 — seen operation, unseen wording;
- Tier C /12 — composition of seen primitives;
- Tier D /12 — entirely unseen property families;
- P2-14 /12 — unchanged CSS edit development set;
- P2-01b /30 — unchanged HTML/CSS/JavaScript development set.

P2-16 scoring records:

- complete-task passes;
- syntax-valid outputs;
- exact-string matches;
- EOS behavior;
- generated token counts;
- deterministic failure categories for requested-edit, wrong-value, preservation, unexpected-change, incomplete-rule, malformed-CSS, repetition, copied-input, premature-EOS and no-EOS cases.

The runner requires Node.js before training so P2-01b JavaScript tasks receive real syntax checks.

## Interpretation

P2-15 already showed that Plex can exactly fit a tiny supplied CSS curriculum. P2-16 asks whether broader curriculum diversity produces reusable edit behavior.

The first important signal is not necessarily 120/120 training. Nonzero Tier A or Tier B performance would be the first evidence that the learned operation is transferring beyond literal supplied examples. Tier C tests composition. Tier D remains the hardest out-of-family test.

P2-14 and P2-01b are development measurements, not final holdouts. The final owner-controlled holdout remains closed.
