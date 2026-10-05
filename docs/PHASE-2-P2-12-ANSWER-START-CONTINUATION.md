# P2-12 v2 checkpoint continuation

Date: 2026-10-05

Status: **one 100-update checkpoint continuation complete; training convergence reached; repeated evaluation is exploratory**

## Result

Following the 100-update fresh run documented in the [original P2-12 v2 report](PHASE-2-P2-12-ANSWER-START-RUN-V2.md), the owner authorized continuing its saved checkpoint for one additional bounded block. The run resumed at step 100, completed 100 more CUDA updates in **37.10 seconds**, and stopped at step 200.

| Measure | Result |
|---|---:|
| Supplied training requests reproduced exactly | **96/96** |
| Previously scored evaluation-only requests reproduced exactly | **64/64** |
| Evaluation misses starting after the expected answer newline | **0/64** |
| Runtime validation loss | 9.4304 → 11.1578 |

The 64/64 score is a repeated score on prompts already evaluated at step 100. It is exploratory and cannot be treated as a fresh or independent holdout result. The small selector-copy task is not evidence of general instruction following or coding ability. The final project holdout remains closed.

## Checkpoint and continuation identity

- Starting checkpoint: `training/artifacts/experiments/p2-12-answer-start-transfer-v2-run-100step-v1/pilot/pilot-checkpoint.pt`
- Starting checkpoint SHA-256: `6379f217ea06ad97db631b5c6149159a31b950c96994d486f7b28878e0751fb4`
- Ending checkpoint SHA-256: `e1e6821eaf5af2bfb9ddb0de7031790dc96e6d0e8f706bb4521d005219736065`
- Training candidate SHA-256: `bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03`
- Evaluation-only set SHA-256: `a81b05aa3452d9b04d9f9b4d6b1a0d0e8ebf2614c3de24c0c4083eb975629fb7`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`
- Seed 1337; micro-batch 1; gradient accumulation 16; original candidate and validation corpus retained.
- Evaluation-only rows were excluded from training and runtime validation loss. The original checkpoint was unchanged.
- No new approval record was written. The continuation was separately authorized by the owner after the first run; the historical approval remains an accurate record of the original fresh run only.

The ignored run artifacts are in `training/artifacts/experiments/p2-12-answer-start-transfer-v2-continuation-100step-v3/`, including `result.json`, `completion-score.json`, metrics, and the step-200 checkpoint.

## Resume-accounting correction

The resume verifier originally counted every nonpadding target when replaying a complete-record sampler. P2-12's answer-focused objective masks prompt targets, while the checkpoint's `tokensProcessedTotal` correctly counts only supervised answer/EOS targets. The first continuation attempt was therefore rejected even though its saved sampling RNG state exactly matched deterministic replay.

`AnswerFocusedCompleteRecordTokenCorpus.replay_progress` now replays the same record choices and counts only answer/EOS targets. This preserves the RNG equality check and aligns replayed token progress with the objective-specific checkpoint telemetry. The successful run resumed from the original checkpoint without modifying it.

## Next step

Create and review a new hash-pinned evaluation-only set with several held-out phrasings, then score the step-200 checkpoint read-only. Do not use those prompts for training or runtime validation loss. Since the original evaluation set has already influenced experiment decisions and its repeated 64/64 score is not independent, keep the next set as development evidence and reserve a distinct final evaluation set. Any additional training should use a separately reviewed candidate and its own authorization.
