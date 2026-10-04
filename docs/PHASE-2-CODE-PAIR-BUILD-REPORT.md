# P2-02 approved code-pair corpus and baseline

The owner approved these exact 36 examples for local training: **“Approve the 36 examples for local training.”** The [approval record](../training/phase2/approvals/p2-02-code-pairs-v2.json) binds that statement to the canonical candidate digest. [Approved source texts and catalog](../training/phase2/data/authored/p2-02-code-pairs-v2/dataset-sources.approved.json) are now materialized separately from the immutable pending-review snapshot. No external text was added and no public license grant is asserted.

## Completed preparation

The separate `p2-code-pairs-v2` dataset built with 36 records, 24 training and 12 validation, no skipped records, and 37,408 output bytes. Each language contributes eight training and four validation examples. Related variants remain in one semantic group and split, using seed 51 and 30% validation groups. This deliberately tiny corpus tests request-to-code formatting; it is not enough to establish general coding ability.

The tokenizer was fitted on the training split only, has 874 entries within the unchanged 16,384-entry model capacity, and round-tripped every record. [The recorded bundle check](../training/phase2/data/authored/p2-02-code-pairs-v2/bundle-readiness.json) verified each exact approved text, split, inference prefix, packed token sequence, and EOS boundary.

| Measurement | Training | Validation |
|---|---:|---:|
| Records | 24 | 12 |
| Packed tokens, including EOS | 2,523 | 2,083 |
| Prompt tokens | 1,701 | 1,241 |
| Answer tokens, including leading newline | 798 | 830 |
| EOS markers | 24 | 12 |
| Largest complete record, including EOS | 131 | 249 |

All records fit the 512-token context. Across both splits, maximum answers including EOS are 68 HTML, 63 CSS, and 127 JavaScript tokens, within unchanged 192/128/192 generation caps. The largest development prompt is 116 tokens. Answers occupy 31.6% of training token positions; this does not meet or replace the broader code-heavy base-corpus target.

Fresh initialization used seed 1337 and 27,566,080 parameters, with `pretrainedCheckpointLoaded: false`. The installed local environment reported Windows, an RTX 4080 SUPER, and CUDA availability. The new checkpoint generated all 30 unchanged development responses on CUDA and was statically scored: **0/30 complete tasks, 40/179 checks, 28 truncated outputs**, no missing or empty responses and no evaluator timeouts. HTML syntax passed 10/10; CSS and JavaScript syntax passed 0/10 each. JavaScript behavior was not executed. This is the matching step-zero baseline, not a trained result. The final holdout remains unopened.

## Identities and local artifacts

| Artifact | SHA-256 |
|---|---|
| Approved candidate JSONL | `88c35a023b0093cb177552c4ddc45533e92d63e0d006f26dbcdad2bd0a2ef72a` |
| Dataset manifest | `63ed4adf0e31f5b2fc770f9bb6b838318e88cc2848b396a72c2419f3c88cc45d` |
| Tokenizer | `0099457ad9b5384a2a9122a9d9ad654a78183af0013b2c5f670f182cb4c8d71b` |
| Tokenizer bundle manifest | `eaa51ba7265017c0a691d72d204e95b7b1318f32a140e772fd550ece74d63c73` |
| Step-zero checkpoint | `825247e0419f18a31f45d02cf00afcafdc6392a94b6bf9adde4ea52c92222113` |
| Initial model weights | `b4fb396cc608249d1106a2bc9968f20af4579745c080759d6bc82f7ff8559546` |
| Step-zero development responses | `93e10b004dee3fe097e090a72b6d341de930961d1b99f3b11945394d00985641` |
| Unchanged development tasks | `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4` |

Artifacts are local and ignored by Git, beneath `training/artifacts`: dataset `datasets/p2-code-pairs-v2`, tokenizer `tokenizers/p2-code-pairs-v2`, checkpoint `initializations/p2-code-pairs-step-zero-v2/initialization.pt`, and baseline `evaluation/p2-code-pairs-step-zero-v2/{run-manifest.json,responses.jsonl,score.json}`. The approval, approved sources, and readiness report are versioned. Prior v3 artifacts remain separate.

## Easiest next step

Verification passed: 39 targeted tests (nine candidate, three approval, eleven dataset, sixteen benchmark), plus exact source/token/EOS checks, every tokenizer roundtrip, and Markdown/JSON/Python delivery checks. Core model and training code was unchanged; the full model/training suite was not rerun.

Preparation and baseline scoring are already done. From the repository root, run this ten-minute diagnostic with an unused output directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizers\p2-code-pairs-v2 `
  --initialization training\artifacts\initializations\p2-code-pairs-step-zero-v2\initialization.pt `
  --output-dir pilot\p2-code-pairs-10m-v1 `
  --minutes 10 `
  --device cuda
```

Training has not started. After the run, generate and score the trained checkpoint on the same development tasks before deciding on longer training:

```powershell
uv run --project training --no-sync python -m plex_training.cli task-generate `
  --checkpoint training\artifacts\pilot\p2-code-pairs-10m-v1\pilot-checkpoint.pt `
  --bundle-dir training\artifacts\tokenizers\p2-code-pairs-v2 `
  --output-dir evaluation\p2-code-pairs-10m-v1 `
  --device cuda
uv run --project training --no-sync python -m plex_training.cli task-evaluate `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --responses training\artifacts\evaluation\p2-code-pairs-10m-v1\responses.jsonl `
  --report training\artifacts\evaluation\p2-code-pairs-10m-v1\score.json
```

Compare complete tasks, syntax, truncation/EOS, validation loss, and resource use independently. The NumPy warning did not prevent initialization or evaluation; no dependency installation was performed. Paid services remain $0 and the storage allocation remains 200 GiB.
