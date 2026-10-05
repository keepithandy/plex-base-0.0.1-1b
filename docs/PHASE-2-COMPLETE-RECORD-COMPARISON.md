# P2-03: complete-record comparison

Recorded October 5, 2026. The complete-record runner is implemented and the bounded 100-update CUDA comparison is complete. **Three seen training answers were reproduced exactly; four passed their full static checks. Development tasks remain 0/30.** P2-03 remains in progress; no useful general coding configuration has been selected.

## Change and controls

The [record-start comparison](PHASE-2-RECORD-START-COMPARISON.md) still concatenated later examples into each 512-token window. The new `complete-record-v1` option in [the verified sampler](../training/src/plex_training/record_sampling.py) instead places one complete training record in each batch row. Each row starts at position zero, ends at its own EOS target, and never receives context from another example. Records that exceed the configured context are rejected rather than truncated.

Batch rows are right-padded only to the longest selected record. Padding targets receive zero loss weight. Causal attention keeps those later padding positions invisible to real tokens; separate batch rows cannot attend to each other. Ordinary next-token loss covers real prompt and answer/EOS targets. The loss is averaged over real targets within each micro-batch, then averaged over the accumulation steps. With micro-batch 1, that gives each sampled record equal loss weight regardless of length. No model architecture or parameter count was changed.

The [runner](../training/src/plex_training/runner.py) now counts actual non-padding target positions after completed optimizer updates, rather than assuming every sequence is 512 tokens. It saves that count in checkpoints and reports padding separately. Resume checks replay the pinned record selections to verify both variable-length token progress and sampling RNG state. Compatible runner-level continuation was tested against uninterrupted training; the existing `pilot-resume` CLI still reconstructs ordinary packed sampling and therefore rejects these experimental checkpoints. CLI continuation for complete records is a next implementation task.

Shared controls were the existing owner-approved 234-example v3 candidate, group-separated 156/78 corpus, training-fitted 1,509-entry tokenizer, matching scratch step-zero weights, seed 1337, 27,566,080 parameters, 512-token maximum context, dropout 0.1, micro-batch 1, accumulation 16, 100 optimizer updates, and ordinary next-token loss. AdamW settings remained learning rate 0.0003, betas 0.9/0.95, weight decay 0.1, epsilon 1e-8, and gradient clipping norm 1.0. Training used only approved training records.

All 156 records were selected, 3–18 times each, across 1,600 sampled examples. The draw order matches the record-start arm's first-record selections. This run trained on **149,760 real target positions**, 18.28% of the packed arms' 819,200 positions. No padding was necessary in this micro-batch-1 run; mixed-length padded batches were checked in tests. The comparison fixes updates and first-record selections, **not total training tokens**. Reset context, sequence lengths, per-record loss weighting, and dropout draws differ from packed training, so the result does not isolate a single causal effect.

## Saved-answer diagnostic, then development evaluation

The saved checkpoint was loaded and checked on the approved corpus prompts before development response generation. Exact reproduction requires the reference text and EOS; static passes use the existing structural/contract checks. These are separate measures.

| Measure | Ordinary packed windows | Record-start packed windows | Complete records |
|---|---:|---:|---:|
| Exact seen training answers | 0/156 | 0/156 | **3/156** |
| Full-static seen training answers | 0/156 | 0/156 | **4/156** |
| Seen training syntax passes | 11/156 | 39/156 | 83/156 |
| Exact / full-static corpus validation answers | 0 / 0 of 78 | 0 / 0 of 78 | 0 / 0 of 78 |
| Corpus validation syntax passes | 6/78 | 7/78 | 23/78 |
| Complete development tasks | 0/30 | 0/30 | **0/30** |
| Development checks passed / total | 35/151 | 32/152 | 45/151 |
| Development HTML / CSS / JavaScript syntax passes | 1 / 2 / 0 | 0 / 2 / 0 | 0 / 7 / 7 |
| Truncated development outputs | 0 | 1 | 0 |
| Real target positions | 819,200 | 819,200 | 149,760 |
| Training wall time | 14.52 s | 15.11 s | 31.22 s |
| Held-out packed next-token loss before | 7.45021 | 7.45021 | 7.45021 |
| Held-out packed next-token loss after | 3.28499 | 3.38407 | 4.32042 |

The three exactly reproduced training answers are `gap-html-bidi-02`, `gap-html-progress-01`, and `gap-html-progress-04`. For example, the progress record generated `<progress value="35" max="100"></progress>` and stopped at EOS. These successes cover two HTML template groups, not all languages. The fourth static pass, `gap-html-bidi-01`, added a paragraph wrapper that was absent from its reference; its structural checks accepted it, but exact reproduction did not. Thus four static passes must not be described as four exact answers.

Training and corpus-validation diagnostics each had no empty or truncated responses. The matched development evaluation also had no missing, empty, truncated, unavailable, or timed-out outputs. A clamp request still produced an unrelated `minutesToUnits` function calling `Math.slice(value)`: syntactically accepted JavaScript does not imply correct behavior. Generated code was never executed; JavaScript was parsed with Node `--check`, and HTML/CSS checks remained static. The development check total varies when the evaluator adds a failing truncation check; partial-check totals are secondary diagnostics, not the release gate. The final holdout was not built or evaluated.

The complete-record run used 695,014,912 bytes peak allocated GPU memory, 792,723,456 bytes reserved GPU memory, and 1,435,439,104 bytes process peak working set. Its saved checkpoint is 330,899,035 bytes. Time and throughput are single-run local observations, not reliable speed comparisons. The missing-NumPy warning did not prevent execution.

## Verified artifacts and reproduction

| Identity | SHA-256 |
|---|---|
| Approved candidate | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Random initialization | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| Complete-record checkpoint | `0737e617facc7ae9d8e3f1c9c6888cdcc066183d40a711f231933161de7e4e2e` |
| Complete-record development responses | `0f6f5b7ec49d218bee5e8dd12a9223503229976be6ce63dfceb8100a44a1263a` |
| Unchanged development task set | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

The ignored local artifacts are the [pilot report](../training/artifacts/pilot/p2-complete-record-100step-v1/pilot-report.json), [saved-answer diagnostic](../training/artifacts/diagnostics/p2-complete-record-100step-v1/report.json), [development responses](../training/artifacts/evaluation/p2-complete-record-100step-v1/responses.jsonl), and [development score](../training/artifacts/evaluation/p2-complete-record-100step-v1/score.json). Existing sources and checkpoint outputs were preserved. This experiment is already run; the owner does not need to repeat it. To reproduce, use a fresh output directory from the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --initialization training\artifacts\initializations\p2-request-following-step-zero-v3\initialization.pt `
  --output-dir pilot\p2-complete-record-my-comparison `
  --sampling-policy complete-record-v1 --answer-weight 1 `
  --minutes 10 --steps 100 --device cuda
```

The experimental option requires its matching built dataset, ordinary loss, at most 100 updates, and at most ten minutes. The full training suite passed **111 tests**, including record isolation/EOS, zero padding loss, unchanged real-token logits under right padding, actual token accounting, exact variable-length CPU resume equivalence, corrupted progress rejection, sampler-change rejection, and experiment bounds. No dependency installations, downloads, paid services, or long training runs were used.

## Decision and next milestone work

Keep P2-03 open. Complete-record training has shown a small amount of seen-answer learning on the broad approved corpus; it has not improved complete-task performance or justified P2-04's longer run. The smaller non-padding token budget also means this run cannot rule out insufficient exposure as a limiting factor.

Next, prepare a **bounded complete-record continuation and learning-curve check**: restore the same checkpoint, tokenizer, corpus, sampler, optimizer, and RNG into a fresh output directory, then permit at most 100 additional updates within ten minutes. Record cumulative real target positions and compare seen exact answers at cumulative steps 100 and 200. Run the same development comparison afterward to distinguish memorization from generalization. Do not change the corpus, model, or objective in that comparison. This continuation is proposed work, not an executed result; no second segment or two-hour run has started. A static-check gain or lower loss alone will not pass the coding-quality gate.
