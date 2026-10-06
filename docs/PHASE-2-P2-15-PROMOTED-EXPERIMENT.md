# P2-15 promoted experiment

P2-15 now runs from the owner-approved promoted data under:

`training/phase2/data/authored/p2-15-css-edit-v1/`

The earlier temporary preparation/runner files were superseded by the promoted-data flow. This wrapper makes that newer flow reproducible while preserving the exact candidate split.

## Fixed semantic split

Training-only families:

- button radius
- callout border color
- navigation alignment
- card shadow
- label font style
- thumbnail width
- badge text transformation
- menu-item opacity

Validation-only families:

- list style
- whitespace handling
- aspect ratio
- outline

The generic grouped dataset builder uses split seed `299` with `30%` validation solely to reproduce this already-approved 8/4 family partition. The wrapper preflights that seed against the repository's SHA-256 ranking rule before building the dataset, and then verifies the resulting group membership again. The **model initialization seed remains 1337**.

## Prepare

From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_15_promoted_experiment.py `
  --output training\artifacts\experiments\p2-15-css-edit-prepared-v1
```

This command:

1. verifies the owner approval and candidate SHA-256;
2. verifies all 36 promoted source files against the reviewed candidate;
3. creates the exact 24/12 dataset split;
4. fits a fresh Plex byte-level BPE tokenizer on the 24 training rows only;
5. verifies prompt/answer/context token budgets;
6. creates a fresh seed-1337 step-zero Plex checkpoint;
7. records hashes and experiment metadata.

It does **not** train the model.

Verify a prepared bundle with:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_15_promoted_experiment.py `
  --output training\artifacts\experiments\p2-15-css-edit-prepared-v1 `
  --verify-only
```

## Run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_15_promoted_experiment.py `
  --prepared training\artifacts\experiments\p2-15-css-edit-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-15-css-edit-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner uses the existing complete-record pilot trainer with ordinary next-token loss and refuses runs above the approved 100-update / 10-minute ceiling.

## Matched scoring

Both step zero and the trained checkpoint are scored on. Node.js must be available on PATH so JavaScript tasks in P2-01b can receive real syntax checks; the runner fails before training if that requirement is missing:

- P2-15: 24 supplied training edits + 12 withheld-family validation edits;
- P2-01b: the existing 30-task development set, reported overall and by language;
- P2-14: the existing 12-task CSS edit development set.

P2-15 validation transfer is called interpretable only after 24/24 supplied training edits pass. P2-01b and P2-14 remain development measurements. The final owner-controlled holdout remains closed.
