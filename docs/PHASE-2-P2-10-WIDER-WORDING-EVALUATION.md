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

## Token-divergence audit

A read-only teacher-forced audit scored the expected tokens after each correct prefix and recorded the first divergence on each actual greedy miss. The checkpoint hash matched before and after; the audit updated no weights and resampled no completions.

| Wording | Exact | Newline top-ranked | First body token top-ranked after `\\n.` | First divergences: answer start / body |
|---|---:|---:|---:|---:|
| Transcribe | 16/16 | 16/16 | 16/16 | 0 / 0 |
| Reproduce verbatim | 6/16 | 12/16 | 10/16 | 4 / 6 |
| Preserve every character | 16/16 | 16/16 | 16/16 | 0 / 0 |
| Write character for character | 5/16 | 15/16 | 5/16 | 1 / 10 |

For all 64 prompts, the expected period ranked first after the expected newline, and EOS ranked first after the expected answer. There were no first divergences at the period. The low-scoring wording cells therefore fail at answer-start selection or, more often, at the first selector-body token—not at period recognition or EOS.

The two low-scoring phrasings fail differently:

- **“Reproduce the selector below verbatim”** had 4/8 exact on the inline layout and 1/8 on the next-line layout. All four skipped-newline failures occurred on the next-line layout and emitted the selector body directly, without the requested answer newline and leading period. The other six misses had already generated `\\n.`; the next greedy token was another newline in all six, duplicating the boundary before the selector body. This is a wording-by-layout interaction, not a general preference for one layout.
- **“Write this selector again, character for character”** had only one answer-start miss; ten failures diverged at the selector body after `\\n.`. Seven of the eleven misses emitted `charlie-list` somewhere in the completion: six used it for a different requested selector and one repeated the correct `.charlie-list` after a duplicated prefix. At the divergence, the expected first body token ranked 2nd–7th on the inline layout's seven misses; it ranked 3rd, 3rd, and 7th in the three body misses on the next-line layout. This suggests a phrase-conditioned selector-body attraction, with `.charlie-list` a frequent competing continuation.

The comparison phrasings provide a useful control: **Transcribe** and **Preserve** scored 16/16, and all expected answer tokens ranked first under teacher forcing in both layouts. Since **Preserve every character** succeeds perfectly, the failures do not isolate the word “character” as the cause; they track the full wording and its interaction with layout. This is evidence of prompt-conditioned continuation on this small matrix; it does not prove a general language mechanism.

The complete 64-record ranks, top-five alternatives, and divergence prefixes are in the ignored local artifact `training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/wider-token-audit-v1.json`.

## Interpretation and next step

The P2-10 answer-start cue and selector-copy behavior do not transfer consistently across paraphrases: the same checkpoint scores 16/16 on two templates and 6/16 or 5/16 on two others. The evaluation also shows why a single held-out wording was too narrow. The audit separates an answer-boundary problem for **Reproduce** on next-line inputs from a selector-body continuation problem for **Write**, including repeated attraction to `charlie-list`. This evidence motivated a review-only P2-11 candidate with these two phrasings in training and four fresh evaluation templates; it does not authorize a run. See the [P2-11 candidate report](PHASE-2-P2-11-BALANCED-WORDING-CANDIDATE.md) for the hash-pinned design and approval boundary.
