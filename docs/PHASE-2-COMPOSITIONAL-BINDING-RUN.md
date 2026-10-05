# P2-04: approved compositional-binding run

Status: **approved for one bounded local diagnostic run**.

## Owner-approved identities

- source operation: `gap-css-layout-01`
- approved training records: 6
- frozen evaluation-only records: 3
- candidate SHA-256: `df7a6b6f8592006c37612b2b179fb9aee278d966914136284d52a63991c8c754`
- evaluation-only SHA-256: `578c7e376301751e61112b02feb2a9651f9858efc2276b0bf5067de2e5acccff`
- objective: `answer-eos-only-complete-record-v1`
- seed: 1337
- maximum updates: 100
- maximum runtime: 10 minutes
- automatic extension: forbidden
- final holdout: closed

The six training pairs are:

- `.actions` + `6px`
- `.actions` + `14px`
- `.filters` + `14px`
- `.filters` + `28px`
- `.controls` + `6px`
- `.controls` + `28px`

The frozen three held-out recombinations are:

- `.actions` + `28px`
- `.filters` + `6px`
- `.controls` + `14px`

Every selector and every gap value occurs exactly twice in training. No held-out pair occurs in training.

## Important isolation rule

The three P2-04 held-out records are not used for training and are not used for runtime validation loss. The training loop keeps the existing `p2-request-following-v3` validation split for its before/after loss telemetry. The three recombinations are opened only after the bounded training run completes, for deterministic completion scoring.

## Prepare the frozen run inputs

The locally generated draft must still exist at:

`training/phase2/drafts/p2-04-compositional-layout-v1`

Preparation verifies its exact approved hashes before copying anything into the artifact directory.

```powershell
uv run --project training --no-sync python training\phase2\prepare_compositional_experiment.py `
  --output training\artifacts\experiments\p2-04-compositional-inputs-v1
```

Preparation does not train Plex.

## Run the diagnostic

```powershell
uv run --project training --no-sync python training\phase2\run_compositional_experiment.py `
  --prepared training\artifacts\experiments\p2-04-compositional-inputs-v1 `
  --output-dir training\artifacts\experiments\p2-04-compositional-run-v1 `
  --steps 100 --minutes 10 --device cuda
```

The run starts from the same recorded seed-1337 scratch tensors used by the prior P2 diagnostics. Full prompts remain in causal context, but prompt targets receive zero loss weight; answer/EOS targets receive unit weight.

## Interpretation gate

Interpret held-out recombination only after checking the six supplied combinations.

- Fewer than 6/6 supplied composition passes: **inconclusive transfer result**. Plex has not yet fit the tiny training matrix sufficiently.
- 6/6 supplied and 0/3 held-out: **no compositional transfer demonstrated** within this CSS operation.
- 6/6 supplied and 1-2/3 held-out: **partial compositional transfer evidence** within this CSS operation.
- 6/6 supplied and 3/3 held-out: **full transfer across this tiny held-out recombination matrix**. This remains a narrow diagnostic, not a broad capability claim.

The result is written to `result.json`; record-level completions are written to `completion-score.json`.
