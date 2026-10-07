# P2-38 — Semantic-Binding Contrast Curriculum

## Status

**Preparation design authorized — October 7, 2026. Model training is not authorized.**

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

## Planned candidate

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

The next step is to author and review the exact 108-record candidate. Training requires a later, separate stage/preflight/owner-authorization sequence.
