# P2-38 — Semantic-Binding First Run Result

## Status

**First bounded run complete — October 7, 2026.**

P2-38 completed the owner-approved semantic-binding contrast run from the verified P2-38 step-zero stage.

## Run accounting

- optimizer updates: **100 / 100**
- elapsed time: **21.426 seconds**
- examples sampled: **1,600**
- real target positions: **548,680**
- padding target positions: **0**
- training records selected: **72 / 72**
- minimum / maximum selections per record: **12 / 33**
- interrupted: **false**
- automatic continuation: **false**
- continuation authorized: **false**
- final project holdout opened: **false**

## Validation trajectory

| P2-38 step | Validation loss |
|---:|---:|
| 0 | 2.6659477899471917 |
| 25 | **2.3299999833106995** |
| 50 | 2.557119940718015 |
| 75 | 2.6024878919124603 |
| 100 | 2.625917633374532 |

Step 25 is the lowest descriptive validation point, but the authorization contract does not permit retrospective checkpoint selection. The official endpoint remains step 100.

## Official endpoint

- checkpoint: `training/artifacts/structured-plan/p2-38-first-run/checkpoints/step-0100.pt`
- SHA-256: `9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6`
- bytes: **330,900,187**

Mean recent training loss at the endpoint was **0.09404514555353671**.

## Checkpoints

- step 25: `b8f638a69556b14e587ed9b887e76fdefdbb245096c1a22b575794acd320578e`
- step 50: `7158850ec06ac5e13b012675331199f418429c4d043ad1ca825c24bc86a6aa6f`
- step 75: `b4669502d2a5c33d5abfc20b8c1867d39d03819cdd66288e26c72f9dca616bba`
- step 100: `9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6`

## Interpretation

P2-38 substantially fit the semantic-binding contrast curriculum, but the fixed endpoint finished only slightly below the stage-zero held-out loss after the earlier step-25 minimum.

This result alone does not establish improved request-conditioned semantic planning on unseen development tasks.

The next milestone is **P2-39 — Structured Bridge Re-evaluation** on the unchanged P2-31 development set.

Machine-readable result:

`training/pretraining/p2-38-first-run-result.json`
