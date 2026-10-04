# P2-02 code-pair ten-minute diagnostic

The owner completed `pilot/p2-code-pairs-10m-v1` without interruption. The approved, separate 24-training/12-validation corpus and its matching 874-entry tokenizer are recorded in the [build report](PHASE-2-CODE-PAIR-BUILD-REPORT.md). The local saved checkpoint was then generated and statically scored against the same 30 development tasks used for its matching random baseline. No final holdout was opened and no JavaScript behavior was executed.

## Matched result

| Measure | Random step zero | Trained step 3,197 |
|---|---:|---:|
| Complete tasks passed | 0/30 | 0/30 |
| Truncated responses | 28/30 | 0/30 |
| HTML syntax passes | 10/10 | 3/10 |
| CSS syntax passes | 0/10 | 7/10 |
| JavaScript syntax passes | 0/10 | 7/10 |
| Static checks passed / total | 40/179 | 47/151 |
| Missing or empty responses | 0 | 0 |
| Evaluator timeouts | 0 | 0 |

Check totals differ because the existing evaluator appends a failing `notTruncated` check only to truncated outputs. Compare complete-task passes and the separate syntax/completion measures; the raw check fractions are not a fixed-denominator benchmark. HTML syntax accepting arbitrary plain text at step zero does not establish correct HTML task completion.

The trained response to the primary-navigation task began with `<address>`, contained DNS/URL definition-list entries, and ended with `</dl>`. It was short and code-shaped, but unrelated to the requested navigation and structurally invalid. This is evidence of task mismatch, not just a decoding-limit problem.

## Training and resources

The run lasted 600.115 seconds and performed 3,197 optimizer steps, processing 26,189,824 tokens at 43,641 tokens/second. Recent training loss reached 0.00724, while held-out loss worsened from **6.89080 to 8.42534** (`validationImproved: false`). This combination is consistent with strong overfitting on the tiny corpus; the held-out loss includes prompt and answer tokens, so it is not an answer-only accuracy measure.

Peak GPU allocation was 802,490,880 bytes, reservation 861,929,472 bytes, and process peak working set 1,362,169,856 bytes. The checkpoint is 330,898,523 bytes. No paid services, dependencies, or new source downloads were used for evaluation. The NumPy warning did not prevent the run or scoring.

## Recorded identities and paths

- Trained checkpoint SHA-256: `aad48a74a8ae7026e510ff5b888deb0790585a42afbce67e891f0d66bf6f48ab`.
- Matching initialization SHA-256: `825247e0419f18a31f45d02cf00afcafdc6392a94b6bf9adde4ea52c92222113`.
- Trained response SHA-256: `93eb52480c0cf26573f8a23f308d64ab1543fce70377d93a0a0425d21a6dd930`.
- Unchanged task-set SHA-256: `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4`.

Local artifacts, beneath `training/artifacts`, are `pilot/p2-code-pairs-10m-v1/{pilot-report.json,pilot-checkpoint.pt,metrics.jsonl}` and `evaluation/p2-code-pairs-10m-v1/{run-manifest.json,responses.jsonl,score.json}`. The baseline remains in `evaluation/p2-code-pairs-step-zero-v2`. Generation verified the checkpoint and tokenizer identities; they match the owner's submitted training report and the approved build.

## Decision and next work

The format diagnostic is complete: responses finish within the fixed limits and CSS/JavaScript syntax improved, but complete-task performance is unchanged and held-out loss worsened. Do not extend this tiny-corpus checkpoint into a two-hour run on the strength of these results.

Next, prepare a broader request-to-code candidate covering more independent task families, retaining whole-family validation splits and the sealed final holdout. Show its exact scope and examples for the agreed source review before inclusion. A subsequent bounded experiment should also inspect intermediate validation losses and shorter stopping budgets rather than assume that more steps help. Keep this run as the recorded format baseline. P2-02 data development remains in progress; P2-04's longer-training gate is not met.
