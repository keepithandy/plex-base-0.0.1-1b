# Phase 2 — Data and coding-evaluation proposal

**Status: owner-approved starting decisions recorded; a small P2-02 corpus and tokenizer have been built.** The exact source review and artifacts are recorded in the [Phase 2 data collection review](PHASE-2-DATA-COLLECTION-REVIEW.md). P2-01 evaluation tasks and harness remain unfinished; no Phase 2 model initialization or training run has started.

## Recommendation

Build the coding evaluation before changing the model or extending training. Keep the P1-14 starter corpus and its reports unchanged as the historical baseline. Prepare a new, reviewed corpus version with source families represented in both training and development, while keeping related projects together. Evaluate code on small, independently authored HTML, CSS, and JavaScript tasks with executable acceptance checks.

The current [P1-20 report](PLEX-EXPERIMENT-REPORT-P1-20.md) shows that the 27.6-million-parameter model reduced next-token loss on the pilot's held-out data, but it generated an incorrect JavaScript function. Phase 2 should therefore measure working outputs directly. All Plex checkpoints must continue to start from random weights; Qwen may be compared only as an optional evaluation baseline if already available locally.

## What stays in scope

- Basic single-file HTML, CSS, and JavaScript generation/completion on local Windows.
- Training from Plex's own random initialization and local checkpoints.
- A reviewed corpus, deterministic development checks, and a final evaluation kept out of training.
- The existing 200 GiB storage allocation and $0 paid-services budget.
- The current maximum 120-minute training duration until evaluation and data gates pass.

Repository editing, multi-file changes, autonomous tool use, paid datasets/services, large downloads, and pretrained Plex weights are out of scope.

## Source plan and approval boundary

The P1-14 approval covered exact pinned snapshots and selected files. It does not automatically approve different files, revisions, or uses. The two source selections below have separate owner approval recorded for this collection; other files and source families remain unapproved.

| Source family | Current status | Proposed Phase 2 use |
|---|---|---|
| Microsoft Web Dev for Beginners | Owner-approved exact P1-14 subset; 34 selected content records. | Approved for the new train/development split by project group. The P2 lock and family/group split are recorded in the [collection review](PHASE-2-DATA-COLLECTION-REVIEW.md); keep the original P1 split and artifacts unchanged. |
| Brad Traversy's 50 Projects in 50 Days | Owner-approved exact P1-14 subset; 54 records used as P1-18/P1-19 validation. | Historical validation only. Do not put these records into Phase 2 training or claim them as a fresh final benchmark; Plex has repeatedly been evaluated on them. |
| MDN `learning-area` | Approved for path review and a small selection. The reviewed snapshot declares CC0 1.0. | Thirteen pinned files from five project groups were selected; no other MDN repositories or binary assets are included. Exact paths, license hash, exclusions, and commit are in the [collection review](PHASE-2-DATA-COLLECTION-REVIEW.md). |

The first Phase 2 dataset includes **two approved source families**, with five project groups from each available to both training and development. The resulting corpus and deterministic split are recorded in the [collection review](PHASE-2-DATA-COLLECTION-REVIEW.md). Do not split related files, translated copies, starter/solution pairs, or repeated examples across sets.

The MDN repository license labels are a screening lead, not approval of every file. Before adding any source, record its exact revision, selected paths, license text/hash, exclusions, attribution/notice handling, and the owner’s approval. Exclude dependencies, generated files, images/fonts, third-party assets, secrets, and material with unclear provenance. Preserve required notices with the local corpus.

### Proposed data mix

Measure proportions by **tokens**, not file or record counts. As an initial target for review, use roughly 70–80% code and 20–30% concise programming explanations, with HTML, CSS, and JavaScript as balanced as the approved source material permits. Report the actual per-language token totals before building; do not duplicate or oversample a weak category just to make the table look balanced.

Raw source files alone do not teach Plex how to turn a request into code. Add a separate, small set of locally authored task/solution examples to training and development if Phase 2 expects natural-language requests. Keep those examples distinct from all evaluation prompts and tests. The source manifest must identify authored records separately from copied source records.

## Split design and required pipeline work

The current dataset pipeline assigns an entire `groupId` to one split, and the tokenizer bundle rejects groups appearing in both splits. That was appropriate for P1-14's two-source experiment, but it cannot produce source-family-balanced training and development splits.

For the next corpus version, preserve that behavior for existing datasets and add explicit identities for:

- `sourceFamilyId`: the repository/course family used for balanced reporting.
- `splitGroupId`: the smallest related unit that must remain together, normally a project, lesson, or example series.
- Record origin: source path and pinned revision, or `owner-authored` for new task/solution records.

Assign whole `splitGroupId` units deterministically within each approved source family so every family appears in both train and development. Keep sibling files and starter/solution pairs together. Fail the build on exact normalized-content overlap between splits; report near-duplicate findings for review. Fit the tokenizer on training text only. The manifest should include the seed, counts and token totals by family, language and split, source/license hashes, filters, duplicate findings, and final split hashes.

Use a new dataset/tokenizer/checkpoint identity for Phase 2. A changed tokenizer changes token IDs, so do not resume a checkpoint with an incompatible tokenizer. Initialize the Phase 2 model from random weights with a recorded seed; compare configurations from the same initialization where practical. Preserve P1 artifacts unchanged.

## Evaluation proposal

### Task sets

Create two small task sets before Phase 2 model comparisons:

| Set | Proposed size | Purpose | Handling |
|---|---:|---|---|
| Development | 30 tasks: 10 each for HTML, CSS, and JavaScript | Debug prompt formats and compare bounded training/configuration choices. | Fixed, versioned, and excluded from training text. May be inspected to guide changes. |
| Final holdout | 60 tasks: 20 each for HTML, CSS, and JavaScript | Decide whether Plex has demonstrated basic coding ability on unseen tasks. | Freeze prompts and hidden checks before the comparison; never use it to select checkpoints, tune prompts, or alter training data. |

Tasks should be small, single-file requests with a clear output contract, such as one JavaScript function, a semantic HTML fragment/page, or a CSS rule set for supplied markup. Include ordinary cases and edge cases. Store each task's prompt, expected output shape, tests, language, difficulty, provenance, and stable ID. Keep task solutions and tests out of the training manifest. Check prompts and expected answers against training/development text for duplication before freezing the final set.

The P1-18 Traversy split remains a historical next-token validation result only. Do not relabel it as the Phase 2 final holdout.

### Checks and score

The primary measure should be **complete task pass rate**: the output meets its format contract, parses, and passes every task-specific behavior/structure check. Report it overall and separately for HTML, CSS, and JavaScript. Also report syntax/parse pass rate, partial assertion counts, timeouts, empty/truncated outputs, and output length. Keep next-token loss as a training diagnostic, not the coding-quality score.

- JavaScript: parse with an installed Node.js `--check` where available, then run deterministic unit/DOM behavior checks in a separate temporary directory with a strict timeout and output cap. Do not execute generated code in the repository or expose credentials. Confirm a safe, local test setup before enabling execution; if isolation is unavailable, report behavioral checks as unavailable rather than calling static parsing a functional pass.
- HTML: parse and check required semantic elements, labels, IDs, and relationships. Use a locally installed browser for rendering/DOM checks if one is available; state clearly which checks ran.
- CSS: verify required selectors/declarations and computed behavior at a fixed viewport using an already installed browser where available. Do not install a browser or parser as part of this proposal. If no browser is available, mark computed-style checks unavailable and limit claims to the checks that actually ran.

Before the final holdout is frozen, define a simple passing-task oracle and test it with known-good examples, deliberately broken outputs, malformed output, empty output, and timeout cases. Fixing the evaluator after seeing Plex's final-set results invalidates that comparison; version any later benchmark as a new set.

### Baselines and decision rule

Run every task with the same prompt template, deterministic decoding settings, and language-specific output limit. Compare:

1. The matching step-zero Plex checkpoint and tokenizer.
2. The trained scratch-initialized Plex checkpoint.
3. An optional trivial baseline (for example, empty output or a fixed minimal template).
4. Optionally, Qwen only if a suitable checkpoint is already present locally. Do not download it or use it to initialize Plex.

Report raw task counts and pass rates per language, together with uncertainty intervals; a small task set supports only an early signal, not a broad capability claim. The owner accepted the starting decision rule that Plex must beat its step-zero checkpoint by a meaningful margin and pass a majority of final tasks in every language, with no language hidden by an aggregate score. The numeric margin and exact pass-oracle contract still need agreement before freezing the final task set.

## Order of work and stop gates

1. **P2-01a — Evaluation design:** the owner accepted the 30/60 task counts and per-language majority rule as a starting gate. Set the numeric meaning of “meaningful improvement,” output contracts, task categories, local tool availability, and safety/timeout behavior before freezing the final tasks.
2. **P2-01b — Evaluation harness and development set:** implement the checks, prove they reject known failures, and author/version the 30 development tasks. Keep the 60 final tasks sealed. Do not run a Phase 2 training experiment yet.
3. **Source review:** completed for the exact Microsoft subset and small MDN selection recorded in the [collection review](PHASE-2-DATA-COLLECTION-REVIEW.md). Other MDN paths and other source families remain unapproved.
4. **P2-02 — New corpus build:** a deterministic family-stratified dataset and fresh tokenizer were built from training text only. The actual mix is more documentation-heavy than the proposed 70–80% code target; review and improve that mix before using it as the preferred Phase 2 training corpus.
5. **P2-03 — Bounded comparisons:** after the evaluation harness and data mix pass review, establish a fresh random initialization, run controlled experiments against the development set with fixed budgets and settings, and compare task pass rates plus memory, throughput, and checkpoint integrity. Keep each run within the existing 120-minute cap.
6. **Freeze and gate:** finalize the 60-task holdout and its numeric threshold before viewing model scores. Proceed to P2-04's next bounded base-checkpoint run only if the harness is valid, data provenance/splits pass review, and development results justify the run.

No uncapped run is proposed. Stay within the 200 GiB Plex allocation and $0 paid-services budget. Report any missing local runtime or unavailable check explicitly; decide on dependencies separately rather than silently installing them.

## Owner decisions recorded for this collection

- MDN `learning-area` was approved for path review and the exact small selection listed in the [collection review](PHASE-2-DATA-COLLECTION-REVIEW.md).
- The exact already approved Microsoft P1-14 subset may be re-split by project group for this new train/development corpus.
- The proposed 30 development / 60 final tasks and the per-language majority plus meaningful-improvement-over-step-zero rule are accepted as a starting gate. A numeric improvement margin is still required before freezing the final tasks.

These decisions authorize only the reviewed source selection and starting evaluation design. The final benchmark is not frozen, the observed corpus mix needs review, and no P2 training run should begin yet.
