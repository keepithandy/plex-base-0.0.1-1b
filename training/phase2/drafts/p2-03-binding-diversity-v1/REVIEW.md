# Exact binding-diversity candidate

Status: pending owner review. 24 proposed training examples: six approved originals plus eighteen new variations. Twelve separate same-family bindings are evaluation-only. No model was trained.

## Proposed training examples

### binding-gap-html-bidi-02-train-0

Request: Put a bdi-isolated word inside a paragraph. Use word "Kyoto". Return only the fragment.

```html
<p><bdi>Kyoto</bdi></p>
```

### binding-gap-html-bidi-02-train-1

Request: Put a bdi-isolated word inside a paragraph. Use word "Lisbon". Return only the fragment.

```html
<p><bdi>Lisbon</bdi></p>
```

### binding-gap-html-bidi-02-train-2

Request: Put a bdi-isolated word inside a paragraph. Use word "Seoul". Return only the fragment.

```html
<p><bdi>Seoul</bdi></p>
```

### binding-gap-html-bidi-02-train-3

Request: Put a bdi-isolated word inside a paragraph. Use word "Nairobi". Return only the fragment.

```html
<p><bdi>Nairobi</bdi></p>
```

### binding-gap-html-progress-01-train-0

Request: Make determinate progress with value 35 and max 100. Return only the fragment.

```html
<progress value="35" max="100"></progress>
```

### binding-gap-html-progress-01-train-1

Request: Make determinate progress with value 18 and max 100. Return only the fragment.

```html
<progress value="18" max="100"></progress>
```

### binding-gap-html-progress-01-train-2

Request: Make determinate progress with value 47 and max 100. Return only the fragment.

```html
<progress value="47" max="100"></progress>
```

### binding-gap-html-progress-01-train-3

Request: Make determinate progress with value 83 and max 100. Return only the fragment.

```html
<progress value="83" max="100"></progress>
```

### binding-gap-css-logical-border-03-train-0

Request: For .top-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.top-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-logical-border-03-train-1

Request: For .card-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.card-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-logical-border-03-train-2

Request: For .banner-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.banner-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-logical-border-03-train-3

Request: For .notice-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.notice-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-layout-01-train-0

Request: Make .toolbar a flex row with a 12px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 12px; align-items: center; }
```

### binding-gap-css-layout-01-train-1

Request: Make .toolbar a flex row with a 6px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 6px; align-items: center; }
```

### binding-gap-css-layout-01-train-2

Request: Make .toolbar a flex row with a 14px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 14px; align-items: center; }
```

### binding-gap-css-layout-01-train-3

Request: Make .toolbar a flex row with a 28px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 28px; align-items: center; }
```

### binding-gap-javascript-division-01-train-0

Request: Write quotientTowardZero(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function quotientTowardZero(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-division-01-train-1

Request: Write integerQuotient(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function integerQuotient(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-division-01-train-2

Request: Write quotientTruncated(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function quotientTruncated(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-division-01-train-3

Request: Write divideTowardZero(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function divideTowardZero(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-array-copy-01-train-0

Request: Write copyItems(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function copyItems(items) {
  return items.slice();
}
```

### binding-gap-javascript-array-copy-01-train-1

Request: Write copyValues(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function copyValues(items) {
  return items.slice();
}
```

### binding-gap-javascript-array-copy-01-train-2

Request: Write shallowClone(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function shallowClone(items) {
  return items.slice();
}
```

### binding-gap-javascript-array-copy-01-train-3

Request: Write copyList(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function copyList(items) {
  return items.slice();
}
```

## Evaluation-only examples

These requests/references will not enter training or tokenizer data.

### binding-gap-html-bidi-02-evaluation-only-0

Request: Put a bdi-isolated word inside a paragraph. Use word "Riga". Return only the fragment.

```html
<p><bdi>Riga</bdi></p>
```

### binding-gap-html-bidi-02-evaluation-only-1

Request: Put a bdi-isolated word inside a paragraph. Use word "Tallinn". Return only the fragment.

```html
<p><bdi>Tallinn</bdi></p>
```

### binding-gap-html-progress-01-evaluation-only-0

Request: Make determinate progress with value 27 and max 100. Return only the fragment.

```html
<progress value="27" max="100"></progress>
```

### binding-gap-html-progress-01-evaluation-only-1

Request: Make determinate progress with value 74 and max 100. Return only the fragment.

```html
<progress value="74" max="100"></progress>
```

### binding-gap-css-logical-border-03-evaluation-only-0

Request: For .summary-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.summary-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-logical-border-03-evaluation-only-1

Request: For .widget-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.widget-edge {
  border-block-start: 2px dashed #334155;
}
```

### binding-gap-css-layout-01-evaluation-only-0

Request: Make .toolbar a flex row with a 10px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 10px; align-items: center; }
```

### binding-gap-css-layout-01-evaluation-only-1

Request: Make .toolbar a flex row with a 22px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 22px; align-items: center; }
```

### binding-gap-javascript-division-01-evaluation-only-0

Request: Write truncatedDivide(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function truncatedDivide(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-division-01-evaluation-only-1

Request: Write wholeQuotient(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function wholeQuotient(a, b) {
  return Math.trunc(a / b);
}
```

### binding-gap-javascript-array-copy-01-evaluation-only-0

Request: Write cloneList(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function cloneList(items) {
  return items.slice();
}
```

### binding-gap-javascript-array-copy-01-evaluation-only-1

Request: Write duplicateArray(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function duplicateArray(items) {
  return items.slice();
}
```

## Identities

Candidate SHA-256: `8f3fc7dfc21c4ebb5ce5b40391e9b123521d13df50b2d349e5d6b7c3faf37c2f`

Evaluation SHA-256: `ea8699efc997c0b4a5cdeb55c0da1d5be1b0d27a8ae9ad6b5164476c0d82ca7c`
