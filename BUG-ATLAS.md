# Plex Nano — Bug Atlas

This file tracks confirmed bugs being worked through before Phase 3 resumes.

Status legend:

- 🔴 **OPEN** — confirmed/reported and not yet fully verified as fixed
- 🟢 **COMPLETE** — fix merged after regression coverage and CI

| ID | Priority | Status | Area | Summary |
|---|---|---|---|---|
| **B01** | **P1** | 🔴 **OPEN** | `training/src/plex_training/answer_weighting.py` | One extra dataset row can escape the answer-weighting verifier. |

## B01 — Answer-weighting dataset/index cardinality

**Priority:** P1  
**Type:** Code defect / verification defect

The verifier previously iterated with `zip(stream, entries)` and then checked `stream.readline()` for leftovers. With exactly one extra JSONL row, `zip` could advance the stream to that unmatched row before discovering that the index iterator was exhausted, causing the later leftover check to miss it.

Required regression coverage:

- N-1 JSONL rows
- N JSONL rows
- N+1 JSONL rows
- N+2 JSONL rows

B01 may be marked green only after the fix is merged with passing regression tests.
