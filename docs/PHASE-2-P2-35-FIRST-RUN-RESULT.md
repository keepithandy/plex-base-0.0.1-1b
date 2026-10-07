# P2-35 — Serialization-Stability First Run Result

## Status

**First bounded run complete — October 7, 2026.**

P2-35 completed the owner-approved serialization-stability run from the verified P2-35 step-zero stage.

## Run accounting

- optimizer updates: **100 / 100**
- elapsed time: **21.136 seconds**
- examples sampled: **1,600**
- real target positions: **299,958**
- padding target positions: **0**
- training records selected: **108 / 108**
- minimum / maximum selections per record: **5 / 24**
- interrupted: **false**
- automatic continuation: **false**
- continuation authorized: **false**
- final project holdout opened: **false**

## Validation trajectory

| P2-35 step | Validation loss |
|---:|---:|
| 0 | 4.335327882033128 |
| 25 | **2.3457500476103563** |
| 50 | 2.582532891860375 |
| 75 | 2.5264235184742856 |
| 100 | 2.65470408476316 |

Step 25 is the lowest descriptive validation point, but the authorization contract does not permit retrospective checkpoint selection. The official endpoint remains step 100.

## Official endpoint

- checkpoint: `training/artifacts/structured-plan/p2-35-first-run/checkpoints/step-0100.pt`
- SHA-256: `1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0`
- bytes: **330,900,251**

Mean recent training loss at the endpoint was **0.12126262169913389**.

## Checkpoints

- step 25: `ccdc876a3842ab590886a1645e72ad4ed233ff49b87f4ea6b12edc04a7de763a`
- step 50: `f2c94a537e7e5308ae94e8bbbf7bbf91d1f309aa62023bb02d9b862aa4e19641`
- step 75: `3a003c7eff2057d0546e7f2fcb10acaa5c8c5064ce7d1f4a3aefb1249396ba40`
- step 100: `1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0`

## Interpretation

P2-35 substantially reduced held-out serialization-curriculum loss, but the lowest point occurred early and the fixed endpoint finished somewhat higher. This result alone does not establish that free-generated structured plans are now valid JSON.

The next milestone is **P2-36 — Structured Bridge Re-evaluation** on the unchanged P2-31 development set.

Machine-readable result:

`training/pretraining/p2-35-first-run-result.json`
