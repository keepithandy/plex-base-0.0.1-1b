# P2-05: counterbalanced composition diagnostic

Status: approved local P2 diagnostic.

P2-04 fit all six supplied CSS layout combinations and composed one of three unseen selector-gap pairings. Two failures replayed learned training solutions. P2-05 tests whether that 1/3 result is a stable compositional capability or a split-specific accident.

## Question

Can Plex independently bind a CSS selector and gap value when every individual selector and gap is familiar, but the exact pair is unseen in the current training fold?

## Matrix

Selectors:

- `.actions`
- `.filters`
- `.controls`

Gap values:

- `6px`
- `14px`
- `28px`

The 3 x 3 space contains nine total combinations.

## Three folds

Each fold trains on six cells and evaluates three. Within every fold:

- each selector appears exactly twice in training,
- each gap appears exactly twice in training,
- each held-out selector appears in training,
- each held-out gap appears in training,
- none of the three held-out pairs appears in that fold's training set.

Across all three folds, every one of the nine matrix cells is held out exactly once.

### Fold A

Held out:

- `.actions + 28px`
- `.filters + 6px`
- `.controls + 14px`

This reproduces the P2-04 split.

### Fold B

Held out:

- `.actions + 6px`
- `.filters + 14px`
- `.controls + 28px`

### Fold C

Held out:

- `.actions + 14px`
- `.filters + 28px`
- `.controls + 6px`

## Important interpretation boundary

P2-05 is counterbalanced cross-validation over one known nine-cell matrix. A pair held out in one fold is intentionally used for training in the other two folds. Therefore the aggregate 9/9 surface is **not** a globally pristine holdout and must not be reported as nine permanently unseen tasks.

The valid claim is narrower: each score asks whether Plex can recombine familiar slot values into a pair that was unseen **within that fold**.

The final project holdout remains unopened.

## Training policy

Every fold uses:

- a fresh scratch initialization,
- seed `1337`,
- the same frozen Plex tokenizer,
- answer/EOS-only complete-record loss,
- full prompt text retained in causal context,
- micro-batch `1`,
- gradient accumulation `16`,
- at most `100` optimizer updates,
- at most `10` minutes,
- no automatic extension.

All three fresh initializations must match the recorded scratch tensors exactly before training starts.

The fold-local held-out rows are excluded from both gradient training and runtime validation loss. Runtime loss telemetry continues to use the existing P2 request-following validation split.

## Local commands

Pull the merged code first:

```powershell
git switch master
git pull
```

Prepare all three folds:

```powershell
uv run --project training --no-sync python training\phase2\prepare_counterbalanced_composition.py `
  --output training\artifacts\experiments\p2-05-counterbalanced-inputs-v1
```

Then run the three-fold diagnostic:

```powershell
uv run --project training --no-sync python training\phase2\run_counterbalanced_composition.py `
  --prepared training\artifacts\experiments\p2-05-counterbalanced-inputs-v1 `
  --output-dir training\artifacts\experiments\p2-05-counterbalanced-run-v1 `
  --steps 100 --minutes 10 --device cuda
```

The runner executes Fold A, Fold B, and Fold C sequentially. It does not authorize a longer run.

## Interpretation gate

First require all three folds to fit their six supplied combinations. If any fold fails 6/6 supplied composition, aggregate transfer is inconclusive.

If all three folds converge, interpret the nine fold-local held-out decisions as:

- `9/9`: full counterbalanced composition on this one CSS operation,
- `7-8/9`: strong counterbalanced composition signal,
- `4-6/9`: partial counterbalanced composition,
- `1-3/9`: limited/inconsistent counterbalanced composition,
- `0/9`: no counterbalanced composition demonstrated after supplied fit.

Regardless of score, this remains a tiny single-operation diagnostic and does not establish general coding capability.
