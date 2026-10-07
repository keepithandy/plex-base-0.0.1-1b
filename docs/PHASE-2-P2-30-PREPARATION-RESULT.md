# P2-30 preparation result — October 7, 2026

**Preparation gate passed. Task fine-tuning remains unauthorized.** The approved task split was repacked with the frozen Web tokenizer and bound to a task-stage step-zero checkpoint containing unchanged P2-29 weights. No P2-30 research optimizer update occurred. The final project holdout stayed sealed; Phase 3 has not started.

Full evidence and executed commands are in [p2-30-preparation-result.json](../training/pretraining/p2-30-preparation-result.json). The separate [first-run draft](../training/pretraining/p2-30-first-finetune-contract.draft.json) has `modelTrainingAuthorized: false`. Committing this draft does not authorize training.

## Dataset and task bundle

The rebuild exactly reproduced all approved identities: **234 total / 156 train / 78 validation records**, unique record IDs within each split, and **zero overlapping record IDs**. No expected hash changed.

| Artifact | SHA-256 |
|---|---|
| Dataset manifest | `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea` |
| Train JSONL | `05fb9b35277b979ef45473af5b2a2c98bef31ee2c1c3133f0af0c68d7cfba554` |
| Validation JSONL | `1e999896304a92c3d39503246f08e1736dc9cbf7c91cb9e0f85d195f34aba3ce` |
| Frozen P2-27 tokenizer | `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697` |
| Task bundle manifest | `7753b1518b737e7f6b8e0b64f4f829b027ed3aad5b33a7613b3715481448eec5` |

The bundle is `training/artifacts/task-finetune/p2-30-request-v3-16k`. It preserves exact approved JSONL bytes and license notices alongside packed records, indices, frozen tokenizer and model configuration. Stage creation re-encodes the hash-pinned texts and verifies every token, EOS boundary and index entry. Rehashing modified token files cannot bypass this check.

| Measure | Train | Validation |
|---|---:|---:|
| Records / exact roundtrips | 156 / 156 | 78 / 78 |
| Packed tokens including EOS | 17,883 | 8,661 |
| Minimum record tokens including EOS | 89 | 92 |
| Maximum record tokens including EOS | 145 | 131 |
| Source text bytes per text token, excluding EOS | 3.6815027923506514 | 3.7477571944541537 |
| Context limit passed | Yes | Yes |

The context remains 512 input positions. Complete-record next-token pairs need record length minus one positions; all records fit without truncation. No tokenizer was fitted for research artifacts and no records moved between splits.

## Stage transition

| Artifact | SHA-256 |
|---|---|
| P2-29 step-500 base | `3b8303f8a6f56527329774b51278b93588b8383205e85bb2f594a58349acca8e` |
| P2-30 task-stage step zero | `d987606e97fd99e7dfcab0f52d29da82b9771d01809abf363ffe0188f8ec02a4` |

The saved stage is `training/artifacts/task-finetune/p2-30-stage0/stage-checkpoint.pt` (110,306,108 bytes), with **27,566,080 parameters**, task step **0**, and task tokens **0**. The new AdamW optimizer contains no moment state. The task sampler matches a fresh `random.Random(1337)` and differs from the saved Web sampler state.

Creation verifies the reloaded checkpoint. A second independent comparison of original P2-29 and staged payloads found **all 76 model-state tensors exactly equal using `torch.equal`**. Original scratch provenance is unchanged, including initial weight SHA-256 `98785d70ee7f68fcfde35ad6136bb3be05ff562374f0bdede2faae93cb80a193`. The stage record identifies P2-29 as the loaded base and records that its optimizer, sampler and training step were not reused as task progress.

This remains Plex's own scratch-trained model prepared for specialization. The stage transition is not a new random initialization. No third-party pretrained weights were loaded.

## Pre-fine-tune baselines

The existing read-only `pilot-evaluate` path accepts the exact task tokenizer/dataset/checkpoint bindings without changing evaluation identity checks:

- CUDA mean task validation loss: **6.821033537387848** at task step zero.
- **16 full batches / 8,192 target positions**, maximum batches requested 100.
- An independent repeat reproduced the result exactly.
- The existing sequential evaluator drops the incomplete tail: **468 remaining target positions were not evaluated**. Future comparisons must retain this coverage or explicitly report a changed protocol.

The unchanged P2-01b development set (`e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4`) scored **0/30 complete tasks**, **30/30 truncated outputs**, and **49/181 static checks passed**. There were no missing, empty, unavailable or timed-out outputs. Each language scored 0/10 complete tasks. Generation used the saved development defaults, greedy decoding, seed 1337, and the unchanged stage checkpoint. JavaScript was parsed with Node `--check`, never executed.

Responses SHA-256: `639af0d8b593d4f1d433637e568da03f077f4f3cda72bd8f325ef459a8e68faa`. Raw results are under `training/artifacts/evaluation/p2-30-stage0-dev`; the generation manifest carries the stage-transition record. P2-01b is previously used development evidence, excluded from gradients, and is not the final holdout. These results do not establish coding competence.

## Review and tests

The PR #71 audit led to these corrections:

- Enforce context limits, preserve approved text/notices, and verify packed tokens/EOS/indices against exact text before staging.
- Separate repack output from inputs; verify notice paths/hashes; clean failed outputs; check actual saved stage storage.
- Verify actual parameter count, scratch provenance, saved tensor equality, optimizer/sampler reset and zero task counters.
- Preserve the Web `pilot` guard and also reject task stages through generic `pilot-resume` and the generic training runner. A dedicated authorized fine-tune path is still required.
- Accept the frozen 1,131,888-byte tokenizer by capping only `tokenizer.json` at 16 MiB; metadata remains capped at 1 MiB. Hash/vocabulary checks remain active. The first development attempt stopped at the old cap before creating output.
- Declare the existing tests' missing `pytest` dependency in the development group and lockfile. NumPy was not installed.

Initial focused checks passed 31 tests. The first broad `unittest` attempt passed 189 tests with two import errors for missing `pytest`; it also omitted function-style tests. After fixes and final code changes:

| Command from repository root | Final result |
|---|---|
| `uv run --project training --no-sync python -m unittest training.tests.test_task_finetune training.tests.test_pilot training.tests.test_tokenizer training.tests.test_cli training.tests.test_data_and_runner training.tests.test_resume_and_completion -v` | **44 passed, 0 failed** |
| `uv run --project training --no-sync python -m pytest training/tests -q` | **207 passed, 0 failed, 2 warnings** |

Warnings were missing NumPy and cuBLAS creating its primary context in a synthetic optimizer test. Neither prevented execution. The suite includes synthetic training checks; **zero research model optimizer updates** occurred. Logs and hashes are recorded in the result JSON. No unresolved failure remains. Local test results are not CI results.

## First-run draft, still unauthorized

Proposed settings: **100 updates / 600 seconds**, CUDA, seed 1337, micro-batch 1, accumulation 16, fresh AdamW at 0.0003 with existing betas/epsilon/weight decay, constant schedule, and **complete-record-v1 with ordinary next-token loss and answer weight 1**. The draft pins the stage checkpoint, bundle, tokenizer and split hashes. Validation/checkpoints are scheduled at steps 25/50/75/100, with validation also at zero. Resume and automatic continuation are forbidden; report the fixed endpoint rather than choosing a checkpoint by validation loss.

The choice follows inspection of actual lengths and the existing sampler. The historical [complete-record arm](PHASE-2-COMPLETE-RECORD-COMPARISON.md) achieved 3/156 exact seen answers versus 0/156 for packed arms, but both had 0/30 development tasks. The [answer-weighted arm](PHASE-2-ANSWER-WEIGHTED-100-STEP-REPORT.md) did not improve complete tasks, so weighting stays at 1.

This matches the historical complete-record sampler, objective, optimizer, update count, seed and record draws. Replaying 1,600 proposed draws without training gives **181,849 real target positions**, versus 149,760 historically. The tokenizer and starting weights differ, so this cannot isolate a pure causal pretraining effect, and cross-tokenizer losses are not directly comparable. No curriculum mixing, model scaling, schedule sweep or final-holdout selection is proposed.

The dedicated contract-enforcing training command is deferred until owner review. No training command is supplied or run. Executed preparation/baseline commands are preserved in the result JSON; choose fresh output directories for deliberate reproduction because existing artifacts are protected from overwrite.
