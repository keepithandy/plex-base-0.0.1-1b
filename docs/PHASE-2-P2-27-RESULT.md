# P2-27 — Web Tokenizer Review Result

## Status

**Complete and closed.**

P2-27 compared four fresh Plex byte-level BPE tokenizers on the frozen P2-26 corpus. Every candidate was fitted on the P2-26 **training split only**. Validation was measured after fitting and was not used to learn BPE merges.

No model weights were initialized or trained during this review. The final project holdout remained closed.

## Frozen corpus identity

Dataset manifest SHA-256:

`2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`

Tokenizer review SHA-256:

`3d462afedf7ae2bae33407f4db4f7ab6b53c2dc46c70bec891c95707a4046db8`

## Candidate results

| Requested vocab | Actual vocab | Train bytes/token | Validation bytes/token | Review-sample bytes/token | Tokenizer SHA-256 |
|---:|---:|---:|---:|---:|---|
| 4,096 | 4,096 | 3.1505327973 | 3.1660634784 | 2.7978723404 | `76c560eac7357dccd955f727dbd724f643654c04c37578994918340fb8fcadd8` |
| 8,192 | 8,192 | 3.3739972546 | 3.3952410288 | 2.9550561798 | `a669f65005a720b3673e3c4a4b32bce4d4e2b74797bd8a191ad59a39084e5303` |
| 12,288 | 12,288 | 3.4693461178 | 3.4786855497 | 3.0760233918 | `4fc23a40328a7727af6db5c9545c740a4f57b4c6fda7c408dd3a9a104ef260a3` |
| **16,384** | **16,384** | **3.5223250861** | **3.5236116328** | **3.0941176471** | **`2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`** |

Higher bytes per token means the tokenizer represents the same text with fewer tokens.

The 16,384 candidate led both informational compression measures reported by the review:

- validation compression leader: **16,384**
- representative-sample compression leader: **16,384**

The successful review command also completed the exact roundtrip checks required by the P2-27 implementation for corpus records and representative HTML/CSS/JavaScript/Plex-format samples.

## Selection

The owner selected and froze the **16,384-token candidate** for P2-28.

Frozen tokenizer SHA-256:

`2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

Local bundle path:

`training/artifacts/tokenizer-reviews/p2-27-web-v1/candidates/vocab-16384`

The selection is also recorded in:

`training/pretraining/p2-27-tokenizer-selection.json`

## Why 16,384

The selected candidate:

- achieved the best validation compression of the four candidates
- achieved the best representative HTML/CSS/JavaScript/Plex-format compression
- matched the existing Plex model vocabulary capacity exactly
- showed nearly identical train and validation bytes-per-token measurements
- requires no architecture change before the controlled 27.6M pilot

P2-27 did not automatically promote the candidate. The review output reported `automaticPromotion: false`; the final freeze is an explicit owner-reviewed decision.

## Scratch-training boundary

P2-27 preserved the scratch-training plan:

- pretrained tokenizer used for candidate fitting: **no**
- pretrained model weights loaded: **no**
- model training performed: **no**
- P2-23b checkpoint continued: **no**
- final project holdout opened: **no**

## Exit decision

P2-27 exit condition is met.

**Next:** P2-28 — Fresh 27.6M Scratch Domain-Pretraining Pilot.
