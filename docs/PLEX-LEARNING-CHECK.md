# P1-17 — Tiny real-text learning check

P1-17's one-record learning check succeeded. The model started from the recorded P1-16 random initialization checkpoint and trained on 16 BPE tokens from one approved training record. From a two-token prompt, greedy decoding reproduced all 16 tokens exactly.

| Measurement | Result |
|---|---:|
| Training steps | 250 |
| Duration | 5.658 seconds |
| Initial next-token loss | 9.437925 |
| Final next-token loss | 0.00002242 |
| Initial token accuracy | 0% |
| Final token accuracy | 100% |
| Reproduced from a two-token prompt | Yes, all 16 tokens |
| Initialization seed | 1337 |
| Model parameters | 27,566,080 |
| Tokenizer vocabulary / model capacity | 9,976 / 16,384 |
| Selected runtime device | CUDA |
| Trained checkpoint | 330,897,243 bytes, including optimizer state |
| Trained checkpoint SHA-256 | `f4dea4a78ebb600766759a1ed3771b130707665c78dbb67a40a923bea93f4305` |
| Starting P1-16 checkpoint SHA-256 | `7a06c575ba229cfbdf758cad6ae7d0c4e504236eeba1dd90c9d531ca4689c7b4` |
| Sample text SHA-256 | `1eb9fc2a228eb395d47e283e4cc8f015abca6457ecb2b0d6bb0eb9cb89507b41` |
| Tokenizer SHA-256 | `76491cb4fb4e452ece1808159126ac78dc154901bd49b1d95870c0ba57ad503e` |

The selected device is the device available to the process that ran this command. It is not a new inventory of the owner's hardware. The generated report at `training/artifacts/learning/p1-17-tiny-v1/learning-report.json` preserves the complete record, including the source record ID, expected/generated token IDs, exact loss values, and tokenizer identity. The checkpoint is at `training/artifacts/learning/p1-17-tiny-v1/tiny-learning.pt`. Both generated files are ignored by Git and count against the 200 GiB artifact allocation.

## What this establishes

The new `learn-check` path loads the P1-16 checkpoint, validates its model and tokenizer identity, slices loss and generation to the learned tokenizer vocabulary, and trains using the real `plex-byte-bpe-v1` sample. The generated checkpoint preserves the optimizer state, RNG state, initialization record, tokenizer hashes, and progress step. The command caps the check at 500 optimizer steps and ten minutes. No test suite was added or run for P1-17; this bounded learning experiment is the milestone demonstration.

This sample came from the training split and was intentionally reused 250 times. Its low final loss and exact reproduction show that the weights can memorize a short sequence and that gradient updates work. They do not establish generalization, coding ability, held-out performance, or useful inference.

## Reproduce

From the repository root, use the existing P1-15 tokenizer and P1-16 initialization. The output directory must be unused.

```powershell
uv sync --project training --locked
uv run --project training --no-sync python -m plex_training.cli learn-check `
  --initialization training\artifacts\initializations\p1-16-starter-v1\initialization.pt `
  --tokenizer-dir training\artifacts\tokenizers\p1-15-starter-v1 `
  --train-tokens training\artifacts\tokenizers\p1-15-starter-v1\train.tokens.u16le `
  --train-index training\artifacts\tokenizers\p1-15-starter-v1\train.index.json `
  --output-dir learning\p1-17-my-run `
  --steps 250 --sample-tokens 16 --minutes 10 --device auto
```

The command selects one short indexed training record, strips its record-ending EOS token, uses the first 16 ordinary tokens, and reserves the first two as the prompt. It measures teacher-forced loss and accuracy before and after training, then greedily generates the continuation. It saves a new checkpoint and JSON report. It does not read the validation split or claim that the held-out records improve.

## Next milestone

P1-17 is complete for this one-sample learning check. P1-18's bounded BPE training/evaluation path has since been prepared and passed a one-step preflight; see the [pilot preparation report](PLEX-PILOT.md). The general `train`, `evaluate`, and `generate` commands remain on the bootstrap byte-v1 format. P1-19 still needs to prove tokenizer-aware checkpoint resumption and generation before runs longer than the two-hour pilot.
