# P2 request-following v3: exact 234-record review

**Pending owner approval. No v3 records are used in training.**

This is a new candidate, not a modification of the approved v2 snapshot. It revises the 180 previous records to give each JavaScript function and CSS selector a distinct meaningful name, and adds 54 examples in nine new groups. The HTML v2 examples keep their existing requested structures; their new ids and split assignments still require approval.

Canonical JSONL SHA-256: `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`.

The source groups are indivisible between training and validation. JavaScript behavior is not executed. Static checks establish the supplied answers' consistency, not Plex capability.

## gap-html-ruby-01 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Use ruby with an rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby>Kyoto<rt>Kyo-to</rt></ruby>
```

## gap-html-ruby-02 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Put the whole ruby pronunciation annotation inside a paragraph. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<p><ruby>Kyoto<rt>Kyo-to</rt></ruby></p>
```

## gap-html-ruby-03 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Use ruby with rt and rp parentheses around the reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby>Kyoto<rp>(</rp><rt>Kyo-to</rt><rp>)</rp></ruby>
```

## gap-html-ruby-04 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Put the word in strong inside ruby, followed by its rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby><strong>Kyoto</strong><rt>Kyo-to</rt></ruby>
```

## gap-html-ruby-05 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Put the word in em inside ruby, followed by its rt reading. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<ruby><em>Kyoto</em><rt>Kyo-to</rt></ruby>
```

## gap-html-ruby-06 — train

Group `html-ruby`; origin `p2-02-request-following-v2`.

Put the whole ruby pronunciation annotation inside a span. Use word "Kyoto"; reading "Kyo-to". Return only the fragment.

```html
<span><ruby>Kyoto<rt>Kyo-to</rt></ruby></span>
```

## gap-html-disclosure-01 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make a collapsed details with summary and paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## gap-html-disclosure-02 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make an expanded details with summary and paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><p>A quiet destination.</p></details>
```

## gap-html-disclosure-03 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make a collapsed details with summary and a one-item unordered list. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><ul><li>A quiet destination.</li></ul></details>
```

## gap-html-disclosure-04 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make an expanded details with summary and a one-item ordered list. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><ol><li>A quiet destination.</li></ol></details>
```

## gap-html-disclosure-05 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make a collapsed details with summary and an emphasized body paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details><summary>Kyoto</summary><p><em>A quiet destination.</em></p></details>
```

## gap-html-disclosure-06 — train

Group `html-disclosure`; origin `p2-02-request-following-v2`.

Make an expanded details with summary and a strongly emphasized body paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<details open><summary>Kyoto</summary><p><strong>A quiet destination.</strong></p></details>
```

## gap-html-bidi-01 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Isolate the word using bdi. Use word "Kyoto". Return only the fragment.

```html
<bdi>Kyoto</bdi>
```

## gap-html-bidi-02 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Put a bdi-isolated word inside a paragraph. Use word "Kyoto". Return only the fragment.

```html
<p><bdi>Kyoto</bdi></p>
```

## gap-html-bidi-03 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Put a bdi-isolated word inside strong. Use word "Kyoto". Return only the fragment.

```html
<strong><bdi>Kyoto</bdi></strong>
```

## gap-html-bidi-04 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Put a bdi-isolated word inside em. Use word "Kyoto". Return only the fragment.

```html
<em><bdi>Kyoto</bdi></em>
```

## gap-html-bidi-05 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Put a bdi-isolated word inside a span with class isolated. Use word "Kyoto". Return only the fragment.

```html
<span class="isolated"><bdi>Kyoto</bdi></span>
```

## gap-html-bidi-06 — train

Group `html-bidi`; origin `p2-02-request-following-v2`.

Put a bdi-isolated word inside a one-item unordered list. Use word "Kyoto". Return only the fragment.

```html
<ul><li><bdi>Kyoto</bdi></li></ul>
```

## gap-html-quote-01 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Mark the sentence as an inline quotation using q. Use sentence "A quiet destination.". Return only the fragment.

```html
<q>A quiet destination.</q>
```

## gap-html-quote-02 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Put an inline q quotation inside a paragraph. Use sentence "A quiet destination.". Return only the fragment.

```html
<p><q>A quiet destination.</q></p>
```

## gap-html-quote-03 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Emphasize an inline q quotation using em around q. Use sentence "A quiet destination.". Return only the fragment.

```html
<em><q>A quiet destination.</q></em>
```

## gap-html-quote-04 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Put an inline q quotation inside strong. Use sentence "A quiet destination.". Return only the fragment.

```html
<strong><q>A quiet destination.</q></strong>
```

## gap-html-quote-05 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Put an inline q quotation inside a span with class quotation. Use sentence "A quiet destination.". Return only the fragment.

```html
<span class="quotation"><q>A quiet destination.</q></span>
```

## gap-html-quote-06 — train

Group `html-quote`; origin `p2-02-request-following-v2`.

Put an inline q quotation inside a one-item ordered list. Use sentence "A quiet destination.". Return only the fragment.

```html
<ol><li><q>A quiet destination.</q></li></ol>
```

## gap-html-abbreviation-01 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Mark the word as abbr with the sentence as its title. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<abbr title="Input and output">I/O</abbr>
```

## gap-html-abbreviation-02 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Put that titled abbreviation inside a paragraph. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<p><abbr title="Input and output">I/O</abbr></p>
```

## gap-html-abbreviation-03 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Put that titled abbreviation inside strong. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<strong><abbr title="Input and output">I/O</abbr></strong>
```

## gap-html-abbreviation-04 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Put that titled abbreviation inside em. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<em><abbr title="Input and output">I/O</abbr></em>
```

## gap-html-abbreviation-05 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Put that titled abbreviation inside a span with class term. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<span class="term"><abbr title="Input and output">I/O</abbr></span>
```

## gap-html-abbreviation-06 — validation

Group `html-abbreviation`; origin `p2-02-request-following-v2`.

Put that titled abbreviation inside a one-item unordered list. Use word "I/O"; sentence "Input and output". Return only the fragment.

```html
<ul><li><abbr title="Input and output">I/O</abbr></li></ul>
```

## gap-html-description-01 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Use dl with one dt word and one dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl>
```

## gap-html-description-02 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Use dl with the dt word inside strong and one dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt><strong>Kyoto</strong></dt><dd>A quiet destination.</dd></dl>
```

## gap-html-description-03 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Use dl with one dt word and the dd sentence inside em. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><em>A quiet destination.</em></dd></dl>
```

## gap-html-description-04 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Use dl with one dt word and the dd sentence inside a paragraph. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><dt>Kyoto</dt><dd><p>A quiet destination.</p></dd></dl>
```

## gap-html-description-05 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Wrap a one-term dl in a section; use dt for the word and dd for the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<section><dl><dt>Kyoto</dt><dd>A quiet destination.</dd></dl></section>
```

## gap-html-description-06 — train

Group `html-description`; origin `p2-02-request-following-v2`.

Use dl with a div wrapping its dt word and dd sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<dl><div><dt>Kyoto</dt><dd>A quiet destination.</dd></div></dl>
```

## gap-html-progress-01 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Make determinate progress with value 35 and max 100. Return only the fragment.

```html
<progress value="35" max="100"></progress>
```

## gap-html-progress-02 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Make determinate progress with value 35, max 100, and the word as fallback text. Use word "Kyoto". Return only the fragment.

```html
<progress value="35" max="100">Kyoto</progress>
```

## gap-html-progress-03 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Make indeterminate progress with the word as fallback text and no value attribute. Use word "Kyoto". Return only the fragment.

```html
<progress>Kyoto</progress>
```

## gap-html-progress-04 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Wrap determinate progress with value 35 and max 100 in a paragraph. Return only the fragment.

```html
<p><progress value="35" max="100"></progress></p>
```

## gap-html-progress-05 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Put indeterminate progress with the word as fallback text and no value attribute inside a span. Use word "Kyoto". Return only the fragment.

```html
<span><progress>Kyoto</progress></span>
```

## gap-html-progress-06 — train

Group `html-progress`; origin `p2-02-request-following-v2`.

Put determinate progress with value 35 and max 100 inside a div with class tracking. Return only the fragment.

```html
<div class="tracking"><progress value="35" max="100"></progress></div>
```

## gap-html-meter-01 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Make a meter with min 0, max 100, and value 35. Return only the fragment.

```html
<meter min="0" max="100" value="35"></meter>
```

## gap-html-meter-02 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Make a meter with min 0, max 100, value 35, and the word as fallback text. Use word "Kyoto". Return only the fragment.

```html
<meter min="0" max="100" value="35">Kyoto</meter>
```

## gap-html-meter-03 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Make a meter with min 0, max 100, value 35, low 20, high 80, and optimum 50. Return only the fragment.

```html
<meter min="0" max="100" value="35" low="20" high="80" optimum="50"></meter>
```

## gap-html-meter-04 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Put a meter with min 0, max 100, and value 35 inside a paragraph. Return only the fragment.

```html
<p><meter min="0" max="100" value="35"></meter></p>
```

## gap-html-meter-05 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Put a meter with min 0, max 100, and value 35 inside a span. Return only the fragment.

```html
<span><meter min="0" max="100" value="35"></meter></span>
```

## gap-html-meter-06 — validation

Group `html-meter`; origin `p2-02-request-following-v2`.

Put a meter with min 0, max 100, and value 35 inside a div with class reading. Return only the fragment.

```html
<div class="reading"><meter min="0" max="100" value="35"></meter></div>
```

## gap-html-contact-01 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put the word in address as plain contact text. Use word "Kyoto". Return only the fragment.

```html
<address>Kyoto</address>
```

## gap-html-contact-02 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put the word in a paragraph inside address. Use word "Kyoto". Return only the fragment.

```html
<address><p>Kyoto</p></address>
```

## gap-html-contact-03 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put the word in strong inside address. Use word "Kyoto". Return only the fragment.

```html
<address><strong>Kyoto</strong></address>
```

## gap-html-contact-04 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put the word in a span with class contact inside address. Use word "Kyoto". Return only the fragment.

```html
<address><span class="contact">Kyoto</span></address>
```

## gap-html-contact-05 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put the word then br then the sentence inside address. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<address>Kyoto<br>A quiet destination.</address>
```

## gap-html-contact-06 — validation

Group `html-contact`; origin `p2-02-request-following-v2`.

Put two paragraphs in address: the word then the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<address><p>Kyoto</p><p>A quiet destination.</p></address>
```

## gap-html-heading-group-01 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Make hgroup containing h1 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h1>Kyoto</h1><p>A quiet destination.</p></hgroup>
```

## gap-html-heading-group-02 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Make hgroup containing h2 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup>
```

## gap-html-heading-group-03 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Make hgroup containing h3 with the word and p with the sentence. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h3>Kyoto</h3><p>A quiet destination.</p></hgroup>
```

## gap-html-heading-group-04 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Make hgroup containing p with the sentence then h2 with the word. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><p>A quiet destination.</p><h2>Kyoto</h2></hgroup>
```

## gap-html-heading-group-05 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Make hgroup containing h2 with the word and p with the sentence inside em. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<hgroup><h2>Kyoto</h2><p><em>A quiet destination.</em></p></hgroup>
```

## gap-html-heading-group-06 — train

Group `html-heading-group`; origin `p2-02-request-following-v2`.

Wrap hgroup in a header; put the word in h2 and the sentence in p. Use word "Kyoto"; sentence "A quiet destination.". Return only the fragment.

```html
<header><hgroup><h2>Kyoto</h2><p>A quiet destination.</p></hgroup></header>
```

## gap-html-navigation-01 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Make a footer navigation named Resources with links to Guides and Support. Return code only.

```html
<nav aria-label="Resources"><a href="/guides">Guides</a><a href="/support">Support</a></nav>
```

## gap-html-navigation-02 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Create a sidebar navigation named Topics containing a list with Art and Music links. Return code only.

```html
<nav aria-label="Topics"><ul><li><a href="/art">Art</a></li><li><a href="/music">Music</a></li></ul></nav>
```

## gap-html-navigation-03 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Create a navigation named Account with Sign in and Help links, separated by a span containing a vertical bar. Return code only.

```html
<nav aria-label="Account"><a href="/signin">Sign in</a><span>|</span><a href="/help">Help</a></nav>
```

## gap-html-navigation-04 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Make a footer with a navigation named Legal containing Terms and Privacy links. Return code only.

```html
<footer><nav aria-label="Legal"><a href="/terms">Terms</a><a href="/privacy">Privacy</a></nav></footer>
```

## gap-html-navigation-05 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Build a list of two section links inside a navigation named Chapters: Start and Finish. Return code only.

```html
<nav aria-label="Chapters"><ol><li><a href="#start">Start</a></li><li><a href="#finish">Finish</a></li></ol></nav>
```

## gap-html-navigation-06 — train

Group `html-navigation`; origin `p2-development-failure-audit`.

Create a header with a brand link named Atlas and navigation named Pages containing a Docs link. Return code only.

```html
<header><a href="/">Atlas</a><nav aria-label="Pages"><a href="/docs">Docs</a></nav></header>
```

## gap-html-forms-01 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Make a form with a label for a required text input id username and a Save submit button. Return code only.

```html
<form><label for="username">Username</label><input id="username" name="username" type="text" required><button type="submit">Save</button></form>
```

## gap-html-forms-02 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Create a labeled textarea id notes in a form with a Send submit button. Return code only.

```html
<form><label for="notes">Notes</label><textarea id="notes" name="notes"></textarea><button type="submit">Send</button></form>
```

## gap-html-forms-03 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Make a form with a label for a select id region with North and South options. Return code only.

```html
<form><label for="region">Region</label><select id="region" name="region"><option value="north">North</option><option value="south">South</option></select></form>
```

## gap-html-forms-04 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Make a labeled number input id quantity with minimum 1 and a Place order submit button. Return code only.

```html
<form><label for="quantity">Quantity</label><input id="quantity" name="quantity" type="number" min="1"><button type="submit">Place order</button></form>
```

## gap-html-forms-05 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Make a form with two radio choices named size, Small and Large, each wrapped in its own label. Return code only.

```html
<form><label><input type="radio" name="size" value="small">Small</label><label><input type="radio" name="size" value="large">Large</label></form>
```

## gap-html-forms-06 — validation

Group `html-forms`; origin `p2-development-failure-audit`.

Make a form with a labeled password input id passcode and a Reset button that does not submit. Return code only.

```html
<form><label for="passcode">Passcode</label><input id="passcode" name="passcode" type="password"><button type="reset">Reset</button></form>
```

## gap-html-content-01 — train

Group `html-content`; origin `p2-development-failure-audit`.

Create a figure with a diagram image diagram.png, descriptive alt text Flow diagram, and caption Process flow. Return code only.

```html
<figure><img src="diagram.png" alt="Flow diagram"><figcaption>Process flow</figcaption></figure>
```

## gap-html-content-02 — train

Group `html-content`; origin `p2-development-failure-audit`.

Make an article with a heading Shipping update and one paragraph Packages leave tomorrow. Return code only.

```html
<article><h2>Shipping update</h2><p>Packages leave tomorrow.</p></article>
```

## gap-html-content-03 — train

Group `html-content`; origin `p2-development-failure-audit`.

Create a table with caption Inventory, one header Item and one body cell Lamp. Return code only.

```html
<table><caption>Inventory</caption><thead><tr><th scope="col">Item</th></tr></thead><tbody><tr><td>Lamp</td></tr></tbody></table>
```

## gap-html-content-04 — train

Group `html-content`; origin `p2-development-failure-audit`.

Build an ordered list with two items, Prepare and Publish, under a heading Workflow. Return code only.

```html
<section><h2>Workflow</h2><ol><li>Prepare</li><li>Publish</li></ol></section>
```

## gap-html-content-05 — train

Group `html-content`; origin `p2-development-failure-audit`.

Make an image of mountains with a descriptive alt inside a linked figure captioned Trail map. Return code only.

```html
<figure><a href="/trails"><img src="mountains.png" alt="Mountain trail"></a><figcaption>Trail map</figcaption></figure>
```

## gap-html-content-06 — train

Group `html-content`; origin `p2-development-failure-audit`.

Create an aside with a heading Tip and a paragraph Read the guide first. Return code only.

```html
<aside><h3>Tip</h3><p>Read the guide first.</p></aside>
```

## gap-css-logical-border-01 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .start-edge: Add a 2px solid #334155 border on the inline start edge only. Return one rule with only the requested declarations.

```css
.start-edge {
  border-inline-start: 2px solid #334155;
}
```

## gap-css-logical-border-02 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .end-edge: Add a 2px solid #334155 border on the inline end edge only. Return one rule with only the requested declarations.

```css
.end-edge {
  border-inline-end: 2px solid #334155;
}
```

## gap-css-logical-border-03 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .top-edge: Add a 2px dashed #334155 border on the block start edge only. Return one rule with only the requested declarations.

```css
.top-edge {
  border-block-start: 2px dashed #334155;
}
```

## gap-css-logical-border-04 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .bottom-edge: Add a 2px dashed #334155 border on the block end edge only. Return one rule with only the requested declarations.

```css
.bottom-edge {
  border-block-end: 2px dashed #334155;
}
```

## gap-css-logical-border-05 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .paired-inline-edge: Add a 2px solid #334155 inline start border and remove the inline end border. Return one rule with only the requested declarations.

```css
.paired-inline-edge {
  border-inline-start: 2px solid #334155;
  border-inline-end: 0;
}
```

## gap-css-logical-border-06 — train

Group `css-logical-border`; origin `p2-02-request-following-v2`.

For .paired-block-edge: Remove the block start border and add a 2px solid #334155 block end border. Return one rule with only the requested declarations.

```css
.paired-block-edge {
  border-block-start: 0;
  border-block-end: 2px solid #334155;
}
```

## gap-css-aspect-01 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .square-thumb: Use a preferred square aspect ratio. Return one rule with only the requested declarations.

```css
.square-thumb {
  aspect-ratio: 1 / 1;
}
```

## gap-css-aspect-02 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .wide-thumb: Use a preferred 16:9 aspect ratio with width 240px. Return one rule with only the requested declarations.

```css
.wide-thumb {
  aspect-ratio: 16 / 9;
  width: 240px;
}
```

## gap-css-aspect-03 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .framed-thumb: Use a preferred 4:3 aspect ratio and cap width at 100%. Return one rule with only the requested declarations.

```css
.framed-thumb {
  aspect-ratio: 4 / 3;
  max-width: 100%;
}
```

## gap-css-aspect-04 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .avatar-box: Use a preferred square aspect ratio with height 120px. Return one rule with only the requested declarations.

```css
.avatar-box {
  aspect-ratio: 1 / 1;
  height: 120px;
}
```

## gap-css-aspect-05 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .poster-box: Use a preferred 16:9 aspect ratio and include padding inside the border-box size. Return one rule with only the requested declarations.

```css
.poster-box {
  aspect-ratio: 16 / 9;
  box-sizing: border-box;
}
```

## gap-css-aspect-06 — train

Group `css-aspect`; origin `p2-02-request-following-v2`.

For .compact-thumb: Use a preferred 4:3 aspect ratio and a minimum width of 180px. Return one rule with only the requested declarations.

```css
.compact-thumb {
  aspect-ratio: 4 / 3;
  min-width: 180px;
}
```

## gap-css-outline-01 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .solid-focus: Use a solid outline style. Return one rule with only the requested declarations.

```css
.solid-focus {
  outline-style: solid;
}
```

## gap-css-outline-02 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .thick-focus: Use a 2px solid #334155 outline. Return one rule with only the requested declarations.

```css
.thick-focus {
  outline: 2px solid #334155;
}
```

## gap-css-outline-03 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .spaced-focus: Use a 2px solid #334155 outline offset outward by 4px. Return one rule with only the requested declarations.

```css
.spaced-focus {
  outline: 2px solid #334155;
  outline-offset: 4px;
}
```

## gap-css-outline-04 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .unoutlined-focus: Remove both the outline and any box shadow. Return one rule with only the requested declarations.

```css
.unoutlined-focus {
  outline: 0;
  box-shadow: none;
}
```

## gap-css-outline-05 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .dotted-focus: Use a dotted outline style, 3px width, and -2px offset. Return one rule with only the requested declarations.

```css
.dotted-focus {
  outline-style: dotted;
  outline-width: 3px;
  outline-offset: -2px;
}
```

## gap-css-outline-06 — train

Group `css-outline`; origin `p2-02-request-following-v2`.

For .dashed-focus: Use a dashed outline style and #334155 outline color. Return one rule with only the requested declarations.

```css
.dashed-focus {
  outline-style: dashed;
  outline-color: #334155;
}
```

## gap-css-cursor-01 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .click-target: Show a pointer cursor. Return one rule with only the requested declarations.

```css
.click-target {
  cursor: pointer;
}
```

## gap-css-cursor-02 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .blocked-target: Show a forbidden cursor and opacity 0.5. Return one rule with only the requested declarations.

```css
.blocked-target {
  cursor: not-allowed;
  opacity: 0.5;
}
```

## gap-css-cursor-03 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .drag-handle: Show a grab cursor and prevent text selection. Return one rule with only the requested declarations.

```css
.drag-handle {
  cursor: grab;
  user-select: none;
}
```

## gap-css-cursor-04 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .busy-target: Show a wait cursor and disable pointer targeting. Return one rule with only the requested declarations.

```css
.busy-target {
  cursor: wait;
  pointer-events: none;
}
```

## gap-css-cursor-05 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .editable-copy: Show a text cursor and color #334155. Return one rule with only the requested declarations.

```css
.editable-copy {
  cursor: text;
  color: #334155;
}
```

## gap-css-cursor-06 — validation

Group `css-cursor`; origin `p2-02-request-following-v2`.

For .plain-target: Show a default cursor and display as a block. Return one rule with only the requested declarations.

```css
.plain-target {
  cursor: default;
  display: block;
}
```

## gap-css-whitespace-01 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .single-line: Keep text on one unwrapped line. Return one rule with only the requested declarations.

```css
.single-line {
  white-space: nowrap;
}
```

## gap-css-whitespace-02 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .preserved-wrap: Preserve whitespace while allowing wraps, including breaks anywhere in long tokens. Return one rule with only the requested declarations.

```css
.preserved-wrap {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

## gap-css-whitespace-03 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .tabbed-copy: Preserve whitespace and use a tab size of 4. Return one rule with only the requested declarations.

```css
.tabbed-copy {
  white-space: pre;
  tab-size: 4;
}
```

## gap-css-whitespace-04 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .ordinary-copy: Collapse ordinary whitespace, allow wrapping, and use line-height 1.5. Return one rule with only the requested declarations.

```css
.ordinary-copy {
  white-space: normal;
  line-height: 1.5;
}
```

## gap-css-whitespace-05 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .spaced-copy: Preserve spaces with break-spaces and set word-spacing to 2px. Return one rule with only the requested declarations.

```css
.spaced-copy {
  white-space: break-spaces;
  word-spacing: 2px;
}
```

## gap-css-whitespace-06 — train

Group `css-whitespace`; origin `p2-02-request-following-v2`.

For .newline-copy: Preserve newlines but collapse spaces, and indent the first line by 1em. Return one rule with only the requested declarations.

```css
.newline-copy {
  white-space: pre-line;
  text-indent: 1em;
}
```

## gap-css-decoration-01 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .underlined-link: Underline text. Return one rule with only the requested declarations.

```css
.underlined-link {
  text-decoration-line: underline;
}
```

## gap-css-decoration-02 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .wavy-link: Use a wavy underline. Return one rule with only the requested declarations.

```css
.wavy-link {
  text-decoration-line: underline;
  text-decoration-style: wavy;
}
```

## gap-css-decoration-03 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .tinted-link: Use an underline colored #334155. Return one rule with only the requested declarations.

```css
.tinted-link {
  text-decoration-line: underline;
  text-decoration-color: #334155;
}
```

## gap-css-decoration-04 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .overline-link: Use both underline and overline with underline offset 4px. Return one rule with only the requested declarations.

```css
.overline-link {
  text-decoration-line: underline overline;
  text-underline-offset: 4px;
}
```

## gap-css-decoration-05 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .struck-label: Use line-through with a thickness of 2px. Return one rule with only the requested declarations.

```css
.struck-label {
  text-decoration-line: line-through;
  text-decoration-thickness: 2px;
}
```

## gap-css-decoration-06 — validation

Group `css-decoration`; origin `p2-02-request-following-v2`.

For .solid-link: Use a solid underline and disable automatic ink skipping. Return one rule with only the requested declarations.

```css
.solid-link {
  text-decoration: underline solid;
  text-decoration-skip-ink: none;
}
```

## gap-css-overflow-01 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .horizontal-scroll: Allow automatic horizontal scrolling. Return one rule with only the requested declarations.

```css
.horizontal-scroll {
  overflow-x: auto;
}
```

## gap-css-overflow-02 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .vertical-scroll: Always provide vertical scrolling. Return one rule with only the requested declarations.

```css
.vertical-scroll {
  overflow-y: scroll;
}
```

## gap-css-overflow-03 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .clipped-panel: Hide overflow on both axes. Return one rule with only the requested declarations.

```css
.clipped-panel {
  overflow: hidden;
}
```

## gap-css-overflow-04 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .clip-context: Clip overflow and create a flow-root formatting context. Return one rule with only the requested declarations.

```css
.clip-context {
  overflow: clip;
  display: flow-root;
}
```

## gap-css-overflow-05 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .one-axis-scroll: Allow automatic horizontal scrolling and hide vertical overflow. Return one rule with only the requested declarations.

```css
.one-axis-scroll {
  overflow-x: auto;
  overflow-y: hidden;
}
```

## gap-css-overflow-06 — validation

Group `css-overflow`; origin `p2-02-request-following-v2`.

For .short-scroll: Allow automatic scrolling on both axes and limit height to 200px. Return one rule with only the requested declarations.

```css
.short-scroll {
  overflow: auto;
  max-height: 200px;
}
```

## gap-css-table-01 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .automatic-table: Use automatic table layout. Return one rule with only the requested declarations.

```css
.automatic-table {
  table-layout: auto;
}
```

## gap-css-table-02 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .fixed-table: Use fixed table layout and width 100%. Return one rule with only the requested declarations.

```css
.fixed-table {
  table-layout: fixed;
  width: 100%;
}
```

## gap-css-table-03 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .collapsed-table: Collapse table borders. Return one rule with only the requested declarations.

```css
.collapsed-table {
  border-collapse: collapse;
}
```

## gap-css-table-04 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .spaced-table: Keep borders separate with 8px spacing. Return one rule with only the requested declarations.

```css
.spaced-table {
  border-collapse: separate;
  border-spacing: 8px;
}
```

## gap-css-table-05 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .below-caption: Place the table caption below the table. Return one rule with only the requested declarations.

```css
.below-caption {
  caption-side: bottom;
}
```

## gap-css-table-06 — train

Group `css-table`; origin `p2-02-request-following-v2`.

For .separate-table: Hide empty cells and keep borders separate. Return one rule with only the requested declarations.

```css
.separate-table {
  empty-cells: hide;
  border-collapse: separate;
}
```

## gap-css-columns-01 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .two-column-copy: Use two text columns. Return one rule with only the requested declarations.

```css
.two-column-copy {
  column-count: 2;
}
```

## gap-css-columns-02 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .narrow-column-copy: Use a preferred column width of 180px. Return one rule with only the requested declarations.

```css
.narrow-column-copy {
  column-width: 180px;
}
```

## gap-css-columns-03 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .three-column-copy: Use three columns separated by 24px gaps. Return one rule with only the requested declarations.

```css
.three-column-copy {
  column-count: 3;
  column-gap: 24px;
}
```

## gap-css-columns-04 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .ruled-copy: Use two columns with a 1px solid #334155 column rule. Return one rule with only the requested declarations.

```css
.ruled-copy {
  column-count: 2;
  column-rule: 1px solid #334155;
}
```

## gap-css-columns-05 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .full-column-title: Make the element span every column. Return one rule with only the requested declarations.

```css
.full-column-title {
  column-span: all;
}
```

## gap-css-columns-06 — train

Group `css-columns`; origin `p2-02-request-following-v2`.

For .sequential-copy: Fill columns sequentially with column-fill auto and height 300px. Return one rule with only the requested declarations.

```css
.sequential-copy {
  column-fill: auto;
  height: 300px;
}
```

## gap-css-object-fit-01 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .contained-photo: Contain the entire image in its existing box. Return one rule with only the requested declarations.

```css
.contained-photo {
  object-fit: contain;
}
```

## gap-css-object-fit-02 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .covered-photo: Cover the existing box with the image and align it at the right bottom. Return one rule with only the requested declarations.

```css
.covered-photo {
  object-fit: cover;
  object-position: right bottom;
}
```

## gap-css-object-fit-03 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .stretched-photo: Stretch the image to fill its box and display it as a block. Return one rule with only the requested declarations.

```css
.stretched-photo {
  object-fit: fill;
  display: block;
}
```

## gap-css-object-fit-04 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .bounded-photo: Contain the image and limit its width to 100%. Return one rule with only the requested declarations.

```css
.bounded-photo {
  object-fit: contain;
  max-width: 100%;
}
```

## gap-css-object-fit-05 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .scaled-photo: Use scale-down image fitting and set its width to 160px. Return one rule with only the requested declarations.

```css
.scaled-photo {
  object-fit: scale-down;
  width: 160px;
}
```

## gap-css-object-fit-06 — train

Group `css-object-fit`; origin `p2-02-request-following-v2`.

For .unfitted-photo: Do not resize the image content for fitting and set its box height to 120px. Return one rule with only the requested declarations.

```css
.unfitted-photo {
  object-fit: none;
  height: 120px;
}
```

## gap-css-layout-01 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .toolbar a flex row with a 12px gap and centered items. Return code only.

```css
.toolbar { display: flex; gap: 12px; align-items: center; }
```

## gap-css-layout-02 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .tile-list a three-column grid with 16px gaps. Return code only.

```css
.tile-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
```

## gap-css-layout-03 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .badge-row wrap its flex items with an 8px gap. Return code only.

```css
.badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
```

## gap-css-layout-04 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .sidebar-layout a grid with a 180px sidebar and flexible content, separated by 24px. Return code only.

```css
.sidebar-layout { display: grid; grid-template-columns: 180px 1fr; gap: 24px; }
```

## gap-css-layout-05 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .actions a flex row that places items at opposite ends and centers them vertically. Return code only.

```css
.actions { display: flex; justify-content: space-between; align-items: center; }
```

## gap-css-layout-06 — train

Group `css-layout`; origin `p2-development-failure-audit`.

Make .stack a column flex container with 20px between children. Return code only.

```css
.stack { display: flex; flex-direction: column; gap: 20px; }
```

## gap-css-state-01 — validation

Group `css-state`; origin `p2-development-failure-audit`.

Give .tab:focus-visible a 3px solid royalblue outline and 3px offset. Return code only.

```css
.tab:focus-visible { outline: 3px solid royalblue; outline-offset: 3px; }
```

## gap-css-state-02 — validation

Group `css-state`; origin `p2-development-failure-audit`.

On .menu-link:hover, underline the text and change color to navy. Return code only.

```css
.menu-link:hover { text-decoration: underline; color: navy; }
```

## gap-css-state-03 — validation

Group `css-state`; origin `p2-development-failure-audit`.

For .send-button:disabled, reduce opacity to 0.4 and show a not-allowed cursor. Return code only.

```css
.send-button:disabled { opacity: 0.4; cursor: not-allowed; }
```

## gap-css-state-04 — validation

Group `css-state`; origin `p2-development-failure-audit`.

For .step-link[aria-current='step'], use font-weight 700 and a 2px solid border below. Return code only.

```css
.step-link[aria-current='step'] { font-weight: 700; border-bottom: 2px solid; }
```

## gap-css-state-05 — validation

Group `css-state`; origin `p2-development-failure-audit`.

For .chip[aria-pressed='true'], use a dark background and white text. Return code only.

```css
.chip[aria-pressed='true'] { background: #1e293b; color: white; }
```

## gap-css-state-06 — validation

Group `css-state`; origin `p2-development-failure-audit`.

For .text-field:invalid, set a crimson border and pale pink background. Return code only.

```css
.text-field:invalid { border: 1px solid crimson; background: mistyrose; }
```

## gap-css-sizing-01 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Make .reading-pane at most 60ch wide with 16px inline padding. Return code only.

```css
.reading-pane { max-width: 60ch; padding-inline: 16px; }
```

## gap-css-sizing-02 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Make .hero-photo fill available width, keep auto height, and display as block. Return code only.

```css
.hero-photo { max-width: 100%; height: auto; display: block; }
```

## gap-css-sizing-03 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Give .video-frame a 16:9 ratio and cap its width at 720px. Return code only.

```css
.video-frame { aspect-ratio: 16 / 9; max-width: 720px; }
```

## gap-css-sizing-04 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Make .quote-box at least 120px tall and include padding in its box size. Return code only.

```css
.quote-box { min-height: 120px; box-sizing: border-box; }
```

## gap-css-sizing-05 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Make .scroll-region at most 240px tall with vertical auto scrolling. Return code only.

```css
.scroll-region { max-height: 240px; overflow-y: auto; }
```

## gap-css-sizing-06 — train

Group `css-sizing`; origin `p2-development-failure-audit`.

Make .cover-art 200px wide and 200px tall, cropping its image to cover. Return code only.

```css
.cover-art { width: 200px; height: 200px; object-fit: cover; }
```

## gap-javascript-binary-01 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write addNumbers(a, b) for finite numbers a and b; return a plus b. Return one JavaScript function.

```javascript
function addNumbers(a, b) {
  return a + b;
}
```

## gap-javascript-binary-02 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write subtractNumbers(a, b) for finite numbers a and b; return a minus b. Return one JavaScript function.

```javascript
function subtractNumbers(a, b) {
  return a - b;
}
```

## gap-javascript-binary-03 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write multiplyNumbers(a, b) for finite numbers a and b; return the product of a and b. Return one JavaScript function.

```javascript
function multiplyNumbers(a, b) {
  return a * b;
}
```

## gap-javascript-binary-04 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write largerNumber(a, b) for finite numbers a and b; return the larger number. Return one JavaScript function.

```javascript
function largerNumber(a, b) {
  return Math.max(a, b);
}
```

## gap-javascript-binary-05 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write smallerNumber(a, b) for finite numbers a and b; return the smaller number. Return one JavaScript function.

```javascript
function smallerNumber(a, b) {
  return Math.min(a, b);
}
```

## gap-javascript-binary-06 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write absoluteGap(a, b) for finite numbers a and b; return the absolute difference. Return one JavaScript function.

```javascript
function absoluteGap(a, b) {
  return Math.abs(a - b);
}
```

## gap-javascript-bound-01 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write capAtLimit(value, limit) for finite numbers value and limit; cap value at the upper limit using a conditional expression. Return one JavaScript function.

```javascript
function capAtLimit(value, limit) {
  return value > limit ? limit : value;
}
```

## gap-javascript-bound-02 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write raiseToLimit(value, limit) for finite numbers value and limit; raise value to the lower limit using a conditional expression. Return one JavaScript function.

```javascript
function raiseToLimit(value, limit) {
  return value < limit ? limit : value;
}
```

## gap-javascript-bound-03 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write exceedsLimit(value, limit) for finite numbers value and limit; report whether value exceeds limit. Return one JavaScript function.

```javascript
function exceedsLimit(value, limit) {
  return value > limit;
}
```

## gap-javascript-bound-04 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write belowLimit(value, limit) for finite numbers value and limit; report whether value is below limit. Return one JavaScript function.

```javascript
function belowLimit(value, limit) {
  return value < limit;
}
```

## gap-javascript-bound-05 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write equalsLimit(value, limit) for finite numbers value and limit; report whether value equals limit. Return one JavaScript function.

```javascript
function equalsLimit(value, limit) {
  return value === limit;
}
```

## gap-javascript-bound-06 — validation

Group `javascript-numeric-comparison`; origin `p2-02-request-following-v2`.

Write distanceFromLimit(value, limit) for finite numbers value and limit; return the absolute distance using a conditional expression. Return one JavaScript function.

```javascript
function distanceFromLimit(value, limit) {
  return value > limit ? value - limit : limit - value;
}
```

## gap-javascript-division-01 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write quotientTowardZero(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded toward zero. Return one JavaScript function.

```javascript
function quotientTowardZero(a, b) {
  return Math.trunc(a / b);
}
```

## gap-javascript-division-02 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write quotientDown(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded down. Return one JavaScript function.

```javascript
function quotientDown(a, b) {
  return Math.floor(a / b);
}
```

## gap-javascript-division-03 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write quotientUp(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the quotient rounded up. Return one JavaScript function.

```javascript
function quotientUp(a, b) {
  return Math.ceil(a / b);
}
```

## gap-javascript-division-04 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write javascriptRemainder(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the JavaScript remainder. Return one JavaScript function.

```javascript
function javascriptRemainder(a, b) {
  return a % b;
}
```

## gap-javascript-division-05 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write isDivisible(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return whether a is divisible by b. Return one JavaScript function.

```javascript
function isDivisible(a, b) {
  return a % b === 0;
}
```

## gap-javascript-division-06 — train

Group `javascript-division`; origin `p2-02-request-following-v2`.

Write absoluteRemainder(a, b) for integers a and b with b nonzero and small enough for exact arithmetic; return the absolute JavaScript remainder. Return one JavaScript function.

```javascript
function absoluteRemainder(a, b) {
  return Math.abs(a % b);
}
```

## gap-javascript-conversion-01 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write secondsToMillis(value) for a finite numeric value; convert seconds to milliseconds. Return one JavaScript function.

```javascript
function secondsToMillis(value) {
  return value * 1000;
}
```

## gap-javascript-conversion-02 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write millisToSeconds(value) for a finite numeric value; convert milliseconds to seconds. Return one JavaScript function.

```javascript
function millisToSeconds(value) {
  return value / 1000;
}
```

## gap-javascript-conversion-03 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write wholeMinutes(value) for a nonnegative finite numeric value; convert nonnegative seconds to completed whole minutes, rounded down. Return one JavaScript function.

```javascript
function wholeMinutes(value) {
  return Math.floor(value / 60);
}
```

## gap-javascript-conversion-04 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write metersToUnits(value) for a finite numeric value; return an object with centimeters and millimeters converted from meters. Return one JavaScript function.

```javascript
function metersToUnits(value) {
  return { centimeters: value * 100, millimeters: value * 1000 };
}
```

## gap-javascript-conversion-05 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write minutesToUnits(value) for a finite numeric value; return an array containing seconds then milliseconds converted from minutes. Return one JavaScript function.

```javascript
function minutesToUnits(value) {
  return [value * 60, value * 60000];
}
```

## gap-javascript-conversion-06 — train

Group `javascript-conversion`; origin `p2-02-request-following-v2`.

Write roundedSeconds(value) for a nonnegative finite numeric value; convert nonnegative milliseconds to seconds rounded up. Return one JavaScript function.

```javascript
function roundedSeconds(value) {
  return Math.ceil(value / 1000);
}
```

## gap-javascript-classification-01 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write isWholeNumber(value) for a finite numeric value; report whether value is an integer. Return one JavaScript function.

```javascript
function isWholeNumber(value) {
  return Number.isInteger(value);
}
```

## gap-javascript-classification-02 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write isPositive(value) for a finite numeric value; report whether value is positive. Return one JavaScript function.

```javascript
function isPositive(value) {
  return value > 0;
}
```

## gap-javascript-classification-03 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write isNegative(value) for a finite numeric value; report whether value is negative. Return one JavaScript function.

```javascript
function isNegative(value) {
  return value < 0;
}
```

## gap-javascript-classification-04 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write isZero(value) for a finite numeric value; report whether value is zero. Return one JavaScript function.

```javascript
function isZero(value) {
  return value === 0;
}
```

## gap-javascript-classification-05 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write numberSign(value) for a finite numeric value; return its sign using Math.sign. Return one JavaScript function.

```javascript
function numberSign(value) {
  return Math.sign(value);
}
```

## gap-javascript-classification-06 — train

Group `javascript-classification`; origin `p2-02-request-following-v2`.

Write absoluteMagnitude(value) for a finite numeric value; return its absolute magnitude. Return one JavaScript function.

```javascript
function absoluteMagnitude(value) {
  return Math.abs(value);
}
```

## gap-javascript-array-lookup-01 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write hasItem(items, value) for an array items and a value, with primitive elements; return whether items includes value. Return one JavaScript function.

```javascript
function hasItem(items, value) {
  return items.includes(value);
}
```

## gap-javascript-array-lookup-02 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write firstItemIndex(items, value) for an array items and a value, with primitive elements; return the first index of value or -1. Return one JavaScript function.

```javascript
function firstItemIndex(items, value) {
  return items.indexOf(value);
}
```

## gap-javascript-array-lookup-03 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write lastItemIndex(items, value) for an array items and a value, with primitive elements; return the last index of value or -1. Return one JavaScript function.

```javascript
function lastItemIndex(items, value) {
  return items.lastIndexOf(value);
}
```

## gap-javascript-array-lookup-04 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write startsWithItem(items, value) for an array items and a value, with primitive elements; return whether value equals the first element, using strict equality. Return one JavaScript function.

```javascript
function startsWithItem(items, value) {
  return items.length > 0 && items[0] === value;
}
```

## gap-javascript-array-lookup-05 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write endsWithItem(items, value) for an array items and a value, with primitive elements; return whether value equals the last element, using strict equality. Return one JavaScript function.

```javascript
function endsWithItem(items, value) {
  return items.length > 0 && items[items.length - 1] === value;
}
```

## gap-javascript-array-lookup-06 — train

Group `javascript-array-lookup`; origin `p2-02-request-following-v2`.

Write countMatchingItems(items, value) for an array items and a value, with primitive elements; count elements strictly equal to value. Return one JavaScript function.

```javascript
function countMatchingItems(items, value) {
  return items.filter(item => item === value).length;
}
```

## gap-javascript-array-copy-01 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write copyItems(items) for an array items; preserve the original array; return a shallow copy. Return one JavaScript function.

```javascript
function copyItems(items) {
  return items.slice();
}
```

## gap-javascript-array-copy-02 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write reverseItems(items) for an array items; preserve the original array; return a reversed shallow copy. Return one JavaScript function.

```javascript
function reverseItems(items) {
  return items.slice().reverse();
}
```

## gap-javascript-array-copy-03 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write withoutFirst(items) for an array items; preserve the original array; return a copy omitting the first element. Return one JavaScript function.

```javascript
function withoutFirst(items) {
  return items.slice(1);
}
```

## gap-javascript-array-copy-04 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write withoutLast(items) for an array items; preserve the original array; return a copy omitting the last element. Return one JavaScript function.

```javascript
function withoutLast(items) {
  return items.slice(0, -1);
}
```

## gap-javascript-array-copy-05 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write takeFirstTwo(items) for an array items; preserve the original array; return a copy of at most the first two elements. Return one JavaScript function.

```javascript
function takeFirstTwo(items) {
  return items.slice(0, 2);
}
```

## gap-javascript-array-copy-06 — train

Group `javascript-array-copy`; origin `p2-02-request-following-v2`.

Write takeLastTwo(items) for an array items; preserve the original array; return a copy of at most the last two elements. Return one JavaScript function.

```javascript
function takeLastTwo(items) {
  return items.slice(-2);
}
```

## gap-javascript-string-slice-01 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write firstCodeUnits(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the first count code units. Return one JavaScript function.

```javascript
function firstCodeUnits(text, count) {
  return text.slice(0, count);
}
```

## gap-javascript-string-slice-02 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write skipCodeUnits(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the first count code units. Return one JavaScript function.

```javascript
function skipCodeUnits(text, count) {
  return text.slice(count);
}
```

## gap-javascript-string-slice-03 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write lastCodeUnits(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return at most the last count code units, or empty if count is zero. Return one JavaScript function.

```javascript
function lastCodeUnits(text, count) {
  return count === 0 ? '' : text.slice(-count);
}
```

## gap-javascript-string-slice-04 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write dropLastCodeUnits(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; remove at most the last count code units, returning text unchanged for zero. Return one JavaScript function.

```javascript
function dropLastCodeUnits(text, count) {
  return count === 0 ? text : text.slice(0, -count);
}
```

## gap-javascript-string-slice-05 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write longerThanCount(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has more than count code units. Return one JavaScript function.

```javascript
function longerThanCount(text, count) {
  return text.length > count;
}
```

## gap-javascript-string-slice-06 — train

Group `javascript-string-slice`; origin `p2-02-request-following-v2`.

Write exactCodeUnitCount(text, count) for a string text and a nonnegative integer count; count UTF-16 code units; return whether text has exactly count code units. Return one JavaScript function.

```javascript
function exactCodeUnitCount(text, count) {
  return text.length === count;
}
```

## gap-javascript-string-build-01 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write bracketText(text) for a string text; surround text with square brackets. Return one JavaScript function.

```javascript
function bracketText(text) {
  return '[' + text + ']';
}
```

## gap-javascript-string-build-02 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write trimOuterSpace(text) for a string text; return text with outer whitespace removed. Return one JavaScript function.

```javascript
function trimOuterSpace(text) {
  return text.trim();
}
```

## gap-javascript-string-build-03 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write upperText(text) for a string text; return text in uppercase. Return one JavaScript function.

```javascript
function upperText(text) {
  return text.toUpperCase();
}
```

## gap-javascript-string-build-04 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write lowerText(text) for a string text; return text in lowercase. Return one JavaScript function.

```javascript
function lowerText(text) {
  return text.toLowerCase();
}
```

## gap-javascript-string-build-05 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write duplicateText(text) for a string text; return an array containing text twice. Return one JavaScript function.

```javascript
function duplicateText(text) {
  return [text, text];
}
```

## gap-javascript-string-build-06 — validation

Group `javascript-string-build`; origin `p2-02-request-following-v2`.

Write labelText(text) for a string text; return an object whose label property contains text. Return one JavaScript function.

```javascript
function labelText(text) {
  return { label: text };
}
```

## gap-javascript-object-lookup-01 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write readProperty(record, key) for a plain object record and a string key; return results without mutation; return the property value. Return one JavaScript function.

```javascript
function readProperty(record, key) {
  return record[key];
}
```

## gap-javascript-object-lookup-02 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write hasOwnProperty(record, key) for a plain object record and a string key; return results without mutation; report whether record has an own property named key. Return one JavaScript function.

```javascript
function hasOwnProperty(record, key) {
  return Object.prototype.hasOwnProperty.call(record, key);
}
```

## gap-javascript-object-lookup-03 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write listObjectKeys(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable string keys; key is unused. Return one JavaScript function.

```javascript
function listObjectKeys(record, key) {
  return Object.keys(record);
}
```

## gap-javascript-object-lookup-04 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write listObjectValues(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable values; key is unused. Return one JavaScript function.

```javascript
function listObjectValues(record, key) {
  return Object.values(record);
}
```

## gap-javascript-object-lookup-05 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write listObjectEntries(record, key) for a plain object record and a string key; return results without mutation; return all own enumerable key-value pairs; key is unused. Return one JavaScript function.

```javascript
function listObjectEntries(record, key) {
  return Object.entries(record);
}
```

## gap-javascript-object-lookup-06 — validation

Group `javascript-object-lookup`; origin `p2-02-request-following-v2`.

Write isPropertyUndefined(record, key) for a plain object record and a string key; return results without mutation; report whether the property value is undefined. Return one JavaScript function.

```javascript
function isPropertyUndefined(record, key) {
  return record[key] === undefined;
}
```

## gap-javascript-arrays-01 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write keepEven(items) for an array of integers; return a new array of even values. Return code only.

```javascript
function keepEven(items) {
  return items.filter(item => item % 2 === 0);
}
```

## gap-javascript-arrays-02 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write doubleValues(items) for an array of numbers; return a new array with each number doubled. Return code only.

```javascript
function doubleValues(items) {
  return items.map(item => item * 2);
}
```

## gap-javascript-arrays-03 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write firstLong(items) for an array of strings; return the first string longer than five characters. Return code only.

```javascript
function firstLong(items) {
  return items.find(item => item.length > 5);
}
```

## gap-javascript-arrays-04 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write allPositive(items) for an array of numbers; report whether every number exceeds zero. Return code only.

```javascript
function allPositive(items) {
  return items.every(item => item > 0);
}
```

## gap-javascript-arrays-05 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write joinNames(items) for an array of strings; join them with a comma and one space. Return code only.

```javascript
function joinNames(items) {
  return items.join(', ');
}
```

## gap-javascript-arrays-06 — train

Group `javascript-arrays`; origin `p2-development-failure-audit`.

Write countEmpty(items) for an array of strings; count the empty strings. Return code only.

```javascript
function countEmpty(items) {
  return items.filter(item => item === '').length;
}
```

## gap-javascript-strings-01 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write startsWithHash(text) for a string; report whether its first character is #. Return code only.

```javascript
function startsWithHash(text) {
  return text.startsWith('#');
}
```

## gap-javascript-strings-02 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write removeOuterSpace(text) for a string; remove whitespace at both ends. Return code only.

```javascript
function removeOuterSpace(text) {
  return text.trim();
}
```

## gap-javascript-strings-03 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write dashSpaces(text) for a string; replace every ordinary space with a dash. Return code only.

```javascript
function dashSpaces(text) {
  return text.replaceAll(' ', '-');
}
```

## gap-javascript-strings-04 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write lastCharacter(text) for a string; return its last UTF-16 code unit or empty string. Return code only.

```javascript
function lastCharacter(text) {
  return text.slice(-1);
}
```

## gap-javascript-strings-05 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write isBlank(text) for a string; report whether trimming leaves an empty string. Return code only.

```javascript
function isBlank(text) {
  return text.trim().length === 0;
}
```

## gap-javascript-strings-06 — validation

Group `javascript-strings`; origin `p2-development-failure-audit`.

Write lineParts(text) for a string; return an array split at newline characters. Return code only.

```javascript
function lineParts(text) {
  return text.split('\n');
}
```

## gap-javascript-objects-01 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write hasTitle(item) for an object; report whether it owns a title property. Return code only.

```javascript
function hasTitle(item) {
  return Object.hasOwn(item, 'title');
}
```

## gap-javascript-objects-02 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write displayLabel(item) for an object with a label property; return that label in square brackets. Return code only.

```javascript
function displayLabel(item) {
  return '[' + item.label + ']';
}
```

## gap-javascript-objects-03 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write objectFieldCount(item) for an object; return its number of own enumerable string keys. Return code only.

```javascript
function objectFieldCount(item) {
  return Object.keys(item).length;
}
```

## gap-javascript-objects-04 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write withActive(item) for an object; return a shallow copy with active set to true. Return code only.

```javascript
function withActive(item) {
  return { ...item, active: true };
}
```

## gap-javascript-objects-05 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write getHeading(item) for an object; return its heading property or the empty string if nullish. Return code only.

```javascript
function getHeading(item) {
  return item.heading ?? '';
}
```

## gap-javascript-objects-06 — train

Group `javascript-objects`; origin `p2-development-failure-audit`.

Write propertyNames(item) for an object; return its own enumerable string keys sorted alphabetically. Return code only.

```javascript
function propertyNames(item) {
  return Object.keys(item).sort();
}
```
