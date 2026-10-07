# 🧪 Changelog

---

## 🚧 Unreleased

_🗓️ Updated October 4, 2026_

### 🧬 Phase 2 — data and training experiments

- Completed the approved **234-example request-following v3** experiment: 156 training / 78 validation records, a fresh 1,509-entry tokenizer fitted on training text only, and a new random initialization. The 100-step CUDA run reduced held-out loss from **7.45021 to 3.28499**, but complete development tasks remained **0/30**, matching step zero. Truncated responses fell from 30/30 to 0/30. See the [v3 result report](docs/PHASE-2-FAILURE-GAP-100-STEP-REPORT.md).
- Reviewed the 180-example model's development failures and prepared the subsequently approved v3 corpus. Replaced repeated CSS selectors and JavaScript function names and added **54 examples** covering navigation, forms, multi-part content, layout, states, sizing, arrays, strings, and objects. Kept related examples together across 38 split groups. All 234 supplied answers passed 1,007 static checks; these checks assess dataset preparation, not model capability. See the [failure review and data changes](docs/PHASE-2-FAILURE-GAP-REVIEW.md).
- Completed the approved **180-example curated request-following** experiment: 120 training / 60 validation records and a fresh 1,064-entry tokenizer. Its 100-step CUDA run reduced held-out loss from **7.08272 to 2.69697**, but complete development tasks remained **0/30**, matching step zero. Truncated responses fell from 26/30 to 0/30. See the [curated experiment report](docs/PHASE-2-CURATED-100-STEP-REPORT.md).
- Curated the earlier 360-record draft into those 180 examples by removing rename-only variants, replacing weak profiles, and adding HTML tree and exact CSS declaration checks. Recorded approval for the exact curated records separately from the twelve previously approved expansion samples. Preserved the original review snapshots and earlier corpora. See the [curation and approval history](docs/PHASE-2-CURATED-DATA-APPROVAL.md).
- Completed the approved **36-example code-pair** diagnostic using 24 training / 12 validation records and an 874-entry tokenizer. The ten-minute run reached 3,197 updates; complete tasks remained **0/30**, while truncations fell from 28/30 to 0/30. Held-out loss worsened from **6.89080 to 8.42534**, consistent with overfitting on the tiny corpus. See the [build and baseline](docs/PHASE-2-CODE-PAIR-BUILD-REPORT.md) and [matched diagnostic results](docs/PHASE-2-CODE-PAIR-10M-REPORT.md).
- Built the earlier **56-record mixed-source P2 v3 corpus** with the approved nine-example authored supplement, a 36/20 split, and a matching tokenizer. Its ten-minute training check reached 922 updates and reduced held-out loss from **9.1694 to 6.4759**. Both step zero and the trained checkpoint passed **0/30** complete development tasks; all 30 trained outputs were truncated. This mixed-source v3 corpus is separate from the later 234-record request-following v3 corpus. See the [dataset report](docs/PHASE-2-DATASET-V3-REPORT.md) and [training and scoring report](docs/PHASE-2-TRAINING-CHECK-V3-REPORT.md).

### 🔍 Reproducibility and documentation

- Added approval-bound source promotion, candidate validation, and tokenizer-bundle checks for the curated and expanded request-following datasets. Checks cover exact source identities, grouped splits, inference prefixes, packed EOS boundaries, tokenizer roundtrips, context limits, and answer caps. Recorded separate dataset, tokenizer, initialization, checkpoint, and response hashes for each experiment.
- Recorded data-mix measurements: the mixed-source v3 training split was 76.3% Markdown by tokenizer positions; answers occupy only 22.6% and 23.1% of the later 180- and 234-example training splits, respectively. These small, prompt-heavy corpora do not establish sufficient scratch-pretraining coverage. See the [data-mix review](docs/PHASE-2-DATA-MIX-REVIEW.md) and experiment reports above.
- Updated the README with the Plex Base project description, measured experiment results, capability limits, and report links. Later experiment reports and this changelog supersede its earlier draft-status snapshot.

### 🧭 Current limits and next experiment

> ⚠️ **Reality check:** All completed Phase 2 experiments still score **0/30 complete tasks** on the static development set. Lower next-token loss and fewer truncated outputs have not established useful coding ability. Static-check totals vary with truncation, so their raw fractions are not a fixed-denominator benchmark. JavaScript behavior and browser-backed HTML/CSS checks remain unavailable; the 60-task final holdout remains unbuilt and unused.

> 🔭 **Up next:** The next planned comparison addresses answer learning on the approved 234-record corpus with an answer-weighted objective or a controlled format change. No completed answer-weighted experiment is recorded here. Longer training remains deferred; the $0 paid-services and 200 GiB storage limits remain in force. See the [roadmap](Plex-ROADMAP.md).

---

## 🏗️ 0.1.0 — Development scaffold

The entries below record earlier milestones. Pending-work statements and test counts describe those milestones, not the latest project status.

### 📚 Phase 2 data preparation

- Collected the owner-approved, hash-pinned 34-file Microsoft P1-14 subset and a 13-file MDN `learning-area` selection into a new family-stratified P2 dataset; fit a new tokenizer using its training split only. Recorded exact paths, notices, split assignments, hashes, and the documentation-heavy mix in [the P2 data collection review](docs/PHASE-2-DATA-COLLECTION-REVIEW.md). P1 artifacts remain unchanged. Added P2-01's approved +10-percentage-point overall / 11-of-20-per-language gate, 30 owner-authored development tasks, and deterministic development-response generation/scoring commands. The 60-task final set, JavaScript behavior isolation, and corpus-mix review remain open; no P2 model training has started.

### 🏋️ Phase 1 training and evaluation

- Completed P1-20's experiment report in [docs/PLEX-EXPERIMENT-REPORT-P1-20.md](docs/PLEX-EXPERIMENT-REPORT-P1-20.md). It records the 120-minute scratch-training pilot, held-out loss change, resource use, checkpoint continuation, and an incorrect CPU-generated completion. The result validates the local training/checkpoint path, not coding ability. Keep the current training cap while planning broader reviewed data and functional evaluation.
- Completed P1-19's bounded resume/completion gate. A one-step CUDA continuation of the completed P1-18 checkpoint advanced from step 43,632 to 43,633 without overwriting the pilot; its original SHA-256 remained unchanged. Held-out loss was 6.530651337759835 and independent evaluation matched. The new checkpoint saves model, optimizer, RNG, fixed schedule, settings, progress, and provenance alongside a copied tokenizer bundle. A separate CPU command generated a bounded BPE completion from the saved weights. Fixed CUDA RNG restoration, and all 46 training tests pass. The sample was incomplete; no uncapped training command is enabled.
- Completed P1-18's 120-minute CUDA pilot from Plex's P1-16 random initialization. The run saved a tokenizer-linked checkpoint after 43,632 updates and 357,433,344 sampled token positions; held-out loss improved from 9.33937 to 6.53100, independently reproduced from the final checkpoint. Peak GPU reservation was 878,706,688 bytes and peak process working set was 1,397,129,216 bytes. The small corpus limits quality claims; P1-19 later verified checkpoint resume and generation.
- Completed P1-15 with a scratch-fitted byte-level BPE tokenizer using only approved training text, pinned Tokenizers 0.23.2, packaged model/settings/provenance/license files, and encoded train/validation corpora. Learned 9,976 entries; all 88 records round-trip exactly and all 11 bundle files reproduce byte-identically. Added bootstrap codec safeguards and tokenizer integrity/holdout/storage tests; all 35 training-workspace tests pass. Random initialization and real-data learning remain upcoming milestones.
- Completed P1-16 with a 27.6M-parameter step-zero checkpoint seeded at 1337 and linked to the P1-15 tokenizer. Recorded the scheme, software versions, model/tokenizer configuration, and weight/checkpoint hashes; pretrained weights were not loaded and no training steps were run.
- Completed P1-17's bounded learning check from the P1-16 checkpoint. One approved 16-token BPE training sample reached 0.0000224 loss and 100% next-token accuracy after 250 updates; greedy decoding reproduced it from a two-token prompt. Saved a tokenizer-linked checkpoint with optimizer state and a result report. This is a one-sample learning demonstration, not a coding-capability result.
- Prepared P1-18's tokenizer-aware, 120-minute-capped training and held-out evaluation commands. Bound checkpoints to tokenizer and both split hashes, masked unused vocabulary IDs, and ran a one-step full-corpus preflight with matching independent validation loss. Added pilot integrity tests; all 39 training-workspace tests passed at that milestone.
- Recorded the owner's successful ten-minute CUDA smoke result: 4,199 steps, 734 MiB peak GPU reservation, about 1.30 GiB process peak RAM, and a 330,894,811-byte checkpoint. Retained the raw result and updated measured-fit status.
- Completed P1-14's owner-approved starter corpus from two pinned MIT source subsets: 34 training records, 54 validation records, 746,848 packaged bytes, preserved license notices, and an identical second build. Added a bounded hash-verifying text downloader, approved source catalog, source lock, and review/build report; all 25 training-workspace tests passed. Fixed the advertised .cjs extension allowlist.

### 🧱 Project and training foundations

- Began P1-11 with a read-only Windows hardware collector and a separate training/inference profile template.
- Recorded the owner-provided CPU, RAM, GPU/VRAM, and free-drive inventory plus limits: 200 GiB storage, $0 paid services, a 10-minute smoke test, a two-hour pilot, and longer runs with resumable checkpoints.
- Started P1-12 with a documented 27.6M-parameter random-initialized experiment proposal, training settings, and analytic memory estimate; runtime measurements await the P1-13 training runner.
- Completed the P1-13 local Python runner for synthetic smoke testing, local corpus preparation, bounded training, evaluation, generation, and Plex-owned checkpoints. Owner Windows verification: Python 3.12.10, PyTorch 2.14.0+cu126, CUDA 12.6 available on an RTX 4080 SUPER; all 13 training tests pass. The 10-minute resource-fit smoke test remains pending.
- Implemented the P1-14 offline local-source curation command, license-review gate, text/secret/syntax filters, normalized exact deduplication, deterministic repository-grouped splits, and provenance manifests.
- Replaced the previous post-P1-10 plan with `Plex-ROADMAP.md`, establishing Plex’s scratch-trained, randomly initialized model goal and keeping Qwen as an optional evaluation baseline.

### 🛠️ Original CLI and editing pipeline

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
