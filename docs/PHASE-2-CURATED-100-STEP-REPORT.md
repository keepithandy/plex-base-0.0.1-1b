# P2-02 curated data: 100-step result

The owner approved the [exact 180 curated examples](../training/phase2/approvals/p2-02-request-following-v2.json) for local training. The [approved source catalog](../training/phase2/data/authored/p2-02-request-following-v2/dataset-sources.approved.json) produced a separate 120-training/60-validation corpus with no skipped records. The fresh tokenizer was fitted on the training split only, and [its recorded bundle check](../training/phase2/data/authored/p2-02-request-following-v2/bundle-readiness.json) verified all 180 exact texts, whole-group splits, roundtrips, inference prefixes, packed EOS boundaries, context limits, and fixed answer caps.

The tokenizer has 1,064 entries. The training split contains 11,551 tokens and the validation split 6,517, each including record EOS markers. Answers, including their leading newline, occupy 22.6% of training token positions; the prompt-heavy format and small corpus remain material limitations. The largest full record is 159 tokens, below the 512-token context. The largest answer including EOS is 30 HTML, 47 CSS, and 52 JavaScript tokens across the two splits, below the fixed 192/128/192 decode caps. All 30 development prompts also fit context.

## Matched comparison

Fresh initialization used seed 1337 and 27,566,080 parameters with `pretrainedCheckpointLoaded: false`. Both checkpoints used the same tokenizer and unchanged 30-task development set. The 100-step run had a ten-minute hard ceiling and finished in 15.38 seconds, processing 819,200 tokens.

| Measure | Random step zero | After 100 steps |
|---|---:|---:|
| Complete development tasks passed | **0/30** | **0/30** |
| Truncated outputs | 26/30 | 0/30 |
| HTML syntax passes | 10/10 | 1/10 |
| CSS syntax passes | 0/10 | 1/10 |
| JavaScript syntax passes | 0/10 | 3/10 |
| Static checks passed / total | 40/177 | 35/151 |
| Missing or empty outputs; evaluator timeouts | 0 | 0 |

The evaluator adds a failing `notTruncated` check only to truncated outputs, so the raw static-check totals differ. The primary complete-task score did not improve. The first trained response to a primary-navigation request was `\n<p><p><p><p><p><p>`—it stopped within the cap but did not satisfy the request. JavaScript was syntax-checked, never executed.

Held-out next-token loss improved from **7.08272 to 2.69697** (`validationImproved: true`); recent training loss was 0.75619. This establishes improvement on the small held-out text split, not useful unseen coding. Training processed about 71 times the training split's token count. Peak GPU allocation was 802,490,880 bytes, reserved memory 861,929,472 bytes, and process peak working set 1,396,985,856 bytes. The checkpoint is 330,898,523 bytes.

## Identities and artifacts

| Artifact | SHA-256 |
|---|---|
| Approved candidate JSONL | `9f6ad8eff96298f45880f9bfe831648364e2a7ed11996e7a7d91d5e984eb3d0b` |
| Dataset manifest | `c6f4c86b545fdc555cdc78a471919a96d9273f81a320365af442eaaa8c4d3108` |
| Fresh tokenizer | `374319ab8a7fa252742224efc09e3f11d28646bb6acfaa68d40ed37ca1d1d324` |
| Random initialization checkpoint | `8212eb8867c26ae12324cc57d3f7385f6e43840ed32650152332d2da03d95c17` |
| 100-step checkpoint | `760c608502fbfc0702e0b80bb188ff7798f3e32728df83378a1f40279d05765c` |
| Step-zero development responses | `986e448285fdbe24940ab5c0bc92f8018a1a68d3ca8168eff61976b624e20998` |
| 100-step development responses | `be25ab87b9f7c45d290bdaf84696528f410738518f7b82ee44c8711e02bc3b52` |
| Unchanged development tasks | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

Local ignored artifacts are under `training/artifacts`: dataset `datasets/p2-request-following-v2`, tokenizer `tokenizers/p2-request-following-v2`, initialization `initializations/p2-request-following-step-zero-v2/initialization.pt`, pilot `pilot/p2-request-following-100step-v2`, and matching evaluation directories `evaluation/p2-request-following-step-zero-v2` and `evaluation/p2-request-following-100step-v2`. The two `score.json` files are in those evaluation directories. Prior v3 and code-pair experiments remain separate.

## Decision and next step

The approved small experiment is complete. The model learned to stop, and its validation loss improved, yet it passed no complete task. **Do not extend this checkpoint to a 300-step or two-hour run solely on this evidence.** Preserve the final holdout for a later milestone.

The next P2-02 work is to inspect the failed responses by language and expand genuinely independent coding-task families and code content. The 180 examples cover only 30 topics, with 120 training records; roughly 77% of training token positions are prompt or boundary text. More records or longer training alone are not evidence of better code. Consider training-objective changes only as a later bounded comparison against the same development tasks. Keep the $0 paid-services and 200 GiB storage limits. The recurring NumPy warning did not prevent preparation, training, or scoring.
