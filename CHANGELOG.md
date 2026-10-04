# Changelog

## 0.1.0 — development scaffold

- Completed P1-15 with a scratch-fitted byte-level BPE tokenizer using only approved training text, pinned Tokenizers 0.23.2, packaged model/settings/provenance/license files, and encoded train/validation corpora. Learned 9,976 entries; all 88 records round-trip exactly and all 11 bundle files reproduce byte-identically. Added bootstrap codec safeguards and tokenizer integrity/holdout/storage tests; all 35 training-workspace tests pass. Random initialization and real-data learning remain upcoming milestones.
- Completed P1-16 with a 27.6M-parameter step-zero checkpoint seeded at 1337 and linked to the P1-15 tokenizer. Recorded the scheme, software versions, model/tokenizer configuration, and weight/checkpoint hashes; pretrained weights were not loaded and no training steps were run. Next is tokenizer-aware tiny-sample learning (P1-17).

- Recorded the owner's successful ten-minute CUDA smoke result: 4,199 steps, 734 MiB peak GPU reservation, about 1.30 GiB process peak RAM, and a 330,894,811-byte checkpoint. Retained the raw result and updated measured-fit status; real-data pilot remains pending.
- Completed P1-14's owner-approved starter corpus from two pinned MIT source subsets: 34 training records, 54 validation records, 746,848 packaged bytes, preserved license notices, and an identical second build. Added a bounded hash-verifying text downloader, approved source catalog, source lock, and review/build report; all 25 training-workspace tests passed. Fixed the advertised .cjs extension allowlist.

- Began P1-11 with a read-only Windows hardware collector and a separate training/inference profile template.
- Recorded the owner-provided CPU, RAM, GPU/VRAM, and free-drive inventory plus limits: 200 GiB storage, $0 paid services, a 10-minute smoke test, a two-hour pilot, and longer runs with resumable checkpoints.
- Started P1-12 with a documented 27.6M-parameter random-initialized experiment proposal, training settings, and analytic memory estimate; runtime measurements await the P1-13 training runner.
- Completed the P1-13 local Python runner for synthetic smoke testing, local corpus preparation, bounded training, evaluation, generation, and Plex-owned checkpoints. Owner Windows verification: Python 3.12.10, PyTorch 2.14.0+cu126, CUDA 12.6 available on an RTX 4080 SUPER; all 13 training tests pass. The 10-minute resource-fit smoke test remains pending.
- Implemented the P1-14 offline local-source curation command, license-review gate, text/secret/syntax filters, normalized exact deduplication, deterministic repository-grouped splits, and provenance manifests.
- Replaced the previous post-P1-10 plan with `Plex-ROADMAP.md`, establishing Plex’s scratch-trained, randomly initialized model goal and keeping Qwen as an optional evaluation baseline.
- Added P1-10 in-memory UTF-8 proposals and unified diffs, preserving original BOM/line endings and unchanged bytes, with file/diff/changed-line limits and a pinned `diff` dependency.
- Added P1-09 selected-path validation, unique anchor and editable-span checks, overlap rejection, and stale-file rechecks before accepting located edits.
- Added P1-08 bounded strict JSON response parsing, duplicate-key rejection, canonical schema enforcement, sanitized failure codes, and parser regression tests.
- Added P1-07 focused prompt assembly, selected-file byte/hash/BOM/newline snapshots, full-file edit spans, budget accounting, stale-snapshot checks, and packaged system rules.
- Added P1-06 deterministic file ranking with inspectable signals, bounded UTF-8 source inspection, explicit target hints, ambiguity refusal, and CLI ranking output.
- Added P1-05 bounded Git/directory enumeration, nested ignore handling, hard exclusions, link/submodule protection, source metadata display, and scanner regression tests.
- Added P1-04 explicit, Git, and non-Git project-root detection, the CLI `--repo` option, and boundary/error tests.
- Added P1-03 HTML/CSS/JavaScript fixture, initial title/reference assertions, and SHA-256 baselines for all three files. CLI tests verify temporary fixture copies remain unchanged.
- Added P1-02 request, repository manifest, model response, and preview result contracts with strict Ajv validation and contract tests.
- Added the P1-01 TypeScript build and npm `plex` executable entry.
- Added help/version commands, explicit unsupported task reporting, and CLI integration tests.
- Documented local Windows setup and the remaining implementation scope.
