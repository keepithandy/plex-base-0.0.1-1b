# P2-36 — Structured Bridge Re-evaluation Result

## Status

**Gate failed with measurable structural improvement — October 7, 2026.**

P2-36 re-ran the unchanged P2-31 structured-plan development set against the fixed P2-35 step-100 endpoint.

## Result

| Metric | P2-33 | P2-36 |
|---|---:|---:|
| Complete plans | 0 / 18 | **0 / 18** |
| Schema-valid plans | 0 / 18 | **5 / 18** |
| Checks passed | 36 / 162 | **56 / 162** |
| Gate | FAIL | **FAIL** |

Per language:

| Language | Complete plans | Schema-valid plans |
|---|---:|---:|
| HTML | 0 / 6 | **0 / 6** |
| CSS | 0 / 6 | **2 / 6** |
| JavaScript | 0 / 6 | **3 / 6** |

Schema-valid tasks:

- `p231-css-03-focus-style`
- `p231-css-06-toolbar-wrap`
- `p231-js-02-unique-by-id`
- `p231-js-03-format-usd`
- `p231-js-05-sum-by`

All five schema-valid plans got:

- language: **correct**
- action: **correct**
- targetKind: **correct**

All five still missed:

- targetRole
- exact constraints
- required hint coverage

Among the remaining 13 outputs:

- **7** were invalid JSON
- **6** were parseable JSON that did not satisfy the strict plan schema

## Interpretation

P2-35 improved serialization enough to move Plex from **0 schema-valid plans to 5**, but did not produce a complete semantic plan.

The failure is now split across two surfaces:

1. **remaining representation instability** on 13/18 tasks
2. **semantic field binding failure** on the 5 tasks that already serialize successfully

This is materially different from P2-33, where all 18 plans failed before semantic scoring.

Do not authorize another training run from aggregate loss alone.

The next milestone is **P2-37 — Bridge Error Decomposition**, which inspects the exact P2-36 raw responses without repairing or rescoring them.

Machine-readable result:

`training/pretraining/p2-36-structured-bridge-result.json`
