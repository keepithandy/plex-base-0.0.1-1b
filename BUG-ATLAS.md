# Plex Nano — Bug Atlas

This file tracks confirmed bugs being worked through before Phase 3 resumes.

Status legend:

- 🔴 **OPEN** — confirmed/reported and not yet fully verified as fixed
- 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/answer_weighting.py` | Exact dataset/index cardinality is now enforced. |
| **B02** | **P1** | 🔴 **OPEN** | `training/src/plex_training/web_contamination.py` | Contamination protection must fail closed when configured coverage is unusable. |

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

The contamination scanner can currently report `passed: true` when no usable protected segment was scanned. Oversized, unreadable, and invalid UTF-8 protected files are silently converted to empty segment lists; an empty protected directory also produces no protection. `protectedFilesScanned` currently counts discovered files rather than successfully read files.

Required regression coverage:

- empty protected directory
- invalid UTF-8 protected file
- oversized protected file
- mixed successful and failed protected-file reads
- protected content with no segment meeting the configured minimum length

### In progress

🔴 **OPEN**

The proposed fix makes usable protection part of the pass condition, records discovered/scanned/skipped protected files explicitly, rejects any skipped protection from a passing result, and requires configured minimum protected-file and protected-segment coverage.

The focused synthetic regression module passes locally. B02 remains open until the pull-request CI run is green and the fix is merged.
