# Phase 2 data-mix review — P2-02

**Status: the v2 P2-02 corpus remains the reproducible baseline; the approved nine-record supplement is included in a built v3 corpus and matching tokenizer. Its v3-matched step-zero baseline scored 0/30 complete tasks, with 29 outputs truncated. No trained P2 checkpoint exists.** This review adds no external source material or downloads.

## Measured composition

The v2 baseline has 30 training records and 17 development records from two approved source families, with whole project groups kept intact. Existing token counts in the [collection report](PHASE-2-DATA-COLLECTION-REVIEW.md) show:

| Split | Markdown records / tokens | HTML, CSS, and JavaScript records / tokens | Direct-code-extension token share |
|---|---:|---:|---:|
| Training | 14 / 78,579 | 16 / 24,616 | 23.9% of 103,195 |
| Development | 9 / 51,695 | 8 / 4,951 | 8.7% of 56,646 |

The direct-code-extension share groups complete HTML, CSS, and JavaScript records; it is a useful proxy, not a syntax-level parse of every token. HTML may contain embedded CSS or JavaScript. Conversely, Markdown contains explanations, diagrams, and code fences. The earlier manual audit estimated about 8,800 code-fence tokens, 57,200 unfenced Markdown tokens, and 11,200 Mermaid tokens in training Markdown. Those estimates are approximate and are not added to the table's extension counts.

The combined v3 corpus has 36 training and 20 development records. Its new tokenizer processed 103,902 training tokens and 56,884 development tokens, with all 56 records round-tripped. These counts use the v3 tokenizer and cannot be compared directly with the v2 token counts above. The nine authored examples are Markdown records containing fenced task solutions, so the v2 extension-share table does not measure their code content. A source-family/language/code-versus-explanation breakdown for v3 remains to be recorded; see the [v3 build report](PHASE-2-DATASET-V3-REPORT.md).

The approved source lock has 23 Microsoft Markdown files, plus 11 Microsoft HTML/CSS/JavaScript files. All 13 selected MDN files are HTML/CSS/JavaScript. This explains why training and development differ substantially in their code-file share: the intact Microsoft project groups place most instructional Markdown in both splits, while the selected MDN groups contribute relatively little text. Do not repair that split by moving individual files across group boundaries.

## P2-02 decision

Keep `p2-02-data-v2` and its tokenizer as the immutable, reproducible baseline. Treat v3 as a reviewed candidate mix that adds nine task/solution examples, not as a demonstrated coding-quality improvement. Do not train the next coding checkpoint as though v3 has met the proposal's rough 70–80% code / 20–30% concise-explanation target. Do not duplicate or oversample code records merely to change the percentages.

The pinned external source selection alone is too small to produce that target while retaining all approved records and whole-group splits. A code-only extension filter would remove most explanatory material and would not add task-to-solution examples, so it is not a sufficient replacement. The raw-source records teach syntax and concepts, but are not paired natural-language coding requests and verified solutions. The nine authored examples add a small task/solution component; their effect on v3's total code/explanation mix remains unmeasured.

The step-zero results are not failure evidence for a trained model: the checkpoint has random weights, all languages scored 0/10, and 29 responses hit their decode caps. Use the baseline for comparison, not to infer which concepts a trained Plex is missing. The next check is a 10-minute real-corpus run followed by evaluation on the same development set and decoding settings. Keep later results separate by language and task, and never copy development prompts or checks into training. The full static result is recorded in the [v3 report](PHASE-2-DATASET-V3-REPORT.md).

The owner approved nine original Codex-authored task/solution examples for local P2 training on 2026-10-04. They are materialized into three language families with each request/solution pair kept in its own split group and added to [catalog v2](../training/phase2/dataset-sources.phase2-v2.json). The owner ran the combined build and tokenizer fit on Windows; the returned counts and hashes are recorded in the [v3 report](PHASE-2-DATASET-V3-REPORT.md). This approval added no external source paths beyond the exact Microsoft and MDN paths in the [P2 source lock](../training/phase2/dataset-source-lock.json).

## JavaScript behavior checks

The development evaluator currently runs `node --check` only; it does not execute generated code. The current Codex task runtime resolved Node.js v24.21.0. A runtime version is not proof of an execution sandbox. Node's `vm` module explicitly is not a security boundary, and Node's permission model does not promise protection from malicious code ([Node VM documentation](https://nodejs.org/docs/latest-v24.x/api/vm.html), [Node permission-model documentation](https://nodejs.org/docs/latest-v24.x/api/permissions.html)).

The current task runtime did not resolve `WindowsSandbox.exe` on `PATH`; checking whether the Windows Sandbox optional feature is enabled failed because DISM requires elevation. Therefore the feature's state on the owner's Windows installation is **unknown**. No generated code was run. Before adding behavioral evaluation, verify an OS-level disposable boundary (for example, Windows Sandbox or a separate disposable VM), disable networking, expose only read-only test inputs, and enforce process time and output limits. Windows Sandbox networking is enabled by default and must be disabled in its configuration ([Microsoft Windows Sandbox overview](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview)).

Until that boundary is demonstrated, keep JavaScript behavior unavailable and do not present static development scores as the P2 coding-quality gate. This review does not change the evaluator or create the final holdout.

## Completion criteria

- A versioned train/development corpus includes the approved additions; v3 is built, while evidence that its mix improves coding quality remains pending.
- Related examples remain grouped; exact duplicates and evaluation leakage are checked; aggregate v3 token totals are recorded, while the full source-family/language/code-explanation breakdown remains pending.
- A matching step-zero development score exists before any failure-guided data adjustment.
- The JavaScript behavior sandbox is verified before any generated code is executed; otherwise that check remains unavailable.
- The corpus and tokenizer rebuild reproducibly, while P1 artifacts and the current P2 baseline remain unchanged.
