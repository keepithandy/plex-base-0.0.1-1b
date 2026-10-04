# P1-16 — Fresh Plex initialization

P1-16 created a step-zero checkpoint with fresh random Plex weights and linked it to the tokenizer produced in P1-15. No pretrained model or checkpoint was loaded, and no data was used for training.

## Recorded run

| Field | Value |
|---|---|
| Seed | 1337 |
| Initialization scheme | `plex-normal-0.02-v1` |
| Initialization device | CPU |
| Model | Decoder-only pre-layer-norm Transformer, six layers, width 512, eight heads, context 512, feed-forward width 2,048, dropout 0.1 |
| Model vocabulary capacity | 16,384 |
| Learned tokenizer vocabulary | 9,976 |
| Parameters | 27,566,080 |
| Optimizer | AdamW, learning rate 0.0003, betas (0.9, 0.95), weight decay 0.1; empty step-zero state |
| Training steps | 0 |
| Checkpoint size | 110,303,036 bytes |
| Checkpoint SHA-256 | `7a06c575ba229cfbdf758cad6ae7d0c4e504236eeba1dd90c9d531ca4689c7b4` |
| Initial model weights SHA-256 | `1311cfe1440d56da446f6d9353ec9237c3fcc76fa170b6ed34c9e692c1b408b4` |
| Tokenizer JSON SHA-256 | `76491cb4fb4e452ece1808159126ac78dc154901bd49b1d95870c0ba57ad503e` |
| Model config SHA-256 | `0179591365be51ddac2feebb8767c19916084629e9a3a51b553d1bb0d62d00b0` |

The initialization recipe is recorded in `initialization.json` and embedded in the safe, weights-only Plex checkpoint:

- Linear, embedding, and attention input projection weights: normal distribution, mean 0 and standard deviation 0.02.
- LayerNorm scales: 1. All linear, attention input projection, and LayerNorm biases: 0.
- Output projection: reuses the token embedding matrix; no separate output weights.
- Seed source: PyTorch's global CPU generator. Initialization runs on CPU with one thread for consistent seed behavior regardless of CUDA availability. The record names the Python and PyTorch versions because the seed does not promise bit-identical weights across different library versions.

## Run it again

Install/sync the locked local environment. From the repository root, choose an unused output directory; the command intentionally refuses overwrite.

```powershell
uv sync --project training --locked
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizers\p1-15-starter-v1 `
  --output-dir initializations\p1-16-my-run `
  --seed 1337
```

The result is placed under `training/artifacts/initializations/p1-16-my-run/`. It contains `initialization.pt`, `initialization.json`, and `result.json`. The checkpoint stores the step-zero model tensors, initialized AdamW state, RNG state, codec, model configuration, tokenizer hashes, initialization recipe, and seed. Its tensors are the starting weights for P1-17's learning check.

`--seed` accepts 0 through 2^63−1. `--storage-limit-gib` accepts a positive amount through the owner's 200 GiB cap; existing artifact storage counts against the remaining amount. The command creates no CUDA workload and performs no model training. The missing NumPy warning from the installed PyTorch build may appear; it did not prevent checkpoint creation. No new tests or test suites were run for P1-16.

## Next step

P1-16 is complete as initialization. P1-17 must make training/evaluation consume `plex-byte-bpe-v1`, preserve this tokenizer identity in trained checkpoints, mask unused output IDs, and show falling loss plus reproduction on a deliberately tiny real-text sample. The current general `train`, `evaluate`, and `generate` commands remain restricted to `byte-v1`; do not pass the BPE token files to them. The two-hour pilot follows P1-17.
