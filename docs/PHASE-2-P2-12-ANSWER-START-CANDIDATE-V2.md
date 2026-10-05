# P2-12 answer-start transfer candidate — evaluation v2

Date: 2026-10-05
Status: **revised review-only package; training not approved or started**

## Revision

This version keeps the P2-12 training JSONL byte-for-byte identical to v1 and revises only the fresh evaluation wording. Two evaluation templates explicitly cue a new line; two ask for an exact or repeated copy without adding another line-break cue. Every record still carries the unchanged output contract, which says to begin the answer on a new line. This gives a more balanced descriptive read on whether performance depends on the phrase itself repeating the line-break instruction.

P2-11's token audit found 9/11 greedy misses first diverged at answer newline. The expected period ranked first on all 64 prompts when the newline was supplied. P2-12 remains a single-arm diagnostic: its result describes this candidate on these prompts and cannot establish that training caused an improvement.

## Candidate design

- Training: **96 records**, six phrasings × two colon layouts × eight selectors. The rows are unchanged from P2-12 v1.
- Evaluation-only: **64 records**, four fresh phrasings × two layouts × eight selectors, with two explicit-newline and two neutral-copy phrasings.
- The evaluation JSONL is disjoint from all P2-10 training/evaluation/wider-evaluation and P2-11 training/evaluation requests, and from P2-12 training requests.
- The 32 exact requests promoted from P2-11 evaluation remain P2-12 training data. Their old results are historical, not P2-12 holdout results.
- Output contract, eight selectors, layouts, model setup, objective, and frozen tokenizer remain fixed. The tokenizer is not refit.
- Proposed fresh run only: seed 1337, at most **100 updates or 10 minutes**, CUDA, microbatch 1, accumulation 16, no automatic extension. This is not run authorization.
- Require 96/96 exact supplied outputs before interpreting held-out evaluation; otherwise mark the evaluation inconclusive.
- No checkpoint was loaded, no scoring or training was performed, and no approval file was created. The final project holdout remains closed.

## Evaluation phrasings

| Cue type | Phrase ID | Template |
|---|---|---|
| Explicit line break | `copy-selector-starting-next-line` | `Copy the selector below exactly, starting on the next line: {value}` |
| Explicit line break | `selector-exactly-on-own-line` | `Put the selector exactly as written on its own line: {value}` |
| Neutral copy | `send-exact-selector-copy` | `Send back an exact copy of the selector: {value}` |
| Neutral copy | `supply-same-selector-again` | `Supply the same selector again: {value}` |

Each template is crossed with inline (`: {value}`) and next-line (`:\n{value}`) input layouts and all eight selectors.

## Exact identities

- Training candidate SHA-256 (unchanged from v1): `bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03`
- Revised evaluation-only SHA-256: `a81b05aa3452d9b04d9f9b4d6b1a0d0e8ebf2614c3de24c0c4083eb975629fb7`
- Review Markdown SHA-256: `9040f6513a7d0fd2a722813d1bf8fa9c2bc50b9c07e37c3bf0419cec2f113a77`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`
- Source P2-11 training candidate: `baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab`
- Source P2-11 evaluation-only set: `f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322`
- Audited P2-11 checkpoint: `6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e`
- Maximum prompt / record including EOS / answer including EOS: 85 / 94 / 9 tokens.

The machine-readable review status is `pending-owner-review`. Evaluation is not approved for training or runtime validation loss. `modelTrained`, `trainingApprovalCreated`, and `finalHoldoutOpened` are false.

## Artifacts

- [Candidate review](../training/phase2/drafts/p2-12-answer-start-transfer-v2/REVIEW.md)
- [Machine-readable review metadata](../training/phase2/drafts/p2-12-answer-start-transfer-v2/review.json)
- [Training candidate JSONL](../training/phase2/drafts/p2-12-answer-start-transfer-v2/candidate.jsonl)
- [Revised evaluation-only JSONL](../training/phase2/drafts/p2-12-answer-start-transfer-v2/evaluation-only.jsonl)
- [Deterministic v2 preparer](../training/phase2/prepare_p2_12_answer_start_candidate_v2.py)
- [Original v1 package and rationale](PHASE-2-P2-12-ANSWER-START-CANDIDATE.md)

## Decision boundary

This revision is ready for exact-record review. Any training requires separate owner approval of the v2 package, the training and evaluation hashes, and the proposed limits. If approved, use fresh initialization and do not continue the P2-11 checkpoint.
