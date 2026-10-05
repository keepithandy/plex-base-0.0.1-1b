# P2-12 v2 answer-start transfer run

Date: 2026-10-05

Status: **approved run and held-out score complete; training convergence gate not met**

## Result

The fresh seed-1337 CUDA run stopped normally at the approved 100-update cap after 15.68 seconds. It exactly reproduced **92/96 training records**, below the predeclared 96/96 convergence gate. The held-out evaluation score of **53/64 is therefore descriptive and formally inconclusive** under the approved protocol. No extension or second run was attempted.

| Fresh evaluation phrasing | Inline | Next-line | Total |
|---|---:|---:|---:|
| Copy the selector below exactly, starting on the next line | 8/8 | 8/8 | 16/16 |
| Put the selector exactly as written on its own line | 6/8 | 5/8 | 11/16 |
| Send back an exact copy of the selector | 8/8 | 8/8 | 16/16 |
| Supply the same selector again | 8/8 | 2/8 | 10/16 |
| **Total** | **30/32** | **23/32** | **53/64** |

The two explicit-newline templates scored 27/32 together; the two neutral-copy templates scored 26/32. That aggregate hides substantial phrase/layout variation: “starting on the next line” and “send back an exact copy” were 16/16, while “on its own line” was 11/16 and “supply the same selector again” fell to 2/8 on next-line input. Inline prompts scored 30/32 versus 23/32 for next-line inputs.

All 64 outputs emitted EOS, but only 53 began with the expected answer newline; those same 53 were exact. All 11 misses skipped the answer newline. Ten then emitted the selector body without its leading period; one emitted `bravo` followed by a newline and `.bravo-item`. This is a saved-output observation; no teacher-forced token-rank audit was run in this step.

Training phrase/layout scores were:

| Training phrasing | Inline | Next-line | Total |
|---|---:|---:|---:|
| Return this selector exactly | 8/8 | 8/8 | 16/16 |
| Copy this selector unchanged | 8/8 | 8/8 | 16/16 |
| Repeat the selector exactly as shown | 8/8 | 5/8 | 13/16 |
| Output only the selector shown here | 8/8 | 8/8 | 16/16 |
| Give only the literal selector shown after this label | 8/8 | 7/8 | 15/16 |
| Please preserve the spelling and punctuation of the selector | 8/8 | 8/8 | 16/16 |
| **Total** | **48/48** | **44/48** | **92/96** |

Validation loss on the separate existing P2 request-following v3 validation split rose from **7.4502** to **9.4304**. The evaluation-only set was excluded from training and runtime validation loss. The loss is separate telemetry, not a coding-task score.

## Exact run identity and bounds

- Training candidate SHA-256: `bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03`
- Evaluation-only SHA-256: `a81b05aa3452d9b04d9f9b4d6b1a0d0e8ebf2614c3de24c0c4083eb975629fb7`
- Review Markdown SHA-256: `9040f6513a7d0fd2a722813d1bf8fa9c2bc50b9c07e37c3bf0419cec2f113a77`
- Approval record: [P2-12 v2 run approval](../training/phase2/approvals/p2-12-answer-start-transfer-v2.json)
- Approval record SHA-256: `73d03a37a71f1f6835e09ecae3d7b9a25ad37ed4d10625a1171f323728bddee4`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; no refit.
- Fresh initialization seed: 1337; no trained checkpoint was continued.
- Approved and actual cap: 100 updates / 10 minutes; actual: 100 updates in 15.68 seconds. Automatic extension: false.
- Initial weights SHA-256: `9095d27bfe7e3c986cca2207937cafd428b1f723970df52714aa55fb55522002`.
- Trained checkpoint SHA-256: `6379f217ea06ad97db631b5c6149159a31b950c96994d486f7b28878e0751fb4`.
- Runtime validation loss: 7.4502 → 9.4304 on the existing 78-record validation split.
- Final project holdout opened: false. Training/evaluation approval did not permit using the evaluation set for training or runtime validation loss.

## Interpretation and next step

The convergence condition failed, so the held-out score cannot support the intended post-convergence interpretation. The descriptive misses still align with the P2-11 pattern: first answer newline is skipped on every incorrect evaluation output, with downstream loss of the leading period. The balanced cue mix did not remove phrase sensitivity; two phrasings are perfect, while two remain weaker, particularly on next-line input. This one fresh run does not show that P2-12 improved performance relative to another training design, and it is not evidence of broad instruction-following or coding ability.

The next useful step is a **read-only audit of the saved token paths for the 11 evaluation misses**, grouped by phrasing and layout. Do not extend this run or start another run from this result. Any further training requires a new candidate (if the data or limits change) and separate approval of its exact hashes and limits. Keep the final project holdout closed.

## Local artifacts

The ignored local run directory is `training/artifacts/experiments/p2-12-answer-start-transfer-v2-run-100step-v1/`. It contains `result.json`, `completion-score.json`, metrics, initialization, and the checkpoint. The prepared, hash-frozen inputs are in `training/artifacts/experiments/p2-12-answer-start-transfer-v2-prepared/`.
