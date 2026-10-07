# P2-26 — Plex Web Corpus v1 Closeout

## Status

**Complete.**

P2-26 produced the first Plex Web corpus candidate large enough for tokenizer review and passed the required provenance, filtering, split, syntax, and contamination gates.

No model pretraining occurred in P2-26. The final project holdout remained closed.

## Frozen local corpus candidate

The accepted P2-26 batch #2 source set was built with the verifier-locked `web-dataset-build` path.

| Field | Result |
|---|---:|
| Web-preflight accepted files | 3,142 |
| Web-preflight accepted normalized bytes | 5,463,479 |
| Final dataset records | 3,140 |
| Train records | 3,071 |
| Validation records | 69 |
| JavaScript syntax rejects after preflight | 2 |
| Final dataset artifact bytes | 6,777,606 |
| Dataset manifest SHA-256 | `2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91` |

The accepted source-byte total is about 5.21 MiB, inside the predeclared 4–6 MiB P2-26 byte-scale target.

## Source policy result

The batch #2 Web preflight reported:

- 1,625 HTML files
- 624 CSS files
- 893 JavaScript files
- 156 exact duplicates removed
- 6 disallowed-suffix files rejected
- 4 minified files rejected
- 6 secret-pattern files rejected
- 13 empty files rejected
- 1 too-short file rejected
- `readyForDeterministicBuild: true`

The final Web-specific build then rejected two additional JavaScript files for invalid syntax. Web-policy-rejected paths were not allowed back into the final v2 corpus.

## Build-parity correction

The first generic batch #2 dataset build exposed a policy mismatch:

- Web verifier: 3,142 accepted files
- generic dataset builder: 3,150 records
- 6 disallowed-suffix files and 4 minified files had been reintroduced
- 2 invalid JavaScript files were independently removed by the dataset builder

That v1 corpus is not the P2-26 promotion candidate.

P2-26 added `web-dataset-build`, which first captures the exact path set accepted by `web-source-verify`, then permits the dataset builder to consume only those paths. The dataset stage may remove additional syntax-invalid files, but it cannot reintroduce a Web-policy rejection.

The corrected v2 corpus contains 3,140 records.

## Contamination gate

The corrected v2 corpus passed `web-contamination-check`:

| Check | Result |
|---|---:|
| Records scanned | 3,140 |
| Protected files scanned | 533 |
| Protected segments scanned | 567 |
| Blocked source-origin matches | 0 |
| Exact protected-content matches | 0 |
| Long substring matches | 0 |
| Minimum substring length | 120 characters |
| Passed | **true** |

The contamination report is tied to dataset manifest SHA-256:

`2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91`

The final project holdout remained:

`closed-not-addressable; remains outside pretraining and is not opened by this checker`

## Scratch-training boundary

P2-26 curated data only.

It did **not**:

- load pretrained Qwen, Llama, GPT, or other model weights
- continue the P2-23b checkpoint
- initialize the P2-28 model
- train the 27.6M model
- open the final project holdout

P2-28 remains planned as a fresh random initialization of the 27,566,080-parameter Plex architecture after P2-27 freezes the tokenizer.

## Exit decision

P2-26 exit condition is met:

> A reproducible, provenance-complete, contamination-clean Plex Web corpus candidate reaches the first-scale target and is ready for tokenizer review.

**Next:** P2-27 — Web Tokenizer Review.
