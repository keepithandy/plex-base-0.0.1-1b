# P2-28 — First Plex Web Scratch-Pretraining Result

## Status

**Complete and closed.**

P2-28 successfully proved that the fresh 27,566,080-parameter Plex Nano can learn from the frozen Plex Web corpus while preserving the scratch-training provenance chain.

## Frozen identities

- dataset manifest SHA-256: `2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- step-zero checkpoint SHA-256: `06c27a452e2a62ed069729d2080b1d2fddb84d41bd336bbda489c066c23f8a86`
- initial model weights SHA-256: `98785d70ee7f68fcfde35ad6136bb3be05ff562374f0bdede2faae93cb80a193`

## Run

The authorized pilot completed all **100 / 100 optimizer steps** on CUDA.

| Measure | Result |
|---|---:|
| Elapsed time | 17.4753 s |
| Token positions processed | 819,200 |
| Throughput | 46,877.65 tokens/s |
| Recent training loss | 4.49267 |
| Validation loss before | 9.809301 |
| Validation loss after | **5.695902** |
| Interrupted | no |
| Peak GPU allocated | 832,899,584 bytes |
| Peak GPU reserved | 874,512,384 bytes |
| Process peak working set | 1,400,102,912 bytes |

The output checkpoint SHA-256 is:

`cd62c66612c2e7c2c95167da6932ecae5ef622c5a62973ba11cce3d99f75cf87`

## Independent held-out verification

The saved step-100 checkpoint was independently evaluated over 100 validation batches / 51,200 validation tokens.

Reproduced held-out mean loss:

**5.6959015655517575**

This exactly matched the loss reported by the training run.

That establishes checkpoint/evaluation consistency for this pilot.

## Interpretation

P2-28 establishes:

- the fresh random initialization is trainable
- the frozen Plex Web corpus and tokenizer integrate correctly
- the model shows a strong early held-out next-token learning signal
- the CUDA training path is stable at this scale
- checkpoint provenance and independent evaluation agree

P2-28 does **not** establish:

- reliable coding ability
- repository-editing ability
- instruction-following capability
- final-holdout performance
- that longer training will continue improving validation

The final project holdout remained closed.

## Decision

The result justifies a longer matched domain-pretraining trajectory.

**Next:** P2-29 — matched 500-step Plex Web domain-pretraining run from the same verified step-zero initialization.
