# Phase 2 v3 training check — P2-02/P2-03 preflight

The repository owner ran a ten-minute training check on the approved v3 corpus on 2026-10-04. This report records the user-supplied CLI output; the checkpoint and full pilot report remain local ignored artifacts.

## Run identity

| Field | Value |
|---|---|
| Initialization | `training/artifacts/initializations/p2-step-zero-v3/initialization.pt` |
| Initialization SHA-256 | `a4c3733f36beeaf964aaf633d08ff9695578d6fc20a0e6c179fbbe72007ec774` |
| Dataset | P2 v3; 36 training records and 20 validation records |
| Train token count | 103,902 |
| Validation token count | 56,884 |
| Dataset manifest SHA-256 | `cf0f75c4c93445993300b0e2965fce96e60c3e929efb87ace1d783c58363ec5f` |
| Tokenizer SHA-256 | `bd0488ff065d577097d14a933d8d3580f3e8d33d1f8dc13d0d00585ea229a7be` |
| Tokenizer bundle manifest SHA-256 | `8f75ec1adb6f6cd8a8386f4ac0b923f140629ba90d4eb75e22fe82791cbb1ae6` |

The initialization record identifies fresh random weights with seed 1337 and `pretrainedCheckpointLoaded: false`. Training used CUDA, micro-batch 1, gradient accumulation 16, context length 512, AdamW at `3e-4`, and a constant learning-rate schedule.

## Results

| Metric | Result |
|---|---:|
| Requested duration | 10 minutes |
| Elapsed | 601.37 seconds |
| Finished steps | 922 |
| Tokens processed | 7,553,024 |
| Throughput | 12,559.64 tokens/second |
| Recent training loss | 0.9067 |
| Validation loss before | 9.1694 |
| Validation loss after | 6.4759 |
| Validation improved | Yes |
| Peak GPU allocated / reserved | 802,490,880 / 853,540,864 bytes |
| Peak process working set | 1,397,747,712 bytes |
| Checkpoint | `training/artifacts/pilot/p2-v3-10m-v1/pilot-checkpoint.pt` (330,898,523 bytes) |
| Checkpoint SHA-256 | `80287a0b5871bb13d61546aa3fd910a745270210e7b5a3872bf6a0fa15ff1608` |

The runner reported `run_finished`, `interrupted: false`, and `validationImproved: true`. Its report field says `P1-18 bounded real-corpus pilot`, the legacy literal present when this run was made. The P2 v3 dataset, tokenizer, initialization, and artifact paths identify this invocation as the P2 v3 ten-minute check. The runner now uses a phase-neutral `bounded real-corpus pilot` label for future reports.

Lower held-out language-model loss shows that training reduced next-token prediction loss on this small corpus. It does not establish that generated code meets task requirements. The step-zero static development score was 0/30, so compare this trained checkpoint against that baseline using the same 30 prompts and decoding settings.

## Next step

On 2026-10-04, the owner generated responses to all 30 development tasks from the step-922 checkpoint above, using CUDA and the same v3 tokenizer. The generation output confirms checkpoint SHA-256 `80287a0b5871bb13d61546aa3fd910a745270210e7b5a3872bf6a0fa15ff1608` and `pretrainedCheckpointLoaded: false`. The response file is `training/artifacts/evaluation/p2-dev-v3-10m-v1/responses.jsonl`, SHA-256 `8af1a30da91b45db19fe86065716d8faa59858a3e68a82edb7e9a8ed74cee95c`.

The owner scored the responses against `p2-01b-dev-v1`, the same 30-task development set used for step-zero. The score file is `training/artifacts/evaluation/p2-dev-v3-10m-v1/score.json`, SHA-256 `c230cc5ec85835ce5452fb9e27448d21eb333fecfca032672dbb9727b615c34e`. It reports:

| Metric | Trained step 922 | Step-zero baseline |
|---|---:|---:|
| Complete tasks passed | 0/30 | 0/30 |
| Individual checks passed | 20/181 | 40/180 |
| Truncated outputs | 30/30 | 29/30 |
| HTML syntax | 10/10 | 10/10 |
| CSS syntax | 0/10 | 0/10 |
| JavaScript syntax | 0/10 | 0/10 |

There were no missing, empty, over-limit, timed-out, or unavailable outputs. Ten outputs passed the no-Markdown-fence check; every output was still marked truncated because generation did not emit EOS within the task's configured token cap. Inspection of the first generated HTML responses shows Markdown/Mermaid tutorial text instead of the requested HTML fragment. The static checks show no complete-task improvement over step-zero and fewer passing checks overall. They do not test JavaScript behavior.

The decrease in held-out language-model loss did not transfer to this coding-task check. Do not start the two-hour run yet. The measured v3 training split is 76.3% Markdown by tokenizer positions; its six authored task/solution records contribute only 719 tokens (0.7%). The model's first HTML responses begin with Markdown/Mermaid tutorial text, while the evaluator requests direct code output. Prepare a small, reviewed request-to-code data-mix proposal using only the development failures as guidance; preserve the final holdout and rerun step-zero plus a bounded training check before spending more training time. The exact split analysis is in the [P2 data-mix review](PHASE-2-DATA-MIX-REVIEW.md).
