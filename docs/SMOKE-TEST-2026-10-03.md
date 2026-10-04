# Plex ten-minute CUDA smoke test

Status: **passed on the owner's Windows machine**. The owner supplied the completion JSON, and its values match the local metrics file and checkpoint byte size in `training/artifacts/smoke/20261004T001350Z`. This report retains the result while the large checkpoint and metrics stay outside Git.

The recorded start time is `2026-10-04T00:13:51.392471+00:00`, which is **October 3, 2026, 8:13:51 PM America/New_York**. The local run reports Python 3.12.10, PyTorch 2.14.0+cu126, CUDA runtime 12.6, and an NVIDIA GeForce RTX 4080 SUPER.

Command:

```powershell
uv run --project training python -m plex_training.cli smoke --minutes 10 --device cuda
```

## Recorded result

```json
{
  "checkpoint": {
    "bytes": 330894811,
    "path": "smoke-checkpoint.pt",
    "step": 4199
  },
  "elapsedSeconds": 600.028673199995,
  "event": "run_finished",
  "interrupted": false,
  "meanRecentLoss": 0.003367093067311089,
  "outputDirectory": "smoke\\20261004T001350Z",
  "peakGpuMemory": {
    "allocatedBytes": 719484416,
    "reservedBytes": 769654784
  },
  "processPeakWorkingSetBytes": 1391067136,
  "step": 4199,
  "stepsThisRun": 4199,
  "tokensPerSecond": 57327.60705676272,
  "validationLossAfter": null,
  "validationPending": true
}
```

| Measurement | Observed value |
|---|---:|
| Elapsed training time | 600.03 seconds |
| Optimizer steps | 4,199 |
| Synthetic training throughput | 57,327.61 token positions/second |
| Peak CUDA memory allocated | 686.15 MiB |
| Peak CUDA memory reserved | 734.00 MiB |
| Peak process working set | 1,326.63 MiB (about 1.30 GiB) |
| Saved checkpoint | 315.57 MiB |

The start event confirms **27,566,080 parameters**, six layers, width 512, eight heads, feed-forward width 2,048, context length 512, vocabulary capacity 16,384, dropout 0.1, seed 1337, and random initialization (`resumedFromStep: 0`). The synthetic source has 65,536 repeating byte-pattern tokens. With the default micro-batch of one and accumulation of 16, the run processed 34,398,208 training token positions.

## Interpretation

The default small model completed forward/backward training for ten minutes, fit the available GPU and system RAM, and wrote a checkpoint. The limit stops after the active optimizer step, explaining the approximately 0.03-second overrun before the final result.

The low loss reflects learning the predictable synthetic pattern. This is evidence of runtime/resource fit; coding-data learning and generalization remain to be measured. There was no held-out corpus in this command, so `validationLossAfter: null` and `validationPending: true` are expected. This throughput is specific to the smoke configuration and must not be treated as a measured rate for later data/tokenizer settings.

PyTorch warned that NumPy was unavailable, but the run completed. No NumPy-dependent operation was needed in this smoke test; dependency installation is not required to interpret this result.

Source approval, tokenizer training, and fresh random initialization are recorded in the [P1-14 source/build report](DATASET-SOURCE-REVIEW.md), [P1-15 tokenizer report](PLEX-TOKENIZER.md), and [P1-16 initialization report](PLEX-INITIALIZATION.md). The later [P1-17 learning check](PLEX-LEARNING-CHECK.md), [P1-18 two-hour pilot](PLEX-PILOT.md), and [P1-19 resume/completion check](PLEX-RESUME-AND-COMPLETION.md) completed. The [P1-20 report](PLEX-EXPERIMENT-REPORT-P1-20.md) records the experiment and its limits; uncapped longer training remains disabled pending a broader-data and functional-evaluation plan.
