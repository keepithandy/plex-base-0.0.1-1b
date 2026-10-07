# P2-32 — First Structured-Plan Training Result

## Status

**First bounded run complete — October 7, 2026. Structured-plan development re-evaluation is pending.**

The owner-authorized P2-32 run completed **100/100 CUDA optimizer updates** in **106.725 seconds** from the verified P2-32 step-zero stage.

## Identity and accounting

- authorization contract SHA-256: `53d99a589c1df01f602e66755673825ae7e16a1ea6e307c442feb891a2e6a18a`
- stage checkpoint SHA-256: `7028ef6341eb8124a8f3d8d4e4b0717045e45645dee2ebf6bcc22e65827736a3`
- bundle manifest SHA-256: `a0d3663bf3ba9a9653ceb52e35594bf3271e4e56cc483dd66f9d149ca38bc6fd`
- candidate SHA-256: `608cf988b96e8578fa2c7948a12e298c4ed25c640098a2bf3710f3b3cc6802d3`
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- optimizer updates: **100**
- examples sampled: **1,600**
- real target positions: **605,231**
- padding target positions: **0**
- all **72/72** training records selected
- minimum / maximum selections per record: **12 / 33**
- interruption: **false**
- automatic continuation: **false**
- final holdout opened: **false**

## Validation trajectory

| P2-32 step | Validation loss |
|---:|---:|
| 0 | 8.002869129180908 |
| 25 | 2.928607435787425 |
| 50 | 2.6066420358770035 |
| 75 | **2.6038764504825367** |
| 100 | 2.6795914734111115 |

Step 75 is the lowest descriptive validation point, but the fixed contract does not permit retrospective checkpoint selection. The official endpoint remains step 100.

## Official endpoint

- checkpoint: `training/artifacts/structured-plan/p2-32-first-run/checkpoints/step-0100.pt`
- SHA-256: `707e46f9e3e87cdd9beec705e2bd55701b37a40e79aad7ab93858fa63f8ebcf4`
- bytes: **330,900,187**

Mean recent training loss at the endpoint was **0.2934114275034517**.

## Interpretation

The representation curriculum produced a large held-out text-loss improvement and stayed relatively flat between steps 50 and 100. That is encouraging, but it does not by itself establish that Plex can emit valid structured plans on the untouched P2-31 development set.

The next milestone is **P2-33 — Structured Bridge Re-evaluation** using the unchanged 18-task P2-31 development set and the original fixed gate.

Machine-readable result:

`training/pretraining/p2-32-first-run-result.json`
