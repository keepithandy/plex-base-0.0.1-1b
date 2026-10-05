# P2-10 explicit answer-start run

Date: 2026-10-05  
Status: **complete for the approved single diagnostic run**

## Result

The fresh seed-1337 CUDA run completed all 100 approved optimizer updates in 15.47 seconds. The model exactly reproduced all **64/64** training selectors, meeting the predeclared convergence gate. Greedy scoring then produced **7/16** exact held-out selectors, so the held-out result is interpretable for this narrow diagnostic, but remains a small, single-run result rather than evidence of general instruction following.

The 16 held-out outputs all emitted EOS. Ten began with a newline; seven of those were exact selectors. The nine misses included five completions that omitted the selector's leading period, two with a duplicated newline/period prefix, one with extra text, and one that returned another selector. The scoring buckets count malformed prefixes as `other` or `extra text`, so they did not appear in the `wrong-known-selector` bucket. By input layout, colon-newline prompts scored **5/8 exact** and **5/8 newline-starting**; colon-space prompts scored **2/8 exact** and **5/8 newline-starting**.

One representative malformed completion was `\n.\n.alpha-panel` for `.alpha-panel`. Its saved token pieces were `\\n`, `.`, `\\n`, `.`, `al`, `pha`, `-`, `pan`, `el`: the explicit boundary cue was followed by a duplicated newline and period. Other misses emitted the selector body without its leading period, such as `bravo-item`. This shows that explicitly cueing a new line increased newline-start incidence relative to the P2-08 checkpoint (10/16 versus 6/16), while exact-selector scoring moved from 4/16 to 7/16. These are descriptive differences between two single bounded checkpoints, not a replicated causal estimate.

Runtime validation loss on the existing P2 request-following validation split rose from **7.4502** to **10.3099**. This separate loss measure does not negate the selector-copy result, and it is not a coding benchmark.

## Approved scope and controls

- Training candidate SHA-256: `ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8`
- Evaluation-only SHA-256: `632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9`
- Review Markdown SHA-256: `9f2e8f16c31861e5ddd8ad1ab1214c77a7a0e67c0020f34b0bdcf0f947026999`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` (no refit)
- Initialization: fresh seed-1337 scratch model; initial tensors matched the recorded seed-1337 initialization exactly.
- Objective: answer and EOS targets only; microbatch 1; gradient accumulation 16; CUDA.
- Bounds: one run, at most 100 updates or 10 minutes; no extension. It reached the update limit.
- The 16 evaluation rows were used only for post-training completion scoring. They were excluded from training and runtime validation loss.
- Final project holdout remained closed.

Prepared packed stream: 64 records / 5,040 tokens; JSONL SHA-256 `dce786c2db21fc9ebd7f53cc9a130b029f4a4ccf88a069cfef361748ef93be20`; token stream SHA-256 `1ee7bbbbf91f63308dc7f985e31ff6dd2f6f19bd84ec7127139d08ba81245823`.

## Artifacts

- Approval: `training/phase2/approvals/p2-10-explicit-answer-start-v1.json`
- Prepared input plan: `training/artifacts/experiments/p2-10-explicit-answer-start-inputs-v1/experiment.json`
- Run result and complete token-level outputs: `training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/result.json` and `completion-score.json`
- Training metrics and checkpoint: `training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/pilot/`

The artifact directory is local and ignored by Git. No final holdout was accessed. This run does not establish coding capability or justify a longer run.

## Next step

Run a read-only token-level audit of P2-10's nine held-out misses, separating first-token boundary errors from period/selector-body errors and EOS behavior. Use those saved outputs and token ranks to decide whether a new candidate is justified. Any additional training requires its own candidate, hash-pinned approval, and bounded-run approval; do not extend this run or continue from its checkpoint.
