# P2-29 — Matched Longer Plex Web Domain Pretraining Result

## Status

**Complete and closed.**

P2-29 replayed the exact P2-28 scratch trajectory from the same verified seed-1337 step-zero checkpoint and changed only the maximum training horizon from 100 to 500 optimizer updates.

## Provenance

- parameters: **27,566,080**
- dataset manifest SHA-256: `2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- step-zero checkpoint SHA-256: `06c27a452e2a62ed069729d2080b1d2fddb84d41bd336bbda489c066c23f8a86`
- seed: **1337**
- sampler: `random-window-v1`
- objective: ordinary next-token loss
- optimizer: AdamW, constant learning rate **0.0003**
- micro-batch: **1**
- gradient accumulation: **16**

The P2-28 step-100 checkpoint was **not** used as the starting point.

## Result

| Measure | Result |
|---|---:|
| Completed updates | **500 / 500** |
| Elapsed | **88.2446 s** |
| Token positions | **4,096,000** |
| Throughput | **46,416.45 tokens/s** |
| Recent training loss | **2.65711** |
| Validation loss before | **9.809301** |
| Validation loss after | **4.824199** |
| Interrupted | no |
| Peak GPU allocated | 832,899,584 bytes |
| Peak GPU reserved | 874,512,384 bytes |
| Process peak working set | 1,399,693,312 bytes |

Output checkpoint SHA-256:

`3b8303f8a6f56527329774b51278b93588b8383205e85bb2f594a58349acca8e`

## Training-loss trajectory

Selected logged training-loss points:

| Step | Loss |
|---:|---:|
| 1 | 9.82117 |
| 100 | 4.54003 |
| 200 | 2.91789 |
| 300 | 3.82426 |
| 400 | 2.96282 |
| 500 | 2.36454 |

The per-log-point training loss is noisy, but the overall trajectory is materially lower by step 500.

## Independent validation

The saved step-500 checkpoint was evaluated separately over 100 validation batches / 51,200 tokens.

Independent held-out loss:

**4.8241992592811584**

That exactly matches the run-reported final validation loss.

P2-28's matched step-100 endpoint was **5.6959015655517575**, so the step-500 endpoint is better on the same validation procedure.

Validation was measured at the run start and run end, not every 100 steps. Therefore P2-29 does **not** claim that held-out loss decreased monotonically throughout all 500 updates.

## Decision

P2-29 establishes that the Web-domain learning signal remained useful through the tested 500-step endpoint.

It still does not establish coding-task capability.

P2-29 is closed. The verified step-500 checkpoint becomes the base-model candidate for **P2-30 task-format fine-tuning**.

The final project holdout remains closed.
