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

Do a read-only token-rank and first-divergence audit of the 11 fresh-evaluation misses, grouped by the two weaker phrasings and input layout. In particular, check whether the next-line “Give only…” failures skip the newline/period boundary or choose the selector body incorrectly. Do not train again until that evidence is reviewed and a separate candidate and approval are prepared.
