# Phase 2 dataset v3 build report — P2-02

The repository owner ran the approved P2 v3 dataset build and tokenizer fit in PowerShell on 2026-10-04. This report records the CLI output supplied for those runs; the artifacts are local and ignored by Git. The v2 corpus and tokenizer remain unchanged.

## Dataset build

The build used [`training/phase2/dataset-sources.phase2-v2.json`](../training/phase2/dataset-sources.phase2-v2.json), validation percentage 30, seed 51, and the configured 200 GiB storage limit. The v2 catalog preserves the approved Microsoft and MDN source entries and adds the nine approved Codex-authored examples as three language-specific families.

| Result | Value |
|---|---:|
| Training records | 36 |
| Development records | 20 |
| Total records | 56 |
| Skipped records | 0 |
| Reported dataset bytes | 711,117 |
| Storage limit | 214,748,364,800 bytes (200 GiB) |

The artifact directory is `training/artifacts/datasets/p2-02-data-v3`. The existing catalog and source pipeline enforce the family-stratified split and preserve each project/example group intact. The CLI reported no skipped content.

## Tokenizer fit

The new `plex-byte-bpe-v1` tokenizer was trained on the v3 training split only, then used to encode and round-trip both splits.

| Result | Training | Development |
|---|---:|---:|
| Records encoded and round-tripped | 36 | 20 |
| Text bytes | 445,981 | 207,411 |
| Tokens, including record end markers | 103,902 | 56,884 |
| Token file SHA-256 | `236c2c6c1698eb3be84eb512912c4e92737c1ec53ba03d9ee6484a3cd61b434f` | `b05942f83fcf7316bd6f3d494edb4f3d68a9009e3a5bb5f615f7dcb66f95ca08` |
| Source JSONL SHA-256 | `528d326e59032a2c346301e7bdd8e756e17bb2b74b9fef5467a7bb723121940a` | `85f26cbbc21aaa4e9759b5c0939f47f8cc844c7f0b39edf725c0b23ee07176ac` |

The tokenizer learned 8,191 entries within the model's 16,384-token capacity. Its SHA-256 is `bd0488ff065d577097d14a933d8d3580f3e8d33d1f8dc13d0d00585ea229a7be`; the reported bundle size is 906,368 bytes. Seven representative round-trip checks passed. The tokenizer artifact is at `training/artifacts/tokenizers/p2-02-data-v3`.

## Matching step-zero initialization


## Step-zero development evaluation

On 2026-10-04, the owner generated responses to all 30 development tasks using CUDA, the step-zero checkpoint above, and the matching v3 tokenizer. The generation report confirms checkpoint SHA-256 `a4c3733f36beeaf964aaf633d08ff9695578d6fc20a0e6c179fbbe72007ec774`, step `0`, and `pretrainedCheckpointLoaded: false`. The output is `training/artifacts/evaluation/p2-dev-step-zero-v3/`; the responses SHA-256 is `622b2c05d596e854e15460e257b1ad518a55e2c11d63526b13cb8f655ea1a43f`.

The owner then scored those responses with `plex-static-task-evaluator-v1` against task set `p2-01b-dev-v1` (SHA-256 `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4`). The result was **0/30 complete tasks passed** (0% overall; descriptive Wilson 95% interval 0–11.35%). Each language scored 0/10. The evaluator reported 40/180 checks passed and 29/30 outputs truncated: 9/10 HTML, 10/10 CSS, and 10/10 JavaScript. All 10 HTML outputs passed the HTML parser; CSS syntax and JavaScript `node --check` passed 0/10 each. There were no missing, empty, over-limit, timed-out, or unavailable responses. JavaScript behavior was not executed.

This is the untrained random checkpoint's static baseline. It verifies that generation and scoring are connected, and gives a point of comparison for a later trained checkpoint. The high truncation rate and random weights make it unsuitable as evidence that the v3 data or a trained model succeeds or fails.

These CLI summaries establish successful data construction and tokenizer encoding. They do not establish coding capability. No model weights were initialized or trained in these runs. The v3 token counts use a different tokenizer from v2 and should not be compared directly with v2 token totals. A per-language, per-source-family, and code-versus-explanation breakdown remains pending, as does a matching step-zero development evaluation. The development evaluator checks JavaScript syntax but does not execute generated code.

## Next step

The step-zero result is the untrained baseline. The completed 10-minute real-corpus check is recorded in the [training report](PHASE-2-TRAINING-CHECK-V3-REPORT.md). Do not treat the step-zero score as a capability claim; the trained checkpoint still needs evaluation on the same 30 tasks with the same decoding settings.
