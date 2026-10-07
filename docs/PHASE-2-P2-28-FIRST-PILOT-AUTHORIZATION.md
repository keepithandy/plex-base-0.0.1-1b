# P2-28 — First Bounded Scratch-Pretraining Pilot Authorization

## Status

**Authorized for one bounded run.**

The P2-28 step-zero initialization has been verified and is now the only permitted starting checkpoint for the first Plex Web domain-pretraining pilot.

## Verified step-zero checkpoint

- parameter count: **27,566,080**
- tokenizer vocabulary: **16,384**
- seed: **1337**
- initialization device: **CPU**
- initialization scheme: `plex-normal-0.02-v1`
- pretrained checkpoint loaded: **false**
- pretrained model weights loaded: **false**
- checkpoint SHA-256: `06c27a452e2a62ed069729d2080b1d2fddb84d41bd336bbda489c066c23f8a86`
- initial model weights SHA-256: `98785d70ee7f68fcfde35ad6136bb3be05ff562374f0bdede2faae93cb80a193`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- tokenizer bundle manifest SHA-256: `fb650f91bbc7f53e788a7f7c22af4950b079423229c1ef85bdd865025e56e880`

The final project holdout remains closed.

## Authorized pilot

This is a **base-domain pretraining pilot**, not instruction tuning.

| Setting | Value |
|---|---|
| Starting checkpoint | verified P2-28 step-zero initialization |
| Device | CUDA |
| Maximum optimizer updates | **100** |
| Maximum wall time | **10 minutes** |
| Micro-batch | 1 |
| Gradient accumulation | 16 |
| Sampling | `random-window-v1` |
| Objective | ordinary next-token loss |
| Answer weighting | 1 |
| Task-format fine-tuning | no |
| Validation maximum batches | 100 |
| Model architecture | unchanged 27,566,080 parameters |

The run must stop at 100 updates or 10 minutes, whichever arrives first.

No continuation beyond this run is authorized until its output is reviewed.

## Exact command

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --initialization training\artifacts\initializations\p2-28-web-v1-step0\initialization.pt `
  --output-dir pilot\p2-28-web-v1-100step `
  --minutes 10 `
  --steps 100 `
  --device cuda `
  --micro-batch 1 `
  --gradient-accumulation 16 `
  --checkpoint-every-minutes 5
```

Do not add `--dataset-dir`, `--answer-weight 4`, or a record-sampling override. Those belong to controlled task-format comparisons, not this base-pretraining pilot.

## Success criteria

This run is a pipeline/learning-behavior pilot, not a coding-capability claim.

After it finishes, review:

1. starting checkpoint identity
2. completed update count
3. validation loss before and after
4. training loss behavior
5. sampled token positions / throughput
6. checkpoint integrity and hash
7. resource stability
8. whether the result justifies a larger P2-29 domain-pretraining run

A lower validation loss is encouraging but does not, by itself, establish coding ability.

## Machine-readable records

- `training/pretraining/p2-28-initialization-result.json`
- `training/pretraining/p2-28-training-contract.json`
