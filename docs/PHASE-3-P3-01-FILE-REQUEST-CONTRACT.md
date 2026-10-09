# P3-01 — File + Request Contract

## Status

**Implementation candidate prepared; tokenizer/context review blocked by inaccessible local tokenizer artifacts. P3-01 is not complete.** The fixture set and task representation are defined, but the required executed tokenizer preflight has not passed. Phase 3 remains active and P3-01 remains the current task.

## Why Phase 3 differs from Phase 2

Phase 2 studied whether Plex could map requests into abstract coding representations. The P2-49 bridge failed at 0/18 complete passes and 0/18 schema-valid results. Phase 3 tests the product task directly: a natural-language request and one file supplied by the caller produce the complete edited file.

## Model-facing contract

The frozen candidate prompt template is:

```text
Edit the supplied file to satisfy the request.
Language: {language}
Request: {request}
File:
{input_file}
Edited file:
```

The model target is only the complete edited file text, followed by EOS. It contains no filename, JSON wrapper, Markdown fence, explanation, patch, or reasoning. Raw file output is the user's requested result and avoids adding an intermediate plan representation.

HTML example:

```text
Edit the supplied file to satisfy the request.
Language: html
Request: Change the button text to Save Changes.
File:
<button>Submit</button>
Edited file:
```

Target: `<button>Save Changes</button>`

CSS example:

```text
Edit the supplied file to satisfy the request.
Language: css
Request: Change the gap to 16px.
File:
.card {
  display: grid;
  gap: 8px;
}
Edited file:
```

Target:

```css
.card {
  display: grid;
  gap: 16px;
}
```

JavaScript example:

```text
Edit the supplied file to satisfy the request.
Language: javascript
Request: Change the retry limit to 5.
File:
const retryLimit = 3;
Edited file:
```

Target: `const retryLimit = 5;`

## Candidate and preservation

The deterministic candidate is `training/phase3/drafts/p3-01-file-edit-contract-v1.jsonl`: 18 contract fixtures, with 6 HTML, 6 CSS, and 6 JavaScript. It is a contract-validation set, not a representative training corpus. Its SHA-256 is `0ca36cb544a89b62c8968c060f83d97e38754cb68e06c178c309daf71bb78f80`; it is 4,263 bytes. JSONL metadata is not the model output format.

Text is UTF-8 without BOM, serialized with LF, and preserves meaningful whitespace. Expected output must differ by one contiguous replacement; surrounding input text remains byte-for-byte the same. Exact expected text measures edit correctness and provides a conservative preservation baseline.

## Scoring contract

- **Exact correctness:** compare output with expected file after CRLF/CR-to-LF normalization; preserve all other whitespace.
- **Preservation:** compare text outside the expected replacement span; record any difference.
- **Unnecessary edits:** record output changes outside the expected replacement. Exact match implies none.
- **Syntax/checkability:** retain a per-language syntax status when a later evaluator has a cheap checker. The expected targets are authored as valid examples; P3-01 adds no parser dependency.

## Tokenizer and context

The frozen tokenizer SHA is `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`. The source P2-48 tokenizer-bundle manifest SHA is `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`. The locally available P2-48 derived bundle manifest SHA is `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`.

The tokenizer artifacts are inaccessible to the review process in this environment, so record-level token counts, roundtrip, maximum including EOS, and 512-token fit are **not verified**. Existing P2-48 reports confirm the frozen tokenizer was used for that earlier candidate, but do not establish P3-01 fixture sizes. P3-01 therefore remains incomplete.

## Authorization and evidence boundary

P3-01 preparation and contract review are authorized. Checkpoint staging, optimizer creation, model training, and automatic continuation are false; training performed is false; research optimizer updates are zero; final holdout remains closed. No checkpoint was staged or changed. This contract does not prove Plex can edit files. It defines a task representation and candidate evaluation shape; editing ability remains unproven.

## Next milestone

After P3-01 review passes and is closed, the next milestone is **P3-02 — Exact Small Replacements**. It has not been started.
