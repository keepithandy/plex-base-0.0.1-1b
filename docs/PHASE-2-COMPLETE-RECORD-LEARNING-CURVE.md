# P2-03: complete-record continuation and learning curve

Recorded October 5, 2026. The bounded continuation advanced the existing complete-record checkpoint from **step 100 to step 200** in **500.47 seconds**, within its ten-minute cap. Exact seen training answers rose from **3/156 to 52/156**, but corpus validation stayed **0/78** and development tasks stayed **0/30**. The original checkpoint is unchanged. P2-03 remains in progress; the Phase 2 coding-quality gate is unmet.

## Implementation and fixed controls

The `pilot-resume` command now reconstructs `complete-record-v1` from the saved training settings and requires the matching `--dataset-dir`. Before reserving a fresh output directory, it verifies the dataset manifest, training text, tokenizer/index, sampler identity, optimizer settings, batch settings, sampling RNG, and actual token progress. It then restores model weights, optimizer moments, and CPU/CUDA random-generator state, copies the matching tokenizer bundle into the new directory, and saves a separate checkpoint and report. Ordinary packed continuation remains supported; record-start packed and answer-weighted continuation are not enabled by this change.

The experiment retained the owner-approved 234-example v3 candidate, group-separated 156/78 corpus, training-fitted 1,509-entry tokenizer, original scratch initialization, model architecture, ordinary next-token objective, complete-record sampler, and optimizer. The model has 27,566,080 parameters, a 512-token maximum context, six layers, width 512, eight heads, feed-forward width 2,048, and dropout 0.1. Training uses micro-batch 1, accumulation 16, seed 1337, AdamW learning rate 0.0003, betas 0.9/0.95, weight decay 0.1, epsilon 1e-8, and gradient clipping norm 1.0. Each example starts at position zero and stops at its own EOS; padding has zero loss weight. Corpus validation uses the unchanged packed next-token loss path.

Only the approved training split received gradient updates. The continuation sampled another 1,600 examples, selecting all 156 training records between 1 and 20 times. It added **150,199 real target positions**, bringing cumulative progress from 149,760 to **299,959**. Padding target count was zero. These counts are actual next-token targets, not an estimate based on the maximum context length.

## Runtime correction and attempt history

The first continuation attempt, `p2-complete-record-200step-v1`, was interrupted while investigating slow CUDA execution. Its logs and any periodic checkpoint were retained, and `aborted-attempt.json` labels it an excluded runtime diagnostic. Its last logged update was step 180; that is not a claim about its last completed update. The accepted comparison uses only the separate completed `p2-complete-record-200step-v2` run, restored again from the unchanged step-100 source. Compute spent in the discarded attempt is additional to the accepted segment's 500.47 seconds.

Checkpoint mapping to CUDA also moved ordinary AdamW's scalar step counters to CUDA. `restore_optimizer` now returns those counters to CPU for non-capturable, non-fused AdamW, while keeping moment tensors on the parameter device. This matches fresh optimizer state placement; fused/capturable counters keep their own placement. A CUDA test verifies the placement and an identical next parameter update against uninterrupted AdamW. This is a correctness-preserving placement correction, not a demonstrated explanation for all observed slowdown.

Other GPU work was active: a read-only snapshot showed 99% aggregate GPU utilization and 9,263 MiB used while Plex reserved less than 0.8 GiB. The owner confirmed other GPU-heavy work and asked to keep it running. Those applications were left running. Timings here are observations under contention, not a speed benchmark or a measured estimate for an idle machine. No additional training segment followed the accepted step-200 run.

## Learning results

The saved-checkpoint diagnostic was run on the approved corpus prompts first, followed by the unchanged 30 development tasks. Both checkpoints used CUDA, greedy decoding, seed 1337, the same prompt template/output contracts, and generation caps of 192 tokens for HTML/JavaScript and 128 for CSS. Exact reproduction requires matching reference text and EOS. Static task passes and syntax passes are separate measures; generated JavaScript is only parsed with Node `--check`, never executed.

| Measure | Step 100 | Step 200 |
|---|---:|---:|
| Exact seen training answers | 3/156 | **52/156** |
| Exact training HTML / CSS / JavaScript answers | 3/54 / 0/54 / 0/48 | **27/54 / 10/54 / 15/48** |
| Full-static seen training passes | 4/156 | 54/156 |
| Seen training syntax passes | 83/156 | 122/156 |
| Exact / full-static corpus validation answers | 0 / 0 of 78 | 0 / 0 of 78 |
| Corpus validation syntax passes | 23/78 | 40/78 |
| Complete development tasks | 0/30 | **0/30** |
| Development passes per language | HTML 0/10; CSS 0/10; JavaScript 0/10 | HTML 0/10; CSS 0/10; JavaScript 0/10 |
| Development static checks passed / total | 45/151 | 45/151 |
| Development HTML / CSS / JavaScript syntax passes | 0 / 7 / 7 | 0 / 5 / 5 |
| Empty / truncated development outputs | 0 / 0 | 0 / 0 |
| Cumulative optimizer updates | 100 | 200 |
| Real targets in this segment | 149,760 | 150,199 |
| Cumulative real targets | 149,760 | **299,959** |
| Held-out packed next-token loss after | 4.32042 | **4.47331** |

All three step-100 exact answers remained exact at step 200. Exact successes now include all three languages: `gap-html-ruby-01` returned `<ruby>Kyoto<rt>Kyo-to</rt></ruby>`; `gap-css-logical-border-03` returned the requested `.top-edge` logical border rule; `gap-javascript-division-01` returned `quotientTowardZero(a, b)` with `Math.trunc(a / b)`. These are supplied training answers, not newly solved tasks.

The two additional static passes were not exact. `gap-html-bidi-01` still added an extra paragraph wrapper. `gap-html-heading-group-04` generated different paragraph wording while satisfying its limited structural checks. Do not describe 54 static passes as 54 exact answers or verified browser behavior.

The development outputs still violate requests. Primary navigation generated malformed markup with unrelated names and links. The card-flex task returned `.actions { display: flex; gap: center; }`, missing its requested selector and valid declarations. The unique-by-id request returned `firstLong(items)` with a numeric filter; Node accepted its syntax, but it did not implement the requested function. Development syntax passes fell from 14 to 10 while complete-task passes and aggregate static-check counts stayed unchanged. Partial-check totals are secondary diagnostics, not the coding-quality gate.

No corpus diagnostic outputs were empty, truncated, or reference-capped at either checkpoint. The step-200 development evaluation had no missing, empty, truncated, over-limit, unavailable, or timed-out outputs. There was no decoding-limit failure concealing a complete-task gain. HTML/CSS checks remain static, JavaScript behavior was not executed, and the 60-task final holdout was neither built nor evaluated.

The larger seen-answer count demonstrates that this training path can learn more of its supplied answers with additional exposure. Zero corpus-validation/development passes and the held-out loss increase do not demonstrate useful generalization. The pattern is consistent with memorization/overfitting; this two-point learning curve does not identify whether data coverage, request binding, training objective, model capacity, or context is the main remaining limit.

## Verification and artifacts

All **116 training-workspace tests passed**, including actual CUDA optimizer placement/update equivalence, exact variable-length CPU continuation, CLI/API wiring, rejection of mismatched training text/settings/token progress before output creation, sampler reconstruction, copied-bundle packaging, ordinary-pilot compatibility, and source preservation. These checks use small temporary fixtures; they do not establish general coding capability.

The accepted continuation records `resumeCheckPassed: true`, 100 additional updates, cumulative step 200, `interrupted: false`, matching tokenizer/dataset records, and `sourceCheckpointUnchanged: true`. Independent read-only verification confirmed both checkpoint hashes, identical saved training settings/data/tokenizer/initialization identities, all 12 copied bundle files byte-identical, and sampler replay matching 299,959 targets plus the saved RNG state. Development generation manifests have identical decoding settings, model configuration, tokenizer, and initial weight identity. The response hash matches both generation manifest and score; the task-set hash remains unchanged.

GPU peak allocated/reserved memory was 694,333,440 / 748,683,264 bytes; peak process working set was 1,399,078,912 bytes. The new checkpoint occupies 330,899,099 bytes. No dependency installation, dataset download, paid service, or two-hour run was used.

| Identity | SHA-256 |
|---|---|
| Approved candidate | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Tokenizer bundle manifest | `4f2bc31f1bc6c913ca71aef62a2e1f4b1cab5aac6f6d8d083d21a38b6eb3cdcc` |
| Scratch initialization | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| Preserved step-100 checkpoint | `0737e617facc7ae9d8e3f1c9c6888cdcc066183d40a711f231933161de7e4e2e` |
| Accepted step-200 checkpoint | `348423a1dcb58639c1384216b67318144658d33e4e37ae48f76a121c851a692b` |
| Step-200 development responses | `24f2e7f4a9fca24b1b3ceef10b4cab62521789e31e8960c5a082b27ecc494d08` |
| Unchanged development task set | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

The ignored local [resume report](../training/artifacts/pilot/p2-complete-record-200step-v2/resume-report.json), [checkpoint](../training/artifacts/pilot/p2-complete-record-200step-v2/resumed-checkpoint.pt), [matching tokenizer](../training/artifacts/pilot/p2-complete-record-200step-v2/tokenizer/manifest.json), [saved-answer diagnostic](../training/artifacts/diagnostics/p2-complete-record-200step-v2/report.json), [development responses](../training/artifacts/evaluation/p2-complete-record-200step-v2/responses.jsonl), and [development score](../training/artifacts/evaluation/p2-complete-record-200step-v2/score.json) are preserved alongside the original [step-100 comparison](PHASE-2-COMPLETE-RECORD-COMPARISON.md).

## Reproduction

The continuation has already finished; the owner does not need to repeat it. To reproduce into a new directory from the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-resume `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --checkpoint training\artifacts\pilot\p2-complete-record-100step-v1\pilot-checkpoint.pt `
  --output-dir pilot\p2-complete-record-my-continuation `
  --steps 100 --minutes 10 --device cuda
```

The command refuses an existing output directory and caps the segment at 100 additional updates and ten minutes. It does not extend itself or overwrite its source. The final holdout remains closed.

## Decision and next task

Follow-up: the owner completed the [transfer diagnostic](PHASE-2-TRANSFER-DIAGNOSTIC.md): step 200 passed all six learned originals and none of twelve variations. The [binding audit](PHASE-2-BINDING-VARIATION-AUDIT.md) is also complete and records the next small candidate to prepare. The proposal below records the earlier decision made from this learning curve.

This continuation implementation and learning-curve check are complete. **Keep P2-03 open and defer P2-04's two-hour run.** P2-02 remains complete at the approved pilot-data scale; successful memorization does not establish data sufficiency or a useful training configuration. No additional training is needed from the owner now.

Next, prepare a small **saved-checkpoint request-following transfer diagnostic** within P2-03. Take a few training families that step 200 now reproduces exactly and vary only requested names, selectors, labels, or literal values in new evaluation prompts. Compare unchanged originals with these variations using the saved step-100/step-200 checkpoints. Check explicit requested properties and syntax; do not call static JavaScript checks behavior tests. Keep these evaluation-only variants out of training/tokenizer data, retain the same decoding limits, and leave the final holdout closed. This can distinguish failures on modest changes within learned families from failures on the broader development task structures without another training run. It has not yet been implemented or executed.

Use that diagnostic to select the next bounded configuration comparison, rather than automatically adding steps or changing several variables at once. Training objectives, model sizes, and context settings remain candidates for P2-03; no configuration has met the complete-task gate yet.
