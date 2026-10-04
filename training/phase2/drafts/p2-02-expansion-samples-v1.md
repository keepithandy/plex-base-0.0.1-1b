# Request-following expansion: twelve review samples

**Pending review. These samples are not approved or included in training.**

Original Codex-authored examples; no external source text. JavaScript behavior cases are unexecuted expectations.

## sample-html-ruby-full

**Request:** Annotate the word Tokyo with the reading To-kyo using ruby and rt elements. Return an HTML fragment.

**Family (keep together):** `html-ruby`

```html
<ruby>Tokyo<rt>To-kyo</rt></ruby>
```

**Review point:** The reading must be nested inside the ruby element, not printed as unrelated text.

## sample-html-ruby-plain

**Request:** Show the word Tokyo in a span without pronunciation annotations. Do not use ruby or rt elements.

**Family (keep together):** `html-ruby`

```html
<span>Tokyo</span>
```

**Review point:** The same word now requires plain text markup; copying the paired ruby answer is wrong.

## sample-html-disclosure-open

**Request:** Create an initially expanded details element with summary Shipping and a paragraph saying Ships tomorrow.

**Family (keep together):** `html-disclosure`

```html
<details open>
  <summary>Shipping</summary>
  <p>Ships tomorrow.</p>
</details>
```

**Review point:** The open attribute controls the initial expanded state; summary and paragraph must be inside details.

## sample-html-disclosure-closed

**Request:** Create an initially collapsed details element with summary Shipping and a paragraph saying Ships tomorrow. Omit the open attribute.

**Family (keep together):** `html-disclosure`

```html
<details>
  <summary>Shipping</summary>
  <p>Ships tomorrow.</p>
</details>
```

**Review point:** Adding open, even open="false", would violate the requested initial collapsed state.

## sample-css-border-start

**Request:** For .note, add a 2px solid #334155 border at the inline start edge only. Return one CSS rule.

**Family (keep together):** `css-logical-border`

```css
.note {
  border-inline-start: 2px solid #334155;
}
```

**Review point:** Use the requested logical start edge; do not replace it with a physical left border.

## sample-css-border-end

**Request:** For .note, add a 2px solid #334155 border at the inline end edge only. Return one CSS rule.

**Family (keep together):** `css-logical-border`

```css
.note {
  border-inline-end: 2px solid #334155;
}
```

**Review point:** The selector and value are identical to the paired request; the required property changes.

## sample-css-aspect-square

**Request:** For .preview, set aspect-ratio to 1 / 1. Return one CSS rule with no other declarations.

**Family (keep together):** `css-aspect-ratio`

```css
.preview {
  aspect-ratio: 1 / 1;
}
```

**Review point:** Exactly one declaration is required. Static checks below do not prove absence of every possible extra declaration.

## sample-css-aspect-wide

**Request:** For .preview, set aspect-ratio to 16 / 9. Return one CSS rule with no other declarations.

**Family (keep together):** `css-aspect-ratio`

```css
.preview {
  aspect-ratio: 16 / 9;
}
```

**Review point:** The same property now requires the requested wide ratio; do not reuse the square value.

## sample-js-product

**Request:** Write combineValues(a, b) for finite numbers that returns their product. Return one JavaScript function.

**Family (keep together):** `javascript-binary-operation`

```javascript
function combineValues(a, b) {
  return a * b;
}
```

**Review point:** Behavior cases are unexecuted expectations. The implementation returns multiplication, not addition.

**Expected cases, not executed:** [{"arguments": [3, 4], "expected": 12}, {"arguments": [-2, 5], "expected": -10}, {"arguments": [0, 8], "expected": 0}]

## sample-js-difference

**Request:** Write combineValues(a, b) for finite numbers that returns a minus b. Return one JavaScript function.

**Family (keep together):** `javascript-binary-operation`

```javascript
function combineValues(a, b) {
  return a - b;
}
```

**Review point:** Same signature and input domain, different operation. Both variants must stay in the same split.

**Expected cases, not executed:** [{"arguments": [3, 4], "expected": -1}, {"arguments": [-2, 5], "expected": -7}, {"arguments": [0, 8], "expected": -8}]

## sample-js-bound-upper

**Request:** Write boundValue(value, limit) for finite numbers that returns value capped at the upper limit. Return one JavaScript function.

**Family (keep together):** `javascript-one-sided-bound`

```javascript
function boundValue(value, limit) {
  return Math.min(value, limit);
}
```

**Review point:** An upper bound uses the smaller number. Function-name checks alone cannot verify this behavior.

**Expected cases, not executed:** [{"arguments": [12, 10], "expected": 10}, {"arguments": [4, 10], "expected": 4}, {"arguments": [-4, -2], "expected": -4}]

## sample-js-bound-lower

**Request:** Write boundValue(value, limit) for finite numbers that returns value raised to at least the lower limit. Return one JavaScript function.

**Family (keep together):** `javascript-one-sided-bound`

```javascript
function boundValue(value, limit) {
  return Math.max(value, limit);
}
```

**Review point:** The paired lower-bound request uses the larger number; copying the upper-bound answer is wrong.

**Expected cases, not executed:** [{"arguments": [12, 10], "expected": 12}, {"arguments": [4, 10], "expected": 10}, {"arguments": [-4, -2], "expected": -2}]

## Verification

All twelve supplied solutions passed 57 static checks, including explicitly forbidden strings. No exact normalized request duplicates were found against development requests or the earlier authored sets. This does not prove absence of semantic overlap. Nesting, exact declaration count, and JavaScript behavior still require the stated review. No final holdout was opened.
