# P2-15 CSS request-to-code candidate v1

**Status: ready for owner review; not approved for training.**

## What this candidate teaches

Each prompt supplies one CSS rule and asks for one bounded edit. The target is the complete updated rule, including declarations that should stay unchanged. The candidate contains 36 original examples in 12 semantic groups: 24 training records (8 groups) and 12 validation records (4 different groups). Related variants are kept together so no edit family crosses the split.

## Why this follows P2-14

P2-14 showed that the existing step-200 model could copy selector strings but did not produce complete CSS edits. This candidate directly teaches that input-rule → instruction → complete-rule format. It is a small diagnostic candidate, not a broad CSS curriculum. Its exact prompts do not overlap P2-14; the split withholds four entire edit families. The P2-14 task set is development-only and already disclosed. The owner-controlled final set remains unopened.

## Example training record

```text
Write a small CSS coding solution.
Request: Starting CSS:
.primary-button { border-radius: 2px; padding: 0.5rem 1rem; }

Replace the corner radius with 6px and keep the padding. Return the complete updated CSS rule with no unrelated changes.
Output contract: Return CSS rules only. Do not include HTML, Markdown fences, or explanations.
Return code only. Do not include Markdown fences or explanations.
.primary-button { border-radius: 6px; padding: 0.5rem 1rem; }
```

## Split

**Training families:** button radius, callout border color, navigation alignment, card shadow, label font style, thumbnail width, badge text transformation, and menu-item opacity (24 records).


**Validation-only families:** list marker, whitespace handling, aspect ratio, and outline (12 records). These records are not trained on; the tokenizer must be fitted only on the training partition after approval.

## Candidate checks and limits

All 36 authored outputs passed the static exact-rule checker (108/108 checks). This validates the examples, not model capability or browser rendering. No exact request duplicates were found against P2-01b or P2-14. Maximum word-level Jaccard overlap was 0.205882 with P2-01b and 0.485714 with P2-14; these are only lexical screens. No external material was copied.

No corpus was built, tokenizer fitted, checkpoint initialized, training run started, or final set opened. Review/approve these exact candidate hashes before any training. After approval, build a separate corpus, fit a fresh tokenizer on training records only, measure token budgets, create a new seed-1337 step-zero checkpoint, then run at most 100 updates or 10 minutes and compare against step zero. This ceiling is a proposal, not run authorization.

## Hashes

- Candidate JSONL: `e9ca83c92a40abd0575db708bd67d2e4ce6888d97bc31ef4a38938a050dfd6cf`
- Training rows: `db29a222896c732fc0b7b43452d6100c281065a99ee22c911f184e458554d19c`
- Validation rows: `d49333860bb73d1e941588e070d9cda24bc4d17f75fd9c7546b1d7bbdc2e5cd8`
- P2-14 development set: `0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e`
- Final holdout opened: **no**

## All examples

### Train

#### p2-15-css-01 — css-button-radius

Request: Starting CSS:
.primary-button { border-radius: 2px; padding: 0.5rem 1rem; }

Replace the corner radius with 6px and keep the padding. Return the complete updated CSS rule with no unrelated changes.

```css
.primary-button { border-radius: 6px; padding: 0.5rem 1rem; }
```

#### p2-15-css-02 — css-button-radius

Request: Starting CSS:
.submit-button { border-radius: 4px; background-color: #1d4ed8; }

Set the corner radius to 0.75rem; preserve the background color. Return the complete updated CSS rule with no unrelated changes.

```css
.submit-button { border-radius: 0.75rem; background-color: #1d4ed8; }
```

#### p2-15-css-03 — css-button-radius

Request: Starting CSS:
.quiet-button { border-radius: 999px; color: #334155; }

Change the radius to 0.25rem and leave the text color as given. Return the complete updated CSS rule with no unrelated changes.

```css
.quiet-button { border-radius: 0.25rem; color: #334155; }
```

#### p2-15-css-04 — css-callout-border

Request: Starting CSS:
.warning-callout { border: 1px solid #94a3b8; padding: 1rem; }

Keep the border width and style, but change its color to #b91c1c. Preserve the padding. Return the complete updated CSS rule with no unrelated changes.

```css
.warning-callout { border: 1px solid #b91c1c; padding: 1rem; }
```

#### p2-15-css-05 — css-callout-border

Request: Starting CSS:
.info-callout { border: 2px dashed #64748b; margin-block: 1rem; }

Change only the border color to #0369a1; keep its width, style, and margin. Return the complete updated CSS rule with no unrelated changes.

```css
.info-callout { border: 2px dashed #0369a1; margin-block: 1rem; }
```

#### p2-15-css-06 — css-callout-border

Request: Starting CSS:
.success-callout { border: 3px solid #475569; background: #f8fafc; }

Use #15803d for the border color and preserve the other declarations. Return the complete updated CSS rule with no unrelated changes.

```css
.success-callout { border: 3px solid #15803d; background: #f8fafc; }
```

#### p2-15-css-07 — css-nav-justify

Request: Starting CSS:
.main-navigation { display: flex; justify-content: flex-start; gap: 1rem; }

Align the flex items at the inline end. Keep the gap and display mode. Return the complete updated CSS rule with no unrelated changes.

```css
.main-navigation { display: flex; justify-content: flex-end; gap: 1rem; }
```

#### p2-15-css-08 — css-nav-justify

Request: Starting CSS:
.toolbar-links { display: flex; justify-content: center; align-items: center; }

Distribute the items with space-between; preserve the other declarations. Return the complete updated CSS rule with no unrelated changes.

```css
.toolbar-links { display: flex; justify-content: space-between; align-items: center; }
```

#### p2-15-css-09 — css-nav-justify

Request: Starting CSS:
.footer-navigation { display: flex; justify-content: space-around; flex-wrap: wrap; }

Set the main-axis alignment to space-evenly and keep wrapping enabled. Return the complete updated CSS rule with no unrelated changes.

```css
.footer-navigation { display: flex; justify-content: space-evenly; flex-wrap: wrap; }
```

#### p2-15-css-10 — css-card-shadow

Request: Starting CSS:
.catalog-card { box-shadow: 0 1px 2px #0002; border-radius: 0.5rem; }

Replace the shadow with 0 4px 12px #0003 and keep the radius. Return the complete updated CSS rule with no unrelated changes.

```css
.catalog-card { box-shadow: 0 4px 12px #0003; border-radius: 0.5rem; }
```

#### p2-15-css-11 — css-card-shadow

Request: Starting CSS:
.profile-card { box-shadow: none; padding: 1.25rem; }

Add a shadow of 0 2px 8px #1e293b33; preserve the padding. Return the complete updated CSS rule with no unrelated changes.

```css
.profile-card { box-shadow: 0 2px 8px #1e293b33; padding: 1.25rem; }
```

#### p2-15-css-12 — css-card-shadow

Request: Starting CSS:
.summary-card { box-shadow: 0 6px 18px #0004; border: 1px solid #cbd5e1; }

Remove the shadow while leaving the border declaration unchanged. Return the complete updated CSS rule with no unrelated changes.

```css
.summary-card { box-shadow: none; border: 1px solid #cbd5e1; }
```

#### p2-15-css-13 — css-label-font-style

Request: Starting CSS:
.field-label { font-style: normal; font-weight: 600; }

Make the label italic and retain its font weight. Return the complete updated CSS rule with no unrelated changes.

```css
.field-label { font-style: italic; font-weight: 600; }
```

#### p2-15-css-14 — css-label-font-style

Request: Starting CSS:
.editorial-note { font-style: italic; color: #475569; }

Return the text to normal style; keep its color. Return the complete updated CSS rule with no unrelated changes.

```css
.editorial-note { font-style: normal; color: #475569; }
```

#### p2-15-css-15 — css-label-font-style

Request: Starting CSS:
.image-caption { font-style: oblique; font-size: 0.875rem; }

Change the font style to italic and preserve the font size. Return the complete updated CSS rule with no unrelated changes.

```css
.image-caption { font-style: italic; font-size: 0.875rem; }
```

#### p2-15-css-16 — css-thumbnail-width

Request: Starting CSS:
.gallery-thumbnail { width: 12rem; height: auto; }

Add max-width: 100% so the thumbnail cannot exceed its container; keep both existing declarations. Return the complete updated CSS rule with no unrelated changes.

```css
.gallery-thumbnail { width: 12rem; height: auto; max-width: 100%; }
```

#### p2-15-css-17 — css-thumbnail-width

Request: Starting CSS:
.avatar-preview { width: 5rem; object-fit: cover; }

Add a 100% maximum width and preserve the width and object-fit settings. Return the complete updated CSS rule with no unrelated changes.

```css
.avatar-preview { width: 5rem; object-fit: cover; max-width: 100%; }
```

#### p2-15-css-18 — css-thumbnail-width

Request: Starting CSS:
.article-image { width: 100%; display: block; }

Add max-width: 42rem; keep the current width and display mode. Return the complete updated CSS rule with no unrelated changes.

```css
.article-image { width: 100%; display: block; max-width: 42rem; }
```

#### p2-15-css-19 — css-badge-transform

Request: Starting CSS:
.status-badge { text-transform: none; letter-spacing: 0.02em; }

Display the badge text in uppercase and keep its letter spacing. Return the complete updated CSS rule with no unrelated changes.

```css
.status-badge { text-transform: uppercase; letter-spacing: 0.02em; }
```

#### p2-15-css-20 — css-badge-transform

Request: Starting CSS:
.category-tag { text-transform: uppercase; padding: 0.25rem; }

Use lowercase text instead; preserve the padding. Return the complete updated CSS rule with no unrelated changes.

```css
.category-tag { text-transform: lowercase; padding: 0.25rem; }
```

#### p2-15-css-21 — css-badge-transform

Request: Starting CSS:
.section-kicker { text-transform: capitalize; color: #64748b; }

Change the text transformation to uppercase and retain its color. Return the complete updated CSS rule with no unrelated changes.

```css
.section-kicker { text-transform: uppercase; color: #64748b; }
```

#### p2-15-css-22 — css-menu-opacity

Request: Starting CSS:
.disabled-menu-item { opacity: 1; pointer-events: auto; }

Set opacity to 0.45 and keep pointer events enabled. Return the complete updated CSS rule with no unrelated changes.

```css
.disabled-menu-item { opacity: 0.45; pointer-events: auto; }
```

#### p2-15-css-23 — css-menu-opacity

Request: Starting CSS:
.loading-menu-item { opacity: 0.8; cursor: progress; }

Make this item fully opaque; leave the progress cursor in place. Return the complete updated CSS rule with no unrelated changes.

```css
.loading-menu-item { opacity: 1; cursor: progress; }
```

#### p2-15-css-24 — css-menu-opacity

Request: Starting CSS:
.inactive-menu-item { opacity: 0.5; pointer-events: none; }

Restore opacity to 1 while keeping pointer events disabled. Return the complete updated CSS rule with no unrelated changes.

```css
.inactive-menu-item { opacity: 1; pointer-events: none; }
```

### Validation

#### p2-15-css-25 — css-list-style

Request: Starting CSS:
.resource-list { list-style-type: disc; padding-inline-start: 1.25rem; }

Use square markers and retain the current indentation. Return the complete updated CSS rule with no unrelated changes.

```css
.resource-list { list-style-type: square; padding-inline-start: 1.25rem; }
```

#### p2-15-css-26 — css-list-style

Request: Starting CSS:
.steps-list { list-style-type: decimal; margin-block: 0; }

Change the markers to lower-alpha and keep the block margins reset. Return the complete updated CSS rule with no unrelated changes.

```css
.steps-list { list-style-type: lower-alpha; margin-block: 0; }
```

#### p2-15-css-27 — css-list-style

Request: Starting CSS:
.feature-list { list-style-type: circle; color: #334155; }

Remove the list markers but keep the text color. Return the complete updated CSS rule with no unrelated changes.

```css
.feature-list { list-style-type: none; color: #334155; }
```

#### p2-15-css-28 — css-white-space

Request: Starting CSS:
.terminal-output { white-space: normal; overflow-x: auto; }

Preserve whitespace and line breaks without wrapping lines; keep horizontal scrolling. Return the complete updated CSS rule with no unrelated changes.

```css
.terminal-output { white-space: pre; overflow-x: auto; }
```

#### p2-15-css-29 — css-white-space

Request: Starting CSS:
.inline-code-sample { white-space: pre; background: #f1f5f9; }

Allow normal wrapping and preserve the background. Return the complete updated CSS rule with no unrelated changes.

```css
.inline-code-sample { white-space: normal; background: #f1f5f9; }
```

#### p2-15-css-30 — css-white-space

Request: Starting CSS:
.message-preview { white-space: pre-wrap; color: #1e293b; }

Collapse whitespace normally and retain the text color. Return the complete updated CSS rule with no unrelated changes.

```css
.message-preview { white-space: normal; color: #1e293b; }
```

#### p2-15-css-31 — css-aspect-ratio

Request: Starting CSS:
.video-frame { aspect-ratio: 4 / 3; width: 100%; }

Change the preferred ratio to 16 / 9 and keep full width. Return the complete updated CSS rule with no unrelated changes.

```css
.video-frame { aspect-ratio: 16 / 9; width: 100%; }
```

#### p2-15-css-32 — css-aspect-ratio

Request: Starting CSS:
.square-preview { aspect-ratio: 16 / 9; max-width: 20rem; }

Make the preferred ratio square and preserve the maximum width. Return the complete updated CSS rule with no unrelated changes.

```css
.square-preview { aspect-ratio: 1 / 1; max-width: 20rem; }
```

#### p2-15-css-33 — css-aspect-ratio

Request: Starting CSS:
.portrait-frame { aspect-ratio: 1 / 1; width: 9rem; }

Set the ratio to 3 / 4 and leave the width unchanged. Return the complete updated CSS rule with no unrelated changes.

```css
.portrait-frame { aspect-ratio: 3 / 4; width: 9rem; }
```

#### p2-15-css-34 — css-outline

Request: Starting CSS:
.keyboard-control { outline: 2px solid #2563eb; outline-offset: 0; }

Move the outline 3px away from the control; preserve its style and color. Return the complete updated CSS rule with no unrelated changes.

```css
.keyboard-control { outline: 2px solid #2563eb; outline-offset: 3px; }
```

#### p2-15-css-35 — css-outline

Request: Starting CSS:
.search-field { outline: 1px dotted #475569; outline-offset: 2px; }

Set the outline offset to -1px; leave the outline itself unchanged. Return the complete updated CSS rule with no unrelated changes.

```css
.search-field { outline: 1px dotted #475569; outline-offset: -1px; }
```

#### p2-15-css-36 — css-outline

Request: Starting CSS:
.dialog-close { outline: none; color: #334155; }

Add a 2px solid #0f766e outline and retain the text color. Return the complete updated CSS rule with no unrelated changes.

```css
.dialog-close { outline: 2px solid #0f766e; color: #334155; }
```
