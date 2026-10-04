# P2-02 request-to-code candidate: review before the next experiment

The owner has approved these exact 36 original Codex-authored request/answer pairs for local training, 12 each for HTML, CSS, and JavaScript. No external source text was added. The [build and baseline report](PHASE-2-CODE-PAIR-BUILD-REPORT.md) records the completed separate corpus, training-fitted tokenizer, random initialization, baseline score, and completed ten-minute commands. The [matched diagnostic](PHASE-2-CODE-PAIR-10M-REPORT.md) scored 0/30 tasks with no truncations and worsening held-out loss. [The complete example guide](../training/phase2/drafts/p2-02-code-pairs-v2/REVIEW.md) remains the original review snapshot; its pending status is historical, and approval is recorded separately.

The v3 trained checkpoint scored 0/30 development tasks and produced Markdown/Mermaid tutorial text in its first HTML responses. Its data was 76.3% Markdown by **file-format token count**, which includes code fences as well as prose; the six authored request/solution examples contributed just 0.7%. That motivates a format-alignment experiment, but does not establish that the mix alone caused the failed score. The [v3 training report](PHASE-2-TRAINING-CHECK-V3-REPORT.md) and [mix review](PHASE-2-DATA-MIX-REVIEW.md) retain the results.

## What this candidate changes

Each record is a plain `.txt` document containing the same `plex-coding-task-v1` prompt used at inference, a newline, and the correct code answer. Answers have no Markdown fences, headings, Mermaid diagrams, or explanations. The existing tokenizer appends EOS id 3 after each record. The inference prompt ends immediately before the newline, so the model learns to produce that newline and then code.

This is a separate, deliberately tiny diagnostic corpus. It is not appended to the tutorial data and is not proposed as enough data for useful general coding. The existing causal training objective covers the prompt and answer together; reply-only loss masking, model changes, new decoding caps, and longer training are outside this candidate.

| Language | Semantic groups | Training examples | Validation examples |
|---|---:|---:|---:|
| HTML | 6 | 8 | 4 |
| CSS | 6 | 8 | 4 |
| JavaScript | 6 | 8 | 4 |
| **Total** | **18** | **24** | **12** |

Each group has two related variants, both assigned to the same split. The existing family-stratified algorithm uses seed 51 and 30% validation groups (rounded to two of six groups per language). This holds out semantic groups rather than moving a numeric or wording variation into validation. HTML topics include abbreviation markup, contact addresses, definition lists, meter/progress elements, and quotations; CSS topics include accents, columns, truncation, logical spacing, list markers, and numeric text; JavaScript topics include array search, calendar arithmetic, parity, rectangle measurements, bounded repetition, and temperature conversion.

## What was checked

- All 36 supplied solutions passed 194/194 static checks: HTML structure/required text and attributes, flat CSS rule parsing/declarations, and JavaScript syntax with Node `--check` plus required function/operation checks. **No JavaScript behavior was executed.** Behavior cases in the guide are expectations for human review, not measured results.
- Nine candidate tests pass, including wrong CSS values, duplicated evaluation requests, cross-split variant moves, draft approval claims, refusal of a final holdout, exact preview parity, deterministic materialization, no overwrite, and rejection of the pending catalog by the production dataset builder.
- All 11 existing dataset tests and 16 existing static benchmark tests pass. This is 36 targeted tests; the full training/model suite was not rerun because core model/training code was not changed.
- No normalized request duplicates were found against the 30 development prompts or the previous nine examples. A word-overlap screen against development requests peaked at 0.260870. This heuristic does not prove absence of semantic overlap; language skills can overlap. No final evaluation set was opened or used.
- Serialized sources reproduce byte-for-byte. The candidate JSONL SHA-256 is `88c35a023b0093cb177552c4ddc45533e92d63e0d006f26dbcdad2bd0a2ef72a`. The review and pending catalog carry this digest.
- As a reference-only check, the existing v3 tokenizer preserved every inference prefix as an exact token prefix of its complete training record. The largest prompt was 108 tokens; the largest complete record, including EOS, was 173. Maximum answer lengths including EOS were 58 HTML, 36 CSS, and 75 JavaScript tokens, below the fixed 192/128/192 decode caps. These measurements must be repeated with the candidate's own training-fitted tokenizer after approval.

The code answers occupy 2,365 of 10,523 training text bytes and 1,511 of 5,820 validation text bytes. The rest is the repeated prompt and request text. These byte measures are not code-token percentages or proof that the broader 70–80% code base-corpus goal is met.

## Files and reproducible review

The canonical records are [candidate JSONL](../training/phase2/drafts/p2-02-code-pairs-v2.jsonl). The [preparation script](../training/phase2/prepare_code_pair_candidate.py) creates the [full guide](../training/phase2/drafts/p2-02-code-pairs-v2/REVIEW.md), grouped source texts, [static review record](../training/phase2/drafts/p2-02-code-pairs-v2/review.json), and [pending source catalog](../training/phase2/drafts/p2-02-code-pairs-v2/dataset-sources.candidate.json). The separate [reference-tokenizer record](../training/phase2/drafts/p2-02-code-pairs-v2/reference-tokenizer-review.json) records the v3-only budget check.

From the repository root, this installed-environment command repeats validation only:

```powershell
uv run --project training --no-sync python training\phase2\prepare_code_pair_candidate.py
```

To reproduce the preview into a fresh directory:

```powershell
uv run --project training --no-sync python training\phase2\prepare_code_pair_candidate.py `
  --prepare-dir training\phase2\drafts\p2-02-code-pairs-v2-review-copy
```

No command above trains a model or marks sources approved. The proposed catalog deliberately has `rightsReviewStatus: pending-owner-review`, which the dataset builder rejects. Missing Node prevents full static review and is reported as an error; nothing is installed automatically.

## Original proposal and accepted decision

The owner accepted the following local-use proposal. Promotion, corpus construction, fresh tokenizer checks, random initialization, and matching step-zero scoring are complete. The ten-minute training diagnostic and matched scoring have also completed; see the diagnostic report above. Use the current [build report](PHASE-2-CODE-PAIR-BUILD-REPORT.md) for actual new-tokenizer measurements and commands. The proposal below preserves the reviewed scope.

Review the requests, answers, and group split in the full guide. Approving these exact 36 examples authorizes their inclusion in a **separate local P2 diagnostic corpus**. This review step comes from our agreed plan to show the new examples before using them. It does not authorize a public dataset license, a new external download, paid resources, or a two-hour training run.

After acceptance, record approval for this digest and promote the accepted sources into a new approved catalog. Build a fresh corpus, fit a new tokenizer on its training split only, verify token/context/EOS budgets, and initialize Plex from random weights with seed 1337. Keep the model and training settings fixed for the proposed ten-minute check. First score its matching step-zero checkpoint on the unchanged 30 development tasks; then run the bounded check and score again. Record complete-task passes, syntax/format success, truncation/EOS, validation loss, and resources independently. The small set can overfit; improved format is useful diagnostic evidence, not a general coding claim. Preserve the final holdout, v3 artifacts, $0 paid-services limit, and 200 GiB storage allocation. A two-hour run is a later decision supported by those measurements.
