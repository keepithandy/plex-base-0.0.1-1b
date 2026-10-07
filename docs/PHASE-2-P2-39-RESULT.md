# P2-39 — Structured Bridge Re-evaluation Result

## Status

**Gate failed with no net bridge improvement — October 7, 2026.**

P2-39 re-ran the unchanged P2-31 structured-plan development set against the fixed P2-38 step-100 endpoint.

## Result

| Metric | P2-36 | P2-39 |
|---|---:|---:|
| Complete plans | 0 / 18 | **0 / 18** |
| Schema-valid plans | 5 / 18 | **5 / 18** |
| Checks passed | 56 / 162 | **54 / 162** |
| Gate | FAIL | **FAIL** |

Schema-valid coverage changed to:

- HTML: **3 / 6**
- CSS: **1 / 6**
- JavaScript: **1 / 6**

Schema-valid tasks:

- `p231-html-02-email-field`
- `p231-html-04-disclosure`
- `p231-html-06-checkbox-group`
- `p231-css-01-card-layout`
- `p231-js-03-format-usd`

Across those five schema-valid plans:

- language: **5 / 5 correct**
- action: **3 / 5 correct**
- targetKind: **5 / 5 correct**
- targetRole: **0 / 5 correct**
- exact constraints: **0 / 5**
- required hint coverage: **0 / 5**

## Interpretation

P2-38 did not improve the structured bridge aggregate:

- complete plans stayed at **0**
- schema-valid plans stayed at **5**
- checks declined from **56 to 54**

The set of schema-valid tasks changed, so P2-38 did alter model behavior, but not in a way that improved the gate.

The next milestone is **P2-40 — Bridge Error Decomposition**, which inspects the exact P2-39 raw responses before any further training decision.

Machine-readable result:

`training/pretraining/p2-39-structured-bridge-result.json`
