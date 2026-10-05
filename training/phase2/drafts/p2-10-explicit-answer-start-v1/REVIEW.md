# P2-10: explicit answer-start cue

Status: **pending owner review**. This stage prepares deterministic files only. It does not create a training approval or train a model.

## Question

Does explicitly telling Plex to begin its answer on a new line improve selector-copy output under held-out wording, compared with P2-08?

P2-08 learned 63/64 supplied prompts, below the 64/64 convergence gate. Its 4/16 held-out score is formally inconclusive. A read-only teacher-forced audit found the expected newline token ranked first on 6/16 held-out prompts; the period token ranked first on all 16 once the expected newline was supplied. P2-10 changes only the output contract to cue the answer start explicitly.

## Controlled design

- Training: 64 rows; four known phrasings × two known input layouts × eight selectors.
- Evaluation-only: 16 rows; the same held-out wording, layouts, and eight selector values as P2-08.
- Output contract for every row: `Return exactly the requested value and nothing else. Begin the answer on a new line.`
- Compared with P2-08, selector values, requests, targets, phrase/layout assignments, frozen tokenizer, architecture, and proposed run settings are held fixed. Only the output contract is changed.
- Require 64/64 exact supplied outputs before interpreting the 16 held-out outputs. If training does not converge, report evaluation as inconclusive.
- This remains a tiny selector-copy diagnostic, not evidence of general instruction understanding or coding ability.

## Phrasing matrix

| Phrase ID | Request template |
|---|---|
| `return-exactly` | `Return this selector exactly: {value}` |
| `copy-unchanged` | `Copy this selector unchanged: {value}` |
| `repeat-as-shown` | `Repeat the selector exactly as shown: {value}` |
| `output-only` | `Output only the selector shown here: {value}` |

Each phrase uses both layouts: inline (`: {value}`) and the selector on the following line (colon, then a line break, then `{value}`).

Held-out wording: `give-back-no-changes` — `Give back this selector with no changes: {value}`

## Approval and safety boundary

- Candidate SHA-256: `ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8`
- Evaluation-only SHA-256: `632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; tokenizer refitting is false.
- Proposed fresh-run limits (not approved): 100 updates / 10 minutes, seed 1337, microbatch 1, accumulation 16, CUDA, no automatic extension.
- Training examples remain `pending-owner-review`; evaluation examples remain `evaluation-only-never-train`.
- No approval artifact exists. No training has run. `finalHoldoutOpened` is false.
- Training may begin only after the owner approves these exact train/evaluation hashes and the proposed bounds.

## Token limits

Maximum prompt / complete-record-with-EOS / answer-with-EOS lengths: 78 / 87 / 9 tokens.
