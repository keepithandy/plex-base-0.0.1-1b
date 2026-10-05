# P2-12: answer-start transfer candidate

Status: **review-only candidate; no training approval exists and no run has started**.

## Question

Does balanced exposure to the two P2-11 phrasings with answer-start misses improve exact copying on four fresh phrasings, under the unchanged explicit answer-start contract?

The P2-11 read-only audit found 9 of 11 greedy misses first diverged at the answer newline. In those cases, the body token was selected immediately and the expected newline ranked second through fourth. Given the expected newline, the expected period ranked first on all 64 prompts, and EOS ranked first on all 64 expected complete answers. Two further misses occurred in selector-body choice. This points to the prompt-conditioned answer start as the main observed failure location; it does not establish a causal explanation for the model's choice.

## Controlled design

- Training: 96 rows; six phrasings × two layouts × eight fixed selectors. The four original P2-10 training phrasings remain; the two P2-11 lower-scoring evaluation phrasings replace the two P2-11 added training phrasings, keeping row count and selector/layout coverage fixed.
- Evaluation-only: 64 rows; four entirely fresh phrasings × two layouts × eight selectors. Requests are disjoint from P2-10 training, original and wider evaluation, P2-11 training and evaluation, and P2-12 training.
- Historical holdout transition: 32 exact requests from the weak P2-11 evaluation templates are now training data; their old scores are historical evidence, not clean P2-12 holdout evidence.
- All rows retain the P2-10 output contract: `Return exactly the requested value and nothing else. Begin the answer on a new line.`. The eight selector targets, two colon layouts, model, architecture, objective, and frozen tokenizer remain fixed.
- Fresh-from-scratch seed 1337 only; do not continue the P2-11 checkpoint. Require **96/96 exact supplied outputs** before interpreting evaluation. Otherwise evaluation is inconclusive.
- Proposed ceiling is 100 updates or 10 minutes, whichever comes first. Expected uniform record exposure is about 100 × 16 / 96 ≈ 16.7 presentations per record. The ceiling is a proposal, not run authorization; the shared complete-record framework caps at 100 updates.

## Training phrasings

| Phrase ID | Template |
|---|---|
| `return-exactly` | `Return this selector exactly: {value}` |
| `copy-unchanged` | `Copy this selector unchanged: {value}` |
| `repeat-as-shown` | `Repeat the selector exactly as shown: {value}` |
| `output-only` | `Output only the selector shown here: {value}` |
| `give-literal-selector-after-label` | `Give only the literal selector shown after this label: {value}` |
| `preserve-spelling-and-punctuation` | `Please preserve the spelling and punctuation of the selector: {value}` |

## Fresh evaluation-only phrasings

| Phrase ID | Template |
|---|---|
| `copy-selector-starting-next-line` | `Copy the selector below exactly, starting on the next line: {value}` |
| `following-line-only-selector` | `On the following line, output only this selector: {value}` |
| `selector-exactly-on-own-line` | `Put the selector exactly as written on its own line: {value}` |
| `literal-selector-on-new-line` | `Return the literal selector unchanged on a new line: {value}` |

Each phrase is crossed with inline (`: {value}`) and next-line (`:
{value}`) layouts and all eight known selectors.

## Hashes and run boundary

- Training candidate SHA-256: `bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03`
- Evaluation-only SHA-256: `d4508dab82615af616ecd176e11a6ca9c8742c2dda2ad4ddd6f337991bbe5455`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; refitting is false.
- Prior evidence: P2-10 candidate `ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8`, original evaluation `632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9`, wider evaluation `da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a`, P2-10 checkpoint `28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb`; P2-11 candidate `baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab`, evaluation `f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322`, checkpoint `6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e`.
- Proposed limits: 100 updates / 10 minutes, seed 1337, microbatch 1, accumulation 16, CUDA, no automatic extension.
- Evaluation approved for training: false. Evaluation approved for runtime validation loss: false. `finalHoldoutOpened`: false.
- No approval artifact exists. Training requires owner approval of these exact hashes and limits. Do not extend a prior run.

## Limits

This is a single-arm diagnostic. It changes the training wording mix and promotes 32 previously evaluated requests, so it cannot isolate phrase effects causally. Small repeated-selector cells are descriptive, not evidence of general instruction understanding or coding ability.
