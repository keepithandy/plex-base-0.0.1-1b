# Plex first experiment (P1-12)

Status: **configuration defined; ten-minute CUDA resource-fit test passed on the owner's Windows machine; real-data pilot pending**. The P1-13 runner's original 13 tests passed using Python 3.12.10 and PyTorch 2.14.0+cu126; CUDA 12.6 detected the RTX 4080 SUPER. The [smoke result](SMOKE-TEST-2026-10-03.md) records 4,199 steps, 734 MiB peak GPU reservation, and about 1.30 GiB process peak RAM. The runner is in [`../training/`](../training/README.md). This experiment is a small from-scratch training pilot, not a claim of useful coding ability. Do not load pretrained weights.

## Model configuration

| Setting | Initial proposal |
|---|---:|
| Architecture | Decoder-only causal Transformer, pre-layer normalization |
| Transformer blocks | 6 |
| Hidden width | 512 |
| Attention heads | 8 (64 dimensions per head) |
| Feed-forward width | 2,048 (4× hidden width) |
| Maximum context | 512 tokens |
| Vocabulary capacity | 16,384 tokens; P1-15 will train a tokenizer to this size with byte fallback |
| Position representation | Learned positional embeddings |
| Input/output token embeddings | Tied |
| Activation | GELU |
| Dropout | 0.1 during training |
| Instantiated parameter count | 27,566,080 (about 27.6 million), confirmed by the smoke start event |

The count assumes standard biased Q/K/V and output projections, two biased feed-forward projections per block, LayerNorm scale/bias parameters, learned token and positional embeddings, a final LayerNorm, and tied token input/output embeddings. The observed instantiated count matches this architectural estimate. The runner fails if it differs without an intentional documented change.

This model is about 18 times smaller than the low end of the eventual 0.5B–1.5B target. Its purpose is to make the training path small enough to debug and measure.

## Training settings

| Setting | Initial proposal |
|---|---:|
| Precision | FP32 for the first reproducible run |
| Optimizer | AdamW |
| Learning rate | 3e-4 |
| Adam betas | (0.9, 0.95) |
| Weight decay | 0.1 |
| Gradient clipping | Global norm 1.0 |
| Micro-batch | 1 sequence |
| Gradient accumulation | 16 steps (effective batch: 16 sequences / 8,192 token positions) |
| Initialization | Fresh CPU initialization, scheme `plex-normal-0.02-v1`, seed 1337; see [P1-16 initialization record](PLEX-INITIALIZATION.md) |

The 10-minute smoke test uses generated deterministic token sequences, needs no dataset download, and measures that forward/backward training runs while reporting elapsed time, tokens per second, peak VRAM, and peak system RAM. The owner completed it successfully; its settings, raw result, and interpretation are in [SMOKE-TEST-2026-10-03.md](SMOKE-TEST-2026-10-03.md). It checks runtime and resource use only; the separate P1-17 tiny-sample test checks reproduction of a real text sample.

After the smoke test fits safely, the two-hour pilot uses only a local, documented dataset after P1-14 prepares it. The pilot records training and validation loss, processed tokens, throughput, and peak memory. P1-19 separately verifies checkpoint resumption; pass that gate before any run longer than the two-hour pilot. The pilot cannot establish general coding skill.

Longer runs may continue without a fixed wall-clock cap only after the smoke test and pilot pass and P1-19 verifies that a checkpoint can resume training. They must save resumable checkpoints and progress logs. Any storage use counts against the owner's 200 GiB Plex allocation. No paid dataset, API, or cloud GPU is in scope under the $0 paid-services budget.

## Resource estimate and measurement gate

At 27,566,080 parameters, FP32 model weights use about 105 MiB and gradients about 105 MiB. AdamW's two FP32 moment buffers add about 210 MiB, for roughly **420 MiB of parameter, gradient, and optimizer state**. This excludes activations, CUDA context/workspaces, allocator overhead, and data buffers, which can raise peak usage substantially. This is not a total VRAM prediction.

The supplied snapshot reported 16,376 MiB total GPU memory and 14,532 MiB free at collection time, plus 31.7 GiB system RAM. Available VRAM varies with other applications. P1-13 must measure on the user's Windows machine and record peak allocated/reserved VRAM, system RAM, tokens per second, and any out-of-memory errors. Start with the proposed micro-batch of one; change settings only from measured results and record each change.

Do not proceed from the two-hour pilot to longer training if the process exceeds the 200 GiB allocation, destabilizes the machine, fails to save and resume a checkpoint, or shows no useful validation progress. Set the final stop rule and checkpoint cadence in the training runner before authorizing a longer run.

## Dependencies and open decisions

- The P1-13 project pins Python 3.12 and PyTorch 2.14.0 with CUDA 12.6. The owner resolved the environment on Windows; the reported runtime is Python 3.12.10, PyTorch 2.14.0+cu126, and CUDA 12.6. The original 13 tests and ten-minute CUDA smoke test passed. P1-18's one-step real-data preflight measured held-out loss and throughput; the two-hour outcome remains unmeasured.
- The tokenizer, data sources, and validation split are defined by P1-14 and P1-15; no dataset download is part of P1-12.
- P1-16 created a 27,566,080-parameter step-zero initialization checkpoint with seed 1337, scheme `plex-normal-0.02-v1`, and the P1-15 tokenizer identity. Its initial weights hash is recorded in [PLEX-INITIALIZATION.md](PLEX-INITIALIZATION.md). No pretrained checkpoint was loaded.
- P1-17 overfit a 16-token sample from one approved training record in 250 steps, with loss decreasing from 9.438 to 0.0000224 and exact greedy reproduction from a two-token prompt. See [PLEX-LEARNING-CHECK.md](PLEX-LEARNING-CHECK.md). This is only a training-path check; held-out validation in the two-hour P1-18 pilot remains necessary.
- The [P1-18 pilot preparation](PLEX-PILOT.md) validates BPE train/held-out splits, ran one full-corpus preflight update, and independently re-evaluated its checkpoint. The final two-hour pilot is still pending.
- CPU inference memory and latency targets remain separate and unmeasured; test them after a Plex checkpoint exists.
