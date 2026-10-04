# P1-18 — Tokenizer-aware pilot preparation

The bounded training and held-out evaluation path is ready. A one-step preflight completed from the P1-16 random initialization using the approved P1-15 BPE training and validation splits. The **two-hour pilot has not run**; P1-18's full training and outcome gate remain pending.

## What the pilot command does

`pilot` verifies the tokenizer and model configuration, the reviewed source manifest, both JSONL split hashes, both packed-token hashes, record counts, token ranges, and distinct train/validation files. It accepts only the matching P1-16 step-zero scratch checkpoint. Training samples from the 147,948-token training split; the 18,394-token held-out validation split is used only for evaluation. Loss uses the 9,976 learned BPE IDs within Plex's 16,384-ID model capacity.

The command measures validation loss before and after training, logs training loss and token throughput, and records memory use, tokenizer identity, dataset hashes, seed, settings, and progress. It saves a checkpoint every five minutes and at completion or Ctrl+C. It refuses an existing output directory and caps training at 120 minutes within the owner's 200 GiB artifact allocation. Checkpoints preserve model and optimizer state, RNG state, initialization provenance, tokenizer identity, and both split identities.

`pilot-evaluate` independently reads a saved pilot checkpoint and the held-out validation split, refuses mismatched tokenizer/dataset identities, and reports its loss. The general byte-v1 commands remain separate; P1-19 will verify tokenizer-aware resume and generation before any longer runs.

## One-step preflight result

| Measurement | Result |
|---|---:|
| Training updates | 1 |
| Training token positions | 8,192 |
| Active run elapsed time | 0.532 seconds |
| Mean training loss for the update | 9.34319 |
| Held-out loss before update | 9.33937 |
| Held-out loss after update | 8.70955 |
| Independent held-out evaluation | 8.70955 over 35 batches / 17,920 targets |
| Process-selected device | CUDA |
| Peak GPU reserved | 775,946,240 bytes |
| Peak process working set | 1,397,448,704 bytes |
| Checkpoint size | 330,897,883 bytes |
| Checkpoint SHA-256 | `043d2c85dab1dcc88efb96fd65d47a2359ee5677e6c6ce336c41edd0984829e0` |
| Starting initialization SHA-256 | `7a06c575ba229cfbdf758cad6ae7d0c4e504236eeba1dd90c9d531ca4689c7b4` |

These numbers describe one short run in the available execution runtime; they are not a two-hour throughput or memory prediction. One update lowered the measured held-out loss, but the full pilot must measure whether that improvement persists. The starter training set is small, so repeated exposure may overfit.

The ignored preflight files are under `training/artifacts/pilot/p1-18-preflight-v1/`: `pilot-checkpoint.pt`, `metrics.jsonl`, and `pilot-report.json`. They count against the 200 GiB storage allocation. Existing P1-01–P1-17 work and the earlier synthetic smoke checkpoint remain intact.

## Run the two-hour-capped pilot

From the repository root in PowerShell, after reviewing the above preflight and with enough uninterrupted time:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --minutes 120 `
  --device cuda `
  --output-dir pilot\p1-18-full-v1
```

`--device auto` permits CPU fallback, though the prior CUDA smoke and preflight used CUDA. Choose a fresh output directory if `p1-18-full-v1` already exists. The command is a local run and uses no paid service or new dataset download. A shorter measured run can use `--minutes 10` or `--steps 100` with a fresh output name; these are development runs, not the completed two-hour pilot.

After the run, independently re-evaluate the saved checkpoint:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-evaluate `
  --checkpoint training\artifacts\pilot\p1-18-full-v1\pilot-checkpoint.pt `
  --device cuda
```

The output folder's `pilot-report.json` and `metrics.jsonl` hold the before/after validation losses, tokens processed, step count, throughput, memory peaks, checkpoint hash, and whether the run was interrupted. P1-18 is complete only after the bounded real-data run is measured and its held-out validation result is assessed against the untrained baseline. The one-step preflight does not establish coding ability.

## Verification

The one-step command and independent evaluation completed on the approved bundle. All 39 training-workspace tests pass. New checks cover modified validation tokens, checkpoint/tokenizer mismatch, vocabulary masking, and rejection of durations above 120 minutes. `git diff --check` passes. The installed PyTorch build still prints a nonfatal missing-NumPy warning.
