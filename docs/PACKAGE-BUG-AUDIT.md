# Plex Nano package bug list

Audit date: 2026-10-08 (local date).
Reviewed revision: `936a01c2585e97d3656f068d7b210a37e56b8046` (`master`).

## Scope and evidence

This is a broad source review of the package, not a new experiment or a claim that every execution path has been exercised. It covers the current file-conditioned contract, shared model/training/checkpoint code, corpus and contamination tooling, completion, CI, package metadata, documentation, and legacy TypeScript parsing/context/proposal utilities. Historical experiment implementations were sampled; their recorded numeric results were not rerun or changed.

The intended product remains a small coding model that changes **caller-supplied** HTML, CSS, and JavaScript. This report does not propose repository discovery or autonomous Git features, a model-size change, or new training authorization.

**24 tracked items: 15 code defects, 6 verification gaps, and 3 maintenance/follow-up items.** Code defects below are supported by source paths and concrete triggering conditions. They are static findings, not newly executed reproductions. Proposed regression checks are future work. No tests, training, optimizer steps, checkpoint staging, or final-holdout inspection were performed for this report. Only this document was added.

Prior P3 corrections are not counted again: frozen candidate identity, the corrected first edit, tokenizer provenance checks, strict authorization fields, and the root-relative CLI defaults are present in the reviewed revision.

Priority: P1 = possible loss of research artifacts or misleading integrity gate; P2 = incorrect behavior or important verification gap; P3 = limited validation/maintenance issue. Priorities reflect the triggering condition, not a claim that existing historical results are invalid.

## Triage index

| ID | Priority | Area | Finding |
|---|---|---|---|
| B01 | P1 | Dataset weights | One extra dataset row can be silently skipped |
| B02 | P1 | Contamination | Missing usable protection can still produce a pass |
| B03 | P2 | Contamination | Shared interior substrings are not detected |
| B04 | P2 | Evidence | Contamination report does not fingerprint scanned corpus/protected contents |
| B05 | P1 | Resume | Existing unrelated checkpoint can be overwritten |
| B06 | P1 | Runner outputs | Metrics and checkpoint may name the same file |
| B07 | P2 | Training | Nonfinite loss/gradients do not stop the shared update path |
| B08 | P2 | Completion | Oversized token prompts silently lose their beginning |
| B09 | P2 | Storage | Checkpoint quota is checked after serialization has consumed space |
| B10 | P2 | P3 outputs | Output paths can overwrite inputs or each other through aliases |
| B11 | P2 | P3 generation | Candidate and review publication can leave a mismatched pair |
| B12 | P3 | Model configuration | Noninteger dimensions pass configuration validation |
| B13 | P3 | Model loss | Explicit zero loss vocabulary silently selects the full vocabulary |
| B14 | P3 | Contamination input | Valid JSON scalars/lists cause an unhandled attribute error |
| B15 | P3 | Checkpoint schema | Boolean version/step values pass integer checks |
| G01 | P2 | CI | Current P3 test module is omitted |
| G02 | P2 | CI | Direct pushes to master do not trigger the workflow |
| G03 | P2 | CI | Broad existing Python coverage is omitted |
| G04 | P2 | CI | Legacy TypeScript checks have no repository workflow |
| G05 | P2 | Portability | Workflow exercises Linux only despite Windows use |
| G06 | P3 | CI triggers | Root line-ending policy changes do not trigger training checks |
| M01 | P3 | CLI wording | Legacy help exposes an unexplained historical milestone |
| M02 | P3 | P3 scorer | Frozen-row precondition should be enforced or explicitly internal |
| M03 | P3 | Completion | Prompt eviction during generation needs an explicit policy |

## Code defects

### B01 — One extra dataset row can escape the answer-weighting verifier

**Location:** `training/src/plex_training/answer_weighting.py:42`, and the `stream.readline()` check after the loop.

**Evidence:** The loop is `zip(stream, entries)`. On its terminating iteration, Python advances the first iterator before learning that the second iterator is exhausted. If the JSONL has exactly one more row than the index, that extra row has already been consumed when `stream.readline()` checks for leftovers. The final record-count check compares against the index, not the full dataset.

**Trigger/impact:** An N-entry index/token file with an N+1-row JSONL, and a matching hash for that JSONL, can pass. The reported dataset hash then covers text not represented in the weights or packed corpus. This is a verification defect; it does not prove any committed corpus has that shape.

**Suggested fix/check:** Use `zip_longest` with an explicit sentinel and reject either unmatched side. Cover N-1, N, N+1, and N+2 rows, especially N+1.

### B02 — Contamination checking fails open when protection is unusable

**Location:** `training/src/plex_training/web_contamination.py:54`, `:82`, `:203`.

**Evidence:** `_protected_segments` returns an empty list for oversized files, unreadable files, and invalid UTF-8. An empty configured directory also yields no protected files. All strings shorter than the minimum are removed. The pass expression checks only whether matches were found; it does not require usable protection or complete reads.

**Trigger/impact:** A nonempty corpus can receive `passed: true` with zero protected segments. If just one of several protected files is skipped, the report can pass with incomplete coverage too. `protectedFilesScanned` counts discovered files, including ones whose contents were skipped.

**Suggested fix/check:** Record explicit read/skip results, fail on unexpected unreadable/oversized protection, and require predeclared minimum coverage. Test empty directories, invalid UTF-8, oversized files, and mixed successful/failed reads using synthetic files only.

### B03 — The substring detector misses an overlap inside both strings

**Location:** `training/src/plex_training/web_contamination.py:192`.

**Evidence:** The comparison is `segment in text` or `text in segment`. This detects whole-string containment, not a shared substring of the configured minimum length.

**Trigger/impact:** Let S be a shared 120-character passage. Protected text `A + S + B` and corpus text `C + S + D`, with different prefixes/suffixes, evade the check even though they share S. The `minimumSubstringCharacters` setting and `substringMatches` report suggest broader coverage than is implemented.

**Suggested fix/check:** Implement bounded shared-window matching after normalization, or explicitly rename/document the detector as whole-segment containment. Test interior overlap, exact threshold, below threshold, and containment. Avoid a quadratic unbounded search.

### B04 — A contamination result cannot identify all bytes it assessed

**Location:** `training/src/plex_training/web_contamination.py:107`, `:209`.

**Evidence:** The scanner reads train/validation JSONL directly and records the manifest hash. It neither verifies these reads against manifest content hashes here nor records hashes of the scanned corpus files, protected configuration, or protected file contents.

**Trigger/impact:** Changing corpus or protected content while retaining the manifest leaves the same manifest identity in a new report. A saved report alone cannot establish which bytes were checked. This is an auditability defect; no downstream reuse of a stale report was demonstrated.

**Suggested fix/check:** Record hashes for all effective inputs and scanner settings/version, and verify manifest-to-file consistency where declared. Check that changing each input changes the report identity. Preserve existing historical reports and version the improved schema.

### B05 — Resume allows replacing a different existing checkpoint

**Location:** `training/src/plex_training/runner.py:290`, `:431`, `:463`.

**Evidence:** Existing checkpoint/metrics protection only applies when `resume_from is None`. Resume later calls checkpoint saving with `overwrite=output_checkpoint.exists()`. There is no corresponding check that an existing destination belongs to this resumed run.

**Trigger/impact:** Resuming checkpoint A while selecting an existing checkpoint B as the output permits replacing B. Selecting an existing unrelated metrics file also appends a second run's events without an ownership check. Artifact-root containment does not prevent collisions within the root.

**Suggested fix/check:** Permit overwrite only for an explicitly established continuation destination, or require a new destination. Bind metrics to a run identity. Mock checkpoint I/O and optimizer work when checking this guard; no training is needed to exercise argument validation.

### B06 — Metrics and checkpoint destinations can be identical

**Location:** `training/src/plex_training/runner.py:288`, `:389`, `:461`, `:498`.

**Evidence:** Both paths are independently constrained to the artifact root but never required to differ. A fresh run accepts the same nonexistent path for both. Metrics create that file, checkpoint saving replaces it, and later metrics append to it.

**Trigger/impact:** One destination cannot reliably serve as both a JSONL event log and a binary checkpoint. Log history is replaced and checkpoint bytes receive appended event text. Do not assume every loader will reject trailing bytes; the definite defect is loss of the separate artifact contracts.

**Suggested fix/check:** Compare canonical paths before creating outputs or loading a model. Reject equality and filesystem aliases. Cover fresh and resume entry points using mocked execution.

### B07 — Shared training updates do not stop on nonfinite values

**Location:** `training/src/plex_training/runner.py:59` (especially the backward, clipping, and optimizer calls near `:98`).

**Evidence:** `_training_step` checks for a missing loss, but not a nonfinite loss. Gradient clipping uses its default nonfinite behavior, and the optimizer is then stepped unconditionally.

**Trigger/impact:** A NaN/Inf loss or gradient can contaminate parameters and optimizer state and later be persisted. This finding concerns the shared runner; it does not assert that every separate historical trainer lacks its own guards or that an existing run diverged.

**Suggested fix/check:** Reject nonfinite loss before backward; reject nonfinite gradient norm before updating; record a failure event without replacing the last good checkpoint. Validate with fake loss/gradient objects and a spy optimizer before any real run is authorized.

### B08 — Completion silently truncates an oversized supplied prompt

**Location:** `training/src/plex_training/completion.py:62`, `:87`, `:101`.

**Evidence:** The public entry point limits UTF-8 bytes to 4096 but does not enforce the model's token context. Generation slices to the last `context_length` tokens from the first step. The returned report includes the original full prompt without a truncation field.

**Trigger/impact:** A byte-valid prompt encoding to more than 512 tokens loses its beginning. That beginning may contain the coding request or relevant supplied-file context. Reported input and effective model input differ without explanation.

**Suggested fix/check:** Reject oversized tokenized prompts with actual/allowed counts, or require an explicit truncation policy and report the exact effective input. Use a fake model that records input IDs for boundary checks.

### B09 — The storage guard permits temporary over-allocation

**Location:** `training/src/plex_training/artifacts.py:63`.

**Evidence:** Before `torch.save`, the writer reserves/checks only one extra byte. The full temporary checkpoint is serialized and synced before actual storage usage is checked.

**Trigger/impact:** With less free allocation than one checkpoint needs, the write can exceed the configured allocation or encounter disk exhaustion before the guard rejects it. Exception cleanup reduces lasting damage but does not prevent the peak allocation.

**Suggested fix/check:** Preflight a conservative size reservation or use a counting/bounded writer, accounting for the old checkpoint plus temporary replacement. Test bounded fake serialization; large real checkpoints are unnecessary.

### B10 — P3 outputs can collide with protected inputs or path aliases

**Location:** `training/src/plex_training/file_conditioned_contract.py:190`, `:278`.

**Evidence:** Generation only compares candidate/review using `Path.absolute()`, then writes both. It does not protect the contract path. Review writes `report_path` after reading inputs without requiring it to differ from the candidate, review metadata, contract, or tokenizer inputs. `absolute()` is also not a complete filesystem-alias check.

**Trigger/impact:** Passing the contract as a generation output overwrites it after successful validation. Passing the candidate as the review report overwrites the candidate with the resulting report. Aliased output paths can overwrite one another despite a textual inequality check.

**Suggested fix/check:** Canonicalize and compare all input/output paths before reading or writing; reject existing-file aliases with same-file checks where supported. Keep overwrite policy explicit. Exercise collisions in a temporary synthetic workspace only.

### B11 — P3 generation can leave candidate and review metadata out of sync

**Location:** `training/src/plex_training/file_conditioned_contract.py:199`, `:205`.

**Evidence:** Candidate bytes are written directly before creating/writing the review destination. There is no staging or recovery across the two outputs, and writes truncate existing targets.

**Trigger/impact:** If the second destination cannot be created/written, the operation raises after replacing the candidate. The previous review metadata may remain beside new candidate bytes, or a partial file may remain after interruption. Consumers' hash checks can reject this, but the preparation operation still leaves a broken artifact pair.

**Suggested fix/check:** Preflight both destinations and stage complete files before publishing, with an explicit recovery strategy for paired publication. Inject failure on the second write and confirm prior artifacts remain usable or the incomplete state is clearly recorded.

### B12 — Model configuration accepts dimensions that are not integers

**Location:** `training/src/plex_training/config.py:19`.

**Evidence:** Positive dimensions are checked with `value <= 0`; divisibility and dropout are checked separately. There is no strict integer check for the dimension fields. For example, a positive fractional `layers` value passes these checks, as can a boolean context length.

**Trigger/impact:** Invalid configuration objects reach model construction or parameter arithmetic and fail later with unrelated errors or misleading counts. Default controlled configuration is unaffected.

**Suggested fix/check:** Require exact integers for dimension fields before arithmetic, rejecting booleans. Keep the controlled model size unchanged. Cover floats, booleans, strings, zero, and negative values through both constructor and `from_dict`.

### B13 — Zero loss vocabulary bypasses the intended range validation

**Location:** `training/src/plex_training/model.py:108`.

**Evidence:** `loss_vocabulary_size or self.config.vocab_size` converts explicit zero to the full vocabulary before the `1 <= vocabulary_size` check.

**Trigger/impact:** A caller's invalid zero value silently changes the loss objective instead of failing. `False` follows the same route. Ordinary valid callers are unaffected.

**Suggested fix/check:** Default only when the argument is `None`; validate exact integer type and bounds otherwise. Check that zero is rejected and `None` retains the normal objective.

### B14 — Contamination JSONL rows are used before checking object type

**Location:** `training/src/plex_training/web_contamination.py:117`.

**Evidence:** After `json.loads`, the code immediately calls `row.get`. JSON `null`, arrays, strings, and numbers are syntactically valid but have no appropriate `.get` method.

**Trigger/impact:** A malformed row produces an attribute error instead of the scanner's filename/line-number validation error. This is a diagnostic failure, not a false clean result.

**Suggested fix/check:** Require a dictionary before accessing fields and return the same contextual `ValueError` used for other malformed records. Cover every nonobject JSON type.

### B15 — Checkpoint schema accepts booleans as version and step

**Location:** `training/src/plex_training/checkpoint.py:80` (version and step checks).

**Evidence:** `True == 1`, so the version comparison accepts a boolean. `isinstance(True, int)` also makes a boolean step acceptable to this reader.

**Trigger/impact:** Malformed metadata passes the common checkpoint reader. Completion has a stricter step check later, so behavior differs by consumer. This is a narrow schema defect, not proof that generated checkpoints contain booleans.

**Suggested fix/check:** Require exact integer types before comparing values. Check the common reader and all metadata consumers consistently without rewriting historical valid artifacts.

## Verification gaps — not additional runtime defects

### G01 — P3 contract tests are absent from CI

**Location:** `.github/workflows/training-tests.yml:28`.

The explicit pytest list omits `training/tests/test_file_conditioned_contract.py`, although P3-01 is the current completed milestone. A pull request can pass this workflow without running the current contract's dedicated tests. Add that module to the portable suite and require it for relevant changes.

### G02 — Direct master pushes have no automated check trigger

**Location:** `.github/workflows/training-tests.yml:3`.

The workflow declares `pull_request` and `workflow_dispatch`, with no `push` event. A direct sync/commit to master therefore does not automatically run it. This is a repository configuration observation; remote branch-protection settings were not inspected. Add an appropriate protected-branch push trigger if direct syncs remain part of the workflow.

### G03 — CI leaves 36 of 62 Python test modules unselected

**Location:** `.github/workflows/training-tests.yml:28`; `training/tests/`.

Inventory comparison found 62 top-level `test_*.py` files, of which the explicit workflow selects 26. Besides the P3 omission tracked separately, omissions include model, config, answer weighting, complete records, record sampling, dataset, benchmark, source fetch, tokenizer review, and all five web corpus/source/materialization/contamination modules. Existing coverage is broader than enforced coverage.

Review the omitted tests for portability, training side effects, and intentional exclusions. Define a portable required suite and a separately authorized experiment suite. Do not indiscriminately run historical training tests as a remedy. The counts describe selected filenames, not executed test cases or a coverage percentage.

### G04 — TypeScript checks have no repository CI workflow

**Location:** `package.json:22`; `.github/workflows/`.

The package defines TypeScript build and tests, but the only repository workflow found is the Python training workflow. Changes in legacy parsing, context, and proposal code lack a repository-provided automated check. Add a narrow maintenance check if this scaffolding remains supported; do not expand it into the product direction.

### G05 — Windows behavior is not exercised by the workflow

**Location:** `.github/workflows/training-tests.yml:16`.

The workflow uses Ubuntu only. The working environment is Windows, and the package handles paths, line endings, file replacement, and memory-mapped data. This is a portability coverage gap, not a claim that all of those operations currently fail. Add a small Windows subset around artifact handling, P3 identities, and CLI defaults without authorizing research training.

### G06 — Root line-ending policy changes do not trigger training CI

**Location:** `.github/workflows/training-tests.yml:5`; `.gitattributes`.

The pull-request path filter only includes `training/**` and the workflow itself. A `.gitattributes`-only change can affect checkout bytes of hash-pinned artifacts without running the checks. Include relevant root policy/configuration files in the trigger filter.

## Maintenance and follow-up items — not counted as confirmed bugs

### M01 — Legacy CLI help needs clearer context

**Location:** `src/cli/main.ts:17`; `package.json:10`.

The `plex` executable routes to legacy TypeScript scaffolding whose help says `Development status: P1-10 proposed buffers and unified diffs.` Current documentation describes Phase 3 of the coding model. The historical label may be valid for that scaffolding, but it needs an explicit legacy qualifier and a pointer to current model commands. Do not rename historical milestones or build new repository-agent features to resolve this wording issue.

### M02 — The P3 scorer relies on an unenforced frozen-row precondition

**Location:** `training/src/plex_training/file_conditioned_contract.py:110`.

The helper documents that it is for frozen fixtures only. It validates a replacement relation but does not itself verify full row equality against the frozen fixture. A custom row retaining a known ID and replacement can receive `known-valid-target` without the original fixture's syntax. Validated current callers remain within the documented precondition, so this is listed as API hardening rather than a proven current evaluation failure. Make the helper internal or enforce frozen identity before asserting known validity.

### M03 — Specify what happens when generation evicts supplied context

**Location:** `training/src/plex_training/completion.py:62`.

Even an initially valid 512-token prompt starts losing prefix tokens once generation extends it. Sliding-window decoding is a legitimate implementation choice; it is not independently counted as a bug. For file-conditioned work, explicitly define whether prompt plus requested output must fit the context, whether eviction is allowed, and what the report records. Keep this separate from B08's undisclosed initial truncation.

## Suggested repair order

1. Protect artifact ownership and path separation: B05, B06, B10, B11.
2. Restore trustworthy corpus/evaluation gates: B01–B04.
3. Guard numerical failure, effective prompt context, and storage: B07–B09.
4. Tighten small validation inconsistencies: B12–B15.
5. Add deliberately scoped CI coverage: G01–G06.
6. Resolve API/documentation follow-ups: M01–M03.

Each fix should receive a small synthetic regression check when testing is authorized. Data checks should use synthetic fixtures, not the closed final holdout. Training authorization remains separate from code changes, preparation, diagnostics, and evaluation.

## Review limits and non-findings

- No checkpoint was loaded or trained, no historical experiment was replayed, and no current capability score was measured.
- Dependency vulnerability databases, remote branch rules, GPU behavior, packaging installation, and live network source fetches were not audited.
- Legacy TypeScript parsing/context/proposal code was reviewed without establishing a new confirmed defect; speculative forged-object scenarios are not included as bugs.
- Roadmap completion wording alone is not evidence of solved semantic transfer. Existing documented failed results remain historical evidence.
- The P3 draft is a small contract fixture set, not a generalization benchmark. Its size and exact-match scoring are scope choices, not defects by themselves.
- This list is a prioritized review backlog, not proof that every listed trigger has occurred in a saved run, nor a guarantee that no other defects remain.
