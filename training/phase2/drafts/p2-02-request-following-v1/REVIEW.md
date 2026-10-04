# Request-following candidate: all 360 examples

**Pending review: not approved or included in training.**

Thirty topic families, six declared requirement profiles per topic, two variants per profile; 29 split groups after merging shared arithmetic/bound templates. All relatives stay together. The approved twelve samples illustrate the style but are not included or replaced here. JavaScript behavior cases are expectations, never executed. Static checks are not a correctness proof. Some profiles change values rather than structure: this draft does not yet meet the proposal's six-distinct-patterns target.

Canonical JSONL SHA-256: `f48ae375ca8c0bca55bbb9a4471f418909db5ec857d99473c25d91d70baad6a5`.

Training format is the unchanged inference prompt, newline, answer; EOS is appended by the tokenizer after approval.

## rf-html-ruby-01-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-1`.

Use ruby with an rt reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby>Kyoto<rt>Kyo-to</rt></ruby>
```

## rf-html-ruby-01-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-1`.

Use ruby with an rt reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby>Osaka<rt>O-sa-ka</rt></ruby>
```

## rf-html-ruby-02-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-2`.

Use ruby with rb for the word and rt for its reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><rb>Kyoto</rb><rt>Kyo-to</rt></ruby>
```

## rf-html-ruby-02-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-2`.

Use ruby with rb for the word and rt for its reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><rb>Osaka</rb><rt>O-sa-ka</rt></ruby>
```

## rf-html-ruby-03-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-3`.

Use ruby with rt and rp parentheses around the reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby>Kyoto<rp>(</rp><rt>Kyo-to</rt><rp>)</rp></ruby>
```

## rf-html-ruby-03-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-3`.

Use ruby with rt and rp parentheses around the reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby>Osaka<rp>(</rp><rt>O-sa-ka</rt><rp>)</rp></ruby>
```

## rf-html-ruby-04-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-4`.

Put the word in strong inside ruby, followed by its rt reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><strong>Kyoto</strong><rt>Kyo-to</rt></ruby>
```

## rf-html-ruby-04-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-4`.

Put the word in strong inside ruby, followed by its rt reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><strong>Osaka</strong><rt>O-sa-ka</rt></ruby>
```

## rf-html-ruby-05-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-5`.

Put the word in em inside ruby, followed by its rt reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><em>Kyoto</em><rt>Kyo-to</rt></ruby>
```

## rf-html-ruby-05-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-5`.

Put the word in em inside ruby, followed by its rt reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ruby><em>Osaka</em><rt>O-sa-ka</rt></ruby>
```

## rf-html-ruby-06-1 — train

Family: `html-ruby`; template: `html/ruby/pattern-6`.

Put the whole ruby pronunciation annotation inside a span. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><ruby>Kyoto<rt>Kyo-to</rt></ruby></span>
```

## rf-html-ruby-06-2 — train

Family: `html-ruby`; template: `html/ruby/pattern-6`.

Put the whole ruby pronunciation annotation inside a span. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><ruby>Osaka<rt>O-sa-ka</rt></ruby></span>
```

## rf-html-disclosure-01-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-1`.

Make a collapsed details with summary and paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## rf-html-disclosure-01-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-1`.

Make a collapsed details with summary and paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Osaka</summary><p>A busy destination.</p></details>
```

## rf-html-disclosure-02-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-2`.

Make an expanded details with summary and paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## rf-html-disclosure-02-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-2`.

Make an expanded details with summary and paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Osaka</summary><p>A busy destination.</p></details>
```

## rf-html-disclosure-03-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-3`.

Make a collapsed details with summary and a one-item unordered list. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Kyoto</summary><ul><li>A quiet destination.</li></ul></details>
```

## rf-html-disclosure-03-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-3`.

Make a collapsed details with summary and a one-item unordered list. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Osaka</summary><ul><li>A busy destination.</li></ul></details>
```

## rf-html-disclosure-04-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-4`.

Make an expanded details with summary and a one-item ordered list. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Kyoto</summary><ol><li>A quiet destination.</li></ol></details>
```

## rf-html-disclosure-04-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-4`.

Make an expanded details with summary and a one-item ordered list. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Osaka</summary><ol><li>A busy destination.</li></ol></details>
```

## rf-html-disclosure-05-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-5`.

Make a collapsed details with summary and an emphasized body paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Kyoto</summary><p><em>A quiet destination.</em></p></details>
```

## rf-html-disclosure-05-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-5`.

Make a collapsed details with summary and an emphasized body paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details><summary>Osaka</summary><p><em>A busy destination.</em></p></details>
```

## rf-html-disclosure-06-1 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-6`.

Make an expanded details with summary and a strongly emphasized body paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Kyoto</summary><p><strong>A quiet destination.</strong></p></details>
```

## rf-html-disclosure-06-2 — train

Family: `html-disclosure`; template: `html/disclosure/pattern-6`.

Make an expanded details with summary and a strongly emphasized body paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<details open><summary>Osaka</summary><p><strong>A busy destination.</strong></p></details>
```

## rf-html-bidi-01-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-1`.

Isolate the word using bdi. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<bdi>Kyoto</bdi>
```

## rf-html-bidi-01-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-1`.

Isolate the word using bdi. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<bdi>Osaka</bdi>
```

## rf-html-bidi-02-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-2`.

Put a bdi-isolated word inside a paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><bdi>Kyoto</bdi></p>
```

## rf-html-bidi-02-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-2`.

Put a bdi-isolated word inside a paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><bdi>Osaka</bdi></p>
```

## rf-html-bidi-03-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-3`.

Put a bdi-isolated word inside strong. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<strong><bdi>Kyoto</bdi></strong>
```

## rf-html-bidi-03-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-3`.

Put a bdi-isolated word inside strong. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<strong><bdi>Osaka</bdi></strong>
```

## rf-html-bidi-04-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-4`.

Put a bdi-isolated word inside em. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<em><bdi>Kyoto</bdi></em>
```

## rf-html-bidi-04-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-4`.

Put a bdi-isolated word inside em. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<em><bdi>Osaka</bdi></em>
```

## rf-html-bidi-05-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-5`.

Put a bdi-isolated word inside a span with class isolated. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span class="isolated"><bdi>Kyoto</bdi></span>
```

## rf-html-bidi-05-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-5`.

Put a bdi-isolated word inside a span with class isolated. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span class="isolated"><bdi>Osaka</bdi></span>
```

## rf-html-bidi-06-1 — validation

Family: `html-bidi`; template: `html/bidi/pattern-6`.

Put a bdi-isolated word inside a one-item unordered list. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ul><li><bdi>Kyoto</bdi></li></ul>
```

## rf-html-bidi-06-2 — validation

Family: `html-bidi`; template: `html/bidi/pattern-6`.

Put a bdi-isolated word inside a one-item unordered list. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ul><li><bdi>Osaka</bdi></li></ul>
```

## rf-html-quote-01-1 — train

Family: `html-quote`; template: `html/quote/pattern-1`.

Mark the sentence as an inline quotation using q. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<q>A quiet destination.</q>
```

## rf-html-quote-01-2 — train

Family: `html-quote`; template: `html/quote/pattern-1`.

Mark the sentence as an inline quotation using q. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<q>A busy destination.</q>
```

## rf-html-quote-02-1 — train

Family: `html-quote`; template: `html/quote/pattern-2`.

Put an inline q quotation inside a paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><q>A quiet destination.</q></p>
```

## rf-html-quote-02-2 — train

Family: `html-quote`; template: `html/quote/pattern-2`.

Put an inline q quotation inside a paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><q>A busy destination.</q></p>
```

## rf-html-quote-03-1 — train

Family: `html-quote`; template: `html/quote/pattern-3`.

Emphasize an inline q quotation using em around q. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<em><q>A quiet destination.</q></em>
```

## rf-html-quote-03-2 — train

Family: `html-quote`; template: `html/quote/pattern-3`.

Emphasize an inline q quotation using em around q. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<em><q>A busy destination.</q></em>
```

## rf-html-quote-04-1 — train

Family: `html-quote`; template: `html/quote/pattern-4`.

Put an inline q quotation inside strong. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<strong><q>A quiet destination.</q></strong>
```

## rf-html-quote-04-2 — train

Family: `html-quote`; template: `html/quote/pattern-4`.

Put an inline q quotation inside strong. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<strong><q>A busy destination.</q></strong>
```

## rf-html-quote-05-1 — train

Family: `html-quote`; template: `html/quote/pattern-5`.

Put an inline q quotation inside a span with class quotation. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span class="quotation"><q>A quiet destination.</q></span>
```

## rf-html-quote-05-2 — train

Family: `html-quote`; template: `html/quote/pattern-5`.

Put an inline q quotation inside a span with class quotation. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span class="quotation"><q>A busy destination.</q></span>
```

## rf-html-quote-06-1 — train

Family: `html-quote`; template: `html/quote/pattern-6`.

Put an inline q quotation inside a one-item ordered list. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ol><li><q>A quiet destination.</q></li></ol>
```

## rf-html-quote-06-2 — train

Family: `html-quote`; template: `html/quote/pattern-6`.

Put an inline q quotation inside a one-item ordered list. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<ol><li><q>A busy destination.</q></li></ol>
```

## rf-html-abbreviation-01-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-1`.

Mark the word as abbr with the sentence as its title. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<abbr title="Input and output">I/O</abbr>
```

## rf-html-abbreviation-01-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-1`.

Mark the word as abbr with the sentence as its title. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<abbr title="Central processing unit">CPU</abbr>
```

## rf-html-abbreviation-02-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-2`.

Put that titled abbreviation inside a paragraph. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<p><abbr title="Input and output">I/O</abbr></p>
```

## rf-html-abbreviation-02-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-2`.

Put that titled abbreviation inside a paragraph. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<p><abbr title="Central processing unit">CPU</abbr></p>
```

## rf-html-abbreviation-03-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-3`.

Put that titled abbreviation inside strong. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<strong><abbr title="Input and output">I/O</abbr></strong>
```

## rf-html-abbreviation-03-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-3`.

Put that titled abbreviation inside strong. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<strong><abbr title="Central processing unit">CPU</abbr></strong>
```

## rf-html-abbreviation-04-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-4`.

Put that titled abbreviation inside em. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<em><abbr title="Input and output">I/O</abbr></em>
```

## rf-html-abbreviation-04-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-4`.

Put that titled abbreviation inside em. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<em><abbr title="Central processing unit">CPU</abbr></em>
```

## rf-html-abbreviation-05-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-5`.

Put that titled abbreviation inside a span with class term. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<span class="term"><abbr title="Input and output">I/O</abbr></span>
```

## rf-html-abbreviation-05-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-5`.

Put that titled abbreviation inside a span with class term. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<span class="term"><abbr title="Central processing unit">CPU</abbr></span>
```

## rf-html-abbreviation-06-1 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-6`.

Put that titled abbreviation inside a one-item unordered list. Use word "I/O", reading "Kyo-to", and sentence "Input and output" where requested; omit unused supplied text. Return only the fragment.

```html
<ul><li><abbr title="Input and output">I/O</abbr></li></ul>
```

## rf-html-abbreviation-06-2 — train

Family: `html-abbreviation`; template: `html/abbreviation/pattern-6`.

Put that titled abbreviation inside a one-item unordered list. Use word "CPU", reading "O-sa-ka", and sentence "Central processing unit" where requested; omit unused supplied text. Return only the fragment.

```html
<ul><li><abbr title="Central processing unit">CPU</abbr></li></ul>
```

## rf-html-description-01-1 — validation

Family: `html-description`; template: `html/description/pattern-1`.

Use dl with one dt word and one dd sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl>
```

## rf-html-description-01-2 — validation

Family: `html-description`; template: `html/description/pattern-1`.

Use dl with one dt word and one dd sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Osaka</dt><dd>A busy destination.</dd></dl>
```

## rf-html-description-02-1 — validation

Family: `html-description`; template: `html/description/pattern-2`.

Use dl with the dt word inside strong and one dd sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt><strong>Kyoto</strong></dt><dd>A quiet destination.</dd></dl>
```

## rf-html-description-02-2 — validation

Family: `html-description`; template: `html/description/pattern-2`.

Use dl with the dt word inside strong and one dd sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt><strong>Osaka</strong></dt><dd>A busy destination.</dd></dl>
```

## rf-html-description-03-1 — validation

Family: `html-description`; template: `html/description/pattern-3`.

Use dl with one dt word and the dd sentence inside em. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><em>A quiet destination.</em></dd></dl>
```

## rf-html-description-03-2 — validation

Family: `html-description`; template: `html/description/pattern-3`.

Use dl with one dt word and the dd sentence inside em. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Osaka</dt><dd><em>A busy destination.</em></dd></dl>
```

## rf-html-description-04-1 — validation

Family: `html-description`; template: `html/description/pattern-4`.

Use dl with one dt word and the dd sentence inside a paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><p>A quiet destination.</p></dd></dl>
```

## rf-html-description-04-2 — validation

Family: `html-description`; template: `html/description/pattern-4`.

Use dl with one dt word and the dd sentence inside a paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><dt>Osaka</dt><dd><p>A busy destination.</p></dd></dl>
```

## rf-html-description-05-1 — validation

Family: `html-description`; template: `html/description/pattern-5`.

Wrap a one-term dl in a section; use dt for the word and dd for the sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<section><dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl></section>
```

## rf-html-description-05-2 — validation

Family: `html-description`; template: `html/description/pattern-5`.

Wrap a one-term dl in a section; use dt for the word and dd for the sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<section><dl><dt>Osaka</dt><dd>A busy destination.</dd></dl></section>
```

## rf-html-description-06-1 — validation

Family: `html-description`; template: `html/description/pattern-6`.

Use dl with a div wrapping its dt word and dd sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><div><dt>Kyoto</dt><dd>A quiet destination.</dd></div></dl>
```

## rf-html-description-06-2 — validation

Family: `html-description`; template: `html/description/pattern-6`.

Use dl with a div wrapping its dt word and dd sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<dl><div><dt>Osaka</dt><dd>A busy destination.</dd></div></dl>
```

## rf-html-progress-01-1 — validation

Family: `html-progress`; template: `html/progress/pattern-1`.

Make determinate progress with value 35 and max 100. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress value="35" max="100"></progress>
```

## rf-html-progress-01-2 — validation

Family: `html-progress`; template: `html/progress/pattern-1`.

Make determinate progress with value 65 and max 100. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress value="65" max="100"></progress>
```

## rf-html-progress-02-1 — validation

Family: `html-progress`; template: `html/progress/pattern-2`.

Make determinate progress with value 35, max 100, and the word as fallback text. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress value="35" max="100">Kyoto</progress>
```

## rf-html-progress-02-2 — validation

Family: `html-progress`; template: `html/progress/pattern-2`.

Make determinate progress with value 65, max 100, and the word as fallback text. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress value="65" max="100">Osaka</progress>
```

## rf-html-progress-03-1 — validation

Family: `html-progress`; template: `html/progress/pattern-3`.

Make indeterminate progress with the word as fallback text and no value attribute. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress>Kyoto</progress>
```

## rf-html-progress-03-2 — validation

Family: `html-progress`; template: `html/progress/pattern-3`.

Make indeterminate progress with the word as fallback text and no value attribute. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<progress>Osaka</progress>
```

## rf-html-progress-04-1 — validation

Family: `html-progress`; template: `html/progress/pattern-4`.

Wrap determinate progress with value 35 and max 100 in a paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><progress value="35" max="100"></progress></p>
```

## rf-html-progress-04-2 — validation

Family: `html-progress`; template: `html/progress/pattern-4`.

Wrap determinate progress with value 65 and max 100 in a paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><progress value="65" max="100"></progress></p>
```

## rf-html-progress-05-1 — validation

Family: `html-progress`; template: `html/progress/pattern-5`.

Put indeterminate progress with the word as fallback text and no value attribute inside a span. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><progress>Kyoto</progress></span>
```

## rf-html-progress-05-2 — validation

Family: `html-progress`; template: `html/progress/pattern-5`.

Put indeterminate progress with the word as fallback text and no value attribute inside a span. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><progress>Osaka</progress></span>
```

## rf-html-progress-06-1 — validation

Family: `html-progress`; template: `html/progress/pattern-6`.

Put determinate progress with value 35 and max 100 inside a div with class tracking. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<div class="tracking"><progress value="35" max="100"></progress></div>
```

## rf-html-progress-06-2 — validation

Family: `html-progress`; template: `html/progress/pattern-6`.

Put determinate progress with value 65 and max 100 inside a div with class tracking. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<div class="tracking"><progress value="65" max="100"></progress></div>
```

## rf-html-meter-01-1 — train

Family: `html-meter`; template: `html/meter/pattern-1`.

Make a meter with min 0, max 100, and value 35. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="35"></meter>
```

## rf-html-meter-01-2 — train

Family: `html-meter`; template: `html/meter/pattern-1`.

Make a meter with min 0, max 100, and value 65. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="65"></meter>
```

## rf-html-meter-02-1 — train

Family: `html-meter`; template: `html/meter/pattern-2`.

Make a meter with min 0, max 100, value 35, and the word as fallback text. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="35">Kyoto</meter>
```

## rf-html-meter-02-2 — train

Family: `html-meter`; template: `html/meter/pattern-2`.

Make a meter with min 0, max 100, value 65, and the word as fallback text. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="65">Osaka</meter>
```

## rf-html-meter-03-1 — train

Family: `html-meter`; template: `html/meter/pattern-3`.

Make a meter with min 0, max 100, value 35, low 20, high 80, and optimum 50. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="35" low="20" high="80" optimum="50"></meter>
```

## rf-html-meter-03-2 — train

Family: `html-meter`; template: `html/meter/pattern-3`.

Make a meter with min 0, max 100, value 65, low 20, high 80, and optimum 50. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<meter min="0" max="100" value="65" low="20" high="80" optimum="50"></meter>
```

## rf-html-meter-04-1 — train

Family: `html-meter`; template: `html/meter/pattern-4`.

Put a meter with min 0, max 100, and value 35 inside a paragraph. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><meter min="0" max="100" value="35"></meter></p>
```

## rf-html-meter-04-2 — train

Family: `html-meter`; template: `html/meter/pattern-4`.

Put a meter with min 0, max 100, and value 65 inside a paragraph. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<p><meter min="0" max="100" value="65"></meter></p>
```

## rf-html-meter-05-1 — train

Family: `html-meter`; template: `html/meter/pattern-5`.

Put a meter with min 0, max 100, and value 35 inside a span. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><meter min="0" max="100" value="35"></meter></span>
```

## rf-html-meter-05-2 — train

Family: `html-meter`; template: `html/meter/pattern-5`.

Put a meter with min 0, max 100, and value 65 inside a span. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<span><meter min="0" max="100" value="65"></meter></span>
```

## rf-html-meter-06-1 — train

Family: `html-meter`; template: `html/meter/pattern-6`.

Put a meter with min 0, max 100, and value 35 inside a div with class reading. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<div class="reading"><meter min="0" max="100" value="35"></meter></div>
```

## rf-html-meter-06-2 — train

Family: `html-meter`; template: `html/meter/pattern-6`.

Put a meter with min 0, max 100, and value 65 inside a div with class reading. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<div class="reading"><meter min="0" max="100" value="65"></meter></div>
```

## rf-html-contact-01-1 — train

Family: `html-contact`; template: `html/contact/pattern-1`.

Put the word in address as plain contact text. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address>Kyoto</address>
```

## rf-html-contact-01-2 — train

Family: `html-contact`; template: `html/contact/pattern-1`.

Put the word in address as plain contact text. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address>Osaka</address>
```

## rf-html-contact-02-1 — train

Family: `html-contact`; template: `html/contact/pattern-2`.

Put the word in a paragraph inside address. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><p>Kyoto</p></address>
```

## rf-html-contact-02-2 — train

Family: `html-contact`; template: `html/contact/pattern-2`.

Put the word in a paragraph inside address. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><p>Osaka</p></address>
```

## rf-html-contact-03-1 — train

Family: `html-contact`; template: `html/contact/pattern-3`.

Put the word in strong inside address. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><strong>Kyoto</strong></address>
```

## rf-html-contact-03-2 — train

Family: `html-contact`; template: `html/contact/pattern-3`.

Put the word in strong inside address. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><strong>Osaka</strong></address>
```

## rf-html-contact-04-1 — train

Family: `html-contact`; template: `html/contact/pattern-4`.

Put the word in a span with class contact inside address. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><span class="contact">Kyoto</span></address>
```

## rf-html-contact-04-2 — train

Family: `html-contact`; template: `html/contact/pattern-4`.

Put the word in a span with class contact inside address. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><span class="contact">Osaka</span></address>
```

## rf-html-contact-05-1 — train

Family: `html-contact`; template: `html/contact/pattern-5`.

Put the word then br then the sentence inside address. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address>Kyoto<br>A quiet destination.</address>
```

## rf-html-contact-05-2 — train

Family: `html-contact`; template: `html/contact/pattern-5`.

Put the word then br then the sentence inside address. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address>Osaka<br>A busy destination.</address>
```

## rf-html-contact-06-1 — train

Family: `html-contact`; template: `html/contact/pattern-6`.

Put two paragraphs in address: the word then the sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><p>Kyoto</p><p>A quiet destination.</p></address>
```

## rf-html-contact-06-2 — train

Family: `html-contact`; template: `html/contact/pattern-6`.

Put two paragraphs in address: the word then the sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<address><p>Osaka</p><p>A busy destination.</p></address>
```

## rf-html-heading-group-01-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-1`.

Make hgroup containing h1 with the word and p with the sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h1>Kyoto</h1><p>A quiet destination.</p></hgroup>
```

## rf-html-heading-group-01-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-1`.

Make hgroup containing h1 with the word and p with the sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h1>Osaka</h1><p>A busy destination.</p></hgroup>
```

## rf-html-heading-group-02-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-2`.

Make hgroup containing h2 with the word and p with the sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup>
```

## rf-html-heading-group-02-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-2`.

Make hgroup containing h2 with the word and p with the sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h2>Osaka</h2><p>A busy destination.</p></hgroup>
```

## rf-html-heading-group-03-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-3`.

Make hgroup containing h3 with the word and p with the sentence. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h3>Kyoto</h3><p>A quiet destination.</p></hgroup>
```

## rf-html-heading-group-03-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-3`.

Make hgroup containing h3 with the word and p with the sentence. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h3>Osaka</h3><p>A busy destination.</p></hgroup>
```

## rf-html-heading-group-04-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-4`.

Make hgroup containing p with the sentence then h2 with the word. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><p>A quiet destination.</p><h2>Kyoto</h2></hgroup>
```

## rf-html-heading-group-04-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-4`.

Make hgroup containing p with the sentence then h2 with the word. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><p>A busy destination.</p><h2>Osaka</h2></hgroup>
```

## rf-html-heading-group-05-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-5`.

Make hgroup containing h2 with the word and p with the sentence inside em. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p><em>A quiet destination.</em></p></hgroup>
```

## rf-html-heading-group-05-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-5`.

Make hgroup containing h2 with the word and p with the sentence inside em. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<hgroup><h2>Osaka</h2><p><em>A busy destination.</em></p></hgroup>
```

## rf-html-heading-group-06-1 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-6`.

Wrap hgroup in a header; put the word in h2 and the sentence in p. Use word "Kyoto", reading "Kyo-to", and sentence "A quiet destination." where requested; omit unused supplied text. Return only the fragment.

```html
<header><hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup></header>
```

## rf-html-heading-group-06-2 — train

Family: `html-heading-group`; template: `html/heading-group/pattern-6`.

Wrap hgroup in a header; put the word in h2 and the sentence in p. Use word "Osaka", reading "O-sa-ka", and sentence "A busy destination." where requested; omit unused supplied text. Return only the fragment.

```html
<header><hgroup><h2>Osaka</h2><p>A busy destination.</p></hgroup></header>
```

## rf-css-logical-border-01-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-1`.

For .rf-logical-border-alpha, set border-inline-start to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-inline-start: 2px solid #334155;
}
```

## rf-css-logical-border-01-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-1`.

For .rf-logical-border-beta, set border-inline-start to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-inline-start: 2px solid #334155;
}
```

## rf-css-logical-border-02-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-2`.

For .rf-logical-border-alpha, set border-inline-end to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-inline-end: 2px solid #334155;
}
```

## rf-css-logical-border-02-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-2`.

For .rf-logical-border-beta, set border-inline-end to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-inline-end: 2px solid #334155;
}
```

## rf-css-logical-border-03-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-3`.

For .rf-logical-border-alpha, set border-block-start to 2px dashed #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-block-start: 2px dashed #334155;
}
```

## rf-css-logical-border-03-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-3`.

For .rf-logical-border-beta, set border-block-start to 2px dashed #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-block-start: 2px dashed #334155;
}
```

## rf-css-logical-border-04-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-4`.

For .rf-logical-border-alpha, set border-block-end to 2px dashed #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-block-end: 2px dashed #334155;
}
```

## rf-css-logical-border-04-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-4`.

For .rf-logical-border-beta, set border-block-end to 2px dashed #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-block-end: 2px dashed #334155;
}
```

## rf-css-logical-border-05-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-5`.

For .rf-logical-border-alpha, set border-inline-start to 2px solid #334155; border-inline-end to 0. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-inline-start: 2px solid #334155;
  border-inline-end: 0;
}
```

## rf-css-logical-border-05-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-5`.

For .rf-logical-border-beta, set border-inline-start to 2px solid #334155; border-inline-end to 0. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-inline-start: 2px solid #334155;
  border-inline-end: 0;
}
```

## rf-css-logical-border-06-1 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-6`.

For .rf-logical-border-alpha, set border-block-start to 0; border-block-end to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-alpha {
  border-block-start: 0;
  border-block-end: 2px solid #334155;
}
```

## rf-css-logical-border-06-2 — train

Family: `css-logical-border`; template: `css/logical-border/pattern-6`.

For .rf-logical-border-beta, set border-block-start to 0; border-block-end to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-logical-border-beta {
  border-block-start: 0;
  border-block-end: 2px solid #334155;
}
```

## rf-css-aspect-01-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-1`.

For .rf-aspect-alpha, set aspect-ratio to 1 / 1. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 1 / 1;
}
```

## rf-css-aspect-01-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-1`.

For .rf-aspect-beta, set aspect-ratio to 1 / 1. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: 1 / 1;
}
```

## rf-css-aspect-02-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-2`.

For .rf-aspect-alpha, set aspect-ratio to 16 / 9. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 16 / 9;
}
```

## rf-css-aspect-02-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-2`.

For .rf-aspect-beta, set aspect-ratio to 16 / 9. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: 16 / 9;
}
```

## rf-css-aspect-03-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-3`.

For .rf-aspect-alpha, set aspect-ratio to auto. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: auto;
}
```

## rf-css-aspect-03-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-3`.

For .rf-aspect-beta, set aspect-ratio to auto. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: auto;
}
```

## rf-css-aspect-04-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-4`.

For .rf-aspect-alpha, set aspect-ratio to 1 / 1; width to 120px. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 1 / 1;
  width: 120px;
}
```

## rf-css-aspect-04-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-4`.

For .rf-aspect-beta, set aspect-ratio to 1 / 1; width to 120px. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: 1 / 1;
  width: 120px;
}
```

## rf-css-aspect-05-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-5`.

For .rf-aspect-alpha, set aspect-ratio to 16 / 9; width to 240px. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 16 / 9;
  width: 240px;
}
```

## rf-css-aspect-05-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-5`.

For .rf-aspect-beta, set aspect-ratio to 16 / 9; width to 240px. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: 16 / 9;
  width: 240px;
}
```

## rf-css-aspect-06-1 — train

Family: `css-aspect`; template: `css/aspect/pattern-6`.

For .rf-aspect-alpha, set aspect-ratio to 4 / 3; max-width to 100%. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-alpha {
  aspect-ratio: 4 / 3;
  max-width: 100%;
}
```

## rf-css-aspect-06-2 — train

Family: `css-aspect`; template: `css/aspect/pattern-6`.

For .rf-aspect-beta, set aspect-ratio to 4 / 3; max-width to 100%. Return one CSS rule with exactly these declarations.

```css
.rf-aspect-beta {
  aspect-ratio: 4 / 3;
  max-width: 100%;
}
```

## rf-css-outline-01-1 — validation

Family: `css-outline`; template: `css/outline/pattern-1`.

For .rf-outline-alpha, set outline-style to solid. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline-style: solid;
}
```

## rf-css-outline-01-2 — validation

Family: `css-outline`; template: `css/outline/pattern-1`.

For .rf-outline-beta, set outline-style to solid. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline-style: solid;
}
```

## rf-css-outline-02-1 — validation

Family: `css-outline`; template: `css/outline/pattern-2`.

For .rf-outline-alpha, set outline-style to dashed. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline-style: dashed;
}
```

## rf-css-outline-02-2 — validation

Family: `css-outline`; template: `css/outline/pattern-2`.

For .rf-outline-beta, set outline-style to dashed. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline-style: dashed;
}
```

## rf-css-outline-03-1 — validation

Family: `css-outline`; template: `css/outline/pattern-3`.

For .rf-outline-alpha, set outline to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline: 2px solid #334155;
}
```

## rf-css-outline-03-2 — validation

Family: `css-outline`; template: `css/outline/pattern-3`.

For .rf-outline-beta, set outline to 2px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline: 2px solid #334155;
}
```

## rf-css-outline-04-1 — validation

Family: `css-outline`; template: `css/outline/pattern-4`.

For .rf-outline-alpha, set outline to 2px solid #334155; outline-offset to 4px. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline: 2px solid #334155;
  outline-offset: 4px;
}
```

## rf-css-outline-04-2 — validation

Family: `css-outline`; template: `css/outline/pattern-4`.

For .rf-outline-beta, set outline to 2px solid #334155; outline-offset to 4px. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline: 2px solid #334155;
  outline-offset: 4px;
}
```

## rf-css-outline-05-1 — validation

Family: `css-outline`; template: `css/outline/pattern-5`.

For .rf-outline-alpha, set outline to 0; box-shadow to none. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline: 0;
  box-shadow: none;
}
```

## rf-css-outline-05-2 — validation

Family: `css-outline`; template: `css/outline/pattern-5`.

For .rf-outline-beta, set outline to 0; box-shadow to none. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline: 0;
  box-shadow: none;
}
```

## rf-css-outline-06-1 — validation

Family: `css-outline`; template: `css/outline/pattern-6`.

For .rf-outline-alpha, set outline-style to dotted; outline-width to 3px; outline-offset to -2px. Return one CSS rule with exactly these declarations.

```css
.rf-outline-alpha {
  outline-style: dotted;
  outline-width: 3px;
  outline-offset: -2px;
}
```

## rf-css-outline-06-2 — validation

Family: `css-outline`; template: `css/outline/pattern-6`.

For .rf-outline-beta, set outline-style to dotted; outline-width to 3px; outline-offset to -2px. Return one CSS rule with exactly these declarations.

```css
.rf-outline-beta {
  outline-style: dotted;
  outline-width: 3px;
  outline-offset: -2px;
}
```

## rf-css-cursor-01-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-1`.

For .rf-cursor-alpha, set cursor to pointer. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: pointer;
}
```

## rf-css-cursor-01-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-1`.

For .rf-cursor-beta, set cursor to pointer. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: pointer;
}
```

## rf-css-cursor-02-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-2`.

For .rf-cursor-alpha, set cursor to text. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: text;
}
```

## rf-css-cursor-02-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-2`.

For .rf-cursor-beta, set cursor to text. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: text;
}
```

## rf-css-cursor-03-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-3`.

For .rf-cursor-alpha, set cursor to wait. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: wait;
}
```

## rf-css-cursor-03-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-3`.

For .rf-cursor-beta, set cursor to wait. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: wait;
}
```

## rf-css-cursor-04-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-4`.

For .rf-cursor-alpha, set cursor to not-allowed; opacity to 0.5. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: not-allowed;
  opacity: 0.5;
}
```

## rf-css-cursor-04-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-4`.

For .rf-cursor-beta, set cursor to not-allowed; opacity to 0.5. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: not-allowed;
  opacity: 0.5;
}
```

## rf-css-cursor-05-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-5`.

For .rf-cursor-alpha, set cursor to grab; user-select to none. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: grab;
  user-select: none;
}
```

## rf-css-cursor-05-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-5`.

For .rf-cursor-beta, set cursor to grab; user-select to none. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: grab;
  user-select: none;
}
```

## rf-css-cursor-06-1 — validation

Family: `css-cursor`; template: `css/cursor/pattern-6`.

For .rf-cursor-alpha, set cursor to default; user-select to text. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-alpha {
  cursor: default;
  user-select: text;
}
```

## rf-css-cursor-06-2 — validation

Family: `css-cursor`; template: `css/cursor/pattern-6`.

For .rf-cursor-beta, set cursor to default; user-select to text. Return one CSS rule with exactly these declarations.

```css
.rf-cursor-beta {
  cursor: default;
  user-select: text;
}
```

## rf-css-whitespace-01-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-1`.

For .rf-whitespace-alpha, set white-space to normal. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: normal;
}
```

## rf-css-whitespace-01-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-1`.

For .rf-whitespace-beta, set white-space to normal. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: normal;
}
```

## rf-css-whitespace-02-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-2`.

For .rf-whitespace-alpha, set white-space to nowrap. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: nowrap;
}
```

## rf-css-whitespace-02-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-2`.

For .rf-whitespace-beta, set white-space to nowrap. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: nowrap;
}
```

## rf-css-whitespace-03-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-3`.

For .rf-whitespace-alpha, set white-space to pre. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: pre;
}
```

## rf-css-whitespace-03-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-3`.

For .rf-whitespace-beta, set white-space to pre. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: pre;
}
```

## rf-css-whitespace-04-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-4`.

For .rf-whitespace-alpha, set white-space to pre-wrap; overflow-wrap to anywhere. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

## rf-css-whitespace-04-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-4`.

For .rf-whitespace-beta, set white-space to pre-wrap; overflow-wrap to anywhere. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

## rf-css-whitespace-05-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-5`.

For .rf-whitespace-alpha, set white-space to pre-line; overflow-wrap to break-word. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: pre-line;
  overflow-wrap: break-word;
}
```

## rf-css-whitespace-05-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-5`.

For .rf-whitespace-beta, set white-space to pre-line; overflow-wrap to break-word. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: pre-line;
  overflow-wrap: break-word;
}
```

## rf-css-whitespace-06-1 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-6`.

For .rf-whitespace-alpha, set white-space to break-spaces; tab-size to 4. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-alpha {
  white-space: break-spaces;
  tab-size: 4;
}
```

## rf-css-whitespace-06-2 — validation

Family: `css-whitespace`; template: `css/whitespace/pattern-6`.

For .rf-whitespace-beta, set white-space to break-spaces; tab-size to 4. Return one CSS rule with exactly these declarations.

```css
.rf-whitespace-beta {
  white-space: break-spaces;
  tab-size: 4;
}
```

## rf-css-decoration-01-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-1`.

For .rf-decoration-alpha, set text-decoration-line to underline. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
}
```

## rf-css-decoration-01-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-1`.

For .rf-decoration-beta, set text-decoration-line to underline. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: underline;
}
```

## rf-css-decoration-02-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-2`.

For .rf-decoration-alpha, set text-decoration-line to line-through. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: line-through;
}
```

## rf-css-decoration-02-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-2`.

For .rf-decoration-beta, set text-decoration-line to line-through. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: line-through;
}
```

## rf-css-decoration-03-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-3`.

For .rf-decoration-alpha, set text-decoration-line to none. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: none;
}
```

## rf-css-decoration-03-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-3`.

For .rf-decoration-beta, set text-decoration-line to none. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: none;
}
```

## rf-css-decoration-04-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-4`.

For .rf-decoration-alpha, set text-decoration-line to underline; text-decoration-style to wavy. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
  text-decoration-style: wavy;
}
```

## rf-css-decoration-04-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-4`.

For .rf-decoration-beta, set text-decoration-line to underline; text-decoration-style to wavy. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: underline;
  text-decoration-style: wavy;
}
```

## rf-css-decoration-05-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-5`.

For .rf-decoration-alpha, set text-decoration-line to underline; text-decoration-color to #334155. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline;
  text-decoration-color: #334155;
}
```

## rf-css-decoration-05-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-5`.

For .rf-decoration-beta, set text-decoration-line to underline; text-decoration-color to #334155. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: underline;
  text-decoration-color: #334155;
}
```

## rf-css-decoration-06-1 — train

Family: `css-decoration`; template: `css/decoration/pattern-6`.

For .rf-decoration-alpha, set text-decoration-line to underline overline; text-underline-offset to 4px. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-alpha {
  text-decoration-line: underline overline;
  text-underline-offset: 4px;
}
```

## rf-css-decoration-06-2 — train

Family: `css-decoration`; template: `css/decoration/pattern-6`.

For .rf-decoration-beta, set text-decoration-line to underline overline; text-underline-offset to 4px. Return one CSS rule with exactly these declarations.

```css
.rf-decoration-beta {
  text-decoration-line: underline overline;
  text-underline-offset: 4px;
}
```

## rf-css-overflow-01-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-1`.

For .rf-overflow-alpha, set overflow-x to auto. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow-x: auto;
}
```

## rf-css-overflow-01-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-1`.

For .rf-overflow-beta, set overflow-x to auto. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow-x: auto;
}
```

## rf-css-overflow-02-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-2`.

For .rf-overflow-alpha, set overflow-y to scroll. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow-y: scroll;
}
```

## rf-css-overflow-02-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-2`.

For .rf-overflow-beta, set overflow-y to scroll. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow-y: scroll;
}
```

## rf-css-overflow-03-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-3`.

For .rf-overflow-alpha, set overflow to hidden. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow: hidden;
}
```

## rf-css-overflow-03-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-3`.

For .rf-overflow-beta, set overflow to hidden. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow: hidden;
}
```

## rf-css-overflow-04-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-4`.

For .rf-overflow-alpha, set overflow to clip; display to flow-root. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow: clip;
  display: flow-root;
}
```

## rf-css-overflow-04-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-4`.

For .rf-overflow-beta, set overflow to clip; display to flow-root. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow: clip;
  display: flow-root;
}
```

## rf-css-overflow-05-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-5`.

For .rf-overflow-alpha, set overflow-x to auto; overflow-y to hidden. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow-x: auto;
  overflow-y: hidden;
}
```

## rf-css-overflow-05-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-5`.

For .rf-overflow-beta, set overflow-x to auto; overflow-y to hidden. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow-x: auto;
  overflow-y: hidden;
}
```

## rf-css-overflow-06-1 — train

Family: `css-overflow`; template: `css/overflow/pattern-6`.

For .rf-overflow-alpha, set overflow to auto; max-height to 200px. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-alpha {
  overflow: auto;
  max-height: 200px;
}
```

## rf-css-overflow-06-2 — train

Family: `css-overflow`; template: `css/overflow/pattern-6`.

For .rf-overflow-beta, set overflow to auto; max-height to 200px. Return one CSS rule with exactly these declarations.

```css
.rf-overflow-beta {
  overflow: auto;
  max-height: 200px;
}
```

## rf-css-table-01-1 — train

Family: `css-table`; template: `css/table/pattern-1`.

For .rf-table-alpha, set table-layout to auto. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  table-layout: auto;
}
```

## rf-css-table-01-2 — train

Family: `css-table`; template: `css/table/pattern-1`.

For .rf-table-beta, set table-layout to auto. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  table-layout: auto;
}
```

## rf-css-table-02-1 — train

Family: `css-table`; template: `css/table/pattern-2`.

For .rf-table-alpha, set table-layout to fixed; width to 100%. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  table-layout: fixed;
  width: 100%;
}
```

## rf-css-table-02-2 — train

Family: `css-table`; template: `css/table/pattern-2`.

For .rf-table-beta, set table-layout to fixed; width to 100%. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  table-layout: fixed;
  width: 100%;
}
```

## rf-css-table-03-1 — train

Family: `css-table`; template: `css/table/pattern-3`.

For .rf-table-alpha, set border-collapse to collapse. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  border-collapse: collapse;
}
```

## rf-css-table-03-2 — train

Family: `css-table`; template: `css/table/pattern-3`.

For .rf-table-beta, set border-collapse to collapse. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  border-collapse: collapse;
}
```

## rf-css-table-04-1 — train

Family: `css-table`; template: `css/table/pattern-4`.

For .rf-table-alpha, set border-collapse to separate; border-spacing to 8px. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  border-collapse: separate;
  border-spacing: 8px;
}
```

## rf-css-table-04-2 — train

Family: `css-table`; template: `css/table/pattern-4`.

For .rf-table-beta, set border-collapse to separate; border-spacing to 8px. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  border-collapse: separate;
  border-spacing: 8px;
}
```

## rf-css-table-05-1 — train

Family: `css-table`; template: `css/table/pattern-5`.

For .rf-table-alpha, set caption-side to bottom. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  caption-side: bottom;
}
```

## rf-css-table-05-2 — train

Family: `css-table`; template: `css/table/pattern-5`.

For .rf-table-beta, set caption-side to bottom. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  caption-side: bottom;
}
```

## rf-css-table-06-1 — train

Family: `css-table`; template: `css/table/pattern-6`.

For .rf-table-alpha, set empty-cells to hide; border-collapse to separate. Return one CSS rule with exactly these declarations.

```css
.rf-table-alpha {
  empty-cells: hide;
  border-collapse: separate;
}
```

## rf-css-table-06-2 — train

Family: `css-table`; template: `css/table/pattern-6`.

For .rf-table-beta, set empty-cells to hide; border-collapse to separate. Return one CSS rule with exactly these declarations.

```css
.rf-table-beta {
  empty-cells: hide;
  border-collapse: separate;
}
```

## rf-css-columns-01-1 — train

Family: `css-columns`; template: `css/columns/pattern-1`.

For .rf-columns-alpha, set column-count to 2. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-count: 2;
}
```

## rf-css-columns-01-2 — train

Family: `css-columns`; template: `css/columns/pattern-1`.

For .rf-columns-beta, set column-count to 2. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-count: 2;
}
```

## rf-css-columns-02-1 — train

Family: `css-columns`; template: `css/columns/pattern-2`.

For .rf-columns-alpha, set column-width to 180px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-width: 180px;
}
```

## rf-css-columns-02-2 — train

Family: `css-columns`; template: `css/columns/pattern-2`.

For .rf-columns-beta, set column-width to 180px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-width: 180px;
}
```

## rf-css-columns-03-1 — train

Family: `css-columns`; template: `css/columns/pattern-3`.

For .rf-columns-alpha, set column-count to 3; column-gap to 24px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-count: 3;
  column-gap: 24px;
}
```

## rf-css-columns-03-2 — train

Family: `css-columns`; template: `css/columns/pattern-3`.

For .rf-columns-beta, set column-count to 3; column-gap to 24px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-count: 3;
  column-gap: 24px;
}
```

## rf-css-columns-04-1 — train

Family: `css-columns`; template: `css/columns/pattern-4`.

For .rf-columns-alpha, set column-count to 2; column-rule to 1px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-count: 2;
  column-rule: 1px solid #334155;
}
```

## rf-css-columns-04-2 — train

Family: `css-columns`; template: `css/columns/pattern-4`.

For .rf-columns-beta, set column-count to 2; column-rule to 1px solid #334155. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-count: 2;
  column-rule: 1px solid #334155;
}
```

## rf-css-columns-05-1 — train

Family: `css-columns`; template: `css/columns/pattern-5`.

For .rf-columns-alpha, set column-span to all. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-span: all;
}
```

## rf-css-columns-05-2 — train

Family: `css-columns`; template: `css/columns/pattern-5`.

For .rf-columns-beta, set column-span to all. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-span: all;
}
```

## rf-css-columns-06-1 — train

Family: `css-columns`; template: `css/columns/pattern-6`.

For .rf-columns-alpha, set column-fill to auto; height to 300px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-alpha {
  column-fill: auto;
  height: 300px;
}
```

## rf-css-columns-06-2 — train

Family: `css-columns`; template: `css/columns/pattern-6`.

For .rf-columns-beta, set column-fill to auto; height to 300px. Return one CSS rule with exactly these declarations.

```css
.rf-columns-beta {
  column-fill: auto;
  height: 300px;
}
```

## rf-css-object-fit-01-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-1`.

For .rf-object-fit-alpha, set object-fit to contain. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: contain;
}
```

## rf-css-object-fit-01-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-1`.

For .rf-object-fit-beta, set object-fit to contain. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: contain;
}
```

## rf-css-object-fit-02-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-2`.

For .rf-object-fit-alpha, set object-fit to cover. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: cover;
}
```

## rf-css-object-fit-02-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-2`.

For .rf-object-fit-beta, set object-fit to cover. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: cover;
}
```

## rf-css-object-fit-03-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-3`.

For .rf-object-fit-alpha, set object-fit to fill. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: fill;
}
```

## rf-css-object-fit-03-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-3`.

For .rf-object-fit-beta, set object-fit to fill. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: fill;
}
```

## rf-css-object-fit-04-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-4`.

For .rf-object-fit-alpha, set object-fit to none; object-position to center. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: none;
  object-position: center;
}
```

## rf-css-object-fit-04-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-4`.

For .rf-object-fit-beta, set object-fit to none; object-position to center. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: none;
  object-position: center;
}
```

## rf-css-object-fit-05-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-5`.

For .rf-object-fit-alpha, set object-fit to scale-down; object-position to left top. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: scale-down;
  object-position: left top;
}
```

## rf-css-object-fit-05-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-5`.

For .rf-object-fit-beta, set object-fit to scale-down; object-position to left top. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: scale-down;
  object-position: left top;
}
```

## rf-css-object-fit-06-1 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-6`.

For .rf-object-fit-alpha, set object-fit to cover; object-position to right bottom. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-alpha {
  object-fit: cover;
  object-position: right bottom;
}
```

## rf-css-object-fit-06-2 — train

Family: `css-object-fit`; template: `css/object-fit/pattern-6`.

For .rf-object-fit-beta, set object-fit to cover; object-position to right bottom. Return one CSS rule with exactly these declarations.

```css
.rf-object-fit-beta {
  object-fit: cover;
  object-position: right bottom;
}
```

## rf-javascript-binary-01-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-1`.

Write transformAlpha(a, b) for finite numbers a and b; return a plus b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a + b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 7}]`

## rf-javascript-binary-01-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-1`.

Write transformBeta(a, b) for finite numbers a and b; return a plus b. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return a + b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 7}]`

## rf-javascript-binary-02-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-2`.

Write transformAlpha(a, b) for finite numbers a and b; return a minus b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a - b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": -1}]`

## rf-javascript-binary-02-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-2`.

Write transformBeta(a, b) for finite numbers a and b; return a minus b. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return a - b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": -1}]`

## rf-javascript-binary-03-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-3`.

Write transformAlpha(a, b) for finite numbers a and b; return the product of a and b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a * b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 12}]`

## rf-javascript-binary-03-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-3`.

Write transformBeta(a, b) for finite numbers a and b; return the product of a and b. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return a * b;
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 12}]`

## rf-javascript-binary-04-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-4`.

Write transformAlpha(a, b) for finite numbers a and b; return the larger number. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.max(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 4}]`

## rf-javascript-binary-04-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-4`.

Write transformBeta(a, b) for finite numbers a and b; return the larger number. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.max(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 4}]`

## rf-javascript-binary-05-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-5`.

Write transformAlpha(a, b) for finite numbers a and b; return the smaller number. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.min(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 3}]`

## rf-javascript-binary-05-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-5`.

Write transformBeta(a, b) for finite numbers a and b; return the smaller number. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.min(a, b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 3}]`

## rf-javascript-binary-06-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-6`.

Write transformAlpha(a, b) for finite numbers a and b; return the absolute difference. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.abs(a - b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 1}]`

## rf-javascript-binary-06-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/binary/pattern-6`.

Write transformBeta(a, b) for finite numbers a and b; return the absolute difference. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.abs(a - b);
}
```

Expected cases (not executed): `[{"arguments": [3, 4], "expected": 1}]`

## rf-javascript-bound-01-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-1`.

Write transformAlpha(value, limit) for finite numbers value and limit; cap value at the upper limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return Math.min(value, limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 4}]`

## rf-javascript-bound-01-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-1`.

Write transformBeta(value, limit) for finite numbers value and limit; cap value at the upper limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return Math.min(value, limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 4}]`

## rf-javascript-bound-02-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-2`.

Write transformAlpha(value, limit) for finite numbers value and limit; raise value to at least the lower limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return Math.max(value, limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 10}]`

## rf-javascript-bound-02-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-2`.

Write transformBeta(value, limit) for finite numbers value and limit; raise value to at least the lower limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return Math.max(value, limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 10}]`

## rf-javascript-bound-03-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-3`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value exceeds limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value > limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## rf-javascript-bound-03-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-3`.

Write transformBeta(value, limit) for finite numbers value and limit; report whether value exceeds limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return value > limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## rf-javascript-bound-04-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-4`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value is below limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value < limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": true}]`

## rf-javascript-bound-04-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-4`.

Write transformBeta(value, limit) for finite numbers value and limit; report whether value is below limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return value < limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": true}]`

## rf-javascript-bound-05-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-5`.

Write transformAlpha(value, limit) for finite numbers value and limit; report whether value equals limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return value === limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## rf-javascript-bound-05-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-5`.

Write transformBeta(value, limit) for finite numbers value and limit; report whether value equals limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return value === limit;
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": false}]`

## rf-javascript-bound-06-1 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-6`.

Write transformAlpha(value, limit) for finite numbers value and limit; return the distance between value and limit. Return one JavaScript function.

```javascript
function transformAlpha(value, limit) {
  return Math.abs(value - limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 6}]`

## rf-javascript-bound-06-2 — train

Family: `javascript-numeric-comparison`; template: `javascript/bound/pattern-6`.

Write transformBeta(value, limit) for finite numbers value and limit; return the distance between value and limit. Return one JavaScript function.

```javascript
function transformBeta(value, limit) {
  return Math.abs(value - limit);
}
```

Expected cases (not executed): `[{"arguments": [4, 10], "expected": 6}]`

## rf-javascript-division-01-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-1`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.trunc(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## rf-javascript-division-01-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-1`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.trunc(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## rf-javascript-division-02-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-2`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded down. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.floor(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -3}]`

## rf-javascript-division-02-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-2`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded down. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.floor(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -3}]`

## rf-javascript-division-03-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-3`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded up. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.ceil(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## rf-javascript-division-03-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-3`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded up. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.ceil(a / b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -2}]`

## rf-javascript-division-04-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-4`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the JavaScript remainder. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a % b;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -1}]`

## rf-javascript-division-04-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-4`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the JavaScript remainder. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return a % b;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": -1}]`

## rf-javascript-division-05-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-5`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return whether a is divisible by b. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return a % b === 0;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": false}]`

## rf-javascript-division-05-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-5`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return whether a is divisible by b. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return a % b === 0;
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": false}]`

## rf-javascript-division-06-1 — validation

Family: `javascript-division`; template: `javascript/division/pattern-6`.

Write transformAlpha(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the absolute JavaScript remainder. Return one JavaScript function.

```javascript
function transformAlpha(a, b) {
  return Math.abs(a % b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": 1}]`

## rf-javascript-division-06-2 — validation

Family: `javascript-division`; template: `javascript/division/pattern-6`.

Write transformBeta(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the absolute JavaScript remainder. Return one JavaScript function.

```javascript
function transformBeta(a, b) {
  return Math.abs(a % b);
}
```

Expected cases (not executed): `[{"arguments": [-7, 3], "expected": 1}]`

## rf-javascript-conversion-01-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-1`.

Write transformAlpha(value) for a finite numeric value; convert seconds to milliseconds. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value * 1000;
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": 2000}]`

## rf-javascript-conversion-01-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-1`.

Write transformBeta(value) for a finite numeric value; convert seconds to milliseconds. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value * 1000;
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": 2000}]`

## rf-javascript-conversion-02-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-2`.

Write transformAlpha(value) for a finite numeric value; convert milliseconds to seconds. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value / 1000;
}
```

Expected cases (not executed): `[{"arguments": [2000], "expected": 2}]`

## rf-javascript-conversion-02-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-2`.

Write transformBeta(value) for a finite numeric value; convert milliseconds to seconds. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value / 1000;
}
```

Expected cases (not executed): `[{"arguments": [2000], "expected": 2}]`

## rf-javascript-conversion-03-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-3`.

Write transformAlpha(value) for a finite numeric value; convert minutes to seconds. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value * 60;
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": 120}]`

## rf-javascript-conversion-03-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-3`.

Write transformBeta(value) for a finite numeric value; convert minutes to seconds. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value * 60;
}
```

Expected cases (not executed): `[{"arguments": [2], "expected": 120}]`

## rf-javascript-conversion-04-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-4`.

Write transformAlpha(value) for a finite numeric value; convert seconds to minutes. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value / 60;
}
```

Expected cases (not executed): `[{"arguments": [120], "expected": 2}]`

## rf-javascript-conversion-04-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-4`.

Write transformBeta(value) for a finite numeric value; convert seconds to minutes. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value / 60;
}
```

Expected cases (not executed): `[{"arguments": [120], "expected": 2}]`

## rf-javascript-conversion-05-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-5`.

Write transformAlpha(value) for a finite numeric value; convert centimeters to meters. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value / 100;
}
```

Expected cases (not executed): `[{"arguments": [250], "expected": 2.5}]`

## rf-javascript-conversion-05-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-5`.

Write transformBeta(value) for a finite numeric value; convert centimeters to meters. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value / 100;
}
```

Expected cases (not executed): `[{"arguments": [250], "expected": 2.5}]`

## rf-javascript-conversion-06-1 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-6`.

Write transformAlpha(value) for a finite numeric value; convert meters to centimeters. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value * 100;
}
```

Expected cases (not executed): `[{"arguments": [2.5], "expected": 250}]`

## rf-javascript-conversion-06-2 — validation

Family: `javascript-conversion`; template: `javascript/conversion/pattern-6`.

Write transformBeta(value) for a finite numeric value; convert meters to centimeters. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value * 100;
}
```

Expected cases (not executed): `[{"arguments": [2.5], "expected": 250}]`

## rf-javascript-classification-01-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-1`.

Write transformAlpha(value) for a finite numeric value; report whether value is an integer. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Number.isInteger(value);
}
```

Expected cases (not executed): `[{"arguments": [2.5], "expected": false}]`

## rf-javascript-classification-01-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-1`.

Write transformBeta(value) for a finite numeric value; report whether value is an integer. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return Number.isInteger(value);
}
```

Expected cases (not executed): `[{"arguments": [2.5], "expected": false}]`

## rf-javascript-classification-02-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-2`.

Write transformAlpha(value) for a finite numeric value; report whether value is positive. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value > 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": false}]`

## rf-javascript-classification-02-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-2`.

Write transformBeta(value) for a finite numeric value; report whether value is positive. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value > 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": false}]`

## rf-javascript-classification-03-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-3`.

Write transformAlpha(value) for a finite numeric value; report whether value is negative. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value < 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": true}]`

## rf-javascript-classification-03-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-3`.

Write transformBeta(value) for a finite numeric value; report whether value is negative. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value < 0;
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": true}]`

## rf-javascript-classification-04-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-4`.

Write transformAlpha(value) for a finite numeric value; report whether value is zero. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return value === 0;
}
```

Expected cases (not executed): `[{"arguments": [0], "expected": true}]`

## rf-javascript-classification-04-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-4`.

Write transformBeta(value) for a finite numeric value; report whether value is zero. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return value === 0;
}
```

Expected cases (not executed): `[{"arguments": [0], "expected": true}]`

## rf-javascript-classification-05-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-5`.

Write transformAlpha(value) for a finite numeric value; return its sign using Math.sign. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.sign(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": -1}]`

## rf-javascript-classification-05-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-5`.

Write transformBeta(value) for a finite numeric value; return its sign using Math.sign. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return Math.sign(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": -1}]`

## rf-javascript-classification-06-1 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-6`.

Write transformAlpha(value) for a finite numeric value; return its absolute magnitude. Return one JavaScript function.

```javascript
function transformAlpha(value) {
  return Math.abs(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": 2}]`

## rf-javascript-classification-06-2 — validation

Family: `javascript-classification`; template: `javascript/classification/pattern-6`.

Write transformBeta(value) for a finite numeric value; return its absolute magnitude. Return one JavaScript function.

```javascript
function transformBeta(value) {
  return Math.abs(value);
}
```

Expected cases (not executed): `[{"arguments": [-2], "expected": 2}]`

## rf-javascript-array-lookup-01-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-1`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether items includes value. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.includes(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## rf-javascript-array-lookup-01-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-1`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; return whether items includes value. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.includes(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## rf-javascript-array-lookup-02-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-2`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return the first index of value or -1. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.indexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 0}]`

## rf-javascript-array-lookup-02-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-2`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; return the first index of value or -1. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.indexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 0}]`

## rf-javascript-array-lookup-03-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-3`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return the last index of value or -1. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.lastIndexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## rf-javascript-array-lookup-03-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-3`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; return the last index of value or -1. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.lastIndexOf(value);
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## rf-javascript-array-lookup-04-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-4`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether value equals the first element, using strict equality. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.length > 0 && items[0] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## rf-javascript-array-lookup-04-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-4`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; return whether value equals the first element, using strict equality. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.length > 0 && items[0] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": true}]`

## rf-javascript-array-lookup-05-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-5`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; return whether value equals the last element, using strict equality. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.length > 0 && items[items.length - 1] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 4], "expected": false}]`

## rf-javascript-array-lookup-05-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-5`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; return whether value equals the last element, using strict equality. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.length > 0 && items[items.length - 1] === value;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 4], "expected": false}]`

## rf-javascript-array-lookup-06-1 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-6`.

Write transformAlpha(items, value) for an array items and a value, with primitive elements; count elements strictly equal to value. Return one JavaScript function.

```javascript
function transformAlpha(items, value) {
  return items.filter(item => item === value).length;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## rf-javascript-array-lookup-06-2 — train

Family: `javascript-array-lookup`; template: `javascript/array-lookup/pattern-6`.

Write transformBeta(items, value) for an array items and a value, with primitive elements; count elements strictly equal to value. Return one JavaScript function.

```javascript
function transformBeta(items, value) {
  return items.filter(item => item === value).length;
}
```

Expected cases (not executed): `[{"arguments": [[2, 4, 2], 2], "expected": 2}]`

## rf-javascript-array-copy-01-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-1`.

Write transformAlpha(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2, 3]}]`

## rf-javascript-array-copy-01-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-1`.

Write transformBeta(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2, 3]}]`

## rf-javascript-array-copy-02-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-2`.

Write transformAlpha(items) for an array items; preserve the original array; return a reversed shallow copy. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice().reverse();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [3, 2, 1]}]`

## rf-javascript-array-copy-02-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-2`.

Write transformBeta(items) for an array items; preserve the original array; return a reversed shallow copy. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice().reverse();
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [3, 2, 1]}]`

## rf-javascript-array-copy-03-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-3`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy omitting the first element. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## rf-javascript-array-copy-03-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-3`.

Write transformBeta(items) for an array items; preserve the original array; return a copy omitting the first element. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice(1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## rf-javascript-array-copy-04-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-4`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy omitting the last element. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(0, -1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## rf-javascript-array-copy-04-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-4`.

Write transformBeta(items) for an array items; preserve the original array; return a copy omitting the last element. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice(0, -1);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## rf-javascript-array-copy-05-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-5`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy of at most the first two elements. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(0, 2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## rf-javascript-array-copy-05-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-5`.

Write transformBeta(items) for an array items; preserve the original array; return a copy of at most the first two elements. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice(0, 2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [1, 2]}]`

## rf-javascript-array-copy-06-1 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-6`.

Write transformAlpha(items) for an array items; preserve the original array; return a copy of at most the last two elements. Return one JavaScript function.

```javascript
function transformAlpha(items) {
  return items.slice(-2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## rf-javascript-array-copy-06-2 — train

Family: `javascript-array-copy`; template: `javascript/array-copy/pattern-6`.

Write transformBeta(items) for an array items; preserve the original array; return a copy of at most the last two elements. Return one JavaScript function.

```javascript
function transformBeta(items) {
  return items.slice(-2);
}
```

Expected cases (not executed): `[{"arguments": [[1, 2, 3]], "expected": [2, 3]}]`

## rf-javascript-string-slice-01-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-1`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the first count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.slice(0, count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "ab"}]`

## rf-javascript-string-slice-01-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-1`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the first count code units. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return text.slice(0, count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "ab"}]`

## rf-javascript-string-slice-02-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-2`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the first count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.slice(count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "cd"}]`

## rf-javascript-string-slice-02-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-2`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the first count code units. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return text.slice(count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": "cd"}]`

## rf-javascript-string-slice-03-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-3`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the last count code units, or empty if count is zero. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return count === 0 ? '' : text.slice(-count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": ""}]`

## rf-javascript-string-slice-03-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-3`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the last count code units, or empty if count is zero. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return count === 0 ? '' : text.slice(-count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": ""}]`

## rf-javascript-string-slice-04-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-4`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the last count code units, returning text unchanged for zero. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return count === 0 ? text : text.slice(0, -count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": "abcd"}]`

## rf-javascript-string-slice-04-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-4`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the last count code units, returning text unchanged for zero. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return count === 0 ? text : text.slice(0, -count);
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 0], "expected": "abcd"}]`

## rf-javascript-string-slice-05-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-5`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has more than count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.length > count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": true}]`

## rf-javascript-string-slice-05-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-5`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has more than count code units. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return text.length > count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": true}]`

## rf-javascript-string-slice-06-1 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-6`.

Write transformAlpha(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has exactly count code units. Return one JavaScript function.

```javascript
function transformAlpha(text, count) {
  return text.length === count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": false}]`

## rf-javascript-string-slice-06-2 — train

Family: `javascript-string-slice`; template: `javascript/string-slice/pattern-6`.

Write transformBeta(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has exactly count code units. Return one JavaScript function.

```javascript
function transformBeta(text, count) {
  return text.length === count;
}
```

Expected cases (not executed): `[{"arguments": ["abcd", 2], "expected": false}]`

## rf-javascript-string-build-01-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-1`.

Write transformAlpha(text) for a string text; surround text with square brackets. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return '[' + text + ']';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "[oak]"}]`

## rf-javascript-string-build-01-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-1`.

Write transformBeta(text) for a string text; surround text with square brackets. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return '[' + text + ']';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "[oak]"}]`

## rf-javascript-string-build-02-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-2`.

Write transformAlpha(text) for a string text; surround text with parentheses. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return '(' + text + ')';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "(oak)"}]`

## rf-javascript-string-build-02-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-2`.

Write transformBeta(text) for a string text; surround text with parentheses. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return '(' + text + ')';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "(oak)"}]`

## rf-javascript-string-build-03-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-3`.

Write transformAlpha(text) for a string text; prepend a hash character. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return '#' + text;
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "#oak"}]`

## rf-javascript-string-build-03-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-3`.

Write transformBeta(text) for a string text; prepend a hash character. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return '#' + text;
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "#oak"}]`

## rf-javascript-string-build-04-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-4`.

Write transformAlpha(text) for a string text; append an exclamation mark. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return text + '!';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "oak!"}]`

## rf-javascript-string-build-04-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-4`.

Write transformBeta(text) for a string text; append an exclamation mark. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return text + '!';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "oak!"}]`

## rf-javascript-string-build-05-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-5`.

Write transformAlpha(text) for a string text; concatenate text to itself. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return text + text;
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "oakoak"}]`

## rf-javascript-string-build-05-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-5`.

Write transformBeta(text) for a string text; concatenate text to itself. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return text + text;
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "oakoak"}]`

## rf-javascript-string-build-06-1 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-6`.

Write transformAlpha(text) for a string text; put one slash before and after text. Return one JavaScript function.

```javascript
function transformAlpha(text) {
  return '/' + text + '/';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "/oak/"}]`

## rf-javascript-string-build-06-2 — train

Family: `javascript-string-build`; template: `javascript/string-build/pattern-6`.

Write transformBeta(text) for a string text; put one slash before and after text. Return one JavaScript function.

```javascript
function transformBeta(text) {
  return '/' + text + '/';
}
```

Expected cases (not executed): `[{"arguments": ["oak"], "expected": "/oak/"}]`

## rf-javascript-object-lookup-01-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-1`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return the property value. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return record[key];
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": 3}]`

## rf-javascript-object-lookup-01-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-1`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; return the property value. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return record[key];
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": 3}]`

## rf-javascript-object-lookup-02-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-2`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; report whether record has an own property named key. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.prototype.hasOwnProperty.call(record, key);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": true}]`

## rf-javascript-object-lookup-02-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-2`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; report whether record has an own property named key. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return Object.prototype.hasOwnProperty.call(record, key);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": true}]`

## rf-javascript-object-lookup-03-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-3`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable string keys; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.keys(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": ["a"]}]`

## rf-javascript-object-lookup-03-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-3`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable string keys; key is unused. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return Object.keys(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": ["a"]}]`

## rf-javascript-object-lookup-04-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-4`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable values; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.values(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [3]}]`

## rf-javascript-object-lookup-04-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-4`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable values; key is unused. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return Object.values(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [3]}]`

## rf-javascript-object-lookup-05-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-5`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable key-value pairs; key is unused. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return Object.entries(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [["a", 3]]}]`

## rf-javascript-object-lookup-05-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-5`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable key-value pairs; key is unused. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return Object.entries(record);
}
```

Expected cases (not executed): `[{"arguments": [{"a": 3}, "a"], "expected": [["a", 3]]}]`

## rf-javascript-object-lookup-06-1 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-6`.

Write transformAlpha(record, key) for a plain object record and a string key; return results without mutation; report whether the property value is undefined. Return one JavaScript function.

```javascript
function transformAlpha(record, key) {
  return record[key] === undefined;
}
```

Expected cases (not executed): `[{"arguments": [{}, "a"], "expected": true}]`

## rf-javascript-object-lookup-06-2 — train

Family: `javascript-object-lookup`; template: `javascript/object-lookup/pattern-6`.

Write transformBeta(record, key) for a plain object record and a string key; return results without mutation; report whether the property value is undefined. Return one JavaScript function.

```javascript
function transformBeta(record, key) {
  return record[key] === undefined;
}
```

Expected cases (not executed): `[{"arguments": [{}, "a"], "expected": true}]`
