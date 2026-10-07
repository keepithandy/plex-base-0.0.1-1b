# P2-31 — Structured Coding Bridge Result

## Status

**Development bridge gate failed — October 7, 2026. Phase 3 entry is not authorized.**

P2-31 evaluated the official P2-30 step-100 checkpoint against 18 new development-only repository-style requests using the strict `plex-structured-edit-plan-v1` JSON contract.

The fixed checkpoint was:

`28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`

The generated response artifact SHA-256 was:

`f4e2dcdc43cdb42bf2835f15bd3ab7ba54a1e97fc23ecdae523985702e69be4c`

No model training occurred during P2-31 and the final project holdout remained sealed.

## Predeclared gate

P2-31 required all of the following:

- at least **12 / 18** complete plans overall
- at least **3 / 6** complete plans in each language
- at least **15 / 18** schema-valid JSON plans

## Result

| Metric | Result |
|---|---:|
| Complete plans | **0 / 18** |
| Schema-valid plans | **0 / 18** |
| Checks passed | **36 / 162** |
| Partial tasks | **18 / 18** |
| HTML | **0 / 6** |
| CSS | **0 / 6** |
| JavaScript | **0 / 6** |
| Gate | **FAIL** |

Every generated response was present and untruncated. Every response then failed strict JSON parsing before semantic fields could be scored.

Therefore the observed failure is classified as a **representation-format failure**. P2-31 does not establish that language/action/target-kind/target-role/constraint semantics are wrong, because the responses never crossed the schema-validity boundary.

It also does not test deterministic repository resolution. Plex Code file/symbol/selector lookup remains outside this failed model-format gate.

## Interpretation

P2-30 already showed that the current model can learn task text, terminate responses, and earn partial coding assertions. Earlier Phase-2 experiments separately demonstrated nonzero learning for semantic role, edit intent, and target kind.

P2-31 reveals the next composition gap:

> Plex Nano has not yet learned to serialize those semantic decisions into the new strict multi-field JSON plan contract.

That is narrower than “the model cannot understand coding requests,” but it still blocks Phase 3 because Plex Code cannot consume a plan that is not machine-readable.

## Decision

Do not enter Phase 3.

Do not continue generic P2-30 training.

Proceed to **P2-32 — Structured-Plan Representation Curriculum**, using a training/validation curriculum that is separate from the P2-31 development tasks. The first objective is strict format reliability plus semantic-field composition, not exact repository resolution.

Machine-readable result:

`training/pretraining/p2-31-structured-bridge-result.json`
