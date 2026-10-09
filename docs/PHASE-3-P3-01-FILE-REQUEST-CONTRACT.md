# P3-01 — File + Request Contract

## Status

**Complete.** The deterministic contract review and frozen-tokenizer context preflight passed. This establishes the task representation and fixture review shape; it does not establish Plex file-editing capability. Phase 3 remains active.

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

The deterministic candidate is `training/phase3/drafts/p3-01-file-edit-contract-v1.jsonl`: 18 contract fixtures, with 6 HTML, 6 CSS, and 6 JavaScript. It is a contract-validation set, not a representative training corpus. Its SHA-256 is `3b3ba80a7845888982967eb879053ea0d4c0dbe22adbd2e59ba00c28992d7b6c`; it is 4,257 bytes. JSONL metadata is not the model output format.

Text is UTF-8 without BOM, serialized with LF, and preserves meaningful whitespace. Expected output must differ by one contiguous replacement; surrounding input text remains byte-for-byte the same. Exact expected text measures edit correctness and provides a conservative preservation baseline.

## Scoring contract

- **Exact correctness:** compare output with expected file after CRLF/CR-to-LF normalization; preserve all other whitespace.
- **Preservation:** compare text outside the expected replacement span; record any difference.
- **Unnecessary edits:** record output changes outside the expected replacement. Exact match implies none.
- **Syntax/checkability:** retain a per-language syntax status when a later evaluator has a cheap checker. The expected targets are authored as valid examples; P3-01 adds no parser dependency.

## Tokenizer and context

The frozen tokenizer SHA is `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`. The source P2-48 tokenizer-bundle manifest SHA is `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`. The locally available P2-48 derived bundle manifest SHA is `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`.

The read-only tokenizer preflight passed using the P2-48 frozen tokenizer (`2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`). The P2-48 derived bundle manifest SHA is `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`, from source tokenizer bundle manifest `46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6`. All 18 prompts and targets roundtripped exactly. Record tokens including EOS ranged from **46 to 77** (mean **61.222**, median **59**); all fit the 512-token context.

## Authorization and evidence boundary

P3-01 preparation and contract review are authorized. Checkpoint staging, optimizer creation, model training, and automatic continuation are false; training performed is false; research optimizer updates are zero; final holdout remains closed. No checkpoint was staged or changed. This contract does not prove Plex can edit files. It defines a task representation and candidate evaluation shape; editing ability remains unproven.

## Next milestone

The next milestone is **P3-02 — Exact Small Replacements**. This documentation update does not start its work or authorize training.
