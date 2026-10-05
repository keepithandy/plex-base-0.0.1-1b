# Plex Base

Plex Base is a small, locally trained coding model project focused on HTML, CSS, and JavaScript. It starts from randomly initialized weights and keeps its own tokenizer, checkpoints, provenance, and training history. The eventual Plex Code client will use the model for repository edits. Pretrained Qwen weights are not an initialization source; Qwen may be used as an evaluation baseline. The project direction and milestones are in [Plex-ROADMAP.md](Plex-ROADMAP.md).

P1-01 through P1-10 are completed and preserved: the repository discovery, ranking, prompt construction, response parsing, edit validation, proposed buffers, and unified diff tools remain available as the eventual model client and evaluation support. Plex's randomly initialized model has completed a synthetic CUDA smoke test, a two-hour real-data pilot, and a one-step checkpoint resume; its saved weights can generate text on CPU. Useful coding ability remains to be demonstrated. P1-11 records the actual hardware and training limits; P1-12 defines the first small model experiment.

## Current status — October 5, 2026

**Plex can train, save and resume checkpoints, generate text, and learn small supplied examples in bounded diagnostics. It has not yet demonstrated successful general coding-task completion.** The model has 27,566,080 parameters and a 512-token context. Phase 1's training infrastructure is recorded through P1-20. P2-07 learned 24/24 supplied copies and transferred to 4/6 held-out wording cases. P2-08 learned 63/64 supplied selector prompts, below its convergence gate, so its 4/16 held-out score is inconclusive. P2-09's frozen-checkpoint audit found the expected answer newline ranked first on 6/16 held-out prompts; the period ranked first in all 16 when the expected newline was supplied. P2-10 learned 64/64 supplied selectors. Its original held-out wording scored 7/16; four additional phrasings scored 43/64. The P2-12 step-200 checkpoint scored 95/96 on a new six-phrase selector-copy development set; its one miss duplicated a selector fragment. These remain narrow copying diagnostics, not evidence of general coding ability. The Phase 2 coding-quality gate remains unmet and the final project holdout remains closed. Next: test a different task family such as constrained CSS edits with deterministic checks, using separate untouched final prompts.

The current evidence points to a narrower bottleneck than simple answer memorization. P2-03's answer-focused objective improved supplied-answer reproduction to 23/24, but transfer stayed at zero. P2-04 then fit all six supplied CSS combinations and composed only 1/3 unseen selector-gap pairs. P2-05 repeated the question across three counterbalanced folds: all 18 supplied combinations were learned, but only 1/9 fold-local held-out combinations composed correctly. P2-06 then learned all supplied examples at each level but scored 0/6 on same-value alternate wording, 0/3 on dual-binding pairings, and 0/3 on CSS composition; this locates the earliest observed failure at single-copy wording transfer.

| Experiment | Recorded result | What it establishes |
|---|---|---|
| Phase 1 two-hour pilot | 43,632 updates; held-out loss 9.33937 → 6.53100; checkpoint resume and CPU generation verified afterward | The local training and checkpoint workflow works; the generated completion was incorrect. |
| Phase 2 v3 ten-minute check | 922 updates; held-out loss 9.1694 → 6.4759; **0/30 complete tasks**, matching step zero; 30/30 outputs truncated | Lower language-model loss did not improve complete-task performance. |
| Phase 2 code-pair ten-minute diagnostic | 3,197 updates; held-out loss 6.89080 → 8.42534; **0/30 complete tasks**, matching step zero; truncations fell from 28/30 to 0/30 | Answers now finish within the limits, but still miss the requested task. The loss pattern is consistent with overfitting. |
| Phase 2 approved 234-example v3, 100 steps | Ordinary and answer-weighted checkpoints both passed **0/30** development tasks; saved-checkpoint diagnostic found **0/156** full static passes on seen training prompts and **0/78** on corpus validation prompts | These short runs did not yet learn complete supplied answers. |
| P2-03 record-start comparison, 100 steps | **0/30** development tasks and **0/156** complete seen training answers; all 156 training records selected as window starts | Record-start sampling alone did not resolve answer learning in this bounded run. |
| P2-03 complete-record comparison, 100 steps | **3/156** exact training answers, **4/156** full static training passes, **0/30** development tasks; 149,760 real target positions | Some seen answers were learned, but useful coding on unseen tasks remained unproven. |
| P2-03 complete-record continuation, step 200 | **52/156** exact training answers, **54/156** full static training passes, **0/78** corpus-validation passes, **0/30** development tasks; 299,959 cumulative real target positions | More supplied answers were learned; unseen-task results did not improve and held-out text loss rose. |
| P2-03 approved binding-diversity comparison, 100 steps per arm | Varied arm learned **20/24** supplied answers; both arms passed **0/12** new binding requests, **0/12** reserved transfer requests and **0/30** development tasks | Learning supplied variations alone did not produce correct completion of new requests. |
| P2-03 answer-focused comparison | Answer-focused training improved supplied-answer reproduction to **23/24**; both objective arms remained at **0/12** new bindings, **0/12** reserved transfer requests, and **0/30** development tasks | The objective substantially improved fitting of supplied mappings without demonstrating transfer. |
| P2-04 compositional-binding diagnostic | Fit **6/6** supplied CSS combinations and passed **1/3** unseen selector-gap recombinations | Plex showed limited compositional transfer inside one tightly controlled CSS operation. |
| P2-05 three-fold counterbalanced composition | Fit **18/18** supplied combinations across three folds but passed only **1/9** fold-local held-out combinations; all nine outputs were syntactically valid CSS | The bottleneck is not merely exposure count or failure to fit the tiny training sets; independent binding remains inconsistent. |
| P2-06 binding-representation diagnostic | All levels learned **6/6** supplied examples; evaluation: single-copy **0/6**, dual-binding **0/3**, CSS composition **0/3**; all dual-binding and CSS held-outs replayed training answers | The earliest failure was single-value transfer to alternate instruction wording, motivating the narrower P2-07 paraphrase-invariance probe. |
| P2-07 instruction-invariance diagnostic | Learned **24/24** supplied copies; passed **4/6** held-out wording cases (**1/3** selectors, **3/3** gaps); EOS **6/6** | Paraphrase exposure transferred consistently for gap copying in this probe, but selector copying remained inconsistent. |
| P2-08 selector format-control run | Learned **63/64** supplied records; evaluation **4/16** exact, formally inconclusive because the supplied set did not converge | Training generally reproduced the answer format, while held-out wording often skipped the answer boundary; final holdout stayed closed. |
| P2-09 answer-boundary audit | On the frozen P2-08 checkpoint, expected newline ranked first on **6/16** evaluation prompts; period ranked first **16/16** when conditioned on the expected newline | The first answer token is the primary shared failure in this narrow probe; selector-body choice is also inconsistent. This is a diagnostic result, not a coding-quality pass. |
| P2-10 explicit answer-start run and wider evaluation | Fresh seed-1337 run completed **100 updates**; **64/64** supplied exact; original held-out **7/16**; wider set **43/64** across four phrasings | Scores ranged from **5/16 to 16/16** by phrasing. Token audit localized misses to answer-start/selector-body choices. See the [run report](docs/PHASE-2-P2-10-EXPLICIT-ANSWER-START-RUN.md) and [wider evaluation](docs/PHASE-2-P2-10-WIDER-WORDING-EVALUATION.md). |
| P2-11 balanced-wording candidate and run | **96/96** supplied exact; fresh evaluation **53/64** on four phrasings after 100 updates | Two phrasings scored 16/16, and two scored 11/16 and 10/16. The read-only audit locates 9/11 misses at the answer-newline decision. The training framework capped this approved run at 100 of its 150-update maximum. See the [candidate report](docs/PHASE-2-P2-11-BALANCED-WORDING-CANDIDATE.md) and [run report](docs/PHASE-2-P2-11-BALANCED-WORDING-RUN.md). |

The v3 corpus contains 56 records (36 training / 20 validation). The separate, owner-approved code-pair corpus contains 36 examples (24 training / 12 validation), balanced across HTML, CSS, and JavaScript, with a fresh 874-entry tokenizer fitted only on its training split. See the [v3 training and scoring report](docs/PHASE-2-TRAINING-CHECK-V3-REPORT.md) and [code-pair preparation and baseline report](docs/PHASE-2-CODE-PAIR-BUILD-REPORT.md).

The original 360-record request-following draft was reviewed and narrowed to an [owner-approved 234-example v3 candidate](docs/PHASE-2-FAILURE-GAP-REVIEW.md). Its corpus, tokenizer, scratch initialization, and two bounded 100-step training checks are recorded. The [saved-checkpoint diagnostic](docs/PHASE-2-SAVED-CHECKPOINT-DIAGNOSTIC.md) evaluated those existing checkpoints without another training run.

The [three-example probe](docs/PHASE-2-THREE-EXAMPLE-PROBE-REPORT.md) learned all three approved training answers exactly by step 25. It used complete-record training and does not establish broader coding ability.

The [sampler audit](docs/PHASE-2-PACKED-WINDOW-EXPOSURE-AUDIT.md) replayed 1,600 production windows: complete examples were present often, but prompts began at inference position zero only 14 times. The [completed P2-03 comparison](docs/PHASE-2-RECORD-START-COMPARISON.md) used record-start windows for 100 steps with the same token budget. It still passed 0/30 development tasks and 0/156 complete seen training answers. The [complete-record follow-up](docs/PHASE-2-COMPLETE-RECORD-COMPARISON.md) learned three seen answers exactly at step 100. Its [bounded continuation to step 200](docs/PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md) reached 52 exact seen answers but still 0/30 development tasks. The source checkpoint is preserved; all 116 training tests passed at that milestone. The subsequent [transfer check](docs/PHASE-2-TRANSFER-DIAGNOSTIC.md) passed six learned originals and none of twelve changed requests. The [binding audit](docs/PHASE-2-BINDING-VARIATION-AUDIT.md) led to the approved [24-example candidate](docs/PHASE-2-BINDING-CANDIDATE-REVIEW.md).

The [binding-diversity comparison](docs/PHASE-2-BINDING-DIVERSITY-RESULT.md) raised supplied-answer learning to 20/24 but left transfer at zero. The answer-focused P2-03 follow-up then reached 23/24 supplied answers while new-binding, reserved-transfer, and development scores remained unchanged at zero; the [P2-04 probe report](docs/PHASE-2-COMPOSITIONAL-BINDING-PROBE.md) records that transition and narrows the next question to recombination rather than basic fitting.

P2-04's approved [compositional-binding run](docs/PHASE-2-COMPOSITIONAL-BINDING-RUN.md) fit all six supplied selector-gap combinations and composed one of three held-out recombinations. P2-05 then counterbalanced the same 3×3 selector-gap space across three fresh-scratch folds. As recorded by the merged [P2-06 design](docs/PHASE-2-P2-06-BINDING-REPRESENTATION.md), P2-05 fit all 18 supplied fold examples but composed only 1/9 fold-local held-outs; six of the nine held-out completions replayed a supplied training solution.

The [P2-06 run report](docs/PHASE-2-P2-06-BINDING-REPRESENTATION-RUN.md) records the three-level results and their limits. The [P2-07 report](docs/PHASE-2-P2-07-INSTRUCTION-INVARIANCE.md) records its crossed phrasing design, approved hashes, bounded run, 24/24 supplied learning, and 4/6 held-out wording result. [P2-08](docs/PHASE-2-P2-08-SELECTOR-FORMAT-RUN.md) records the 63/64 supplied result and formally inconclusive held-out score. [P2-09](docs/PHASE-2-P2-09-ANSWER-BOUNDARY-DIAGNOSTIC.md) records the frozen-checkpoint token audit. The tokenizer remained frozen and the final holdout stayed closed throughout these diagnostics.

The development evaluator uses 30 static tasks. It does not execute JavaScript behavior or browser-backed HTML/CSS checks, and its changing check totals are not a fixed-denominator benchmark. The 60-task final holdout remains unbuilt. The owner-approved final target is at least a 10-percentage-point overall improvement over matching step zero and at least 11/20 tasks passed per language. Those gates have not been met.

## Reports and training instructions

- [Training workspace and commands](training/README.md)
- [Phase 1 experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md)
- [P2-03 complete-record continuation and learning-curve result](docs/PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md)
- [P2-03 completed transfer diagnostic](docs/PHASE-2-TRANSFER-DIAGNOSTIC.md) — step 200 passed 6/6 learned originals and 0/12 variations.
- [P2-03 binding-variation audit and proposed next experiment](docs/PHASE-2-BINDING-VARIATION-AUDIT.md)
- [P2-03 approved 24-example binding-diversity candidate](docs/PHASE-2-BINDING-CANDIDATE-REVIEW.md)
- [P2-03 completed binding-diversity comparison](docs/PHASE-2-BINDING-DIVERSITY-RESULT.md)
- [P2-03 answer-focused comparison preparation](docs/PHASE-2-ANSWER-FOCUSED-COMPARISON-PREP.md)
- [P2-04 compositional-binding probe and P2-03 answer-focused result](docs/PHASE-2-COMPOSITIONAL-BINDING-PROBE.md)
- [P2-04 approved compositional-binding run](docs/PHASE-2-COMPOSITIONAL-BINDING-RUN.md)
- [P2-05 counterbalanced composition diagnostic](docs/PHASE-2-P2-05-COUNTERBALANCED-COMPOSITION.md)
- [P2-06 binding-representation probe](docs/PHASE-2-P2-06-BINDING-REPRESENTATION.md)
- [P2-07 instruction-invariance probe](docs/PHASE-2-P2-07-INSTRUCTION-INVARIANCE.md) — approved bounded run, measured result, and diagnostic limits.
- [P2-08 selector wording/layout run](docs/PHASE-2-P2-08-SELECTOR-FORMAT-RUN.md) — bounded run, convergence gate, measured outcomes, and limits.
- [P2-09 answer-boundary audit](docs/PHASE-2-P2-09-ANSWER-BOUNDARY-DIAGNOSTIC.md) — frozen-checkpoint token ranks and the candidate approval boundary for follow-up training.
- [P2-10 explicit answer-start candidate review](training/phase2/drafts/p2-10-explicit-answer-start-v1/REVIEW.md) — exact approved candidate definition and hashes.
- [P2-10 explicit answer-start run](docs/PHASE-2-P2-10-EXPLICIT-ANSWER-START-RUN.md) — bounded result and next read-only diagnostic.
- [P2-10 wider wording evaluation](docs/PHASE-2-P2-10-WIDER-WORDING-EVALUATION.md) — 64 hash-pinned held-out prompts scored read-only on the existing checkpoint.
- [P2-11 balanced-wording candidate](docs/PHASE-2-P2-11-BALANCED-WORDING-CANDIDATE.md) — hash-pinned 96/64 design and explicit note about prior evaluation prompts promoted to training.
- [P2-11 balanced-wording run](docs/PHASE-2-P2-11-BALANCED-WORDING-RUN.md) — approved bounded result, read-only token audit, and next training-approval boundary.
- [P2-03 original complete-record comparison](docs/PHASE-2-COMPLETE-RECORD-COMPARISON.md)
- [P2-03 milestone review and record-start comparison](docs/PHASE-2-RECORD-START-COMPARISON.md)
- [Phase 2 data-mix review](docs/PHASE-2-DATA-MIX-REVIEW.md)
- [Evaluation design and remaining behavior checks](docs/PHASE-2-EVALUATION-DESIGN.md)
- [Hardware and training limits](docs/HARDWARE-AND-TRAINING-PROFILE.md)
- [Changelog](CHANGELOG.md) — historical implementation entries; the current status above includes later experiment reports and local draft work.

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

P1-12 defines a 27.6-million-parameter decoder-only Transformer, 512-token context, and FP32 AdamW settings. The full configuration and analytic memory estimate are in [`docs/FIRST-EXPERIMENT.md`](docs/FIRST-EXPERIMENT.md). P1-13 is implemented and its original 13 training tests pass on the owner's Windows setup (Python 3.12.10, PyTorch 2.14.0+cu126, CUDA 12.6). The owner completed the [ten-minute CUDA smoke test](docs/SMOKE-TEST-2026-10-03.md): 4,199 steps, 57,327.61 synthetic token positions/second, 734 MiB peak GPU reservation, and about 1.30 GiB peak process RAM. The [two-hour real-data pilot](docs/PLEX-PILOT.md) improved held-out loss from 9.33937 to 6.53100; a [one-step P1-19 continuation](docs/PLEX-RESUME-AND-COMPLETION.md) then verified resume and saved-checkpoint generation. No pretrained weights are used.

## P1-13 local training runner

The separate Python workspace is in [`training/`](training/README.md). It provides commands to inspect the runtime, prepare small local corpora, train, evaluate, generate, and run a bounded synthetic-data smoke test. The owner's ten-minute CUDA smoke test passed. P1-14 is complete for the [approved starter corpus](docs/DATASET-SOURCE-REVIEW.md): 34 training records, 54 validation records, preserved MIT notices, and reproducible provenance, totaling under 1 MiB. See [`docs/DATASET-PIPELINE.md`](docs/DATASET-PIPELINE.md).

## P1-15 Plex tokenizer

The Phase 1 byte-level BPE tokenizer is trained and packaged with the model configuration. It fitted only the approved training text and learned 9,976 token entries within the existing 16,384 model capacity. All 88 records round-tripped exactly; a separate rebuild produced all 11 bundle files byte-identically. The bundle occupies about 0.99 MiB. All 35 training-workspace tests passed at that milestone. Later Phase 2 corpora use separate tokenizers and matching checkpoints. Settings, artifact hashes, and reproduction commands are in the [tokenizer report](docs/PLEX-TOKENIZER.md).

P1-16 created a step-zero random initialization checkpoint tied by hash to this tokenizer. P1-17 then trained from it on one short training record: loss fell from 9.438 to 0.0000224, and greedy decoding reproduced the 16-token sample from a two-token prompt in 250 steps. See the [learning check report](docs/PLEX-LEARNING-CHECK.md). This confirms the basic training path can learn and repeat one memorized sample; it does not measure coding ability. P1-18 completed a two-hour real-data pilot using separate train and held-out validation splits. P1-19 verified a one-step CUDA checkpoint resume and independent CPU generation from the saved Plex weights.

The [P1-18 pilot](docs/PLEX-PILOT.md) ran for 7,200 seconds on the approved BPE corpus: 43,632 updates and 357,433,344 sampled token positions. Held-out loss fell from 9.33937 to 6.53100, reproduced by independent evaluation of the final checkpoint. The [P1-19 resume check](docs/PLEX-RESUME-AND-COMPLETION.md) advanced that checkpoint to step 43,633; its held-out loss was 6.53065, independently reproduced, and a separate CPU command generated a bounded but incorrect completion. The [P1-20 experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md) records these results and their limits: the run validates training infrastructure, not coding ability. Training remains capped while broader data and functional evaluation are planned.

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

For the latest training results and data-review status, see [Current status](#current-status--october-5-2026). The CLI still does not invoke the trained model or apply repository edits. Proposed HTML validation remains scheduled as P3-03 in the [roadmap](Plex-ROADMAP.md).
