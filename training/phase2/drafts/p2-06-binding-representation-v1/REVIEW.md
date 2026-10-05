# P2-06 binding-representation probe

Status: **pending owner review**. No model has been trained on these records.

P2-06 separates three questions with independent fresh-model arms: can Plex preserve one requested binding, can it preserve two bindings simultaneously, and can it compose the same two bindings into CSS?

## Level 1 — single-copy

Six training examples expose each selector and gap once. Six evaluation examples use the same values with alternate request wording. This is deliberately a representation/instruction test, not a novel-value holdout.

## Level 2 — dual-binding

Six selector-gap pairs are trained and three pairings are held out. The output is only two labeled lines, so CSS generation is removed.

## Level 3 — CSS composition

Uses the exact same six training pairs and three held-out pairs as Level 2, but requires the full CSS rule. A Level-2 pass with a Level-3 failure would isolate code composition from multi-binding preservation.

## Decision ladder

- If Level 1 fails, investigate basic prompt-bound copying/token representation before composition.
- If Level 1 passes but Level 2 fails, the bottleneck is simultaneous independent binding.
- If Level 2 passes but Level 3 fails, the bottleneck is composing preserved bindings into code.
- If all three pass, revisit P2-05 distribution effects rather than representation capacity alone.

## Approval boundary

The preparer writes review artifacts only. Training remains unauthorized until the exact JSONL hashes are reviewed and approved. The final project holdout stays closed.

## single-copy

### Training candidate

**p2-06-single-selector-0-train**

Request:

```text
Return this selector exactly: .actions
```

Expected:

```text
.actions
```

**p2-06-single-selector-1-train**

Request:

```text
Return this selector exactly: .filters
```

Expected:

```text
.filters
```

**p2-06-single-selector-2-train**

Request:

```text
Return this selector exactly: .controls
```

Expected:

```text
.controls
```

**p2-06-single-gap-0-train**

Request:

```text
Return this gap exactly: 6px
```

Expected:

```text
6px
```

**p2-06-single-gap-1-train**

Request:

```text
Return this gap exactly: 14px
```

Expected:

```text
14px
```

**p2-06-single-gap-2-train**

Request:

```text
Return this gap exactly: 28px
```

Expected:

```text
28px
```

### Evaluation only

**p2-06-single-selector-0-eval**

Request:

```text
Copy this selector without changes: .actions
```

Expected:

```text
.actions
```

**p2-06-single-selector-1-eval**

Request:

```text
Copy this selector without changes: .filters
```

Expected:

```text
.filters
```

**p2-06-single-selector-2-eval**

Request:

```text
Copy this selector without changes: .controls
```

Expected:

```text
.controls
```

**p2-06-single-gap-0-eval**

Request:

```text
Copy this gap value without changes: 6px
```

Expected:

```text
6px
```

**p2-06-single-gap-1-eval**

Request:

```text
Copy this gap value without changes: 14px
```

Expected:

```text
14px
```

**p2-06-single-gap-2-eval**

Request:

```text
Copy this gap value without changes: 28px
```

Expected:

```text
28px
```

## dual-binding

### Training candidate

**p2-06-dual-0-train**

Request:

```text
Selector: .actions
Gap: 6px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.actions
gap=6px
```

**p2-06-dual-1-train**

Request:

```text
Selector: .actions
Gap: 14px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.actions
gap=14px
```

**p2-06-dual-2-train**

Request:

```text
Selector: .filters
Gap: 14px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.filters
gap=14px
```

**p2-06-dual-3-train**

Request:

```text
Selector: .filters
Gap: 28px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.filters
gap=28px
```

**p2-06-dual-4-train**

Request:

```text
Selector: .controls
Gap: 6px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.controls
gap=6px
```

**p2-06-dual-5-train**

Request:

```text
Selector: .controls
Gap: 28px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.controls
gap=28px
```

### Evaluation only

**p2-06-dual-0-eval**

Request:

```text
Selector: .actions
Gap: 28px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.actions
gap=28px
```

**p2-06-dual-1-eval**

Request:

```text
Selector: .filters
Gap: 6px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.filters
gap=6px
```

**p2-06-dual-2-eval**

Request:

```text
Selector: .controls
Gap: 14px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.controls
gap=14px
```

## css-composition

### Training candidate

**p2-06-css-0-train**

Request:

```text
Selector: .actions
Gap: 6px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.actions { display: flex; gap: 6px; align-items: center; }
```

**p2-06-css-1-train**

Request:

```text
Selector: .actions
Gap: 14px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.actions { display: flex; gap: 14px; align-items: center; }
```

**p2-06-css-2-train**

Request:

```text
Selector: .filters
Gap: 14px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.filters { display: flex; gap: 14px; align-items: center; }
```

**p2-06-css-3-train**

Request:

```text
Selector: .filters
Gap: 28px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.filters { display: flex; gap: 28px; align-items: center; }
```

**p2-06-css-4-train**

Request:

```text
Selector: .controls
Gap: 6px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.controls { display: flex; gap: 6px; align-items: center; }
```

**p2-06-css-5-train**

Request:

```text
Selector: .controls
Gap: 28px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.controls { display: flex; gap: 28px; align-items: center; }
```

### Evaluation only

**p2-06-css-0-eval**

Request:

```text
Selector: .actions
Gap: 28px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.actions { display: flex; gap: 28px; align-items: center; }
```

**p2-06-css-1-eval**

Request:

```text
Selector: .filters
Gap: 6px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.filters { display: flex; gap: 6px; align-items: center; }
```

**p2-06-css-2-eval**

Request:

```text
Selector: .controls
Gap: 14px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```text
.controls { display: flex; gap: 14px; align-items: center; }
```

## Identities

```json
{
  "css-composition": {
    "candidateJsonlSha256": "a84de00032d543a4b2bc9e9d67ef0bea5ef2cc94b080ea862f37179253b1ec6b",
    "evaluationJsonlSha256": "969ca23edf91ff9175e9ac502395a5aa850b541c3392843e20aa82b38eb56dee",
    "evaluationOnlyRecords": 3,
    "trainingRecords": 6
  },
  "dual-binding": {
    "candidateJsonlSha256": "856f20637a3bd42e0b6838964503a3aaf74a86af3a0d464128194f9ab3c6aabb",
    "evaluationJsonlSha256": "e3afa59441365fd2a88089704755f5b9fbb9b27f88804416616272283c5d5399",
    "evaluationOnlyRecords": 3,
    "trainingRecords": 6
  },
  "single-copy": {
    "candidateJsonlSha256": "13452867b30a38b9ffc3e42ef440d3ac560c3103d5d479d014525eae10a12727",
    "evaluationJsonlSha256": "9cf9777c431de134f880eb152d84794af9f848e69f25a36420c605bcc6a144c8",
    "evaluationOnlyRecords": 6,
    "trainingRecords": 6
  }
}
```
