# P2-15 pre-approval verification

P2-15 remains a review-only CSS request-to-code candidate. This verification step strengthens the boundary between reviewing the candidate and authorizing a training run.

## Candidate under review

- Candidate: `p2-15-css-edit-candidate-v1`
- Candidate JSONL SHA-256: `e9ca83c92a40abd0575db708bd67d2e4ce6888d97bc31ef4a38938a050dfd6cf`
- Training records: 24
- Validation records: 12
- Semantic families: 12, with no family crossing the train/validation split
- Proposed run ceiling after separate approval: 100 updates or 10 minutes
- Fresh initialization: required
- Seed: 1337
- Final project holdout: closed

## Verification command

From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\verify_p2_15_css_edit_candidate.py
```

The verifier is intentionally read-only. It does not create a corpus, fit a tokenizer, initialize a checkpoint, or train a model.

## What is verified

The verifier fails closed unless all of the following remain true:

1. The deterministic 36-row candidate exactly matches the pinned candidate SHA-256.
2. The saved candidate JSONL is byte-for-byte identical to the deterministic rows.
3. The split remains exactly 24 training / 12 validation records.
4. All 12 semantic groups remain isolated to a single split.
5. Every row remains `pending-owner-review`.
6. The pinned P2-14 development task set is unchanged.
7. `review.json` still records the exact candidate identity, split hashes, closed holdout, and no training/tokenizer activity.
8. The proposed experiment remains a fresh seed-1337 initialization capped at 100 updates or 10 minutes and still requires separate owner approval.
9. Every generated per-record `.txt` file matches the deterministic request/solution text exactly.
10. The review directory contains no unexpected files and is missing no expected files.
11. `REVIEW.md` still contains the pinned hashes, pending-review status, closed-holdout statement, and exactly one listing for every candidate record.

## Approval boundary

Passing this verifier is **not** approval to train.

A later training-preparation step must require an explicit owner approval artifact that identifies the exact candidate hash and exact run limits. Until that approval exists, P2-15 should remain review-only and no tokenizer, checkpoint, or training output should be created from this candidate.
