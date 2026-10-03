# Plex first experiment (P1-12)

Status: **configuration proposed; measured resource fit pending the P1-13 training runner**. This experiment is a small from-scratch training pilot, not a claim of useful coding ability. Do not load pretrained weights.

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
| Estimated parameter count | 27,566,080 (about 27.6 million) |

The count assumes standard biased Q/K/V and output projections, two biased feed-forward projections per block, LayerNorm scale/bias parameters, learned token and positional embeddings, a final LayerNorm, and tied token input/output embeddings. It is an architectural estimate; P1-13 must report the instantiated count and fail if it differs without an intentional documented change.

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
| Initialization | Random; exact scheme and seed recorded in P1-16 |

The 10-minute smoke test uses generated deterministic token sequences, needs no download, and measures that forward/backward training runs while reporting elapsed time, tokens per second, peak VRAM, and peak system RAM. It checks runtime and resource use only; the separate P1-17 tiny-sample test proves the model can learn.

After the smoke test fits safely, the two-hour pilot uses only a local, documented dataset after P1-14 prepares it. The pilot records training and validation loss, processed tokens, throughput, and peak memory. P1-19 separately verifies checkpoint resumption; pass that gate before any run longer than the two-hour pilot. The pilot cannot establish general coding skill.

Longer runs may continue without a fixed wall-clock cap only after the smoke test and pilot pass and P1-19 verifies that a checkpoint can resume training. They must save resumable checkpoints and progress logs. Any storage use counts against the owner's 200 GiB Plex allocation. No paid dataset, API, or cloud GPU is in scope under the $0 paid-services budget.

## Resource estimate and measurement gate

At 27,566,080 parameters, FP32 model weights use about 105 MiB and gradients about 105 MiB. AdamW's two FP32 moment buffers add about 210 MiB, for roughly **420 MiB of parameter, gradient, and optimizer state**. This excludes activations, CUDA context/workspaces, allocator overhead, and data buffers, which can raise peak usage substantially. This is not a total VRAM prediction.

The supplied snapshot reported 16,376 MiB total GPU memory and 14,532 MiB free at collection time, plus 31.7 GiB system RAM. Available VRAM varies with other applications. P1-13 must measure on the user's Windows machine and record peak allocated/reserved VRAM, system RAM, tokens per second, and any out-of-memory errors. Start with the proposed micro-batch of one; change settings only from measured results and record each change.

Do not proceed from the two-hour pilot to longer training if the process exceeds the 200 GiB allocation, destabilizes the machine, fails to save and resume a checkpoint, or shows no useful validation progress. Set the final stop rule and checkpoint cadence in the training runner before authorizing a longer run.

## Dependencies and open decisions

- No Python environment or ML framework has been installed for this milestone. P1-13 introduces and records the local training toolchain.
- The tokenizer, data sources, and validation split are defined by P1-14 and P1-15; no dataset download is part of P1-12.
- The exact random initialization scheme and seed are recorded in P1-16.
- CPU inference memory and latency targets remain separate and unmeasured; test them after a Plex checkpoint exists.
