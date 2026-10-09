# Plex Nano — Bug Atlas

This file tracks confirmed bugs being worked through before Phase 3 resumes.

Status legend:

- 🔴 **OPEN** — confirmed/reported and not yet fully verified as fixed
- 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🟢 **COMPLETE** | `training/src/plex_training/answer_weighting.py` | Exact dataset/index cardinality is now enforced. |

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

