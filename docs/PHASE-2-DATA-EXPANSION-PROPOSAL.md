# P2-02 next data experiment: following the request

Plex now finishes its answers, but still answers the wrong task. The [completed ten-minute diagnostic](PHASE-2-CODE-PAIR-10M-REPORT.md) passed 0/30 tasks and worsened held-out loss. The next experiment should improve the examples before spending more time training.

**Current status: the owner approved the exact twelve samples. Curation of the larger draft is complete in a smaller 180-record candidate, ready for exact-record approval. No expanded corpus is built, tokenized, or trained.** The [curated approval guide](PHASE-2-CURATED-DATA-APPROVAL.md) records the changes, recalculated split, checks, and remaining approval step. The proposal below preserves the original 360-record target; curation removed rename-only duplicates rather than padding that count.

## Proposed scope

Prepare **360 original request/code examples**, 120 each for HTML, CSS, and JavaScript, without downloads or paid services. Organize them into ten independent task families per language and twelve examples per family. Keep every related example, operation contrast, naming variant, and structural template in its family's split group. The current deterministic seed-51, 30%-of-groups algorithm would select three of ten groups per language for validation: **252 training and 108 validation examples**, or 84/36 per language. These are proposed counts, not a measured build.

| Language | Proposed family coverage |
|---|---|
| HTML | Ruby pronunciation; disclosures; bidirectional isolation; quotations; abbreviations; descriptions; progress indicators; measurement indicators; contact markup; grouped headings |
| CSS | Logical borders; aspect ratios; outlines; cursor states; whitespace handling; text decoration; overflow behavior; table layout; multicolumn layout; replaced-element fitting |
| JavaScript | Binary arithmetic; one-sided bounds; integer division/remainder; unit conversion; number classification; array lookup; array copying; string slicing; string construction; object-property lookup |

Family names are planning categories, not immutable final assignments. During drafting, merge categories into one split group if their solutions share a structural template. Recompute and report the actual split if this changes the group count; never force the proposed counts by separating near-duplicates.

The twelve examples within a family must include more than renaming variables or changing numbers: request contrasts, output-structure changes, bounded edge cases, and distinct combinations of requirements. At least six distinct structural or operation patterns per family are a drafting target. Record the generator/template lineage explicitly and reject families that cannot satisfy this without padding. Some underlying skills overlap with existing development tasks; exact prompts and solutions must not be copied. The unchanged development set may guide error analysis, while the final holdout stays unopened.

This is a larger **instruction-format experiment**, not a sufficient scratch-pretraining dataset. The old training split had only 2,523 tokens, and the run processed about 10,380 times that size. More authored examples may help, but record count alone does not establish diversity or capability. Report distinct families, templates, code/prompt tokens, and duplication alongside total records. A substantially larger reviewed base corpus may still be necessary for useful coding.

## What the samples demonstrate

See the [twelve exact requests and answers](../training/phase2/drafts/p2-02-expansion-samples-v1.md) and [machine-readable sample record](../training/phase2/drafts/p2-02-expansion-samples-v1.json). They illustrate six families, four examples per language:

- HTML: the same word needs either ruby pronunciation markup or a plain span; the same disclosure needs either expanded or collapsed initial state.
- CSS: the same selector and border value need either the logical start or end property; the same selector needs either a square or wide aspect ratio.
- JavaScript: the same function signature needs multiplication or subtraction; another signature needs an upper or lower bound.

Each contrast pair stays in one split group. A repeated function name should not be enough for Plex to choose an answer: the request must control the operation. Samples illustrate the proposed style; they are not all 360 examples, a new benchmark, or evidence of model improvement.

The [sample review record](../training/phase2/drafts/p2-02-expansion-samples-v1-review.json) records 12/12 supplied solutions passing 57 static checks, including literal forbidden-string checks. No exact normalized request duplicates were found against the development prompts or earlier authored examples. JavaScript behavior was not executed; nesting and exact declaration-count review limits are stated beside the answers. The pending sample JSON digest is `f558326d52842512fb03e027395c999ad97fc613eeef648c4c102c4d4006b8c6`.

## Review and validation before inclusion

Keep the existing `plex-coding-task-v1` inference prompt, plain code-only answers, and EOS record boundary. All draft records must carry original-authorship provenance, stable IDs, family/template lineage, checks, and explicit pending approval. Keep review notes and expected behavior cases out of training text.

Check every supplied answer using the existing HTML/CSS static evaluator and Node `--check` for JavaScript. Required strings, function names, or operations do not prove JavaScript behavior. Expected behavior cases need separate review; generated JavaScript remains unexecuted under the current gate. Check nesting, omitted attributes, and extra declarations explicitly where the existing evaluator cannot establish the full requirement.

Screen requests and solutions against earlier approved authored examples and the unchanged development prompts. Reject exact duplicates, review near-duplicates, and keep template siblings together. Publish all exact records and the complete review guide, measured counts, check results, limitations, and canonical digest before seeking owner approval. Do not promote this sample file or an unfinished full candidate into an approved source catalog.

After approval, build a separate corpus and fit a fresh tokenizer on training only. Verify prefix consistency, each packed record's EOS, context length, fixed answer caps, and roundtrips with that tokenizer. Initialize a fresh random checkpoint, seed 1337, with no pretrained weights. Preserve all earlier artifacts and source approvals.

## Proposed bounded comparison after approval

Keep the architecture, optimizer, learning rate, prompt format, and decoding caps unchanged initially so the new data is the main change. Generate and score its matching step-zero baseline first. Begin with a **100-step** diagnostic, using the existing step-bounded pilot command and a ten-minute wall-clock ceiling. That limits the first experiment's token exposure rather than assuming that the full ten minutes is helpful.

The present runner records baseline and final held-out loss, but does not automatically retain a best-validation checkpoint or stop on rising validation loss. Make no such claim. Inspect validation loss, examples, complete-task scores, syntax, and EOS before scheduling a fresh 300-step comparison from the same initialization. A new run must use a new output directory; do not keep training the tiny-corpus checkpoint with incompatible token IDs.

Do not open the final holdout or schedule a two-hour run based on improved syntax or lower training loss alone. The next training budget remains bounded, local, $0 paid services, and within 200 GiB. No command needs to run on the owner's machine while the expanded candidate is being drafted.
