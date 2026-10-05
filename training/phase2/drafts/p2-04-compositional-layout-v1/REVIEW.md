# P2-04 compositional-binding probe candidate

Status: **pending owner review**. No model has been trained on these records.

Failed-operation source: `gap-css-layout-01`.

The probe uses two independently varied binding slots. Every individual slot value appears in training, while each evaluation example is a pairing never shown during training.

## Training candidate

### compositional-gap-css-layout-01-train-0

Bindings: `{"gap": "6px", "selector": ".actions"}`

Request: Make .actions a flex row with a 6px gap and centered items. Return code only.

```css
.actions { display: flex; gap: 6px; align-items: center; }
```

### compositional-gap-css-layout-01-train-1

Bindings: `{"gap": "14px", "selector": ".actions"}`

Request: Make .actions a flex row with a 14px gap and centered items. Return code only.

```css
.actions { display: flex; gap: 14px; align-items: center; }
```

### compositional-gap-css-layout-01-train-2

Bindings: `{"gap": "14px", "selector": ".filters"}`

Request: Make .filters a flex row with a 14px gap and centered items. Return code only.

```css
.filters { display: flex; gap: 14px; align-items: center; }
```

### compositional-gap-css-layout-01-train-3

Bindings: `{"gap": "28px", "selector": ".filters"}`

Request: Make .filters a flex row with a 28px gap and centered items. Return code only.

```css
.filters { display: flex; gap: 28px; align-items: center; }
```

### compositional-gap-css-layout-01-train-4

Bindings: `{"gap": "6px", "selector": ".controls"}`

Request: Make .controls a flex row with a 6px gap and centered items. Return code only.

```css
.controls { display: flex; gap: 6px; align-items: center; }
```

### compositional-gap-css-layout-01-train-5

Bindings: `{"gap": "28px", "selector": ".controls"}`

Request: Make .controls a flex row with a 28px gap and centered items. Return code only.

```css
.controls { display: flex; gap: 28px; align-items: center; }
```

## Evaluation only — never train

### compositional-gap-css-layout-01-evaluation-only-0

Bindings: `{"gap": "28px", "selector": ".actions"}`

Request: Make .actions a flex row with a 28px gap and centered items. Return code only.

```css
.actions { display: flex; gap: 28px; align-items: center; }
```

### compositional-gap-css-layout-01-evaluation-only-1

Bindings: `{"gap": "6px", "selector": ".filters"}`

Request: Make .filters a flex row with a 6px gap and centered items. Return code only.

```css
.filters { display: flex; gap: 6px; align-items: center; }
```

### compositional-gap-css-layout-01-evaluation-only-2

Bindings: `{"gap": "14px", "selector": ".controls"}`

Request: Make .controls a flex row with a 14px gap and centered items. Return code only.

```css
.controls { display: flex; gap: 14px; align-items: center; }
```

## Identities

Candidate SHA-256: `df7a6b6f8592006c37612b2b179fb9aee278d966914136284d52a63991c8c754`

Evaluation SHA-256: `578c7e376301751e61112b02feb2a9651f9858efc2276b0bf5067de2e5acccff`
