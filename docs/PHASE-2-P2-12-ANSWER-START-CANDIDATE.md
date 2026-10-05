# P2-12 answer-start transfer candidate

Date: 2026-10-05
Status: **review-only candidate prepared; training not approved or started**

## Why this candidate

The P2-11 read-only token audit found 9 of 11 greedy misses first diverged on the answer newline. In each of those cases the selector body began immediately, and the expected newline ranked second through fourth. Conditional on the expected newline, the period ranked first for all 64 prompts; EOS ranked first for all 64 expected complete answers. Two misses diverged in the selector body. The evidence localizes most observed errors to selecting the first answer token for those prompts, but it does not establish why the model selected that continuation.

P2-12 is designed to test whether balanced training exposure to the two P2-11 lower-scoring phrasings transfers to other fresh phrasings. It retains the existing answer-start contract, fixed selectors, layouts, model setup, objective, and tokenizer. It is a single-arm diagnostic and cannot establish a causal effect of wording changes.

## Candidate design

- Training: **96 records**, six phrase templates × two colon layouts × eight selectors. Four templates remain from the P2-10 training matrix. The two P2-11 weak evaluation phrasings replace P2-11's two extra training phrasings.
- Evaluation-only: **64 records**, four new phrasings × two layouts × eight selectors. The generator checked exact-request disjointness against P2-10 training/evaluation/wider evaluation, P2-11 training/evaluation, and P2-12 training.
- **32 exact requests** from P2-11 evaluation become P2-12 training data. Their earlier scores are historical evidence; they are no longer P2-12 holdouts.
- Output contract: `Return exactly the requested value and nothing else. Begin the answer on a new line.`
- Eight selectors and layouts remain fixed. The tokenizer is frozen; no refit.
- Proposed fresh run only: seed 1337, at most **100 updates or 10 minutes**, CUDA, microbatch 1, accumulation 16, no automatic extension. This remains a proposal, not run authorization.
- Require 96/96 exact supplied outputs before interpreting the fresh evaluation; otherwise label evaluation inconclusive.
- The final project holdout remains closed. No checkpoint was loaded, no scoring was performed, and no training approval file was created.

## Phrase matrices

### Training

| Phrase ID | Template |
|---|---|
| `return-exactly` | `Return this selector exactly: {value}` |
| `copy-unchanged` | `Copy this selector unchanged: {value}` |
| `repeat-as-shown` | `Repeat the selector exactly as shown: {value}` |
| `output-only` | `Output only the selector shown here: {value}` |
| `give-literal-selector-after-label` | `Give only the literal selector shown after this label: {value}` |
| `preserve-spelling-and-punctuation` | `Please preserve the spelling and punctuation of the selector: {value}` |

### Fresh evaluation-only

| Phrase ID | Template |
|---|---|
| `copy-selector-starting-next-line` | `Copy the selector below exactly, starting on the next line: {value}` |
| `following-line-only-selector` | `On the following line, output only this selector: {value}` |
| `selector-exactly-on-own-line` | `Put the selector exactly as written on its own line: {value}` |
| `literal-selector-on-new-line` | `Return the literal selector unchanged on a new line: {value}` |

Each template is crossed with inline (`: {value}`) and next-line (`:\n{value}`) layouts. All records use the same eight known selector targets.

## Exact identities

- Training candidate SHA-256: `bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03`
- Evaluation-only JSONL SHA-256: `d4508dab82615af616ecd176e11a6ca9c8742c2dda2ad4ddd6f337991bbe5455`
- Review Markdown SHA-256: `dcc185be9c46edbad1743239afbc30a0321adeb2770e3215155cd4fdea743e04`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`
- Source P2-11 training candidate: `baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab`
- Source P2-11 evaluation-only set: `f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322`
- Audited P2-11 checkpoint: `6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e`
- Maximum observed prompt / record including EOS / answer including EOS: 85 / 94 / 9 tokens.

The machine-readable review status is `pending-owner-review`. Evaluation is not approved for training or runtime validation loss. `modelTrained`, `trainingApprovalCreated`, and `finalHoldoutOpened` are all false in the review record.

## Artifacts

- [Candidate review](../training/phase2/drafts/p2-12-answer-start-transfer-v1/REVIEW.md)
- [Machine-readable review metadata](../training/phase2/drafts/p2-12-answer-start-transfer-v1/review.json)
- [Training candidate JSONL](../training/phase2/drafts/p2-12-answer-start-transfer-v1/candidate.jsonl)
- [Evaluation-only JSONL](../training/phase2/drafts/p2-12-answer-start-transfer-v1/evaluation-only.jsonl)
- [Deterministic candidate preparer](../training/phase2/prepare_p2_12_answer_start_candidate.py)

## Decision boundary

This package is ready for exact-record review. A training run requires separate owner approval of the candidate hash, evaluation hash, and limits above. If approved, run only the new P2-12 candidate from fresh initialization; do not continue P2-11. No run has been started by preparing this package.
