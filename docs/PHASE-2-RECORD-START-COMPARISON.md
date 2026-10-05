# P2-03: record-start sampler comparison

Recorded October 5, 2026. **P2-02's bounded data deliverables are complete; P2-03 is in progress.** The new 100-step sampler comparison passed **0/30 development tasks**, so no two-hour run is justified by this result.

## Why the roadmap appeared stuck at P2-02

P2-02 calls for an approved, group-separated corpus and adjustments to its code/explanation mix using development failures. The [source review](PHASE-2-DATA-COLLECTION-REVIEW.md) and [data-mix review](PHASE-2-DATA-MIX-REVIEW.md) record the family-stratified source collection. The later [failure review](PHASE-2-FAILURE-GAP-REVIEW.md), explicit [owner approval](../training/phase2/approvals/p2-02-request-following-v3.json), and [234-example build report](PHASE-2-FAILURE-GAP-100-STEP-REPORT.md) record the revised request-to-code corpus, group-separated 156/78 split, training-fitted tokenizer, checked prompt prefixes/EOS/context budgets, scratch initialization, and matched development results.

Those deliverables meet the current data milestone at this small pilot scale. The corpus remains tiny and template-based; completing P2-02 does not establish sufficient training data for useful coding. More data can be proposed later if evidence warrants it.

The roadmap conflated the unmet Phase 2 coding gate with completion of P2-02's data work. It also retained stale “current” and “latest” labels on older corpus versions. Answer weighting, the three-example learning probe, and sampling comparisons are P2-03 training-configuration investigations. They should not keep the data milestone open indefinitely. Their original reports and approvals remain part of the history.

P2-03 is **not complete**: no useful configuration has been selected. P2-01's behavior/browser checks and final evaluation remain outstanding. P2-04's longer training and the overall Phase 2 capability gate remain deferred.

## Controlled change

The [sampler audit](PHASE-2-PACKED-WINDOW-EXPOSURE-AUDIT.md) found only 14 of 1,600 ordinary random windows started exactly at a prompt. The new `record-start-v1` sampler selects uniformly, with replacement, from verified training-record starts. At the end of the packed corpus it wraps through the final EOS to the first training prompt. It never samples validation tokens. Every input/target pair remains a one-token shift with 512 target positions.

The [implementation](../training/src/plex_training/record_sampling.py) checks the training JSONL identity and reconstructs every indexed record with the matching tokenizer. It rejects changed offsets, row counts, token bytes, invalid prompt formats, and first records too long for the window. The checkpoint records the sampler kind, index hash, text hash, selection policy, and wrap policy. Resume validation rejects a different sampler or a legacy checkpoint whose original policy cannot establish that continuation. Ordinary sampling remains the default. This experimental pilot option requires ordinary loss, a matching built dataset, at most 100 steps, and at most ten minutes.

Shared settings were unchanged: approved 234-example v3 corpus, 1,509-entry tokenizer, 27,566,080-parameter model, random step-zero initialization and seed 1337, 512-token context, micro-batch 1, accumulation 16, ordinary next-token loss, AdamW learning rate 0.0003, betas 0.9/0.95, weight decay 0.1, epsilon 1e-8, dropout 0.1, and 100 optimizer updates. Both arms processed **819,200 target positions**. The new arm used all 156 records as first records, with 3–18 selections each; 30/1,600 windows wrapped at EOF.

This changes which windows are drawn and their boundary distribution. Later records within a window still have preceding context and nonzero positions. Circular packing also adds a final-to-first training-record transition. This is not a complete isolation of positional effects, nor is one seed enough to establish a general ranking of samplers.

## Matched results

Both checkpoints used the unchanged 30-task development set, greedy decoding, and the same per-language generation limits. Evaluation performs static contract checks and Node `--check` syntax checks; generated JavaScript is never executed.

| Measure | Ordinary random windows | Record-start windows |
|---|---:|---:|
| Complete development tasks | 0/30 | 0/30 |
| Static checks passed / total | 35/151 | 32/152 |
| HTML / CSS / JavaScript syntax passes | 1 / 2 / 0 | 0 / 2 / 0 |
| Truncated development outputs | 0/30 | 1/30 |
| Held-out next-token loss before training | 7.45021 | 7.45021 |
| Held-out next-token loss after training | 3.28499 | 3.38407 |
| Training wall time | 14.52 seconds | 15.11 seconds |
| Exact or full-static seen training answers | 0/156 | 0/156 |
| Seen training syntax passes | 11/156 | 39/156 |
| Exact or full-static corpus validation answers | 0/78 | 0/78 |
| Corpus validation syntax passes | 6/78 | 7/78 |

The check total adds a failing truncation check when needed; these totals are not a fixed-denominator quality benchmark. The new diagnostic had one truncated training answer and one truncated corpus-validation answer. Syntax improved on some seen prompts, but neither exact reproduction nor full task completion improved. Held-out text loss and complete-task results do not favor adopting this sampler.

The CUDA training checkpoint is 330,898,779 bytes. Peak allocated GPU memory was 802,490,880 bytes, reserved memory 861,929,472 bytes, and process peak working set 1,399,767,040 bytes. Timing is a single local observation rather than a performance benchmark. The missing-NumPy warning did not prevent training, checkpoint loading, generation, or scoring.

## Artifacts and reproduction

| Identity | SHA-256 |
|---|---|
| Approved candidate | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Random initialization | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| Record-start checkpoint | `9bbf765ae4be074ae22f7cbd6a30b04af19c777240b5786cdbbaf23d6ceacfbc` |
| Record-start development responses | `e1ed387dcff3638e7f03b5496fbadd20d54d28ad5c4d8bb80115601747969c64` |
| Development task set | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

The ignored local artifacts are the [pilot report](../training/artifacts/pilot/p2-record-start-100step-v1/pilot-report.json), [development score](../training/artifacts/evaluation/p2-record-start-100step-v1/score.json), and [234-example diagnostic](../training/artifacts/diagnostics/p2-record-start-100step-v1/report.json). Previous artifacts were not overwritten. From the repository root, choose an unused output directory to reproduce:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --initialization training\artifacts\initializations\p2-request-following-step-zero-v3\initialization.pt `
  --output-dir pilot\p2-record-start-my-comparison `
  --sampling-policy record-start-v1 --answer-weight 1 `
  --minutes 10 --steps 100 --device cuda
```

This run is already complete; the owner does not need to repeat it. The full training suite passed 106 tests. After adding the legacy-policy rejection guard, all five sampler tests and seven resume/completion tests passed again. Checks covered exact circular input/target alignment, EOS preservation, deterministic record selection, corrupted input rejection, saved sampler identity, compatible and incompatible resume, and experimental run bounds. No downloads, installations, paid resources, or final-holdout evaluation were used.

## Next P2-03 step

Prepare a bounded **complete-record comparison** on the existing approved training split: reset context/positions per example and mask padding targets rather than concatenate later examples into the same window. Begin from the matching scratch step-zero checkpoint. Explicitly record actual non-padding target positions, updates, record exposures, memory, and time; padding must not be counted as trained tokens. The shorter sequences change the token budget, so report that limitation rather than claiming equivalence with this packed comparison.

Check seen-answer learning before a matched development evaluation. Keep the corpus, tokenizer, model size, and optimizer fixed, use a fresh output path, and retain a ten-minute ceiling. This is a proposed next implementation, not an executed result. The present evidence does not justify a two-hour run or opening the final holdout.
