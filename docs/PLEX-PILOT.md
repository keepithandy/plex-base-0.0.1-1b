# P1-18 — Two-hour tokenizer-aware pilot

**Status: complete for the bounded pilot.** The owner ran the full 120-minute CUDA pilot from the P1-16 random initialization on the approved P1-15 BPE corpus. The saved checkpoint and held-out result were independently verified. The later [P1-19 one-step continuation](PLEX-RESUME-AND-COMPLETION.md) verified tokenizer-aware resumption and independent generation from saved weights.

## What the pilot command does

`pilot` verifies the tokenizer and model configuration, the reviewed source manifest, both JSONL split hashes, both packed-token hashes, record counts, token ranges, and distinct train/validation files. It accepts only the matching P1-16 step-zero scratch checkpoint. Training samples from the 147,948-token training split; the 18,394-token held-out validation split is used only for evaluation. Loss uses the 9,976 learned BPE IDs within Plex's 16,384-ID model capacity.

The command measures validation loss before and after training, logs training loss and token throughput, and records memory use, tokenizer identity, dataset hashes, seed, settings, and progress. It saves a checkpoint every five minutes and at completion or Ctrl+C. It refuses an existing output directory and caps training at 120 minutes within the owner's 200 GiB artifact allocation. Checkpoints preserve model and optimizer state, RNG state, initialization provenance, tokenizer identity, and both split identities.

`pilot-evaluate` independently reads a saved pilot checkpoint and the held-out validation split, refuses mismatched tokenizer/dataset identities, and reports its loss. The general byte-v1 commands remain separate. The later P1-19 commands `pilot-resume` and `complete` verified the BPE continuation and saved-checkpoint generation path.

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

These numbers describe the one-update preparation check, not the full pilot. The starter training set is small, so repeated exposure may overfit.

The ignored preflight files are under `training/artifacts/pilot/p1-18-preflight-v1/`: `pilot-checkpoint.pt`, `metrics.jsonl`, and `pilot-report.json`. They count against the 200 GiB storage allocation. Existing P1-01–P1-17 work and the earlier synthetic smoke checkpoint remain intact.

## Completed two-hour pilot

The successful run is stored locally under `training/artifacts/pilot/p1-18-full-v2/`. Its `pilot-report.json`, `metrics.jsonl`, and `pilot-checkpoint.pt` are ignored by Git. The first `p1-18-full-v1` attempt ended without a final report and is not used for this result. The completed run was uninterrupted and stopped at its 120-minute cap.

| Measurement | Completed run |
|---|---:|
| Elapsed time | 7,200.018 seconds |
| Optimizer updates | 43,632 |
| Training token positions processed, including repeated sampling | 357,433,344 |
| Reported throughput | 49,643.40 token positions/second |
| Recent mean training loss | 0.02910 |
| Held-out loss before training | 9.33937 |
| Held-out loss after training | 6.53100 |
| Independent held-out evaluation | 6.530996513366699 over 35 batches / 17,920 targets |
| Peak GPU allocated / reserved | 801,311,232 / 878,706,688 bytes |
| Peak process working set | 1,397,129,216 bytes |
| Checkpoint size | 330,897,883 bytes |
| Checkpoint SHA-256 | `8f00c895637a4062037f7a49fb7fdaf1193771243c3727bdd9b9059da93a1298` |
| Starting initialization SHA-256 | `7a06c575ba229cfbdf758cad6ae7d0c4e504236eeba1dd90c9d531ca4689c7b4` |

The final held-out loss is lower by 2.80837 (about 30.1%) than the untrained baseline. The checkpoint's SHA-256 matches the saved report, and the independent evaluation matched its final loss exactly. The 147,948-token training split is tiny relative to 357 million sampled training positions; the low training loss and much higher held-out loss suggest memorization and weak transfer to the separate web-code source group, though the different source distributions also affect that gap. This is evidence of a working bounded training path and improvement on this particular held-out split, not evidence of useful general coding ability. Broader reviewed training data and stronger evaluation are still needed.

To independently recheck the completed checkpoint from the repository root in PowerShell:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-evaluate `
  --checkpoint training\artifacts\pilot\p1-18-full-v2\pilot-checkpoint.pt `
  --device cuda
```

To reproduce the full experiment, use a fresh output directory; the command refuses overwrite and starts again from the scratch initialization:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --minutes 120 --device cuda `
  --output-dir pilot\p1-18-reproduction-v1
```

No further long run is required for P1-18. The [P1-19 technical gate](PLEX-RESUME-AND-COMPLETION.md) passed with a one-step continuation, and the [P1-20 experiment report](PLEX-EXPERIMENT-REPORT-P1-20.md) records the combined results. Uncapped training is not enabled or justified by this small corpus.

## Verification

The one-step command and independent evaluation completed on the approved bundle; all 39 training-workspace tests passed at implementation time. The owner completed the full two-hour run, and the saved report, checkpoint hash, and separate `pilot-evaluate` result were checked on the completed checkpoint. The installed PyTorch build still prints a nonfatal missing-NumPy warning.
