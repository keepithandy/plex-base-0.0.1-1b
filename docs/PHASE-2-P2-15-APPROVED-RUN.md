# P2-15 approved CSS request-to-code diagnostic

**Status: approved and implemented; local preparation/training result not yet recorded.**

P2-15 follows the P2-14 result where the P2-12 step-zero and step-200 checkpoints both scored 0/12 on constrained single-rule CSS edits. The P2-15 experiment changes the training target from narrow selector copying to complete request-to-code CSS edits.

## Owner-approved identity

- Candidate: `p2-15-css-edit-candidate-v1`
- Candidate SHA-256: `e9ca83c92a40abd0575db708bd67d2e4ce6888d97bc31ef4a38938a050dfd6cf`
- Training-row SHA-256: `db29a222896c732fc0b7b43452d6100c281065a99ee22c911f184e458554d19c`
- Validation-row SHA-256: `d49333860bb73d1e941588e070d9cda24bc4d17f75fd9c7546b1d7bbdc2e5cd8`
- Training records: 24 across 8 CSS edit families
- Validation records: 12 across 4 different CSS edit families
- Training objective: `answer-eos-only-complete-record-v1`
- Fresh model initialization: seed 1337
- Maximum updates: 100
- Maximum duration: 10 minutes
- Micro-batch: 1
- Gradient accumulation: 16
- Device: CUDA
- Automatic extension: disabled
- Final project holdout: closed

The validation families are never gradient-training records. They may be used for runtime validation loss and for the matched step-zero/post-training CSS exact-rule score.

## Fresh tokenizer boundary

P2-15 deliberately does not reuse the P2-12 tokenizer.

Preparation builds an exact local dataset from the approved P2-15 rows and fits a fresh Plex byte-level BPE tokenizer using the **24 training rows only**. The 12 validation rows are encoded after the tokenizer is fit but do not contribute to BPE fitting.

Tokenizer policy:

- codec: `plex-byte-bpe-v1`
- requested vocabulary capacity: 16,384
- minimum frequency: 2
- fit split: train
- validation text used for fit: no

The preparation step rejects any record that exceeds Plex's 512-token context or the CSS generation budget under the newly fitted tokenizer.

## Prepare the experiment

From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_15_experiment.py `
  --output training\artifacts\experiments\p2-15-css-edit-prepared-v1
```

Preparation performs the following without training:

1. re-runs the P2-15 integrity verifier;
2. validates the exact owner approval;
3. builds exact train/validation JSONL;
4. fits the fresh tokenizer on training rows only;
5. verifies token budgets;
6. creates a fresh seed-1337 step-zero checkpoint;
7. records hashes in `experiment.json`.

To verify an already prepared bundle:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_15_experiment.py `
  --output training\artifacts\experiments\p2-15-css-edit-prepared-v1 `
  --verify-only
```

## Run the bounded diagnostic

```powershell
uv run --project training --no-sync python training\phase2\run_p2_15_experiment.py `
  --prepared training\artifacts\experiments\p2-15-css-edit-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-15-css-edit-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The runner fails closed above either approved ceiling.

## Scoring design

Before the first optimizer update, the runner scores the step-zero checkpoint on:

- all 24 supplied training records;
- all 12 family-disjoint validation records.

After training, it scores the same records again with the same deterministic generation settings:

- temperature 0;
- seed 1337;
- the candidate's `css_stylesheet_exact` checker;
- no final holdout access.

The main reported values are:

- complete-rule passes at step zero;
- complete-rule passes after training;
- exact-string matches;
- EOS/no-EOS counts;
- train and validation deltas;
- validation loss from the fixed 12-record validation split;
- sampler/accounting integrity.

Validation transfer is labeled interpretable only if the model reaches 24/24 supplied training-rule passes. Otherwise the result remains a useful training measurement but the held-out-family transfer claim is marked inconclusive.

## What P2-15 can establish

A positive result would show that this small Plex model can learn complete single-rule CSS edits and transfer to some withheld CSS property families under a tightly controlled local diagnostic.

It would **not** establish:

- general CSS competence;
- multi-rule stylesheet editing;
- HTML/JavaScript editing;
- repository-level task completion;
- broad coding ability;
- final holdout performance.

Those remain later gates.
