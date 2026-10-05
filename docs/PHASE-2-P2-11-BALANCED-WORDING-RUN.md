# P2-11 balanced-wording run

Date: 2026-10-05
Status: **approved bounded run and post-training evaluation complete**

## Result

The fresh seed-1337 CUDA run completed **100 optimizer updates** and exactly reproduced **96/96 training records**, meeting the predeclared convergence gate. Greedy post-training scoring on the four fresh held-out phrasings produced **53/64 exact selectors**. This result is interpretable for the narrow diagnostic, but it is one initialization over eight repeated selector values, not evidence of broad instruction understanding or coding ability.

| Fresh held-out phrasing | Exact | Inline | Next-line |
|---|---:|---:|---:|
| Repeat this CSS selector exactly as provided | 16/16 | 8/8 | 8/8 |
| Write out the supplied selector unchanged | 16/16 | 8/8 | 8/8 |
| Please preserve the spelling and punctuation of the selector | 11/16 | 6/8 | 5/8 |
| Give only the literal selector shown after this label | 10/16 | 7/8 | 3/8 |

Across layouts, inline requests scored **29/32** and next-line requests **24/32**. All 64 outputs emitted EOS; 55/64 began with a newline. There was one wrong-known-selector output and ten malformed/other outputs. Nine misses omitted the leading period; one duplicated the answer boundary. The weakest cell was the next-line layout under “Give only the literal selector shown after this label” (3/8).

## Read-only token audit of the 11 misses

Teacher-forced ranks and the saved greedy paths were audited against the unchanged step-100 checkpoint. The checkpoint SHA-256 was identical before and after (`6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e`). No weights were updated, no completions were resampled, and the final holdout remained closed.

| Expected decision | Top-ranked over 64 prompts |
|---|---:|
| Answer newline at the prompt | 55/64 |
| Selector period after the expected newline | 64/64 |
| First selector-body token after the expected `\n.` | 61/64 |
| EOS after the expected full answer | 64/64 |

At the actual first divergence, **9/11 misses diverged on the answer newline**, none diverged on the period, and **2/11 diverged at the selector body**. The nine start failures generated the selector body immediately, omitting both the answer newline and its leading period. All nine actual first tokens were greedy top-ranked; the expected newline ranked 2nd–4th. This localizes the dominant error to choosing the first answer token for these prompts, rather than predicting the period after an expected newline.

The two body divergences were both under “Give only the literal selector shown after this label”: inline `.echo-label` chose the `b` token for `.bravo-item` instead of expected `e` (rank 3), and next-line `.charlie-list` emitted a second newline instead of expected `ch` (rank 3), duplicating the answer boundary. For that phrasing, four of the five next-line misses skipped the answer newline; its inline layout had one body-choice miss. The “Please preserve the spelling and punctuation” misses all five diverged at answer start across both layouts (two inline, three next-line). Both 16/16 phrasings ranked the expected newline, period, first body token, and EOS first on all 16 prompts.

This audit supports a narrow phrasing-conditioned answer-start failure in the two lower-scoring templates, with one separate wrong-selector choice and one duplicated boundary. It does not establish why the model prefers those continuations or show general language understanding. Full per-token ranks, top-five alternatives, and all 64 records are in the ignored local artifact `training/artifacts/experiments/p2-11-balanced-wording-transfer-v1-run-100step-v1/token-error-audit-v1.json`; the read-only auditor is `training/phase2/audit_p2_11_evaluation_misses.py`.

Runtime validation loss on the existing P2 request-following validation split rose from **7.4502** to **9.2535**. This loss is a separate telemetry measure and is not a coding-task score.

## Approval and actual limits

- Training candidate SHA-256: `baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab`
- Evaluation-only SHA-256: `f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322`
- Candidate review SHA-256: `ed7ec3306db112633df38a0f51c95932d5c5dc030667eb87688dfdc49f3e4989`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; no refit.
- The owner approved one fresh seed-1337 run, up to 150 updates or 10 minutes, CUDA, microbatch 1, accumulation 16, without extension.
- The shared complete-record training framework enforces a **100-update ceiling**. A 150-step invocation stopped at that preflight guard before any optimizer update and produced no checkpoint. The approved run therefore used a 100-step cap, below the approved maximum; it reached that cap in 15.18 seconds. No shared framework limit was changed.
- Training exposure: 1,600 sampled records, with 7–27 selections per record. The four fresh evaluation templates were used only after training and were excluded from both training and runtime validation loss.
- Validation source: existing 78-record P2 request-following v3 validation split. Loss rose by 1.8033.
- Final project holdout remained closed. No P2-10 checkpoint was continued, and no automatic extension occurred.

The 32 exact requests from the two weak P2-10 wider-evaluation templates were deliberately promoted into P2-11 training. Their P2-10 results remain historical results; P2-11's reported 53/64 uses only the four fresh templates.

## Artifacts

The exact owner approval is in `training/phase2/approvals/p2-11-balanced-wording-transfer-v1.json`. The preparer and runner are `training/phase2/prepare_p2_11_experiment.py` and `training/phase2/run_p2_11_experiment.py`.

The ignored local run directory is `training/artifacts/experiments/p2-11-balanced-wording-transfer-v1-run-100step-v1/`; it contains `result.json`, per-record `completion-score.json`, metrics, initialization, and the checkpoint. The trained checkpoint SHA-256 is `6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e`.

## Next step

Before another training proposal, review the audit's answer-start finding and decide whether a follow-up should test a more explicit first-answer-token cue or add balanced examples for these two failure-prone phrasings. Any follow-up needs a new candidate, a clean fresh evaluation set, its own exact hashes and approval, and must stay within the training framework's 100-update complete-record ceiling unless that shared limit is separately justified and approved. Do not extend the P2-11 run.
