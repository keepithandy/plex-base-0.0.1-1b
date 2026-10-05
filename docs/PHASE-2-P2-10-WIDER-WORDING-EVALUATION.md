# P2-10 wider held-out wording evaluation

Date: 2026-10-05  
Status: **reviewed set scored read-only against the existing P2-10 checkpoint**

## Result

The frozen P2-10 checkpoint scored **43/64 exact selectors** across four additional held-out request templates. Each wording was crossed with the same eight selectors and both colon layouts. Every output emitted EOS; 59/64 began with the requested newline. The result varies sharply by wording:

| Held-out wording | Inline | Selector on next line | Total |
|---|---:|---:|---:|
| Transcribe this CSS selector | 8/8 | 8/8 | **16/16** |
| Reproduce the selector below verbatim | 5/8 | 1/8 | **6/16** |
| Preserve every character in this selector | 8/8 | 8/8 | **16/16** |
| Write this selector again, character for character | 1/8 | 4/8 | **5/16** |
| **Total** | **22/32** | **21/32** | **43/64** |

Across the 64 completions, the remaining categories were 4 wrong known selectors, 7 expected selectors with extra text, and 10 other malformed or incomplete outputs. EOS was present in all cases, so termination is not the observed failure. Input layout was nearly balanced in aggregate; the larger differences are between phrasings and the interaction of wording with layout.

Including the original 16-row P2-10 held-out wording result (7/16), the descriptive total across five held-out templates is **50/80**. This is a small selector-copy diagnostic with eight repeated values, not a coding benchmark or a broad estimate of natural-language generalization. Two phrasings being perfect does not cancel the 6/16 and 5/16 cells.

## Set review and identities

The additional set contains 64 unique evaluation-only requests: four new templates × eight selectors × two input layouts. It retains the exact P2-10 output contract, target selector values, frozen tokenizer, and the existing step-100 P2-10 checkpoint. None of its requests occur in the P2-10 training or original evaluation rows.

- Evaluation-only JSONL SHA-256: `da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a`
- Review JSON SHA-256: `df35024a11d7cd08e6f1df9a21e5cb1703d836a6770e7e6ae5cac353ec1a4946`
- Review Markdown SHA-256: `f6b29aaa9982c5d59c08f6dd67f1a5ed8397921e7721994593ade869837d2500`
- Existing checkpoint SHA-256 before and after scoring: `28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; no refit.
- Maximum prompt / answer-plus-EOS length: 82 / 9 tokens.
- Training rows: 0. Runtime validation-loss rows: 0. Weight updates: 0. Final holdout opened: false.
- Scoring was deterministic greedy inference; no stochastic sampling was used.

Review metadata and JSONL are in `training/phase2/drafts/p2-10-wider-heldout-eval-v1/`. Per-prompt completions and token IDs are in the ignored local artifact `training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/wider-evaluation-score-v1.json`.

## Interpretation and next step

The P2-10 answer-start cue and selector-copy behavior do not transfer consistently across paraphrases: the same checkpoint scores 16/16 on two templates and 6/16 or 5/16 on two others. The evaluation also shows why a single held-out wording was too narrow. Do not start another training run based on this aggregate alone. The next useful read-only analysis is to inspect token-level divergences in the 21 wider-set misses, grouped by wording and layout, and compare them with the two perfect cells. A later training candidate would need to state a separate mechanism-level hypothesis, a fresh candidate and hashes, and its own owner approval.
