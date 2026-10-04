# Phase 2 data-mix review — P2-02

**Status: the existing P2-02 corpus is a reproducible pipeline baseline, not yet the preferred coding-training mix. The tracked repository has no P2 checkpoint or development score, so there are no recorded model failures to use for data changes.** This review uses only the already approved, pinned source selection. It does not add or download data.

## Measured composition

The current corpus has 30 training records and 17 development records from two approved source families, with whole project groups kept intact. Existing token counts in the [collection report](PHASE-2-DATA-COLLECTION-REVIEW.md) show:

| Split | Markdown records / tokens | HTML, CSS, and JavaScript records / tokens | Direct-code-extension token share |
|---|---:|---:|---:|
| Training | 14 / 78,579 | 16 / 24,616 | 23.9% of 103,195 |
| Development | 9 / 51,695 | 8 / 4,951 | 8.7% of 56,646 |

The direct-code-extension share groups complete HTML, CSS, and JavaScript records; it is a useful proxy, not a syntax-level parse of every token. HTML may contain embedded CSS or JavaScript. Conversely, Markdown contains explanations, diagrams, and code fences. The earlier manual audit estimated about 8,800 code-fence tokens, 57,200 unfenced Markdown tokens, and 11,200 Mermaid tokens in training Markdown. Those estimates are approximate and are not added to the table's extension counts.

The approved source lock has 23 Microsoft Markdown files, plus 11 Microsoft HTML/CSS/JavaScript files. All 13 selected MDN files are HTML/CSS/JavaScript. This explains why training and development differ substantially in their code-file share: the intact Microsoft project groups place most instructional Markdown in both splits, while the selected MDN groups contribute relatively little text. Do not repair that split by moving individual files across group boundaries.

## P2-02 decision

Keep `p2-02-data-v2` and its tokenizer as the immutable, reproducible baseline. Do not train the next coding checkpoint on this mix as though it met the proposal's rough 70–80% code / 20–30% concise-explanation target. Do not duplicate or oversample code records merely to change the percentages.

The locked selection is too small to produce that target while retaining all approved records and whole-group splits. A code-only extension filter would remove most explanatory material and would not add task-to-solution examples, so it is not a sufficient replacement. The current raw-source records also teach syntax and concepts, but are not paired natural-language coding requests and verified solutions.

There is no evidence yet about which kinds of tasks Plex fails. First compare a fresh P2 step-zero checkpoint against the existing 30-task development set, using the matching P2 tokenizer and fixed evaluation settings. Keep the results separate by language and task. After that baseline exists, use its concrete misses to shape a new training mix; never copy development prompts or checks into training.

The current task runtime could not inspect the ignored P2 dataset, tokenizer, or checkpoint artifact directories because access was denied. Therefore this review relies on the tracked manifests and recorded reports and does not assert whether additional local P2 artifacts exist outside Git.

To reach a more useful mix, prepare a new versioned selection that adds either (a) a separately reviewed, code-focused group of examples with adequate HTML/CSS/JavaScript coverage, or (b) a small set of locally authored task/solution records with explicit provenance. Keep every project/example family intact across splits, retain license notices, report code and explanation token counts by language and split, and fit a new tokenizer on training text only. The previous approval covers the exact Microsoft and MDN paths listed in the [P2 source lock](../training/phase2/dataset-source-lock.json); it does not cover additional files or synthesized records. No such additions are included here.

## JavaScript behavior checks

The development evaluator currently runs `node --check` only; it does not execute generated code. The current Codex task runtime resolved Node.js v24.21.0. A runtime version is not proof of an execution sandbox. Node's `vm` module explicitly is not a security boundary, and Node's permission model does not promise protection from malicious code ([Node VM documentation](https://nodejs.org/docs/latest-v24.x/api/vm.html), [Node permission-model documentation](https://nodejs.org/docs/latest-v24.x/api/permissions.html)).

The current task runtime did not resolve `WindowsSandbox.exe` on `PATH`; checking whether the Windows Sandbox optional feature is enabled failed because DISM requires elevation. Therefore the feature's state on the owner's Windows installation is **unknown**. No generated code was run. Before adding behavioral evaluation, verify an OS-level disposable boundary (for example, Windows Sandbox or a separate disposable VM), disable networking, expose only read-only test inputs, and enforce process time and output limits. Windows Sandbox networking is enabled by default and must be disabled in its configuration ([Microsoft Windows Sandbox overview](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview)).

Until that boundary is demonstrated, keep JavaScript behavior unavailable and do not present static development scores as the P2 coding-quality gate. This review does not change the evaluator or create the final holdout.

## Completion criteria

- A versioned train/development corpus improves the coding mix using reviewed source additions or explicitly attributed local examples.
- Related examples remain grouped; exact duplicates and evaluation leakage are checked; token totals by source family, language, and code/explanation category are recorded.
- A matching step-zero development score exists before any failure-guided data adjustment.
- The JavaScript behavior sandbox is verified before any generated code is executed; otherwise that check remains unavailable.
- The corpus and tokenizer rebuild reproducibly, while P1 artifacts and the current P2 baseline remain unchanged.
