# P2-02 request-to-code candidate v2

**Status: draft for owner review; not approved for training.**

This original, Codex-authored set contains 36 request/answer pairs: 12 each for HTML, CSS, and JavaScript. Two related variants stay in each semantic group. Seed 51 selects whole groups: 24 training records and 12 validation records (8/4 per language). No external source text was copied.

## Why a separate candidate

The v3 training split was 76.3% Markdown, with its six authored examples supplying 0.7% of token positions. The ten-minute model passed 0/30 development tasks and emitted Markdown/Mermaid text. This candidate isolates request-to-code formatting; it is deliberately tiny and cannot establish broad coding ability. It is proposed as a separate diagnostic corpus, not appended to the existing tutorial corpus.

## Exact training format

Every source `.txt` file is the unchanged `plex-coding-task-v1` prompt, one newline, and a code-only answer. There are no Markdown headings, fences, review checks, or behavior notes in training text. The existing tokenizer pipeline appends EOS id 3 after each record; the literal marker is never source text. The existing causal objective trains on both prompt and answer tokens; answer-only loss masking is not introduced.

```text
Write a small CSS coding solution.
Request: For input[type="radio"], set accent-color to #146c43. Return one rule.
Output contract: Return CSS rules only. Use the requested selector and declarations. Do not include HTML, Markdown fences, or explanations.
Return code only. Do not include Markdown fences or explanations.
input[type="radio"] {
  accent-color: #146c43;
}
```

## Review and verification

All 36 authored solutions passed 194/194 static checks. HTML structure and declared attributes/text were checked; CSS uses the evaluator's flat-rule parser. JavaScript was syntax-checked with Node `--check`, never executed. The listed behavior cases are review expectations, not measured behavioral results. These checks validate supplied examples, not Plex outputs.

Exact normalized requests were checked against the 30 development prompts. A request-word Jaccard screen had maximum overlap 0.26087; it is a heuristic, not proof against semantic leakage. The semantic families below differ from the development tasks; broad language skills necessarily overlap. No final holdout was opened. Variants are grouped so parameter changes never create train/validation leakage.

The candidate catalog keeps `rightsReviewStatus: pending-owner-review`, so the production dataset builder refuses it. Owner approval is still needed for these exact records because the agreed next step was to review new examples before use. The previous nine-record approval covers only that earlier set. Approval would authorize local P2 training, not assert an external license or approve a public release.

## Proposed experiment after review

1. Approve or revise these exact examples and their whole-group split.
2. Build a separate corpus and fit a fresh tokenizer on its training split only. Record token mix and verify prompt/answer/EOS budgets with that new tokenizer before training. Preserve v3 artifacts.
3. Initialize fresh random Plex weights, seed 1337, and score the same 30 development tasks at step zero.
4. Run a ten-minute CUDA check with the existing model and training settings; score the same tasks again. Compare complete-task passes, syntax, fences, EOS/truncation, held-out loss, and resource use separately.
5. A two-hour run is a later decision based on those results; this draft schedules no training. Keep the $0 paid-service and 200 GiB limits. Qwen weights are never initialization weights.

This is not yet the 70–80% code base-corpus target: serialized prompts occupy part of each record. Code-answer and total text bytes are recorded in `review.json`; a code-token share must be measured with the candidate's own training-fitted tokenizer after approval.

## All examples

### HTML

#### pair-html-abbreviation-arrival — train

Group: `html-abbreviation`

Write a paragraph containing the abbreviation ETA. Give the abbr element a title of Estimated time of arrival.

```html
<p><abbr title="Estimated time of arrival">ETA</abbr></p>
```

#### pair-html-abbreviation-work — train

Group: `html-abbreviation`

Write a paragraph containing the abbreviation WIP. Give the abbr element a title of Work in progress.

```html
<p><abbr title="Work in progress">WIP</abbr></p>
```

#### pair-html-contact-help — train

Group: `html-contact`

Create an address element containing a mailto link to help@example.test, labeled Contact support.

```html
<address>
  <a href="mailto:help@example.test">Contact support</a>
</address>
```

#### pair-html-contact-press — train

Group: `html-contact`

Create an address element containing a mailto link to press@example.test, labeled Press contact.

```html
<address>
  <a href="mailto:press@example.test">Press contact</a>
</address>
```

#### pair-html-definitions-editor — train

Group: `html-definitions`

Create a definition list with these term and description pairs: Tab: Moves to the next editable field.; Escape: Closes the current dialog.

```html
<dl>
  <dt>Tab</dt>
  <dd>Moves to the next editable field.</dd>
  <dt>Escape</dt>
  <dd>Closes the current dialog.</dd>
</dl>
```

#### pair-html-definitions-network — train

Group: `html-definitions`

Create a definition list with these term and description pairs: DNS: Looks up the address for a domain.; URL: Identifies a resource location.

```html
<dl>
  <dt>DNS</dt>
  <dd>Looks up the address for a domain.</dd>
  <dt>URL</dt>
  <dd>Identifies a resource location.</dd>
</dl>
```

#### pair-html-meter-capacity — validation

Group: `html-meter`

Create a labeled meter with id seats-used, label Seats occupied, minimum 0, maximum 30, and current value 18.

```html
<label for="seats-used">Seats occupied</label>
<meter id="seats-used" min="0" max="30" value="18">18 of 30</meter>
```

#### pair-html-meter-storage — validation

Group: `html-meter`

Create a labeled meter with id storage-used, label Storage used, minimum 0, maximum 100, and current value 70.

```html
<label for="storage-used">Storage used</label>
<meter id="storage-used" min="0" max="100" value="70">70 of 100</meter>
```

#### pair-html-progress-download — train

Group: `html-progress`

Show a labeled progress element named download-progress. Its visible label is Download progress; value is 45 and maximum is 100.

```html
<label for="download-progress">Download progress</label>
<progress id="download-progress" value="45" max="100">45 of 100</progress>
```

#### pair-html-progress-lessons — train

Group: `html-progress`

Show a labeled progress element named lesson-progress. Its visible label is Lessons completed; value is 6 and maximum is 12.

```html
<label for="lesson-progress">Lessons completed</label>
<progress id="lesson-progress" value="6" max="12">6 of 12</progress>
```

#### pair-html-quotation-care — validation

Group: `html-quotation`

Create a blockquote containing a paragraph with the text "Clear names help the next reader." and a cite attribute of /notes/names.

```html
<blockquote cite="/notes/names">
  <p>Clear names help the next reader.</p>
</blockquote>
```

#### pair-html-quotation-clarity — validation

Group: `html-quotation`

Create a blockquote containing a paragraph with the text "Small steps make progress visible." and a cite attribute of /notes/progress.

```html
<blockquote cite="/notes/progress">
  <p>Small steps make progress visible.</p>
</blockquote>
```

### CSS

#### pair-css-accent-radio — train

Group: `css-accent`

For input[type="radio"], set accent-color to #146c43. Return one rule.

```css
input[type="radio"] {
  accent-color: #146c43;
}
```

#### pair-css-accent-slider — train

Group: `css-accent`

For input[type="range"], set accent-color to #663399. Return one rule.

```css
input[type="range"] {
  accent-color: #663399;
}
```

#### pair-css-columns-guide — train

Group: `css-columns`

For .guide-text, set column-count to 3, column-gap to 1.5rem. Return one rule.

```css
.guide-text {
  column-count: 3;
  column-gap: 1.5rem;
}
```

#### pair-css-columns-notes — train

Group: `css-columns`

For .reading-notes, set column-count to 2, column-gap to 2rem. Return one rule.

```css
.reading-notes {
  column-count: 2;
  column-gap: 2rem;
}
```

#### pair-css-ellipsis-subject — validation

Group: `css-ellipsis`

For .message-subject, set white-space to nowrap, overflow to hidden, text-overflow to ellipsis. Return one rule.

```css
.message-subject {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

#### pair-css-ellipsis-title — validation

Group: `css-ellipsis`

For .file-name, set white-space to nowrap, overflow to hidden, text-overflow to ellipsis. Return one rule.

```css
.file-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

#### pair-css-logical-spacing-caption — train

Group: `css-logical-spacing`

For .caption-text, set margin-inline to 0, padding-inline to 0.75rem, padding-block to 0.25rem. Return one rule.

```css
.caption-text {
  margin-inline: 0;
  padding-inline: 0.75rem;
  padding-block: 0.25rem;
}
```

#### pair-css-logical-spacing-notice — train

Group: `css-logical-spacing`

For .notice-text, set margin-inline to auto, padding-inline to 1rem, padding-block to 0.5rem. Return one rule.

```css
.notice-text {
  margin-inline: auto;
  padding-inline: 1rem;
  padding-block: 0.5rem;
}
```

#### pair-css-markers-roman — train

Group: `css-markers`

For .chapters, set list-style-type to upper-roman, list-style-position to outside. Return one rule.

```css
.chapters {
  list-style-type: upper-roman;
  list-style-position: outside;
}
```

#### pair-css-markers-square — train

Group: `css-markers`

For .checklist, set list-style-type to square, list-style-position to inside. Return one rule.

```css
.checklist {
  list-style-type: square;
  list-style-position: inside;
}
```

#### pair-css-numeric-elapsed — validation

Group: `css-numeric`

For .elapsed-time, set font-variant-numeric to tabular-nums, text-align to center. Return one rule.

```css
.elapsed-time {
  font-variant-numeric: tabular-nums;
  text-align: center;
}
```

#### pair-css-numeric-score — validation

Group: `css-numeric`

For .score-value, set font-variant-numeric to tabular-nums, text-align to right. Return one rule.

```css
.score-value {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
```

### JavaScript

#### pair-javascript-array-search-positive — validation

Group: `javascript-array-search`

Write firstPositive(values), returning the first finite number greater than zero in an array. Ignore other values. Return null when absent or input is not an array.

```javascript
function firstPositive(values) {
  if (!Array.isArray(values)) return null;
  const found = values.find(value => Number.isFinite(value) && value > 0);
  return found === undefined ? null : found;
}
```

Review cases (not executed): `[{"arguments": [[-2, "4", 0, 3, 8]], "expected": 3}, {"arguments": [[]], "expected": null}, {"arguments": [null], "expected": null}]`

#### pair-javascript-array-search-text — validation

Group: `javascript-array-search`

Write firstNonblank(values), finding the first string with non-whitespace content in an array and returning it trimmed. Return an empty string when absent or input is not an array.

```javascript
function firstNonblank(values) {
  if (!Array.isArray(values)) return "";
  const found = values.find(value => typeof value === "string" && value.trim().length > 0);
  return found === undefined ? "" : found.trim();
}
```

Review cases (not executed): `[{"arguments": [[null, " ", " ok ", "later"]], "expected": "ok"}, {"arguments": [[]], "expected": ""}, {"arguments": ["ok"], "expected": ""}]`

#### pair-javascript-calendar-february — train

Group: `javascript-calendar`

Write daysInFebruary(year) for positive integer Gregorian years: 29 in leap years, otherwise 28. Return null for invalid years.

```javascript
function daysInFebruary(year) {
  if (!Number.isInteger(year) || year <= 0) return null;
  const leap = year % 400 === 0 || (year % 4 === 0 && year % 100 !== 0);
  return leap ? 29 : 28;
}
```

Review cases (not executed): `[{"arguments": [2000], "expected": 29}, {"arguments": [1900], "expected": 28}, {"arguments": [2023], "expected": 28}, {"arguments": [-1], "expected": null}]`

#### pair-javascript-calendar-leap — train

Group: `javascript-calendar`

Write isLeapYear(year) for the Gregorian calendar. Positive integer years divisible by 400, or by 4 but not 100, are leap years; invalid years return false.

```javascript
function isLeapYear(year) {
  return Number.isInteger(year) && year > 0 && (year % 400 === 0 || (year % 4 === 0 && year % 100 !== 0));
}
```

Review cases (not executed): `[{"arguments": [2000], "expected": true}, {"arguments": [1900], "expected": false}, {"arguments": [2024], "expected": true}, {"arguments": [0], "expected": false}]`

#### pair-javascript-parity-even — train

Group: `javascript-parity`

Write isEven(value), returning true only for even integers. Return false for non-integers or non-number inputs.

```javascript
function isEven(value) {
  return Number.isInteger(value) && value % 2 === 0;
}
```

Review cases (not executed): `[{"arguments": [-4], "expected": true}, {"arguments": [3], "expected": false}, {"arguments": [2.5], "expected": false}]`

#### pair-javascript-parity-odd — train

Group: `javascript-parity`

Write isOdd(value), returning true only for odd integers, including negative odd integers. Return false for other inputs.

```javascript
function isOdd(value) {
  return Number.isInteger(value) && Math.abs(value % 2) === 1;
}
```

Review cases (not executed): `[{"arguments": [-3], "expected": true}, {"arguments": [4], "expected": false}, {"arguments": ["3"], "expected": false}]`

#### pair-javascript-rectangle-area — train

Group: `javascript-rectangle`

Write rectangleArea(width, height). Return their product for finite nonnegative numbers; otherwise return null.

```javascript
function rectangleArea(width, height) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 0 || height < 0) return null;
  return width * height;
}
```

Review cases (not executed): `[{"arguments": [3, 4], "expected": 12}, {"arguments": [0, 5], "expected": 0}, {"arguments": [-1, 4], "expected": null}]`

#### pair-javascript-rectangle-perimeter — train

Group: `javascript-rectangle`

Write rectanglePerimeter(width, height). Return twice the sum of the sides for finite nonnegative numbers; otherwise return null.

```javascript
function rectanglePerimeter(width, height) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 0 || height < 0) return null;
  return 2 * (width + height);
}
```

Review cases (not executed): `[{"arguments": [3, 4], "expected": 14}, {"arguments": [0, 5], "expected": 10}, {"arguments": ["3", 4], "expected": null}]`

#### pair-javascript-repetition-divider — validation

Group: `javascript-repetition`

Write makeDivider(symbol, width), repeating a string whose JavaScript length is exactly 1 for integer widths from 0 through 64. Return an empty string for invalid arguments.

```javascript
function makeDivider(symbol, width) {
  if (typeof symbol !== "string" || symbol.length !== 1 || !Number.isInteger(width) || width < 0 || width > 64) return "";
  return symbol.repeat(width);
}
```

Review cases (not executed): `[{"arguments": ["-", 4], "expected": "----"}, {"arguments": ["ab", 4], "expected": ""}, {"arguments": ["-", 0], "expected": ""}]`

#### pair-javascript-repetition-text — validation

Group: `javascript-repetition`

Write repeatText(text, count). Repeat a string count times for integer counts from 0 through 100. Return an empty string for invalid arguments.

```javascript
function repeatText(text, count) {
  if (typeof text !== "string" || !Number.isInteger(count) || count < 0 || count > 100) return "";
  return text.repeat(count);
}
```

Review cases (not executed): `[{"arguments": ["ab", 3], "expected": "ababab"}, {"arguments": ["ab", 0], "expected": ""}, {"arguments": ["ab", 101], "expected": ""}]`

#### pair-javascript-temperature-celsius — train

Group: `javascript-temperature`

Write toCelsius(fahrenheit), converting a finite Fahrenheit number to Celsius. Return null for non-number or non-finite input.

```javascript
function toCelsius(fahrenheit) {
  if (!Number.isFinite(fahrenheit)) return null;
  return (fahrenheit - 32) * 5 / 9;
}
```

Review cases (not executed): `[{"arguments": [32], "expected": 0}, {"arguments": [212], "expected": 100}, {"arguments": [null], "expected": null}]`

#### pair-javascript-temperature-fahrenheit — train

Group: `javascript-temperature`

Write toFahrenheit(celsius), converting a finite Celsius number to Fahrenheit. Return null for non-number or non-finite input.

```javascript
function toFahrenheit(celsius) {
  if (!Number.isFinite(celsius)) return null;
  return celsius * 9 / 5 + 32;
}
```

Review cases (not executed): `[{"arguments": [0], "expected": 32}, {"arguments": [100], "expected": 212}, {"arguments": ["0"], "expected": null}]`
