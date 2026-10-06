# P2-22b Edit Intent Continuation

## Status

Owner-approved continuation of the exact P2-22 v1 step-100 checkpoint.

Fixed schedule:

```text
100 -> 200 -> 300 -> 400 -> 500
```

Each transition is one isolated +100-update CUDA continuation. No continuation beyond cumulative step 500 is authorized.

## Preserved state

- 150 training records / 75 evaluation records
- tokenizer SHA `8f09812c2165cb928c1908f7a81ef59d5e8b6f3f8acb185e083bf1324ed23e5a`
- 27,566,080 parameters
- optimizer state
- complete-record sampler state
- CPU/CUDA RNG trajectory
- seed 1337
- ordinary next-token complete-record objective
- `complete-record-v1`
- micro-batch 1
- gradient accumulation 16
- existing A/B/C edit-intent scorer

P2-14 and P2-01b remain excluded from gradients. The final holdout remains closed.

## Reviewed step-100 source

- supplied fit: 64/150
- Level A/B/C: 24/50, 22/50, 18/50
- Tier A/B/C: 6/25, 2/25, 7/25
- training intent totals:
  - REPLACE 1/30
  - INSERT 8/30
  - DELETE 20/30
  - RENAME 21/30
  - TOGGLE 14/30
- validation loss: 7.0730092866 -> 3.3212734972
- mean recent loss: 0.4386107448
- cumulative tokens: 151,505

## Scoring

Score cumulative steps 200, 300, 400 and 500.

For training and each held-out tier, retain exact results for:

```text
REPLACE
INSERT
DELETE
RENAME
TOGGLE
```

Also retain validation loss, recent training loss, cumulative tokens, P2-14 and P2-01b results, and checkpoint identity.

## Run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_22b_continuation.py `
  --prepared training\artifacts\experiments\p2-22-edit-intent-prepared-v1 `
  --source-run training\artifacts\experiments\p2-22-edit-intent-run-v1 `
  --output-dir training\artifacts\experiments\p2-22b-edit-intent-continuation-v1
```

The runner exposes no step or duration override for extending the fixed schedule.

Do not automatically continue after step 500.
