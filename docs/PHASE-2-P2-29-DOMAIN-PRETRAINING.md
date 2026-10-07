# P2-29 — Matched Longer Plex Web Domain Pretraining

## Status

**Active — one 500-step matched run authorized.**

P2-29 extends only the training horizon. All other controlled inputs remain identical to P2-28.

## Why replay from step zero

P2-29 intentionally starts again from the same verified P2-28 **step-zero checkpoint**, rather than resuming the P2-28 step-100 checkpoint.

This produces a clean matched trajectory:

```text
same random initialization
same corpus
same tokenizer
same seed
same optimizer
same batch settings
same sampler
same objective
        ↓
only training horizon changes
100 steps → 500 steps
```

That makes the longer run easier to interpret and prevents a resume-path difference from becoming another experimental variable.

## Authorized settings

| Setting | Value |
|---|---|
| Starting checkpoint | P2-28 verified step-zero |
| Parameters | 27,566,080 |
| Device | CUDA |
| Maximum updates | **500** |
| Maximum time | **10 minutes** |
| Micro-batch | 1 |
| Gradient accumulation | 16 |
| Sampling | `random-window-v1` |
| Loss | ordinary next-token loss |
| Optimizer | AdamW |
| Learning rate | 0.0003 constant |
| Task fine-tuning | no |
| Answer weighting | 1 |

## Exact command

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --initialization training\artifacts\initializations\p2-28-web-v1-step0\initialization.pt `
  --output-dir pilot\p2-29-web-v1-500step `
  --minutes 10 `
  --steps 500 `
  --device cuda `
  --micro-batch 1 `
  --gradient-accumulation 16 `
  --checkpoint-every-minutes 5
```

## Review gate

After the run:

1. inspect validation loss before/after
2. independently reproduce the final held-out loss
3. inspect the metrics trajectory for whether validation improves or begins worsening
4. confirm checkpoint/tokenizer/dataset identities
5. record resource use and throughput
6. do not continue beyond step 500 without another reviewed decision

The final project holdout remains closed.
