# Plex

Plex is a small coding model project. Its goal is to train Plex Code from randomly initialized weights and keep its own checkpoints and training history. Pretrained Qwen weights are not an initialization source; Qwen may be used as an evaluation baseline. The authoritative direction is in [Plex-ROADMAP.md](Plex-ROADMAP.md).

P1-01 through P1-10 are completed and preserved: the repository discovery, ranking, prompt construction, response parsing, edit validation, proposed buffers, and unified diff tools remain available as the eventual model client and evaluation support. A randomly initialized Plex model has completed the ten-minute synthetic CUDA smoke test and saved a checkpoint; coding-data training and useful inference remain to be demonstrated. P1-11 records the actual hardware and training limits; P1-12 defines the first small model experiment.

## Development on Windows

Use Node.js 24 LTS and npm. Dependencies are pinned in `package-lock.json`.

```powershell
npm ci
npm run build
npm test
npm start -- --help
```

To test the actual `plex` executable without a global install, pack and install into a local test directory:

```powershell
npm pack
npm install --prefix ".test-artifacts\local install" --omit=dev --ignore-scripts --no-audit --no-fund .\plex-code-cli-0.1.0.tgz
& ".\.test-artifacts\local install\node_modules\.bin\plex.cmd" --help
```

The package is private to prevent accidental registry publication. Build output, dependencies, local test installs, archives, and weights are ignored by Git. Runtime dependencies are Ajv for JSON contracts and `ignore` for non-Git ignore rules; both operate locally.

## P1-11 hardware collection

[`scripts/collect-hardware.ps1`](scripts/collect-hardware.ps1) prints CPU model and logical processor count, total RAM, Windows GPU names, fixed-drive free/total space, and available GPU memory when an installed NVIDIA `nvidia-smi` can report it. Windows CIM supplies hardware names and memory/storage details; the script deliberately ignores `Win32_VideoController.AdapterRAM` because that value may be capped or inaccurate. If `nvidia-smi` is absent or cannot query memory, GPU memory is labeled unavailable. No software is installed, no persistent settings are changed, and no files are written. Hostname and username are omitted.

From the repository root in PowerShell, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\collect-hardware.ps1"
```

The execution-policy override applies only to this PowerShell process; it does not persistently change system policy. Copy the complete JSON printed to the console and provide it with [`docs/HARDWARE-AND-TRAINING-PROFILE.md`](docs/HARDWARE-AND-TRAINING-PROFILE.md) when refreshing the hardware snapshot. Also record how much space Plex may use, any paid-services budget, and the first experiment's time limit. If you have inference RAM or latency limits, include them; otherwise leave them `unknown`. Run this on your Windows computer—the development host's hardware has not been used as your profile.

Training and inference limits are separate in the [profile](docs/HARDWARE-AND-TRAINING-PROFILE.md). The hardware inventory and owner-set limits are recorded there: 200 GiB of storage, $0 paid services, a 10-minute smoke test, and a two-hour pilot. Practical training capacity will be measured before longer checkpointed runs. The eventual inference goal is local Windows operation with CPU support required and GPU acceleration optional. Model size, memory ceiling, and latency targets remain unknown. Plex starts from random weights; Qwen is only a possible evaluation baseline.

## P1-12 first experiment

P1-12 defines a 27.6-million-parameter decoder-only Transformer, 512-token context, and FP32 AdamW settings. The full configuration and analytic memory estimate are in [`docs/FIRST-EXPERIMENT.md`](docs/FIRST-EXPERIMENT.md). P1-13 is implemented and its original 13 training tests pass on the owner's Windows setup (Python 3.12.10, PyTorch 2.14.0+cu126, CUDA 12.6). The owner completed the [ten-minute CUDA smoke test](docs/SMOKE-TEST-2026-10-03.md): 4,199 steps, 57,327.61 synthetic token positions/second, 734 MiB peak GPU reservation, and about 1.30 GiB peak process RAM. The two-hour pilot follows the data/tokenizer and tiny-learning milestones. Before longer training, P1-19 must verify checkpoint resumption. No pretrained weights are used.

## P1-13 local training runner

The separate Python workspace is in [`training/`](training/README.md). It provides commands to inspect the runtime, prepare small local corpora, train, evaluate, generate, and run a bounded synthetic-data smoke test. The owner's ten-minute CUDA smoke test passed. P1-14 is complete for the [approved starter corpus](docs/DATASET-SOURCE-REVIEW.md): 34 training records, 54 validation records, preserved MIT notices, and reproducible provenance, totaling under 1 MiB. See [`docs/DATASET-PIPELINE.md`](docs/DATASET-PIPELINE.md).

## P1-15 Plex tokenizer

Plex's own byte-level BPE tokenizer is trained and packaged with the model configuration. It fitted only the approved training text and learned 9,976 token entries within the existing 16,384 model capacity. All 88 records round-trip exactly; a separate rebuild produced all 11 bundle files byte-identically. The bundle occupies about 0.99 MiB. All 35 training-workspace tests pass. Settings, artifact hashes, and reproduction commands are in the [tokenizer report](docs/PLEX-TOKENIZER.md).

P1-16 created a step-zero random initialization checkpoint tied by hash to this tokenizer. P1-17 then trained from it on one short training record: loss fell from 9.438 to 0.0000224, and greedy decoding reproduced the 16-token sample from a two-token prompt in 250 steps. See the [learning check report](docs/PLEX-LEARNING-CHECK.md). This confirms the basic training path can learn and repeat one memorized sample; it does not measure coding ability. Next, P1-18 is the two-hour real-data pilot, using the separate train and held-out validation splits. Checkpoint/resume coverage and general-purpose tokenizer-aware train/evaluation/generation are still required before longer runs in P1-19.

The [P1-18 pilot path](docs/PLEX-PILOT.md) now trains with the BPE corpus and measures held-out loss. A one-step preflight completed and independent evaluation matched its final validation result. The **two-hour run remains pending**; the pilot report documents the exact local command and its completion check. P1-19 remains the gate for tokenizer-aware checkpoint resumption and generation before longer runs.

## Current CLI behavior

| Command | Result | Exit code |
|---|---|---|
| `plex --help`, `plex -h`, or `plex` | Usage and development status | 0 |
| `plex --version`, `plex -v` | Version | 0 |
| Unknown flag or malformed request | Argument error | 2 |
| `plex [--repo <directory>] "change the page title to DungeonDex"` | Metadata, rankings, selected file, estimated prompt size and snapshot hash; implementation unavailable | 1 |
| Ambiguous or missing target context | Rankings and `INSUFFICIENT CONTEXT`; no selection | 1 |
| Invalid explicit repository path | Project detection error | 1 |

## Project-root detection

`src/repo/detect.ts` resolves roots without writing files or changing Git state. An explicit `--repo` path is resolved relative to the working directory and remains the project boundary, even inside a larger Git repository. Without it, a nested Git working directory resolves to its Git top level; a non-Git directory remains the project root with no search for parent package files.

Paths must exist and be directories; results use canonical absolute paths. A missing Git executable produces a directory fallback with an explicit note. Corrupt Git metadata, bare repositories, Git errors, and timeouts stop detection. Git queries have fixed arguments, a five-second timeout, and ignore inherited Git location overrides such as `GIT_DIR` and `GIT_WORK_TREE`. Normal Git configuration, including trusted-directory policy, is preserved.

```powershell
npm start -- --repo fixtures/simple-web-project "change the page title to DungeonDex"
```

This prints the selected boundary, eligible source files, and their rankings. The fixture selects `index.html`, constructs its focused context and snapshot, then reports implementation unavailable. It does not call a model or generate a patch.

## Safe file enumeration

`src/repo/scan.ts` returns a deterministic repository manifest containing sorted relative paths, extensions, and byte sizes. Git projects use a bounded, NUL-delimited `git ls-files --cached --others --exclude-standard --stage` query within the selected directory. Index modes exclude tracked symlinks and submodules, including Windows symlink emulation. Missing tracked files are skipped. Tracked files remain eligible even if later added to `.gitignore`, unless a hard exclusion applies.

Non-Git projects use bounded directory traversal with root and nested `.gitignore` rules. Nested negations can override file patterns; ignored parent directories are pruned. This fallback does not load Git's global ignore file, `.git/info/exclude`, or ignore rules above the selected boundary.

Both paths allow `.html`, `.css`, `.js`, `.mjs`, and `.cjs`, with normalized extension metadata. They exclude dependency/build/cache directories, `.git`, sensitive directories and `.env` files, common minified/bundled/generated filenames, traversal symlinks/junctions, and nested Git projects. Paths must stay within the canonical root and be compatible with Windows path rules. Each candidate gets only a prefix read of up to 4 KiB; files containing NUL bytes in that prefix are excluded as binary impostors. Complete UTF-8 validation and focused source reads belong to context construction.

Default limits are 1,000 eligible files, 128 KiB per source file, 20,000 enumeration entries, 64 path components, 4 MiB of total prefix/ignore inspection, 1 MiB of Git output, and a five-second Git timeout. Individual `.gitignore` files are limited to 64 KiB. Exceeding a limit, unreadable paths, or a Git query failure stops the scan without returning a partial manifest. `scanProject(project, options)` accepts lower limits for callers and tests; larger limits and unknown options are rejected.

The scanner performs no filesystem or Git writes. Metadata and realpath checks reject links and changed files during inspection; later context and patch stages must recheck selected paths because enumeration is not an atomic filesystem snapshot. Tests cover ignores, hard exclusions, limits, missing files, Git index preservation, explicit boundaries, and Windows junctions. The OS file-symlink test reports a skip when Windows does not grant symlink creation rights.

## Contracts

`src/core/contracts.ts` defines TypeScript types; `schemas.ts` defines the canonical JSON schemas, including the model's constrained-output schema. `validate.ts` checks unknown values without coercion, defaults, or stripping fields.

Requests require a nonblank task and working directory. Repository manifests contain bounded metadata for supported web source files. Model responses allow only `patch`, `no_change`, `insufficient_context`, and `unsupported`; patches require edits, and all other statuses require an empty edit list. Runtime failures belong to the orchestrator. Results describe previews only, allow at most one repair, and require passing check evidence for a validated proposal.

Schema acceptance does not establish filesystem containment, safe anchors, UTF-8 edit byte size, or task correctness. Those checks belong to later milestones.

## Strict model-response parsing

`parseModelResponse(text)` in `src/core/parse.ts` accepts exactly one JSON value surrounded only by JSON whitespace, then validates it against the canonical model-response schema. It rejects prose, Markdown fences, comments, trailing documents, incomplete JSON, duplicate decoded object keys, unknown fields, incorrect types/statuses, empty old anchors, and more than ten edits. It does not extract, coerce, strip fields, or repair output. Valid source strings, including escaped whitespace and Unicode, remain unchanged; empty replacements are permitted.

Response text is capped at 4 MiB of UTF-8 bytes before parsing, and nested values are limited to depth 64. Failures throw `ResponseParseError` with a stable code and `invalid_output` status, without exposing model text, field names, or parser diagnostics. The parser is ready for the later runtime adapter; the CLI still does not invoke a model. Parsing alone does not authorize edits or establish anchor uniqueness or path safety.

## Candidate-file ranking

`src/repo/rank.ts` returns sorted candidates, integer scores, individual signal contributions, and either one selected path or an insufficient-context result. Scores order evidence; they are not model-confidence percentages or correctness guarantees.

| Signal | Points | Maximum contributions per file |
|---|---|---|
| Explicit relative path | 120 | One per distinct path hint |
| Explicit filename | 80 | One per distinct filename hint |
| Task keyword in path | 12 | 3 |
| Suggested language | 30 | 1 |
| Task keyword in source | 4 | 5 |
| Identifier or selector match | 20 | 3 |
| HTML title element for a title task | 40 | 1 |
| Conventional `index.html` for a title task | 5 | 1 |

Tasks are tokenized with generic instruction words removed, retaining whole identifiers and camel-case parts. Filename/path hints support case-insensitive matching, relative paths, Windows separators, and quoted names with spaces. Tied scores use lexical path order for display, but ties never justify selection. A title task matching several HTML titles requires a unique filename/path hint or distinguishing path keyword, even when `index.html` has a higher score. Missing named files, duplicated basenames, missing title context, and explicit multi-file requests stop safely. The Phase 1 selector supports one target; mixed-language tasks without an explicit target also stop.

Ranking inspects source sequentially under a 4 MiB total budget and a 128 KiB per-file limit. Each read rechecks root containment, path components, links, file identity, size, and modification time, then decodes strict UTF-8. Source is discarded after extracting signals. `rankCandidates(task, manifest, { maxInspectionBytes })` can lower the inspection budget; failures never return a partial ranking. Title, identifier, and selector signals are lexical heuristics, not HTML/CSS/JavaScript validation. Import/reference expansion and broader multi-file selection remain later work.

Ranked candidates also record the SHA-256 of the raw source inspected during ranking, so context construction can detect later same-size changes. The CLI displays the first ten ranked candidates and their reasons; the API returns the complete bounded ranking. Tests exercise the real three-file title fixture, ambiguous pages, named targets, CSS/JavaScript signals, ties, inspection limits, unchanged fixture hashes, and changed/link-swapped paths.

## Bounded context and selection snapshots

`buildContext(task, manifest, ranking, options)` in `src/context/build.ts` requires one uniquely selected file from the manifest and ranking. It reads only that selected file, checks its hash against ranking, and builds two messages: packaged system rules from `prompts/implementation.txt` and a JSON user context. The user context contains the task, minimal project metadata, the complete selected source, edit constraints, and the canonical model-response schema. Other candidate source, original buffers, hashes, and the absolute project path are not added to the model's context. Source comments/strings remain JSON data; delimiters are not a guarantee against model prompt injection, so deterministic patch checks remain essential.

Phase 1 supplies the whole selected file and one editable span `[0, source.length)` measured in JavaScript UTF-16 string positions. It never cuts arbitrary sections to fit. A required file that cannot fit yields `INSUFFICIENT CONTEXT`; optional related-file expansion and parser-based sections remain later work.

The local snapshot retains raw original bytes, SHA-256, UTF-8 encoding, BOM presence, newline style, decoded source, and editable spans. The BOM is excluded from model source but retained in the original bytes for later patch preservation. Bundle/message/span wrappers are frozen; buffers remain mutable Node buffers, so verification also checks their integrity. `verifySelectionSnapshot(bundle)` safely rereads the selected file and rejects missing/link-swapped files, changed bytes, or modified in-memory originals. Construction verifies again after asynchronous token accounting. Snapshots are held in memory and are not automatically saved to disk.

`src/context/budget.ts` reserves 768 output tokens and 256 safety/template tokens inside a default 4,096-token context, leaving 3,072 input tokens. A separate serialized-input cap is 32 KiB. Serialization includes all messages and the response schema, not only source text. Without a runtime counter, `ceil(UTF-8 serialized bytes / 4)` is explicitly an estimate and `requiresRuntimeCheck` remains true. It cannot prove that a model's native chat template fits.

The budget API accepts lower limits and an optional async `countTokens` callback. A runtime adapter must count the complete formatted native prompt, including the schema already in the user message. This count supersedes the preliminary estimate; invalid/failing counters and exceeded byte/token limits stop construction. Runtime integration remains P1-13+, and injected-counter tests do not demonstrate live inference. The CLI currently prints the estimated budget and snapshot hash without dumping source or invoking a model.

## Edit-path and anchor validation

`validateEditAnchors(response, bundle)` in `src/core/edit-validation.ts` accepts a schema-valid patch and the selected snapshot. For each edit it requires the exact selected relative path, rejecting traversal, absolute paths, Windows drive or UNC forms, alternate data streams, and case aliases. Existing files are the only edit targets; the model cannot use an empty old anchor to create or delete a file.

Each nonempty old string must occur exactly once in the original selected source and fit completely inside one editable UTF-16 span. Multiple edits are located against that same original source, then checked for overlap. Validation rereads the selected file and verifies its raw SHA-256 snapshot before returning frozen located edits. Error codes do not include model-provided paths or source text.

## Proposed buffers and unified diffs

`buildProposal(response, bundle)` in `src/core/proposal.ts` applies validated edits to a copy of the original UTF-8 bytes in reverse source-position order. The original bytes stay untouched. It preserves a UTF-8 BOM and every byte outside edited ranges, including unchanged CRLF and Unicode text. On single-style files, new replacement line breaks are normalized to the original LF, CRLF, or CR style. Mixed-style files require the replacement's line-break sequence to match the old anchor's sequence. Files without an original line break use LF for added lines. Invalid UTF-16, NUL, and new BOM characters in replacements are rejected.

The resulting file must be nonempty, changed, and at most 128 KiB. Plex uses pinned [`diff` 9.0.0](https://www.npmjs.com/package/diff) to generate a unified diff from original and proposed text. A proposal is limited to 100 added/deleted diff lines and a 256 KiB diff; changed-line counts include both removed and added lines. The returned preview includes its proposed bytes, decoded source, SHA-256 hashes, diff, and changed-line count. The byte buffer remains mutable like any Node buffer; downstream checks must recheck its hash before trusting it. Proposed HTML validation is scheduled as P3-03.

## Web fixture

`fixtures/simple-web-project` contains only `index.html`, `style.css`, and `app.js`. Its initial page title is `Example`; local CSS styles the page and JavaScript connects a button to a status message. Open `index.html` directly in a browser to view it.

Tests assert the title, its location in the head, and the CSS/JS references. `tests/fixtures/simple-web-project.sha256.json` records a SHA-256 digest of each file's raw bytes; fixture files use LF endings enforced by `.gitattributes`. Intentional fixture updates must also update the baseline. CLI tests operate on temporary copies and compare all three hashes before and after the task.

P1-11 is complete; P1-12's configuration and ten-minute resource-fit check are recorded, with the real-data pilot pending; P1-13 implementation and owner smoke testing are complete. P1-14 is complete for the approved starter corpus; next is P1-15's tokenizer. See the [updated roadmap](Plex-ROADMAP.md), [hardware and training profile](docs/HARDWARE-AND-TRAINING-PROFILE.md), [first experiment definition](docs/FIRST-EXPERIMENT.md), and [training workspace instructions](training/README.md). HTML validation is scheduled as P3-03.
