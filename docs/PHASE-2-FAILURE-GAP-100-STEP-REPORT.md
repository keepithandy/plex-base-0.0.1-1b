# P2-02 v3: approved data and 100-step diagnostic

The repository owner approved the exact [234-record v3 candidate](../training/phase2/approvals/p2-02-request-following-v3.json) for local training. Its [approved source catalog](../training/phase2/data/authored/p2-02-request-following-v3/dataset-sources.approved.json) produced a separate corpus with **156 training and 78 validation records**, no skips, and whole source groups kept in one split. The earlier approved 180-record corpus and its checkpoint remain separate.

The fresh tokenizer was fitted on the v3 training split only and has 1,509 entries. The [bundle check](../training/phase2/data/authored/p2-02-request-following-v3/bundle-readiness.json) matched all 234 exact reviewed texts to the dataset and packed token records, including inference-prompt prefixes and EOS boundaries. All records fit the 512-token context and fixed per-language answer caps. The training split contains 14,770 tokens including EOS markers; answers including their leading newline occupy **23.1%** of token positions. This remains a very small, prompt-heavy corpus.

Fresh initialization used seed 1337 and 27,566,080 parameters with `pretrainedCheckpointLoaded: false`. The 100-step CUDA run had a ten-minute hard ceiling and finished in 14.52 seconds, processing 819,200 tokens. Its held-out next-token loss fell from **7.45021 to 3.28499**. That measures prediction of held-out corpus text, not coding-task success.

## Matched development-task comparison

Both checkpoints used the same v3 tokenizer and unchanged 30-task development set. The evaluator performed static contract and syntax checks; generated JavaScript was parsed with Node `--check` and **never executed**.

| Measure | Random step zero | After 100 steps |
|---|---:|---:|
| Complete tasks passed | **0/30** | **0/30** |
| Truncated outputs | 30/30 | 0/30 |
| HTML syntax passes | 10/10 | 1/10 |
| CSS syntax passes | 0/10 | 2/10 |
| JavaScript syntax passes | 0/10 | 0/10 |
| Static checks passed / total | 40/181 | 35/151 |
| Missing or empty outputs; evaluator timeouts | 0 | 0 |

The raw static-check totals differ because the evaluator adds a failing `notTruncated` check only when an output is truncated. The complete-task pass rate did not improve. A navigation request produced `\n<nav>Kyoto</a><li><li><li>`; CSS responses often reused `.spaced-photo`, and JavaScript answers used names such as `firstCodeUnits` for unrelated requests. These are saved observations, not an independent quality score. The development set guided v3 data selection, so later gains on this same set would also need final-holdout confirmation.

## Reproducible identities

| Artifact | SHA-256 |
|---|---|
| Approved candidate JSONL | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Training-fitted tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Random initialization checkpoint | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| 100-step checkpoint | `b2d4b7a3e35affe398b2e269f7b2dd7f1d9d86e528f2d2d8148d7a887e2620eb` |
| Step-zero development responses | `f0b0e65425b05135e09a5602385e2f1e27f30aae3280e5fdbbda9ef894586d14` |
| 100-step development responses | `678ef8a8716ef048ff11a062a0697a43a7cccd6271c77a01887f0a6e26680675` |
| Unchanged development task set | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

Ignored local artifacts live under `training/artifacts`: `datasets/p2-request-following-v3`, `tokenizers/p2-request-following-v3`, `initializations/p2-request-following-step-zero-v3`, `pilot/p2-request-following-100step-v3`, and evaluation directories `evaluation/p2-request-following-step-zero-v3` and `evaluation/p2-request-following-100step-v3`. The exact [step-zero score](../training/artifacts/evaluation/p2-request-following-step-zero-v3/score.json) and [100-step score](../training/artifacts/evaluation/p2-request-following-100step-v3/score.json) are in those directories. The v3 checkpoint is 330,898,459 bytes. Peak allocated GPU memory was 802,490,880 bytes; peak process working set was 1,397,071,872 bytes.

The approved source bytes match the review copy, a wrong approval digest is rejected, and the pending review catalog still refuses a build. Seven focused approval/candidate tests passed. The NumPy import warning did not prevent the CUDA run or scoring. Nothing was downloaded or installed, and the $0 paid-services and 200 GiB storage limits remain in force.

## Decision

The data change removed the single-name and seven-selector pattern from the **training examples**, but the 100-step checkpoint still failed every development task. **Do not extend this checkpoint to a 300-step or two-hour run solely because held-out text loss fell.** The next small experiment should address answer learning directly: measure and compare an answer-weighted training objective or another controlled format change on this approved corpus, with the same step-zero and development tasks. That work is a new implementation decision; no longer run or final-holdout evaluation has started.
