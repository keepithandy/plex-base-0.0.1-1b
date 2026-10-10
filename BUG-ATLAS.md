# 🐛 Plex Nano — Bug Atlas

> **Fix tracker** · Confirmed defects and their regression evidence across the Plex training and file-conditioned coding workspaces.

> [!TIP]
> **Atlas status:** 🟢 **15 complete** · 🔴 **0 open**
>
> **Priority mix:** 🔴 4 P1 · 🟠 7 P2 · 🔵 4 P3
>
> Each entry keeps the original failure mode, required regression coverage, resolution, and verification record together.

## 🗂️ Issue overview

**Status key:** 🔴 **OPEN** — confirmed and not fully verified as fixed · 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/answer_weighting.py` | Exact dataset/index cardinality is now enforced. |
| **B02** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Protection coverage and directory discovery now fail closed. |
| **B03** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Interior shared substrings at the configured threshold are now detected. |
| **B04** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Contamination reports now fingerprint exact effective inputs and verify declared split hashes. |
| **B05** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/runner.py` | Resume enforces artifact ownership and safe metrics record boundaries. |
| **B06** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/runner.py` | Destination checks reject Windows aliases and checkpoint staging collisions before model work. |
| **B07** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/runner.py` | Shared training updates now fail closed on nonfinite loss or gradient norm. |
| **B08** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/completion.py` | Completion rejects prompts that exceed model token context instead of truncating silently. |
| **B09** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/artifacts.py` | Checkpoint serialization now enforces storage allocation before temporary writes exceed it. |
| **B10** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/file_conditioned_contract.py` | P3 outputs cannot overwrite protected inputs or collide through canonical/filesystem aliases. |
| **B11** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/file_conditioned_contract.py` | P3 candidate and review metadata now publish as a staged, recoverable coordinated pair. |
| **B12** | **P3** | 🟢 **COMPLETE** | `training/src/plex_training/config.py` | Model dimension fields now require exact positive integers and reject booleans/non-integers. |
| **B13** | **P3** | 🟢 **COMPLETE** | `training/src/plex_training/model.py` | Loss vocabulary defaults only on `None`; explicit values now require exact integer type and valid bounds. |
| **B14** | **P3** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Contamination JSONL rows now require JSON objects before field access, with split/line diagnostics. |
| **B15** | **P3** | 🟢 **COMPLETE** | `training/src/plex_training/checkpoint.py` | Checkpoint format version and step now require exact integer types before schema/range validation. |

---

## 🔧 B01 — Answer-weighting dataset/index cardinality

**Priority:** P1  
**Type:** Code defect / verification defect

The verifier previously iterated with `zip(stream, entries)` and then checked `stream.readline()` for leftovers. With exactly one extra JSONL row, `zip` could advance the stream to that unmatched row before discovering that the index iterator was exhausted, causing the later leftover check to miss it.

Required regression coverage:

- N-1 JSONL rows
- N JSONL rows
- N+1 JSONL rows
- N+2 JSONL rows

### Resolution

🟢 **COMPLETE**

Fixed by replacing `zip(stream, entries)` plus the trailing `readline()` check with `zip_longest(..., fillvalue=sentinel)` and explicit rejection of either unmatched side.

Verified cases:

- N-1 rows: rejected
- N rows: accepted
- N+1 rows: rejected
- N+2 rows: rejected

The answer-weighting regression module is now included in the repository CI suite.

Verification run:

- **159 passed**
- **2 skipped**
- **1 warning**

---

## 🔧 B02 — Contamination protection coverage

**Priority:** P1  
**Type:** Code defect / verification defect

The contamination scanner previously allowed `passed: true` when no usable protected segment was scanned. Oversized, unreadable, and invalid UTF-8 protected files were silently converted to empty segment lists; an empty protected directory also produced no protection. `protectedFilesScanned` counted discovered files rather than successfully read files.

Required regression coverage:

- empty protected directory
- invalid UTF-8 protected file
- oversized protected file
- mixed successful and failed protected-file reads
- protected content with no segment meeting the configured minimum length

### Resolution

🟢 **COMPLETE**

The scanner now makes usable protection part of the pass condition, records protected files as discovered/scanned/skipped with explicit reasons, rejects any skipped protection from a passing result, and requires predeclared minimum protected-file and protected-segment coverage.

Follow-up: each configured protected path must also contribute at least one usable segment. A usable directory can no longer mask another configured directory that is empty or contains only short content, or a configured short-only file. Coverage failures identify the affected configured path. Regression coverage includes those mixed cases and two usable directories.

Reopened and resolved after discovering that recursive glob enumeration suppressed nested-directory permission failures. Discovery now uses explicit directory enumeration and metadata checks; failures to open or finish enumerating a directory, or inspect an entry, raise a contextual error before a passing report can be written. Links, Windows reparse points, and special files are rejected instead of silently omitted.

Follow-up verification: **17 focused tests passed**, **1 checkpoint/training test deselected**, and **1 existing NumPy warning**. Synthetic regressions cover directory-open failure, mid-enumeration failure, entry-metadata failure, links, reparse points, and special files alongside usable protection. Restoring access detects the exact contamination match in the previously unreadable directory. No research training or final-holdout access was performed.

Verified cases:

- empty protected directory: rejected
- invalid UTF-8 protected file: rejected
- oversized protected file: rejected
- mixed successful/unreadable reads: rejected
- short-only protected content below the minimum segment length: rejected
- usable protected content with no contamination match: accepted

The contamination regression module is now included in the repository CI suite.

Verification run:

- **167 passed**
- **2 skipped**
- **1 warning**

---

## 🔧 B03 — Interior shared-substring contamination detection

**Priority:** P2  
**Type:** Code defect / verification defect

The scanner currently checks only whether an entire protected segment is contained in a corpus record or vice versa. Two longer strings can therefore share a protected interior passage at or above `minimumSubstringCharacters` while neither whole string contains the other.

Required regression coverage:

- shared substring inside both strings
- overlap exactly at the configured threshold
- overlap one character below the threshold
- existing whole-segment containment behavior

### Resolution

🟢 **COMPLETE**

The scanner now computes the exact longest shared substring with a suffix automaton, preserving whole-segment containment while adding interior-overlap detection without an unbounded quadratic search. The report records the detected overlap length.

Verified cases:

- interior overlap above the threshold: rejected
- overlap exactly at the threshold: rejected
- overlap one character below the threshold: accepted
- existing whole-segment containment: rejected

Verification run:

- **170 passed**
- **2 skipped**
- **1 warning**

---

## 🔧 B04 — Contamination report input identity

**Priority:** P2  
**Type:** Code defect / auditability defect

The v1 contamination report records the dataset manifest hash but not the exact train/validation JSONL bytes, protected configuration bytes, or protected-file bytes assessed by the scanner. A saved report therefore cannot independently identify all effective inputs. The Plex Web dataset builder already declares train and validation SHA-256 values in `manifest.json`, but the contamination scanner does not verify those declarations.

Required regression coverage:

- train JSONL identity is recorded from the exact bytes parsed
- validation JSONL identity is recorded from the exact bytes parsed
- protected config and readable protected-file identities are recorded
- declared train/validation manifest hashes are verified and mismatches are rejected
- changing manifest, corpus, protected config, protected content, scanner settings, or scanner version changes the assessment identity
- existing v1 report files are not rewritten

### Resolution

🟢 **COMPLETE**

The v2 report records scanner version/settings, raw-byte SHA-256 and byte counts for the manifest, both dataset splits, protected config, and readable protected files. It derives a canonical `assessmentSha256` from those effective inputs. Dataset split hashes declared by the builder are verified before the report is written.

Verified cases:

- train and validation hashes are computed from the exact bytes parsed by the scanner
- a declared train or validation hash mismatch is rejected before a report is written
- changing corpus bytes changes `assessmentSha256` even when the manifest has no declared split hashes and remains byte-identical
- changing manifest, protected config, protected content, scanner settings, or scanner version changes `assessmentSha256`
- readable protected files and the protected config receive explicit raw-byte SHA-256 fingerprints
- an existing v1 report file is not rewritten by a v2 scan
- prior B01-B03 and B02 follow-up regressions remain green

The first CI attempt exposed a stale B02 unreadable-file test mock that intercepted text-mode reads while the v2 scanner now reads exact raw bytes. The synthetic mock was updated to intercept the raw-byte open path; scanner behavior itself remained fail-closed.

Verification run:

- **177 passed**
- **2 skipped**
- **1 warning**

Historical v1 reports remain untouched; new reports use `schemaVersion: 2` and `plex-web-contamination-report-v2`.

---

## 🔧 B05 — Resume artifact ownership

**Priority:** P1  
**Type:** Code defect / artifact-integrity defect

The training runner previously skipped checkpoint/metrics collision protection whenever `resume_from` was set. A resumed run could therefore target an unrelated existing checkpoint and later overwrite it, while an unrelated existing metrics file would be appended to without an ownership check.

Required regression coverage:

- resuming checkpoint A cannot target an already-existing checkpoint B
- collision rejection happens before checkpoint loading or optimizer work where possible
- in-place continuation of the exact checkpoint being resumed remains supported
- a fresh continuation checkpoint path remains supported
- checkpoints persist a stable run identity across continuation
- every metrics event carries that run identity
- an existing metrics file must prove the same run identity before append
- unrelated or legacy/unidentifiable existing metrics are rejected

### Resolution

🟢 **COMPLETE**

Resume now establishes artifact ownership before training begins. Existing checkpoint overwrite is allowed only when the destination resolves to the same checkpoint supplied as `resume_from`; otherwise an existing destination is rejected before checkpoint loading. Fresh continuation destinations remain supported.

Runner-created checkpoints persist a 32-character `runId`, and every metrics event carries that same identity. Before a resume appends to an existing metrics file, every nonempty event must prove the resumed checkpoint's `runId`. Unrelated, malformed, empty, or legacy/unidentifiable existing metrics are rejected. Legacy checkpoints without a `runId` remain resumable when fresh output and metrics paths are selected, at which point a new identity is established.

Completion follow-up: an existing metrics file must also end with a line terminator. An unterminated final event previously passed ownership checks and became invalid JSONL when the next event was appended. Resume now rejects that file before optimizer construction and preserves its bytes. LF, CRLF, and CR line endings remain supported; valid appends preserve the original records. A fresh metrics destination remains available when an old log cannot be safely continued.

Verified cases:

- checkpoint A cannot overwrite existing checkpoint B
- checkpoint collision rejection occurs before checkpoint I/O
- unrelated metrics are rejected before optimizer construction
- exact in-place continuation of checkpoint A remains supported
- continuation to a fresh checkpoint path remains supported
- `runId` persists from checkpoint through resumed checkpoint and returned summary
- every metrics event from an owned run carries the same `runId`
- overwrite permission is tracked as runner ownership rather than inferred from destination existence

The first CI attempt exposed exception wrapping in the new metrics guard: `FileExistsError` is an `OSError`, so the intended ownership error was being caught by the generic I/O handler. The helper now preserves explicit ownership failures before handling unrelated I/O errors.

Verification run:

- **179 passed**
- **2 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

---

## 🔧 B06 — Distinct metrics and checkpoint destinations

**Priority:** P1  
**Type:** Code defect / artifact-contract defect

The training runner previously constrained the checkpoint and metrics destinations independently to the artifact root but never required them to be distinct. A single path could therefore be used for both the JSONL metrics stream and the binary checkpoint, allowing one artifact contract to overwrite or corrupt the other.

Required regression coverage:

- a fresh run rejects the same nonexistent path for checkpoint and metrics
- destination separation is checked before model construction or device selection
- resume rejects checkpoint/metrics aliases before checkpoint loading
- canonical path aliases are rejected
- existing filesystem aliases such as hard links are rejected
- no output bytes are created or modified when the guard rejects the request

### Resolution

🟢 **COMPLETE**

The runner now checks destination separation immediately after both paths are canonicalized beneath the artifact root and before resume ownership checks, device selection, model construction, or checkpoint loading.

Canonical equality is rejected directly, covering identical paths and aliases that resolve to the same pathname. When both destinations already exist, filesystem identity is checked with `samefile`, which also rejects distinct pathnames that refer to the same underlying file, including hard links.

Completion follow-up: Windows can treat nonexistent `output` and `output.` (or `output `) as the same file even when path resolution returns different spellings. Before canonicalization, Windows output names now reject trailing dots/spaces in any component, reserved device names, alternate data streams, invalid characters, drive-relative paths, and device namespaces. The metrics destination must also differ from the checkpoint's `.tmp` staging file, including existing filesystem aliases. All these checks run before device selection or checkpoint loading for both fresh and resumed runs.

Resolved Windows destinations are validated again so path resolution cannot introduce an ambiguous spelling hidden by the original input. This boundary is covered with simulated link resolution; native symlink creation was unavailable because the local account lacks that Windows privilege.

Follow-up review and verification for B05/B06: **28 focused tests passed**, **8 unrelated/model-execution tests deselected**, and **1 existing NumPy warning** on Windows. Coverage includes rejection without artifact mutation, safe metrics appends, the native nonexistent Windows alias cases, resolved destination validation, checkpoint staging collisions, and the prior B04-B06 regressions. No research training or final-holdout access was performed.

Verified cases:

- a fresh run with one shared nonexistent checkpoint/metrics path is rejected
- the fresh-run guard fires before device selection or model construction
- a resume using existing hard-linked checkpoint/metrics destinations is rejected
- the resume guard fires before device selection or checkpoint loading
- rejected fresh requests create no output
- rejected alias requests preserve the existing bytes unchanged
- existing B05 checkpoint ownership and metrics `runId` behavior remains green for distinct destinations

Verification run:

- **181 passed**
- **2 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

---

## 🔧 B07 — Nonfinite training update guard

**Priority:** P2  
**Type:** Code defect / training-integrity defect

The shared training step previously checked only for a missing loss. A NaN or Inf loss could reach backward, and gradient clipping used its default nonfinite behavior before the optimizer was stepped unconditionally. That could contaminate model parameters or optimizer state and later allow corrupted state to be checkpointed.

Required regression coverage:

- a nonfinite loss is rejected before backward
- a nonfinite gradient norm is rejected before `optimizer.step()`
- the optimizer is not stepped in either failure case
- a numerical failure emits a `run_failed` event with a stable reason
- a numerical failure does not execute the final checkpoint save
- an existing resumed checkpoint remains byte-for-byte unchanged after failure

### Resolution

🟢 **COMPLETE**

The shared training step now fails closed at both numerical mutation boundaries. A nonfinite loss is rejected before backward, and gradient clipping uses `error_if_nonfinite=True` so a NaN/Inf total gradient norm raises before `optimizer.step()`. Both cases use a dedicated `TrainingNumericsError` with a stable reason.

At the run level, that numerical exception records a `run_failed` metrics event and is immediately re-raised. The normal post-loop validation and final checkpoint save are therefore skipped. If the run was resuming an existing checkpoint, the last good checkpoint remains untouched.

Verified cases:

- nonfinite loss is rejected before backward
- loss failure leaves model gradients unset and never calls `optimizer.step()`
- a finite loss that produces an infinite gradient is rejected at gradient-norm clipping
- gradient failure never calls `optimizer.step()`
- numerical failure records `run_started` followed by `run_failed`
- `run_failed` records the stable numerical reason and current step
- the final checkpoint save is not invoked after numerical failure
- an existing resumed checkpoint remains byte-for-byte unchanged

Verification run:

- **188 passed**
- **4 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

---

## 🔧 B08 — Oversized completion prompt truncation

**Priority:** P2  
**Type:** Code defect / input-integrity defect

Completion previously limited the raw UTF-8 prompt to 4096 bytes but did not require the tokenized prompt to fit the model context. Generation sliced the prompt to the final `context_length` tokens from the first decoding step, so an accepted prompt could silently lose its beginning while the result still reported the original full prompt.

Required regression coverage:

- a prompt with exactly `context_length` tokens reaches the model unchanged
- a prompt with `context_length + 1` tokens is rejected
- the rejection reports both the actual token count and allowed model context
- the oversized prompt is rejected before the model's first completion call
- the public `complete_pilot` entry point inherits the same guard

### Resolution

🟢 **COMPLETE**

Completion now rejects a tokenized prompt when its length exceeds the loaded model context. The error includes the actual prompt token count and the allowed context size. The rolling context window is still used only after an initially valid prompt begins generation.

Verified cases:

- exactly at the context limit: accepted intact
- one token over the context limit: rejected
- rejection includes actual and allowed token counts
- public completion rejects the oversized prompt before model evaluation
- existing completion sampling and EOS tests remain green

Verification run:

- **190 passed**
- **4 skipped**
- **1 warning**

---

## 🔧 B09 — Temporary checkpoint over-allocation

**Priority:** P2  
**Type:** Code defect / storage-integrity defect

The atomic checkpoint writer previously checked only one extra byte before serialization. The full temporary checkpoint could therefore be written and synced before the configured artifact allocation was checked again, allowing the temporary file to exceed the allocation at peak usage.

Required regression coverage:

- serialization is bounded by the remaining configured allocation
- an over-budget write is rejected before that chunk reaches the temporary file
- partial temporary output is cleaned up after failure
- overwrite peak accounting includes the old checkpoint while the temporary replacement exists
- an over-budget overwrite preserves the previous checkpoint bytes
- large real checkpoints are not required for the regression

### Resolution

🟢 **COMPLETE**

Checkpoint serialization now computes the artifact bytes already allocated before creating the temporary file and wraps the temporary stream in a bounded writer. Each serialization write is checked before it reaches disk, so a write that would cross the configured allocation is rejected without causing the temporary checkpoint to exceed the budget.

Overwrite peak usage also counts the existing destination until the atomic replacement occurs. A failed over-budget replacement therefore preserves the previous checkpoint and removes the partial temporary file.

Completion follow-up: storage enumeration previously used recursive globbing, which could silently omit an unreadable directory and understate the starting allocation. Accounting now explicitly enumerates directories and inspects each entry. Directory-open, enumeration, and metadata failures stop the write; links, reparse points, and special files are rejected rather than omitted. A failed final accounting check also cleans up the temporary output while preserving the old checkpoint.

The original synthetic 80-byte hidden artifact plus 30-byte write under a 100-byte limit now fails before serialization when discovery is denied, and fails the byte budget when access is restored. Normal toy checkpoint serialization and weights-only loading were also verified.

Verified cases:

- an over-budget serialization chunk is rejected before that chunk is written
- partial temporary output is removed after failure
- existing unrelated artifact bytes reduce the available checkpoint budget
- overwrite peak accounting includes the old checkpoint bytes
- an over-budget overwrite leaves the previous checkpoint byte-for-byte unchanged
- normal real checkpoint serialization remains compatible with the bounded writer
- large real checkpoint fixtures were not required

Verification run:

- **192 passed**
- **4 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

---

## 🔧 B10 — P3 protected-input and path-alias collisions

**Priority:** P2  
**Type:** Code defect / artifact-integrity defect

P3-01 generation previously compared only candidate and review output spellings with `Path.absolute()`. It did not protect the contract input. Review similarly compared the optional report only against candidate, review metadata, and contract spellings, leaving tokenizer inputs unprotected and filesystem aliases incompletely handled.

Required regression coverage:

- generation rejects the contract itself as an output
- generation rejects a canonical path alias of the contract
- candidate and review outputs cannot be existing filesystem aliases
- review report cannot overwrite the candidate
- review report cannot alias tokenizer input files
- collision rejection occurs before protected inputs are read
- rejected operations preserve all protected bytes
- ordinary unrelated output overwrite behavior remains unchanged

### Resolution

🟢 **COMPLETE**

P3-01 now checks output separation before protected input reads. Output paths are resolved canonically, output/output and output/input pairs are compared, and existing pairs are additionally checked with filesystem identity so distinct hard-link names cannot bypass the guard. Filesystem-identity lookup failures fail closed.

Generation protects the contract from both candidate and review outputs and prevents the two generation outputs from aliasing each other. Review protects the candidate, draft review metadata, contract, tokenizer bundle directory, and tokenizer manifest/config/data files from the optional report output. Existing unrelated output overwrite behavior remains unchanged.

Completion follow-up: fresh Windows names such as `output` and `output.` previously bypassed the existing-file identity check and allowed review metadata to replace the candidate. P3 now validates output spellings before and after resolution using the shared Windows guard also used by the training runner. Ambiguous names are rejected before protected input reads or output writes, for both generation outputs and review reports. Normal candidate generation remains intact.

Follow-up verification for B09/B10: **15 focused allocation/path tests passed** and **18 P3 contract tests passed** on Windows (these selections overlap). The focused run reported **1 existing NumPy warning**. Independent synthetic replays confirmed both original failures are blocked, and positive checks confirmed normal checkpoint serialization/loading and candidate generation. Resolved-link spelling is simulated because native Windows symlink privileges are unavailable. No research training or final-holdout access was performed.

During verification, the repository workflow was found not to include the P3 file-conditioned contract test module. The workflow now runs that module explicitly so these regressions are part of pull-request CI.

Verified cases:

- contract supplied directly as a generation output: rejected before contract read
- canonical path spelling that resolves back to the contract: rejected
- existing hard-linked candidate/review generation outputs: rejected
- report equal to candidate: rejected before review input reads
- report hard-linked to a tokenizer input: rejected
- collision failures preserve protected candidate, review, contract, and tokenizer bytes
- P3 contract regressions now execute in the main training CI suite

Verification run:

- **207 passed**
- **6 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

---

## 🔧 B11 — P3 paired candidate/review publication

**Priority:** P2  
**Type:** Code defect / artifact-consistency defect

P3-01 generation previously wrote candidate bytes directly to the final destination and only afterward created or replaced the review metadata. If the second write failed, the candidate could already be new while the previous review metadata remained, leaving a broken pair. Direct final writes also exposed partial-output risk during interruption.

Required regression coverage:

- both candidate and review bytes are fully staged before either final destination is replaced
- failure while staging the second file preserves the previous pair
- failure while publishing the second file restores the previous candidate
- fresh/temporary transaction files are cleaned after a recoverable failure
- overwrite remains supported for existing regular candidate/review files
- caught interruption/failure cannot silently leave a mixed pair
- if rollback itself fails, a recovery backup and explicit transaction marker remain
- stale transaction artifacts fail closed instead of being overwritten

### Resolution

🟢 **COMPLETE**

P3-01 generation now stages and fsyncs both candidate and review bytes before either final destination is replaced. Existing regular output files remain explicitly overwriteable. At commit time, an existing candidate is moved to a recovery backup, the staged candidate is published, and only then is the staged review metadata published.

If review publication fails, the previous candidate is restored; when there was no previous candidate, the newly published candidate is removed. Caught interruption paths use the same rollback because publication recovery catches `BaseException`. A machine-readable `.p3txn` marker exists only during the commit window. If rollback itself fails or the process is terminated before recovery can run, the marker and candidate backup make the incomplete state explicit.

Stale staging, backup, or transaction-marker artifacts fail closed rather than being overwritten. Successful or recoverable failed publications clean temporary staging state.

Verified cases:

- both new artifacts are fully staged before final publication begins
- failure while staging the second file preserves the old candidate/review pair
- failure while publishing review metadata restores the previous candidate
- recoverable failures remove staging, backup, and transaction artifacts
- rollback failure leaves the previous candidate backup plus a machine-readable recovery marker
- a stale transaction marker blocks a later generation and is preserved for inspection
- existing regular candidate/review files can still be regenerated successfully
- prior B10 protected-input and path-alias checks remain in the same publication path

Verification run:

- **214 passed**
- **9 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, or final-holdout access was performed for this fix.

### Follow-up completion review - 2026-10-10

The original fix missed interruption immediately after a successful replacement: review publication could complete, then recovery restored only the candidate and removed the marker, silently leaving a mixed pair. B11 was reopened for this confirmed failure.

Publication now stages recovery copies of **both** existing outputs before commit and records replacement intent **before** each syscall. Recovery restores both prior files (or removes outputs that did not previously exist), including interruptions immediately after a successful replacement. Failed recovery retains the marker and the remaining recovery copy; stale review backups also fail closed.

Follow-up verification: **25 passed, 2 deselected** in the supplied-file contract suite. The new regression covers 16 interruption combinations, review rollback failure, and stale review recovery backups. The two frozen-tokenizer tests were excluded; no research model, training, or final holdout was opened. Original verification counts above remain historical evidence. Publication is recoverable, not a simultaneous two-file filesystem transaction; abrupt process termination requires inspecting the recorded recovery state.

---

## 🔧 B12 — Strict model dimension types

**Priority:** P3  
**Type:** Code defect / configuration-validation defect

Model configuration previously checked dimension positivity without first requiring exact integer types. Positive fractional values could reach model construction or parameter arithmetic, booleans were accepted as integer-like dimensions, and strings could fail later with unrelated type errors.

Required regression coverage:

- every model dimension field rejects positive fractional values
- every model dimension field rejects booleans
- every model dimension field rejects strings
- every model dimension field rejects zero
- every model dimension field rejects negative values
- the same invalid inputs are rejected through direct construction and `from_dict`
- type rejection occurs before divisibility or parameter-count arithmetic
- the controlled default configuration and parameter count remain unchanged

### Resolution

🟢 **COMPLETE**

All six model dimension fields now require `type(value) is int` before positivity, divisibility, or parameter-count arithmetic. This deliberately rejects booleans despite Python's `bool` subclassing `int`, and it converts previously late or misleading failures for fractional/string dimensions into deterministic configuration validation failures.

`from_dict` retains its existing checkpoint-facing error contract by wrapping the underlying validation failure as `Checkpoint model_config is invalid`. Dropout validation is unchanged.

Verified cases for every dimension field through both direct construction and `from_dict`:

- positive fractional value: rejected
- boolean: rejected
- string: rejected
- zero: rejected
- negative integer: rejected
- controlled default dimensions remain unchanged
- controlled default parameter count remains exactly **27,566,080**

Verification run:

- **216 passed**
- **9 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, checkpoint modification, or final-holdout access was performed for this fix.

---

## 🔧 B13 — Explicit loss-vocabulary validation

**Priority:** P3  
**Type:** Code defect / objective-validation defect

The model previously used `loss_vocabulary_size or self.config.vocab_size`, so explicit zero or `False` silently selected the full model vocabulary before range validation. That changed the requested training/evaluation objective instead of rejecting an invalid argument.

Required regression coverage:

- `None` retains the normal full-vocabulary loss objective
- explicit zero is rejected
- explicit `False` is rejected rather than treated as zero/full-vocabulary fallback
- explicit non-integer values are rejected before slicing/arithmetic
- negative and above-capacity integer values remain rejected
- existing valid reduced-vocabulary loss behavior remains unchanged

### Resolution

🟢 **COMPLETE**

Loss-vocabulary selection now defaults to the full configured vocabulary only when `loss_vocabulary_size is None`. Every explicit value must have exact type `int` before range validation, so booleans and other non-integers cannot be truthiness-coerced into a different objective.

Explicit integer values must satisfy `1 <= loss_vocabulary_size <= config.vocab_size`. Existing valid reduced-vocabulary loss behavior remains unchanged.

Verified cases:

- `None`: uses the complete configured vocabulary and matches full-logit cross-entropy
- zero: rejected instead of selecting the full vocabulary
- `False`: rejected as a non-exact integer
- float: rejected as a non-exact integer
- string: rejected as a non-exact integer
- negative integer: rejected by range validation
- above-capacity integer: rejected by range validation
- existing valid reduced-vocabulary masking remains green

Verification run:

- **218 passed**
- **9 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, checkpoint modification, or final-holdout access was performed for this fix.

---

## 🔧 B14 — Contamination JSONL row object validation

**Priority:** P3  
**Type:** Code defect / diagnostic-validation defect

Dataset split rows were parsed as JSON and then immediately accessed with `.get()`. Syntactically valid non-object JSON values such as `null`, arrays, strings, numbers, and booleans therefore raised unrelated attribute errors instead of the scanner's contextual validation error.

Required regression coverage:

- JSON `null` is rejected before field access
- JSON arrays are rejected before field access
- JSON strings are rejected before field access
- JSON numbers are rejected before field access
- JSON booleans are rejected before field access
- errors identify the exact split filename and line number
- both train and validation split paths use the same validation
- no contamination report is written after the malformed row is rejected

### Resolution

🟢 **COMPLETE**

Each decoded dataset JSONL row is now required to be a dictionary immediately after `json.loads` and before any field access. Syntactically valid non-object JSON therefore follows the scanner's deterministic validation path instead of raising an attribute error.

The error preserves the exact split filename and line number: `ValueError("<split>.jsonl:<line> must contain a JSON object")`. Existing invalid-JSON and missing-text diagnostics remain unchanged.

Verified in both `train.jsonl` and `validation.jsonl`:

- JSON `null`: rejected contextually
- JSON array: rejected contextually
- JSON string: rejected contextually
- JSON number: rejected contextually
- JSON boolean: rejected contextually
- line number is preserved after a valid preceding row
- no contamination report is written after malformed-row rejection
- existing contamination scanner regressions remain green

Verification run:

- **219 passed**
- **9 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, checkpoint modification, or final-holdout access was performed for this fix.

---

## 🔧 B15 — Exact checkpoint version/step types

**Priority:** P3  
**Type:** Code defect / checkpoint-schema defect

The common checkpoint reader previously compared `formatVersion` by value and validated `step` with `isinstance(..., int)`. Because Python booleans are integer-like, `formatVersion=True`, `step=True`, and `step=False` could pass metadata validation. Numeric equality also allowed `formatVersion=1.0`.

Required regression coverage:

- `formatVersion=True` is rejected by the common reader
- `formatVersion=1.0` is rejected despite comparing equal to version 1
- `step=True` is rejected
- `step=False` is rejected
- exact integer `formatVersion=1` remains accepted
- exact integer historical `step=0` remains accepted
- existing completion/resume metadata consumers remain consistent with the common reader
- historical valid checkpoint payloads require no rewriting

### Resolution

🟢 **COMPLETE**

The common checkpoint reader now requires `type(formatVersion) is int` before comparing the supported format version and `type(step) is int` before applying the non-negative step range. Boolean and integer-like metadata therefore cannot pass the shared checkpoint schema.

Consumer review confirmed completion and resume already apply exact-integer step checks at their additional product-specific boundaries. Runner and evaluation consume step metadata only after `read_checkpoint` succeeds, so the shared reader now provides the consistent base guarantee without rewriting or migrating historical valid artifacts.

Verified cases:

- `formatVersion=True`: rejected
- `formatVersion=1.0`: rejected despite numeric equality with version 1
- `step=True`: rejected
- `step=False`: rejected
- exact integer `formatVersion=1`: accepted
- historical exact integer `step=0`: accepted
- valid v1 model configuration/state still loads through the common reader
- existing completion/resume/checkpoint regressions remain green

Verification run:

- **221 passed**
- **9 skipped**
- **1 warning**

No model training authorization, research training, corpus promotion, checkpoint rewriting, or final-holdout access was performed for this fix.
