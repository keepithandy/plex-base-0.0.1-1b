# P2-34 — Output-Boundary Diagnostic Result

## Status

**Diagnostic complete — October 7, 2026.**

P2-34 inspected the exact P2-33 response artifact without repairing or rescoring any output.

## Result

All **18 / 18** responses were classified as:

`malformed-json-candidate`

The responses consistently learned the outside boundary of the contract:

- **18 / 18** start with `{`
- **18 / 18** end with `}`
- **18 / 18** contain an opening brace
- **18 / 18** contain a closing brace
- **18 / 18** contain `"schemaVersion"`
- **0 / 18** contain Markdown fences
- **0 / 18** contain an embedded parseable JSON object
- **0 / 18** contain an embedded strict plan

All 18 begin with the same broad prefix:

`{"schemaVersion":1,"lang`

There were **17 unique response strings** and one duplicate response.

## Diagnosis

The primary failure is now classified as:

**JSON grammar / serialization instability**

Plex learned:

- to begin a plan object
- the schemaVersion prefix
- the broad full-plan shape
- to terminate with a closing brace

Plex did not reliably learn:

- `key : value` transitions
- comma → next-key transitions
- stable distinction between keys and values
- nested `constraints` object grammar
- nested `constraints` / `searchHints` array boundaries

Representative outputs contain structures such as:

- values replacing keys
- duplicated `constraints` keys
- `"action":"targetKind"`
- missing colons between fields
- repeated key/value fragments inside constraint objects

This is narrower than the earlier “model will not emit JSON” hypothesis. The model is attempting the right representation family but corrupting the interior grammar during autoregressive generation.

## Decision

Do not continue generic P2-32 training.

Proceed to **P2-35 — Serialization Stability Curriculum**, which isolates local JSON transitions before returning to full request-to-plan generation.

Machine-readable result:

`training/pretraining/p2-34-output-boundary-result.json`
