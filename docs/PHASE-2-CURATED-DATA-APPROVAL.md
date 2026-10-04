# P2-02: approve the curated request-following candidate

**Completed:** the owner approved these exact 180 examples. The separate corpus, training-only tokenizer, random initialization, 100-step run, and matched development scoring are recorded in the [result report](PHASE-2-CURATED-100-STEP-REPORT.md). It passed 0/30 complete tasks despite lower held-out loss. The approval instructions below are historical; no second approval or run is needed.

The diversity and supplied-answer review is complete. The candidate is ready for **exact-record approval for a small local experiment**, not yet included in training. Your prior approval remains attached to the twelve original samples; this separate version contains 180 revised examples.

## What you would approve

Approve [these exact 180 requests and code answers](../training/phase2/drafts/p2-02-request-following-v2/REVIEW.md) for local Plex training and held-out validation. No external text was added. These are original Codex-authored examples; no public license grant is asserted. The [canonical JSONL](../training/phase2/drafts/p2-02-request-following-v2/candidate.jsonl) and [review record](../training/phase2/drafts/p2-02-request-following-v2/review.json) identify the version by SHA-256:

`9f6ad8eff96298f45880f9bfe831648364e2a7ed11996e7a7d91d5e984eb3d0b`

| Language | Training examples | Validation examples |
|---|---:|---:|
| HTML | 42 | 18 |
| CSS | 42 | 18 |
| JavaScript | 36 | 24 |
| **Total** | **120** | **60** |

There are 30 topic families, six profiles per topic, and 29 indivisible split groups. Shared arithmetic/bound template relatives still form one combined group. The existing seed-51, 30%-of-groups split was recalculated with the new source-family identities. Counts differ by language because groups have different sizes; no sibling was moved to force a numeric balance.

## What changed from the 360-record draft

- Removed all 180 rename/text-only second variants. The older draft remains unchanged for comparison.
- Replaced value-only CSS profiles with six distinct property-name combinations per topic, tied to explicit requested effects. Requests now describe the desired result rather than simply list the output declarations.
- Replaced repeated string delimiters and unit-conversion factors with different operations and output shapes, including scalars, arrays, objects, and rounding. Replaced duplicated bound bodies with explicitly requested conditional expressions; all related topics remain grouped.
- Removed unused word/reading/sentence inputs from HTML prompts. Replaced the `rb` ruby-base example with a paragraph containing a ruby annotation.
- Removed HTML checks that only matched the entire answer verbatim. Added exact reviewed tree expectations to check parent/child order, text, and attributes; added exact CSS-rule expectations to reject extra as well as missing declarations.

For example, instead of two copies of `aspect-ratio: 1 / 1` with renamed selectors, this candidate includes a square preferred ratio, a widescreen preferred ratio with fixed width, a ratio constrained by maximum width, a ratio with fixed height, border-box sizing, and minimum width. The conditions now require different declaration combinations.

For JavaScript, a request to convert completed whole minutes rounds down, while a request to convert milliseconds into seconds rounded up uses a different rounding operation. Another request returns a named object of units, and another returns an array. The full guide shows every exact request, answer, and expected example result.

The HTML review used the current standard's [ruby content model](https://html.spec.whatwg.org/multipage/text-level-semantics.html#the-ruby-element) and [heading-group content model](https://html.spec.whatwg.org/multipage/sections.html#the-hgroup-element) as authoring references. No specification passages were copied into training text.

## Verification and limits

All **180 supplied answers passed 878 static/structural checks**. Node `--check` parsed JavaScript without executing it. Five focused tests passed, demonstrating rejection of wrong HTML nesting even when required tags exist, unrequested CSS declarations, value-only structural duplicates, cross-split group moves, and attempts to build the pending catalog. All serialized source texts reproduce the current canonical records byte-for-byte.

A conservative duplicate screen finds 180 distinct structures: HTML compares tag trees, text-node presence, and attribute names while ignoring text/value contents; CSS compares property-name sets; JavaScript normalizes function/parameter names and literal values while retaining operations and call structure. Each topic has six distinct profiles under this rule. This measure is not proof of 180 independent semantic skills. Wrappers and related language constructs remain related, so entire topic/template groups stay together.

No exact normalized requests duplicate the unchanged development prompts or earlier approved authored sets. Exact request/solution duplicates within the candidate are rejected. The final holdout remains unopened. Supplied JavaScript results were inspected but not executed; static checks do not establish JavaScript behavior or browser rendering. Expected HTML trees and CSS declarations are authored review expectations, not independent browser conformance tests.

The planned source texts total 51,074 training bytes and 24,924 validation bytes, excluding notices and metadata. Code answers occupy 7,604 and 3,358 of those bytes respectively. These are **byte measurements**, not tokenizer-fitted code proportions; this small task-format corpus does not meet or replace the larger code-heavy scratch-pretraining goal.

The [reference tokenizer check](../training/phase2/drafts/p2-02-request-following-v2/reference-tokenizer-review.json) used the existing 874-entry tokenizer only. All prefixes matched, all records fit 512 tokens, and maximum answers including EOS were 60 HTML, 63 CSS, and 68 JavaScript tokens under the fixed 192/128/192 caps. The largest complete record was 207 tokens. A fresh training-only tokenizer must still be fitted after approval, with these checks repeated on its actual IDs.

## Easiest next steps

1. Review this summary and any examples in the full guide. To approve this exact version, say **“Approve the 180 curated examples for local training.”**
2. After approval, build its separate corpus, fit its tokenizer on training only, repeat identity/context/EOS checks, initialize fresh random weights, and score the unchanged development tasks at step zero.
3. Run a **100-step diagnostic with a ten-minute ceiling**, then score the saved checkpoint against that matching baseline. Keep the architecture, optimizer, prompt format, and decoding limits fixed initially.

No command needs to run now. The pending catalog deliberately prevents accidental training. Nothing was downloaded or installed, no new checkpoint was created, no paid services were used, and no training was performed. The $0 budget and 200 GiB allocation remain in force. A two-hour run stays deferred until smaller experiments show useful task performance.
