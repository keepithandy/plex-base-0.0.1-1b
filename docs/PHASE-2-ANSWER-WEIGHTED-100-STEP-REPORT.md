# P2-02: controlled answer-weighted training check

The [approved v3 corpus](PHASE-2-FAILURE-GAP-100-STEP-REPORT.md) contains 234 original local-use examples and produced a 156-training/78-validation split. The ordinary 100-step run improved held-out text prediction but passed **0/30** development coding tasks. This experiment changed only the *training loss weights*: prompt targets retained weight 1, while the code answer and end-of-record target received weight 4. Sampling, the 1,509-entry tokenizer, 27,566,080-parameter model, seed-1337 random initialization, optimizer, 100-step limit, ten-minute ceiling, and 30 development tasks stayed fixed. The final holdout was not opened.

The new [answer-span mapper](../training/src/plex_training/answer_weighting.py) checks the dataset JSONL hash, token index, every packed record, and the tokenizer's prompt-prefix boundary before training. Its verified map marks 11,198 prompt tokens and 3,572 answer/EOS tokens across the 156 training records. Weight 4 gives answer/EOS targets **56.1% of the planned total loss weight**, versus 24.2% of raw token positions. The map SHA-256 is `a27c3ccefb61f4670814766c75e206be3e62d0c137de11563dc55d129d61e413`; its identity is saved in the checkpoint's `trainingSettings.answerObjective`. A weighted checkpoint cannot silently resume under the ordinary objective.

## Matched result

| Measure | Ordinary loss | Answer weight 4 |
|---|---:|---:|
| Complete development tasks passed | **0/30** | **0/30** |
| Static checks passed / total | 35/151 | 34/151 |
| HTML syntax passes | 1/10 | 0/10 |
| CSS syntax passes | 2/10 | 3/10 |
| JavaScript syntax passes | 0/10 | 0/10 |
| Truncated outputs | 0/30 | 0/30 |
| Held-out ordinary next-token loss after 100 steps | 3.28499 | 3.41129 |
| Training wall time | 14.52 s | 31.28 s |

Both arms began at the same 7.45021 held-out ordinary next-token loss. The weighted arm lowered that loss from step zero, but finished slightly worse than ordinary training and passed no additional coding task. Its recent training loss is on a different weighted scale, so comparing that number directly with ordinary training loss would be misleading. A navigation request still produced broken markup, and a clamp request began with an unrelated `propertyNames` function. [Ordinary responses](../training/artifacts/evaluation/p2-request-following-100step-v3/responses.jsonl) and [weighted responses](../training/artifacts/evaluation/p2-request-following-answer4-100step-v1/responses.jsonl) are saved for inspection. Generated JavaScript was checked with Node `--check`, never executed.

| Shared or resulting artifact | SHA-256 |
|---|---|
| Approved v3 candidate JSONL | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Random initialization | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| Ordinary 100-step checkpoint | `b2d4b7a3e35affe398b2e269f7b2dd7f1d9d86e528f2d2d8148d7a887e2620eb` |
| Weighted 100-step checkpoint | `6e7542cc1d68abe55ee510e8ca443b55a115c9a4b68fa86fba2bda8e288401e3` |
| Ordinary development responses | `678ef8a8716ef048ff11a062a0697a43a7cccd6271c77a01887f0a6e26680675` |
| Weighted development responses | `b0c6defce867b558e85929530cdd9b40f0de2c111fa840f5dc29228d9f1d8305` |

The weighted pilot artifacts are under `training/artifacts/pilot/p2-request-following-answer4-100step-v1`; its [pilot report](../training/artifacts/pilot/p2-request-following-answer4-100step-v1/pilot-report.json) records the objective and hardware use. The matching [development score](../training/artifacts/evaluation/p2-request-following-answer4-100step-v1/score.json) is under `training/artifacts/evaluation/p2-request-following-answer4-100step-v1`. The run used CUDA, processed 819,200 sampled token positions, and finished within the ten-minute ceiling. No dependency installation, dataset download, paid resource, or longer training run was performed.

The full training suite passed **101 tests**. Focused tests showed that weighted and ordinary sampling draw identical input/target windows from the same random seed, that altering corpus identity or offsets is rejected, that all-ones weights preserve ordinary loss, and that a weighted checkpoint cannot resume as ordinary loss. `git diff --check` passed.

## Decision

Answer weighting changed the training objective as designed but did not improve the primary coding-task score. **Do not extend this checkpoint to two hours on the present evidence.** The next planning step is to identify whether the tiny approved corpus, prompt/answer format, or model behavior is the limiting factor through small diagnostics on existing data, then propose one reviewable change. Reusing this development set for iteration is allowed; any later capability claim still requires the untouched final holdout.
