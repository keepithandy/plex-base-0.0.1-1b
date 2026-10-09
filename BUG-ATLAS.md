# Plex Nano — Bug Atlas

This file tracks confirmed bugs being worked through before Phase 3 resumes.

Status legend:

- 🔴 **OPEN** — confirmed/reported and not yet fully verified as fixed
- 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/answer_weighting.py` | Exact dataset/index cardinality is now enforced. |
| **B02** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Protection coverage and directory discovery now fail closed. |
| **B03** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Interior shared substrings at the configured threshold are now detected. |
| **B04** | **P2** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Contamination reports now fingerprint exact effective inputs and verify declared split hashes. |
| **B05** | **P1** | 🔴 **OPEN** | `training/src/plex_training/runner.py` | Resume must not overwrite another checkpoint or append to metrics owned by another run. |

## B01 — Answer-weighting dataset/index cardinality

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

## B02 — Contamination protection coverage

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

## B03 — Interior shared-substring contamination detection

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

## B04 — Contamination report input identity

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

## B05 — Resume artifact ownership

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

### In progress

🔴 **OPEN**

The proposed fix establishes explicit artifact ownership before training begins. Existing checkpoint overwrite is allowed only when the destination resolves to the same checkpoint supplied as `resume_from`; otherwise the destination must not already exist. A per-run `runId` is stored in checkpoints and metrics events, and existing metrics must contain only that same identity before a resume can append. Legacy checkpoints without a run identity remain resumable when new output/metrics paths are selected.

B05 remains open until pull-request CI is green and the fix is merged.
