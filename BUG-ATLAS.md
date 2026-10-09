# Plex Nano — Bug Atlas

This file tracks confirmed bugs being worked through before Phase 3 resumes.

Status legend:

- 🔴 **OPEN** — confirmed/reported and not yet fully verified as fixed
- 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/answer_weighting.py` | Exact dataset/index cardinality is now enforced. |
| **B02** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/web_contamination.py` | Contamination protection now fails closed when configured coverage is unusable. |
| **B03** | **P2** | 🔴 **OPEN** | `training/src/plex_training/web_contamination.py` | Interior shared substrings at the configured threshold must be detected. |

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

### In progress

🔴 **OPEN**

The proposed fix computes the exact longest shared substring with a suffix automaton, preserving whole-segment containment while adding interior-overlap detection without an unbounded quadratic search.

B03 remains open until the pull-request CI run is green and the fix is merged.
