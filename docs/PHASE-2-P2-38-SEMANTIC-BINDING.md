# P2-38 — Semantic-Binding Contrast Curriculum

## Status

**Candidate review complete and locked staging/preflight path prepared — October 7, 2026. Model training is not authorized.**

P2-37 showed that P2-35 improved JSON serialization but introduced a new dominant failure mode: Plex often reuses familiar curriculum concepts instead of binding the new request to the correct semantic target.

All five schema-valid P2-36 plans reused literal P2-35 target roles.

P2-38 is designed to attack that failure directly.

## Core change

P2-38 will **not** use the six-stage P2-35 curriculum.

There will be:

- no micro-JSON prefix records
- no isolated target identity records
- no isolated constraint-object records
- no nested-array-only records

Every training example will use the real production structured-plan prompt and require one complete strict plan.

## Reviewed candidate

- **108 records**
- **36 contrast groups**
- **3 records per group**
- **72 train**
- **36 validation**

Per language:

| Language | Train groups | Validation groups | Train records | Validation records |
|---|---:|---:|---:|---:|
| HTML | 8 | 4 | 24 | 12 |
| CSS | 8 | 4 | 24 | 12 |
| JavaScript | 8 | 4 | 24 | 12 |

## Contrast-group rule

Each group contains three closely related requests with similar surface wording but different semantic details.

Example shape:

- request A → semantic target A
- request B → semantic target B
- request C → semantic target C

The model therefore cannot succeed by learning a single generic completion for the group. It has to attend to the request-specific details.

## Anti-collapse rules

The reviewer must require:

- every request is unique
- every targetRole is unique across the entire candidate
- zero exact P2-31 development request overlap
- zero P2-31 development targetRole overlap
- zero P2-35 targetRole overlap
- all solutions are strict full plans
- all records use the production structured-plan prompt
- contrast groups stay wholly inside train or validation
- each contrast group has exactly three distinct semantic targets

## Protected data

The following remain excluded from gradients:

- P2-31 development requests/targets
- P2-36 response strings
- P2-01b development data
- final project holdout

The P2-35 target roles are also explicitly excluded from the P2-38 candidate to prevent reinforcing the observed collapse.

## Tokenizer

The existing frozen 16K tokenizer remains in force.

No tokenizer refit is authorized.

## Governance

Preparation contract:

`training/pretraining/p2-38-semantic-binding-preparation-contract.json`

Current state:

- data preparation authorized: **true**
- model training authorized: **false**
- automatic extension: **false**
- training command: **none**
- research optimizer updates: **0**
- final holdout opened: **false**

## Static review and tokenizer preflight

The [candidate](../training/phase2/drafts/p2-38-semantic-binding-candidate-v1.jsonl) and [review metadata](../training/phase2/drafts/p2-38-semantic-binding-candidate-v1.review.json) are pinned to SHA-256 `137e2ccf8e015ba74a109ce53f3c7adf502262a4d2a79382e21bfc69a1ea7ab8` (86,973 bytes). The authored candidate contains 108 strict full plans, 36 intact three-record groups, 72 train records, and 36 validation records. Each language has 8 train groups and 4 validation groups. All 108 requests and all 108 target roles are unique. P2-31 exact-request overlap, P2-31 target-role overlap, and P2-35 target-role overlap are all zero. No P2-36 response strings were used as candidate data.

The dedicated read-only reviewer uses the production `render_plan_request_prompt(...)` and strict `parse_plan_response(...)`. It passed static review. Local frozen-tokenizer preflight also passed: tokenizer SHA-256 `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`, 16,384 vocabulary entries, 108/108 rendered-record roundtrips, maximum **395 tokens including EOS** within the 512-token context, **24,793 train tokens**, and **12,409 validation tokens**. The bundle manifest SHA-256 was `17f02f7f0b786be770f964b445854684fee0a010793672149e7fcc6c611aae5d`.

```powershell
uv run --project training --no-sync python -m plex_training.cli plan-semantic-binding-review `
  --bundle-dir training/artifacts/structured-plan/p2-35-training-bundle
```

This command performs zero optimizer updates. Candidate review is complete. A separate locked P2-38 bundle/stage/preflight path now exists, but the first-run contract remains draft-only and unauthorized. See [P2-38 Training Path](PHASE-2-P2-38-TRAINING-PATH.md). `modelTrainingAuthorized=false`, `researchOptimizerUpdates=0`, and `finalHoldoutOpened=false`.
