# P2-28 — Fresh 27.6M Scratch Domain-Pretraining Pilot

## Status

**Active — initialization gate only.**

P2-28 starts by creating and verifying a brand-new step-zero Plex checkpoint from random weights. This contract authorizes the initialization step only. It does **not** authorize model training yet.

The purpose of separating initialization from training is to make the scratch provenance auditable before any optimizer update occurs.

## Frozen inputs

### P2-26 corpus

Dataset directory:

`training/artifacts/datasets/p2-26-web-batch-2-v2`

Dataset manifest SHA-256:

`2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`

Corpus:

- 3,140 records
- 3,071 train
- 69 validation
- contamination gate passed
- final project holdout closed

### P2-27 tokenizer

Selected bundle:

`training/artifacts/tokenizer-reviews/p2-27-web-v1/candidates/vocab-16384`

Tokenizer SHA-256:

`2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

Tokenizer review SHA-256:

`3d462afedf7ae2bae33407f4db4f7ab6b53c2dc46c70bec891c95707a4046db8`

Requested and actual vocabulary size: **16,384**.

The tokenizer was fitted on the P2-26 training split only.

## Exact model configuration

P2-28 keeps the existing Plex Nano architecture unchanged:

| Field | Value |
|---|---:|
| Parameters | **27,566,080** |
| Vocabulary capacity | 16,384 |
| Context length | 512 |
| Model width | 512 |
| Transformer layers | 6 |
| Attention heads | 8 |
| Feed-forward width | 2,048 |
| Dropout | 0.1 |

No model-size increase is allowed inside this pilot.

## Fresh-random-initialization contract

The P2-28 step-zero checkpoint must satisfy all of the following:

1. **Seed:** 1337.
2. **Initialization device:** CPU.
3. **Initialization thread count:** 1.
4. **Model family:** `plex-from-scratch`.
5. **Purpose:** `fresh-random-initialization`.
6. **Parameter count:** exactly 27,566,080.
7. **Tokenizer:** exact frozen P2-27 16,384-token bundle.
8. **Pretrained checkpoint loaded:** false.
9. **Pretrained model weights loaded:** false.
10. **Resume checkpoint:** none.
11. **Training step:** zero.
12. Record both the initial model-weights SHA-256 and checkpoint SHA-256.
13. The final project holdout remains closed.

The existing Plex `initialize` implementation already creates the model on CPU from the configured random initialization scheme and records the required scratch-provenance fields. P2-28 binds that mechanism to the frozen P2-27 tokenizer.

## Explicitly forbidden starting points

P2-28 must **not** start from:

- P2-23b
- any P1 pilot checkpoint
- any earlier Plex trained checkpoint
- Qwen weights
- Llama weights
- GPT weights
- any other third-party pretrained model weights

Existing checkpoints may later be used as historical evaluation references only. They are not initialization sources.

## Authorized initialization command

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --output-dir initializations\p2-28-web-v1-step0 `
  --seed 1337
```

Expected output location:

`training/artifacts/initializations/p2-28-web-v1-step0`

## Required evidence before training can open

The initialization output must be reviewed and recorded before any P2-28 optimizer update is authorized.

At minimum it must report:

- `parameterCount: 27566080`
- `actualTokenizerVocabularySize: 16384`
- `seed: 1337`
- `pretrainedCheckpointLoaded: false`
- a nonempty `checkpointSha256`
- a nonempty `initialModelWeightsSha256`

The tokenizer bundle must remain internally tied to the frozen P2-26 dataset manifest.

If any identity or required field differs, stop P2-28 and investigate rather than training.

## Training authorization

**Not yet authorized by this contract.**

After the step-zero output is verified, P2-28 will record that initialization and freeze the bounded pilot-training parameters separately. That prevents accidental continuation, unreviewed hyperparameter drift, or training from the wrong tokenizer/checkpoint.

## Scratch meaning

Plex remains scratch-trained because P2-28 begins from newly generated random model weights. The permissively licensed HTML/CSS/JavaScript corpus and the fresh Plex tokenizer are training inputs; they are not pretrained model weights.

## Machine-readable contract

See:

`training/pretraining/p2-28-scratch-pilot-contract.json`
