# P2-08: selector copying with wording and layout controls

## Result

The approved one-arm run completed 100/100 optimizer updates in 15.51 seconds on CUDA. The training set scored **63/64 exact selector outputs**. The experiment's interpretation rule requires all 64 supplied records to be learned before interpreting held-out performance. The run therefore did **not** pass the convergence gate, and its evaluation is formally **inconclusive**.

The held-out set scored 4/16 exact outputs, with 2 wrong-known-selector outputs and 10 malformed outputs. EOS was emitted for all 16. These raw counts are descriptive only; they are not a transfer rate or evidence for or against instruction invariance because training did not fully converge.

The one supplied-record miss was the `repeat-as-shown` / `colon-newline` request for `.filters`; the model emitted `\n.\n.echo-label` and EOS. On evaluation, the two `.filters` requests returned the known selector `.actions`. Most other non-exact evaluation outputs omitted the selector's leading period (for example, `.alpha-panel` became `alpha-panel`). Both layouts had evaluation errors, so this run does not isolate a layout effect.

## Approved design and run

P2-08 tests one selector-copy operation with eight known selector values. Training crosses four phrasings, two input layouts, and all eight selectors (64 records). Evaluation holds out the `give-back-no-changes` phrasing while reusing those same selector values in both layouts (16 records). The layout itself is represented in training. This is a narrow test of held-out wording with known values and crossed input layout, not CSS composition or broad language understanding.

The run used one fresh seed-1337 scratch model, answer/EOS-only complete-record loss, the frozen tokenizer, microbatch 1, gradient accumulation 16, and a cap of 100 updates or 10 minutes with no extension. Initial model tensors matched the recorded seed-1337 initialization. The training/evaluation hashes, tokenizer hash, exact run bounds, and approval are recorded in `training/phase2/approvals/p2-08-selector-format-v1.json`.

| Measure | Result |
|---|---:|
| Training exact | 63/64 |
| Training EOS | 64/64 |
| Evaluation exact, descriptive | 4/16 |
| Evaluation wrong known selector, descriptive | 2/16 |
| Evaluation malformed output, descriptive | 10/16 |
| Evaluation EOS | 16/16 |
| Training record draws | 1,600 |
| Supervised answer/EOS targets | 11,785 |
| Excluded prompt targets | 89,721 |
| Padding targets | 0 |
| Sampler replay | Matched training telemetry |
| Tokenizer refitted | No |
| Final project holdout opened | No |

`otherOrNoEos` in the machine-readable score combines malformed output and missing EOS; in this run, every evaluation emitted EOS, so all 10 cases in that category were malformed outputs.

## Scope and next step

The run stopped at the approved limit. Do not continue this checkpoint or interpret the held-out score as a successful or failed transfer result. The next useful experiment should first examine why one of the 64 supplied training prompts remains malformed at the cap, with particular attention to the newline layout and leading-period tokenization. Any new candidate or training run needs its own review and exact-hash approval. The final project holdout remains closed.

The complete record-level outputs, generated token IDs, optimizer telemetry, checkpoint identity, and sampler accounting remain in the local ignored artifact `training/artifacts/experiments/p2-08-selector-format-run-v1/result.json` and `completion-score.json`; they are not committed to the repository.
