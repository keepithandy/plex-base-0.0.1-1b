# P2-11: balanced wording transfer candidate

Status: **review-only candidate; no training approval exists and no run has started**.

## Question

Does adding balanced exposure to two previously weak request phrasings improve exact selector copying on fresh, independently held-out phrasings, under the unchanged explicit answer-start contract?

P2-10's wider read-only audit found 43/64 exact outputs. “Reproduce the selector below verbatim” scored 6/16, with answer-start skips on next-line inputs and duplicated newlines after the expected prefix. “Write this selector again, character for character” scored 5/16, with ten body-token divergences and frequent attraction to `charlie-list`. “Transcribe” and “Preserve” each scored 16/16. P2-11 deliberately promotes the 32 exact requests from those two weak P2-10 wider-evaluation templates into training. Their historical scores remain in the report, but those requests are no longer held-out for a future run. Four entirely new phrasing templates provide fresh evaluation-only requests.

## Controlled design

- Training: 96 rows; six phrasings × two layouts × eight selectors. Four phrases retain the P2-10 training matrix; two phrases add examples for the observed weak wording patterns.
- Evaluation-only: 64 rows; four new phrasings × two layouts × eight selectors. Their exact requests are disjoint from P2-10 training, original evaluation, and wider evaluation, and from P2-11 training.
- Historical holdout transition: 32 of the P2-10 wider-evaluation requests (the two low-scoring phrasings × two layouts × eight selectors) are reused as P2-11 training requests. Their P2-10 results remain historical evidence, not a clean holdout for this follow-up.
- All rows retain the P2-10 output contract: `Return exactly the requested value and nothing else. Begin the answer on a new line.`. Selector targets, model, architecture, objective, and frozen tokenizer remain fixed.
- Fresh-from-scratch seed 1337 only. Do not continue the P2-10 checkpoint.
- Require **96/96 exact supplied outputs** before interpreting held-out scores. Otherwise mark evaluation inconclusive.
- The proposed 150-update cap keeps expected uniform record exposure near P2-10's 100 updates over 64 training rows (150 × 16 / 96 ≈ 25 selections per record in expectation). The cap is a proposal, not run authorization.

## Training phrasings

| Phrase ID | Template |
|---|---|
| `return-exactly` | `Return this selector exactly: {value}` |
| `copy-unchanged` | `Copy this selector unchanged: {value}` |
| `repeat-as-shown` | `Repeat the selector exactly as shown: {value}` |
| `output-only` | `Output only the selector shown here: {value}` |
| `reproduce-selector-verbatim` | `Reproduce the selector below verbatim: {value}` |
| `write-selector-character-for-character` | `Write this selector again, character for character: {value}` |

## Fresh evaluation-only phrasings

| Phrase ID | Template |
|---|---|
| `repeat-css-selector-as-provided` | `Repeat this CSS selector exactly as provided: {value}` |
| `give-literal-selector-after-label` | `Give only the literal selector shown after this label: {value}` |
| `preserve-spelling-and-punctuation` | `Please preserve the spelling and punctuation of the selector: {value}` |
| `write-supplied-selector-unchanged` | `Write out the supplied selector unchanged: {value}` |

Each phrase is crossed with inline (`: {value}`) and next-line (`:\n{value}`) layouts and the unchanged eight selectors.

## Hashes and run boundary

- Training candidate SHA-256: `baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab`
- Evaluation-only SHA-256: `f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; refitting is false.
- Prior evidence reviewed: P2-10 candidate `ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8`, original evaluation `632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9`, wider evaluation `da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a`, checkpoint `28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb`.
- Proposed limits: 150 updates / 10 minutes, seed 1337, microbatch 1, accumulation 16, CUDA, no automatic extension.
- Evaluation approved for training: false. Evaluation approved for runtime validation loss: false. `finalHoldoutOpened`: false.
- No approval artifact exists. Training may begin only after owner approval of these exact hashes and proposed limits.

## Limits

This single-arm diagnostic is sized to preserve expected record exposure while adding phrase variety. It will not isolate phrase diversity from the larger number of unique training records and must not be described as a causal comparison. It remains a tiny selector-copy test, not evidence of general instruction understanding or coding ability.
