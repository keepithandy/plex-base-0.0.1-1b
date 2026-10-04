# Curated request-following candidate: all 180 examples

**Pending owner approval for these exact records; not in training.**

The earlier twelve samples are approved separately. This candidate removes 180 rename-only variants, revises weak profiles, and preserves the previous draft. There are 60 examples per language, six conservative syntax profiles per topic, and 29 indivisible split groups. This is a small instruction-format experiment, not a sufficient scratch-pretraining corpus.

Canonical JSONL SHA-256: `9f6ad8eff96298f45880f9bfe831648364e2a7ed11996e7a7d91d5e984eb3d0b`.

Expected JavaScript cases are review notes, never executed. HTML tree checks and exact CSS declarations supplement the existing static checks. Checks establish supplied-answer consistency, not browser behavior or Plex capability.

## curated-html-ruby-01 — train

Family: `html-ruby`.

Use ruby with an rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby>Kyoto<rt>Kyo-to</rt></ruby>
```

## curated-html-ruby-02 — train

Family: `html-ruby`.

Put the whole ruby pronunciation annotation inside a paragraph. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<p><ruby>Kyoto<rt>Kyo-to</rt></ruby></p>
```

## curated-html-ruby-03 — train

Family: `html-ruby`.

Use ruby with rt and rp parentheses around the reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby>Kyoto<rp>(</rp><rt>Kyo-to</rt><rp>)</rp></ruby>
```

## curated-html-ruby-04 — train

Family: `html-ruby`.

Put the word in strong inside ruby, followed by its rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby><strong>Kyoto</strong><rt>Kyo-to</rt></ruby>
```

## curated-html-ruby-05 — train

Family: `html-ruby`.

Put the word in em inside ruby, followed by its rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby><em>Kyoto</em><rt>Kyo-to</rt></ruby>
```

## curated-html-ruby-06 — train

Family: `html-ruby`.

Put the whole ruby pronunciation annotation inside a span. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<span><ruby>Kyoto<rt>Kyo-to</rt></ruby></span>
```

## curated-html-disclosure-01 — train

Family: `html-disclosure`.

Make a collapsed details with summary and paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## curated-html-disclosure-02 — train

Family: `html-disclosure`.

Make an expanded details with summary and paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## curated-html-disclosure-03 — train

Family: `html-disclosure`.

Make a collapsed details with summary and a one-item unordered list. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><ul><li>A quiet destination.</li></ul></details>
```

## curated-html-disclosure-04 — train

Family: `html-disclosure`.

Make an expanded details with summary and a one-item ordered list. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><ol><li>A quiet destination.</li></ol></details>
```

## curated-html-disclosure-05 — train

Family: `html-disclosure`.

Make a collapsed details with summary and an emphasized body paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><p><em>A quiet destination.</em></p></details>
```

## curated-html-disclosure-06 — train

Family: `html-disclosure`.

Make an expanded details with summary and a strongly emphasized body paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><p><strong>A quiet destination.</strong></p></details>
```

## curated-html-bidi-01 — validation

Family: `html-bidi`.

Isolate the word using bdi. Use word "Kyoto". Return only the fragment.

```html
<bdi>Kyoto</bdi>
```

## curated-html-bidi-02 — validation

Family: `html-bidi`.

Put a bdi-isolated word inside a paragraph. Use word "Kyoto". Return only the fragment.

```html
<p><bdi>Kyoto</bdi></p>
```

## curated-html-bidi-03 — validation

Family: `html-bidi`.

Put a bdi-isolated word inside strong. Use word "Kyoto". Return only the fragment.

```html
<strong><bdi>Kyoto</bdi></strong>
```

## curated-html-bidi-04 — validation

Family: `html-bidi`.

Put a bdi-isolated word inside em. Use word "Kyoto". Return only the fragment.

```html
<em><bdi>Kyoto</bdi></em>
```

## curated-html-bidi-05 — validation

Family: `html-bidi`.

Put a bdi-isolated word inside a span with class isolated. Use word "Kyoto". Return only the fragment.

```html
<span class="isolated"><bdi>Kyoto</bdi></span>
```

## curated-html-bidi-06 — validation

Family: `html-bidi`.

Put a bdi-isolated word inside a one-item unordered list. Use word "Kyoto". Return only the fragment.

```html
<ul><li><bdi>Kyoto</bdi></li></ul>
```

## curated-html-quote-01 — validation

Family: `html-quote`.

Mark the sentence as an inline quotation using q. Use sentence "A quiet destination.". Return only the fragment.

```html
<q>A quiet destination.</q>
```

## curated-html-quote-02 — validation

Family: `html-quote`.

Put an inline q quotation inside a paragraph. Use sentence "A quiet destination.". Return only the fragment.

```html
<p><q>A quiet destination.</q></p>
```

## curated-html-quote-03 — validation

Family: `html-quote`.

Emphasize an inline q quotation using em around q. Use sentence "A quiet destination.". Return only the fragment.

```html
<em><q>A quiet destination.</q></em>
```

## curated-html-quote-04 — validation

Family: `html-quote`.

Put an inline q quotation inside strong. Use sentence "A quiet destination.". Return only the fragment.

```html
<strong><q>A quiet destination.</q></strong>
```

## curated-html-quote-05 — validation

Family: `html-quote`.

Put an inline q quotation inside a span with class quotation. Use sentence "A quiet destination.". Return only the fragment.

```html
<span class="quotation"><q>A quiet destination.</q></span>
```

## curated-html-quote-06 — validation

Family: `html-quote`.

Put an inline q quotation inside a one-item ordered list. Use sentence "A quiet destination.". Return only the fragment.

```html
<ol><li><q>A quiet destination.</q></li></ol>
```

## curated-html-abbreviation-01 — train

Family: `html-abbreviation`.

Mark the word as abbr with the sentence as its title. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<abbr title="Input and output">I/O</abbr>
```

## curated-html-abbreviation-02 — train

Family: `html-abbreviation`.

Put that titled abbreviation inside a paragraph. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<p><abbr title="Input and output">I/O</abbr></p>
```

## curated-html-abbreviation-03 — train

Family: `html-abbreviation`.

Put that titled abbreviation inside strong. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<strong><abbr title="Input and output">I/O</abbr></strong>
```

## curated-html-abbreviation-04 — train

Family: `html-abbreviation`.

Put that titled abbreviation inside em. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<em><abbr title="Input and output">I/O</abbr></em>
```

## curated-html-abbreviation-05 — train

Family: `html-abbreviation`.

Put that titled abbreviation inside a span with class term. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<span class="term"><abbr title="Input and output">I/O</abbr></span>
```

## curated-html-abbreviation-06 — train

Family: `html-abbreviation`.

Put that titled abbreviation inside a one-item unordered list. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<ul><li><abbr title="Input and output">I/O</abbr></li></ul>
```

## curated-html-description-01 — train

Family: `html-description`.

Use dl with one dt word and one dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl>
```

## curated-html-description-02 — train

Family: `html-description`.

Use dl with the dt word inside strong and one dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt><strong>Kyoto</strong></dt><dd>A quiet destination.</dd></dl>
```

## curated-html-description-03 — train

Family: `html-description`.

Use dl with one dt word and the dd sentence inside em. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><em>A quiet destination.</em></dd></dl>
```

## curated-html-description-04 — train

Family: `html-description`.

Use dl with one dt word and the dd sentence inside a paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><p>A quiet destination.</p></dd></dl>
```

## curated-html-description-05 — train

Family: `html-description`.

Wrap a one-term dl in a section; use dt for the word and dd for the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<section><dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl></section>
```

## curated-html-description-06 — train

Family: `html-description`.

Use dl with a div wrapping its dt word and dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><div><dt>Kyoto</dt><dd>A quiet destination.</dd></div></dl>
```

## curated-html-progress-01 — train

Family: `html-progress`.

Make determinate progress with value 35 and max 100. Return only the fragment.

```html
<progress value="35" max="100"></progress>
```

## curated-html-progress-02 — train

Family: `html-progress`.

Make determinate progress with value 35, max 100, and the word as fallback text. Use word "Kyoto". Return only the fragment.

```html
<progress value="35" max="100">Kyoto</progress>
```

## curated-html-progress-03 — train

Family: `html-progress`.

Make indeterminate progress with the word as fallback text and no value attribute. Use word "Kyoto". Return only the fragment.

```html
<progress>Kyoto</progress>
```

## curated-html-progress-04 — train

Family: `html-progress`.

Wrap determinate progress with value 35 and max 100 in a paragraph. Return only the fragment.

```html
<p><progress value="35" max="100"></progress></p>
```

## curated-html-progress-05 — train

Family: `html-progress`.

Put indeterminate progress with the word as fallback text and no value attribute inside a span. Use word "Kyoto". Return only the fragment.

```html
<span><progress>Kyoto</progress></span>
```

## curated-html-progress-06 — train

Family: `html-progress`.

Put determinate progress with value 35 and max 100 inside a div with class tracking. Return only the fragment.

```html
<div class="tracking"><progress value="35" max="100"></progress></div>
```

## curated-html-meter-01 — train

Family: `html-meter`.

Make a meter with min 0, max 100, and value 35. Return only the fragment.

```html
<meter min="0" max="100" value="35"></meter>
```

## curated-html-meter-02 — train

Family: `html-meter`.

Make a meter with min 0, max 100, value 35, and the word as fallback text. Use word "Kyoto". Return only the fragment.

```html
<meter min="0" max="100" value="35">Kyoto</meter>
```

## curated-html-meter-03 — train

Family: `html-meter`.

Make a meter with min 0, max 100, value 35, low 20, high 80, and optimum 50. Return only the fragment.

```html
<meter min="0" max="100" value="35" low="20" high="80" optimum="50"></meter>
```

## curated-html-meter-04 — train

Family: `html-meter`.

Put a meter with min 0, max 100, and value 35 inside a paragraph. Return only the fragment.

```html
<p><meter min="0" max="100" value="35"></meter></p>
```

## curated-html-meter-05 — train

Family: `html-meter`.

Put a meter with min 0, max 100, and value 35 inside a span. Return only the fragment.

```html
<span><meter min="0" max="100" value="35"></meter></span>
```

## curated-html-meter-06 — train

Family: `html-meter`.

Put a meter with min 0, max 100, and value 35 inside a div with class reading. Return only the fragment.

```html
<div class="reading"><meter min="0" max="100" value="35"></meter></div>
```

## curated-html-contact-01 — validation

Family: `html-contact`.

Put the word in address as plain contact text. Use word "Kyoto". Return only the fragment.

```html
<address>Kyoto</address>
```

## curated-html-contact-02 — validation

Family: `html-contact`.

Put the word in a paragraph inside address. Use word "Kyoto". Return only the fragment.

```html
<address><p>Kyoto</p></address>
```

## curated-html-contact-03 — validation

Family: `html-contact`.

Put the word in strong inside address. Use word "Kyoto". Return only the fragment.

```html
<address><strong>Kyoto</strong></address>
```

## curated-html-contact-04 — validation

Family: `html-contact`.

Put the word in a span with class contact inside address. Use word "Kyoto". Return only the fragment.

```html
<address><span class="contact">Kyoto</span></address>
```

## curated-html-contact-05 — validation

Family: `html-contact`.

Put the word then br then the sentence inside address. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<address>Kyoto<br>A quiet destination.</address>
```

## curated-html-contact-06 — validation

Family: `html-contact`.

Put two paragraphs in address: the word then the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<address><p>Kyoto</p><p>A quiet destination.</p></address>
```

## curated-html-heading-group-01 — train

Family: `html-heading-group`.

Make hgroup containing h1 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h1>Kyoto</h1><p>A quiet destination.</p></hgroup>
```

## curated-html-heading-group-02 — train

Family: `html-heading-group`.

Make hgroup containing h2 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup>
```

## curated-html-heading-group-03 — train

Family: `html-heading-group`.

Make hgroup containing h3 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h3>Kyoto</h3><p>A quiet destination.</p></hgroup>
```

## curated-html-heading-group-04 — train

Family: `html-heading-group`.

Make hgroup containing p with the sentence then h2 with the word. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><p>A quiet destination.</p><h2>Kyoto</h2></hgroup>
```

## curated-html-heading-group-05 — train

Family: `html-heading-group`.

Make hgroup containing h2 with the word and p with the sentence inside em. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p><em>A quiet destination.</em></p></hgroup>
```

## curated-html-heading-group-06 — train

Family: `html-heading-group`.

Wrap hgroup in a header; put the word in h2 and the sentence in p. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<header><hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup></header>
```

## curated-css-logical-border-01 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Add a 2px solid #334155 border on the inline start edge only. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-inline-start: 2px solid #334155;
}
```

## curated-css-logical-border-02 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Add a 2px solid #334155 border on the inline end edge only. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-inline-end: 2px solid #334155;
}
```

## curated-css-logical-border-03 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-block-start: 2px dashed #334155;
}
```

## curated-css-logical-border-04 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Add a 2px dashed #334155 border on the block end edge only. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-block-end: 2px dashed #334155;
}
```

## curated-css-logical-border-05 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Add a 2px solid #334155 inline start border and remove the inline end border. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-inline-start: 2px solid #334155;
  border-inline-end: 0;
}
```

## curated-css-logical-border-06 — validation

Family: `css-logical-border`.

For .rf-logical-border-alpha: Remove the block start border and add a 2px solid #334155 block end border. Return one rule with only the requested declarations.

```css
.rf-logical-border-alpha {
  border-block-start: 0;
  border-block-end: 2px solid #334155;
}
```

## curated-css-aspect-01 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred square aspect ratio. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 1 / 1;
}
```

## curated-css-aspect-02 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred 16:9 aspect ratio with width 240px. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 16 / 9;
  width: 240px;
}
```

## curated-css-aspect-03 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred 4:3 aspect ratio and cap width at 100%. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 4 / 3;
  max-width: 100%;
}
```

## curated-css-aspect-04 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred square aspect ratio with height 120px. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 1 / 1;
  height: 120px;
}
```

## curated-css-aspect-05 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred 16:9 aspect ratio and include padding inside the border-box size. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 16 / 9;
  box-sizing: border-box;
}
```

## curated-css-aspect-06 — train

Family: `css-aspect`.

For .rf-aspect-alpha: Use a preferred 4:3 aspect ratio and a minimum width of 180px. Return one rule with only the requested declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 4 / 3;
  min-width: 180px;
}
```

## curated-css-outline-01 — train

Family: `css-outline`.

For .rf-outline-alpha: Use a solid outline style. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline-style: solid;
}
```

## curated-css-outline-02 — train

Family: `css-outline`.

For .rf-outline-alpha: Use a 2px solid #334155 outline. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline: 2px solid #334155;
}
```

## curated-css-outline-03 — train

Family: `css-outline`.

For .rf-outline-alpha: Use a 2px solid #334155 outline offset outward by 4px. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline: 2px solid #334155;
  outline-offset: 4px;
}
```

## curated-css-outline-04 — train

Family: `css-outline`.

For .rf-outline-alpha: Remove both the outline and any box shadow. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline: 0;
  box-shadow: none;
}
```

## curated-css-outline-05 — train

Family: `css-outline`.

For .rf-outline-alpha: Use a dotted outline style, 3px width, and -2px offset. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline-style: dotted;
  outline-width: 3px;
  outline-offset: -2px;
}
```

## curated-css-outline-06 — train

Family: `css-outline`.

For .rf-outline-alpha: Use a dashed outline style and #334155 outline color. Return one rule with only the requested declarations.

```css
.rf-outline-alpha {
  outline-style: dashed;
  outline-color: #334155;
}
```

## curated-css-cursor-01 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a pointer cursor. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: pointer;
}
```

## curated-css-cursor-02 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a forbidden cursor and opacity 0.5. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: not-allowed;
  opacity: 0.5;
}
```

## curated-css-cursor-03 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a grab cursor and prevent text selection. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: grab;
  user-select: none;
}
```

## curated-css-cursor-04 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a wait cursor and disable pointer targeting. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: wait;
  pointer-events: none;
}
```

## curated-css-cursor-05 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a text cursor and color #334155. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: text;
  color: #334155;
}
```

## curated-css-cursor-06 — validation

Family: `css-cursor`.

For .rf-cursor-alpha: Show a default cursor and display as a block. Return one rule with only the requested declarations.

```css
.rf-cursor-alpha {
  cursor: default;
  display: block;
}
```

## curated-css-whitespace-01 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Keep text on one unwrapped line. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: nowrap;
}
```

## curated-css-whitespace-02 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Preserve whitespace while allowing wraps, including breaks anywhere in long tokens. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

## curated-css-whitespace-03 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Preserve whitespace and use a tab size of 4. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: pre;
  tab-size: 4;
}
```

## curated-css-whitespace-04 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Collapse ordinary whitespace, allow wrapping, and use line-height 1.5. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: normal;
  line-height: 1.5;
}
```

## curated-css-whitespace-05 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Preserve spaces with break-spaces and set word-spacing to 2px. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: break-spaces;
  word-spacing: 2px;
}
```

## curated-css-whitespace-06 — train

Family: `css-whitespace`.

For .rf-whitespace-alpha: Preserve newlines but collapse spaces, and indent the first line by 1em. Return one rule with only the requested declarations.

```css
.rf-whitespace-alpha {
  white-space: pre-line;
  text-indent: 1em;
}
```

## curated-css-decoration-01 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Underline text. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
}
```

## curated-css-decoration-02 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Use a wavy underline. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
  text-decoration-style: wavy;
}
```

## curated-css-decoration-03 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Use an underline colored #334155. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
  text-decoration-color: #334155;
}
```

## curated-css-decoration-04 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Use both underline and overline with underline offset 4px. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline overline;
  text-underline-offset: 4px;
}
```

## curated-css-decoration-05 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Use line-through with a thickness of 2px. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: line-through;
  text-decoration-thickness: 2px;
}
```

## curated-css-decoration-06 — train

Family: `css-decoration`.

For .rf-decoration-alpha: Use a solid underline and disable automatic ink skipping. Return one rule with only the requested declarations.

```css
.rf-decoration-alpha {
  text-decoration: underline solid;
  text-decoration-skip-ink: none;
}
```

## curated-css-overflow-01 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Allow automatic horizontal scrolling. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow-x: auto;
}
```

## curated-css-overflow-02 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Always provide vertical scrolling. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow-y: scroll;
}
```

## curated-css-overflow-03 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Hide overflow on both axes. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow: hidden;
}
```

## curated-css-overflow-04 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Clip overflow and create a flow-root formatting context. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow: clip;
  display: flow-root;
}
```

## curated-css-overflow-05 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Allow automatic horizontal scrolling and hide vertical overflow. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow-x: auto;
  overflow-y: hidden;
}
```

## curated-css-overflow-06 — train

Family: `css-overflow`.

For .rf-overflow-alpha: Allow automatic scrolling on both axes and limit height to 200px. Return one rule with only the requested declarations.

```css
.rf-overflow-alpha {
  overflow: auto;
  max-height: 200px;
}
```

## curated-css-table-01 — train

Family: `css-table`.

For .rf-table-alpha: Use automatic table layout. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  table-layout: auto;
}
```

## curated-css-table-02 — train

Family: `css-table`.

For .rf-table-alpha: Use fixed table layout and width 100%. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  table-layout: fixed;
  width: 100%;
}
```

## curated-css-table-03 — train

Family: `css-table`.

For .rf-table-alpha: Collapse table borders. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  border-collapse: collapse;
}
```

## curated-css-table-04 — train

Family: `css-table`.

For .rf-table-alpha: Keep borders separate with 8px spacing. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  border-collapse: separate;
  border-spacing: 8px;
}
```

## curated-css-table-05 — train

Family: `css-table`.

For .rf-table-alpha: Place the table caption below the table. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  caption-side: bottom;
}
```

## curated-css-table-06 — train

Family: `css-table`.

For .rf-table-alpha: Hide empty cells and keep borders separate. Return one rule with only the requested declarations.

```css
.rf-table-alpha {
  empty-cells: hide;
  border-collapse: separate;
}
```

## curated-css-columns-01 — validation

Family: `css-columns`.

For .rf-columns-alpha: Use two text columns. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-count: 2;
}
```

## curated-css-columns-02 — validation

Family: `css-columns`.

For .rf-columns-alpha: Use a preferred column width of 180px. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-width: 180px;
}
```

## curated-css-columns-03 — validation

Family: `css-columns`.

For .rf-columns-alpha: Use three columns separated by 24px gaps. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-count: 3;
  column-gap: 24px;
}
```

## curated-css-columns-04 — validation

Family: `css-columns`.

For .rf-columns-alpha: Use two columns with a 1px solid #334155 column rule. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-count: 2;
  column-rule: 1px solid #334155;
}
```

## curated-css-columns-05 — validation

Family: `css-columns`.

For .rf-columns-alpha: Make the element span every column. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-span: all;
}
```

## curated-css-columns-06 — validation

Family: `css-columns`.

For .rf-columns-alpha: Fill columns sequentially with column-fill auto and height 300px. Return one rule with only the requested declarations.

```css
.rf-columns-alpha {
  column-fill: auto;
  height: 300px;
}
```

## curated-css-object-fit-01 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Contain the entire image in its existing box. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: contain;
}
```

## curated-css-object-fit-02 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Cover the existing box with the image and align it at the right bottom. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: cover;
  object-position: right bottom;
}
```

## curated-css-object-fit-03 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Stretch the image to fill its box and display it as a block. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: fill;
  display: block;
}
```

## curated-css-object-fit-04 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Contain the image and limit its width to 100%. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: contain;
  max-width: 100%;
}
```

## curated-css-object-fit-05 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Use scale-down image fitting and set its width to 160px. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: scale-down;
  width: 160px;
}
```

## curated-css-object-fit-06 — train

Family: `css-object-fit`.

For .rf-object-fit-alpha: Do not resize the image content for fitting and set its box height to 120px. Return one rule with only the requested declarations.

```css
.rf-object-fit-alpha {
  object-fit: none;
  height: 120px;
}
```

## curated-javascript-binary-01 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return a plus b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a + b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 7}]`

## curated-javascript-binary-02 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return a minus b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a - b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": -1}]`

## curated-javascript-binary-03 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return the product of a and b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a * b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 12}]`

## curated-javascript-binary-04 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return the larger number. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.max(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 4}]`

## curated-javascript-binary-05 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return the smaller number. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.min(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 3}]`

## curated-javascript-binary-06 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(a, b) for finite numbers a and b; return the absolute difference. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.abs(a - b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 1}]`

## curated-javascript-bound-01 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; cap value at the upper limit using a conditional expression. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value > limit ? limit : value;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 4}]`

## curated-javascript-bound-02 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; raise value to the lower limit using a conditional expression. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value < limit ? limit : value;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 10}]`

## curated-javascript-bound-03 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value exceeds limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value > limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## curated-javascript-bound-04 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value is below limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value < limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": true}]`

## curated-javascript-bound-05 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value equals limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value === limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## curated-javascript-bound-06 — validation

Family: `javascript-numeric-comparison`.

Write transformAlpha(value, limit) for finite numbers value and limit; return the absolute distance using a conditional expression. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value > limit ? value - limit : limit - value;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 6}]`

## curated-javascript-division-01 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.trunc(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## curated-javascript-division-02 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded down. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.floor(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -3}]`

## curated-javascript-division-03 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded up. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.ceil(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## curated-javascript-division-04 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the JavaScript remainder. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a % b;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -1}]`

## curated-javascript-division-05 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return whether a is divisible by b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a % b === 0;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": false}]`

## curated-javascript-division-06 — validation

Family: `javascript-division`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the absolute JavaScript remainder. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.abs(a % b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": 1}]`

## curated-javascript-conversion-01 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a finite numeric value; convert seconds to milliseconds. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value * 1000;
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": 2000}]`

## curated-javascript-conversion-02 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a finite numeric value; convert milliseconds to seconds. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value / 1000;
}
```

Expected cases (not executed): `[{"arguments": [2000], "expected": 2}]`

## curated-javascript-conversion-03 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a nonnegative finite numeric value; convert nonnegative seconds to completed whole minutes, rounded down. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.floor(value / 60);
}
```

Expected cases (not executed): `[{"arguments": [125], "expected": 2}]`

## curated-javascript-conversion-04 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a finite numeric value; return an object with centimeters and millimeters converted from meters. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return { centimeters: value * 100, millimeters: value * 1000 };
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": {"centimeters": 200, "millimeters": 2000}}]`

## curated-javascript-conversion-05 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a finite numeric value; return an array containing seconds then milliseconds converted from minutes. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return [value * 60, value * 60000];
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": [120, 120000]}]`

## curated-javascript-conversion-06 — train

Family: `javascript-conversion`.

Write transformAlpha(value) for a nonnegative finite numeric value; convert nonnegative milliseconds to seconds rounded up. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.ceil(value / 1000);
}
```

Expected cases (not executed): `[{"arguments": [1500], "expected": 2}]`

## curated-javascript-classification-01 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; report whether value is an integer. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Number.isInteger(value);
}
```

Expected cases (not executed): `[{"arguments": [2.5], "expected": false}]`

## curated-javascript-classification-02 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; report whether value is positive. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value > 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": false}]`

## curated-javascript-classification-03 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; report whether value is negative. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value < 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": true}]`

## curated-javascript-classification-04 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; report whether value is zero. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value === 0;
}
```

Expected cases (not executed): `[{"arguments": [0], "expected": true}]`

## curated-javascript-classification-05 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; return its sign using Math.sign. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.sign(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": -1}]`

## curated-javascript-classification-06 — train

Family: `javascript-classification`.

Write transformAlpha(value) for a finite numeric value; return its absolute magnitude. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.abs(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": 2}]`

## curated-javascript-array-lookup-01 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether items includes value. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.includes(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## curated-javascript-array-lookup-02 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return the first index of value or -1. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.indexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 0}]`

## curated-javascript-array-lookup-03 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return the last index of value or -1. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.lastIndexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## curated-javascript-array-lookup-04 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether value equals the first element, using strict equality. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.length > 0 && items[0] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## curated-javascript-array-lookup-05 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether value equals the last element, using strict equality. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.length > 0 && items[items.length - 1] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 4], "expected": false}]`

## curated-javascript-array-lookup-06 — train

Family: `javascript-array-lookup`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; count elements strictly equal to value. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.filter(item => item === value).length;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## curated-javascript-array-copy-01 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2, 3]}]`

## curated-javascript-array-copy-02 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a reversed shallow copy. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice().reverse();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [3, 2, 1]}]`

## curated-javascript-array-copy-03 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy omitting the first element. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## curated-javascript-array-copy-04 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy omitting the last element. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(0, -1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## curated-javascript-array-copy-05 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy of at most the first two elements. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(0, 2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## curated-javascript-array-copy-06 — train

Family: `javascript-array-copy`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy of at most the last two elements. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(-2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## curated-javascript-string-slice-01 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the first count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.slice(0, count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "ab"}]`

## curated-javascript-string-slice-02 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the first count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.slice(count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "cd"}]`

## curated-javascript-string-slice-03 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the last count code units, or empty if count is zero. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return count === 0 ? '' : text.slice(-count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": ""}]`

## curated-javascript-string-slice-04 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the last count code units, returning text unchanged for zero. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return count === 0 ? text : text.slice(0, -count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": "abcd"}]`

## curated-javascript-string-slice-05 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has more than count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.length > count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": true}]`

## curated-javascript-string-slice-06 — train

Family: `javascript-string-slice`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has exactly count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.length === count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": false}]`

## curated-javascript-string-build-01 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; surround text with square brackets. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return '[' + text + ']';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "[oak]"}]`

## curated-javascript-string-build-02 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; return text with outer whitespace removed. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return text.trim();
}
```

Expected cases (not executed): `[{"arguments": [" oak "], "expected": "oak"}]`

## curated-javascript-string-build-03 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; return text in uppercase. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return text.toUpperCase();
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "OAK"}]`

## curated-javascript-string-build-04 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; return text in lowercase. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return text.toLowerCase();
}
```

Expected cases (not executed): `[{"arguments": ["OAK"], "expected": "oak"}]`

## curated-javascript-string-build-05 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; return an array containing text twice. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return [text, text];
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": ["oak", "oak"]}]`

## curated-javascript-string-build-06 — train

Family: `javascript-string-build`.

Write transformAlpha(text) for a string text; return an object whose label property contains text. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return { label: text };
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": {"label": "oak"}}]`

## curated-javascript-object-lookup-01 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return the property value. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return record[key];
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": 3}]`

## curated-javascript-object-lookup-02 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; report whether record has an own property named key. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.prototype.hasOwnProperty.call(record, key);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": true}]`

## curated-javascript-object-lookup-03 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable string keys; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.keys(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": ["a"]}]`

## curated-javascript-object-lookup-04 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable values; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.values(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [3]}]`

## curated-javascript-object-lookup-05 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable key-value pairs; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.entries(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [["a", 3]]}]`

## curated-javascript-object-lookup-06 — validation

Family: `javascript-object-lookup`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; report whether the property value is undefined. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return record[key] === undefined;
}
```

Expected cases (not executed): `[{"arguments": [{}, "a"], "expected": true}]`
