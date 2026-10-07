# P2-30 — Task-Format Fine-Tuning

## Status

**First bounded run complete — October 7, 2026. No continuation is authorized.**

The [preparation result](PHASE-2-P2-30-PREPARATION-RESULT.md) records exact stage-zero evidence. The immutable [first-run authorization](../training/pretraining/p2-30-first-finetune-contract.json) was executed exactly once for **100/100 CUDA updates**. The [first-run result](PHASE-2-P2-30-FIRST-RUN-RESULT.md) records validation **6.8210 → 3.0633 best descriptive value → 3.4313 fixed endpoint**, final checkpoint SHA-256 `28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`, and P2-01b **0/30 complete tasks with 0 truncations and 41/151 static assertions passed**.

P2-30 transitions Plex from Web-domain pretraining into task-format fine-tuning.

The first controlled question is deliberately narrow:

> Does the P2-29 Web-pretrained checkpoint learn the already-approved request-following curriculum better than the earlier scratch-only task runs?

## Base checkpoint

P2-30 starts from the verified P2-29 step-500 model:

`training/artifacts/pilot/p2-29-web-v1-500step/pilot-checkpoint.pt`

SHA-256:

`3b8303f8a6f56527329774b51278b93588b8383205e85bb2f594a58349acca8e`

This is a **stage transition**, not a continuation of Web-domain optimization.

## First task curriculum

Use the already owner-approved **P2-02 request-following v3** corpus:

- candidate SHA-256: `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`
- records: **234**
- training: **156**
- validation: **78**
- languages: HTML / CSS / JavaScript
- approval: `training/phase2/approvals/p2-02-request-following-v3.json`

This curriculum is useful because Plex previously trained on the same task family from scratch and still scored **0/30 complete development tasks**. Reusing the task format after Web pretraining gives P2-30 a direct comparison.

## Tokenizer rule

The historical request-following bundle used a 1,509-token tokenizer. **Do not reuse it.**

P2-30 must preserve the exact approved textual train/validation split but retokenize it with the frozen P2-27 Web tokenizer:

- vocabulary: **16,384**
- tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`

No new tokenizer is fitted.

## Stage-transition rule

The existing generic pilot resume path intentionally requires the dataset identity to remain unchanged. It therefore cannot be used to silently switch from the Web corpus to task data.

P2-30 needs a dedicated fine-tuning transition that:

1. verifies the exact P2-29 checkpoint
2. loads the **model weights**
3. preserves the 27,566,080-parameter architecture and 16K tokenizer
4. **does not reuse the Web-pretraining optimizer state**
5. **does not reuse the Web sampler/RNG progress as task-stage progress**
6. starts a fresh fine-tuning optimizer/stage counter
7. records the P2-29 checkpoint as the base-model provenance
8. binds the new task dataset identity explicitly

This keeps “pretraining” and “fine-tuning” auditable as separate stages.

## Protected evaluation

- P2-30 validation records stay out of gradient training.
- P2-01b stays out of gradient training.
- The final project holdout remains closed.
- Previously used development/evaluation material remains development evidence, not a newly virgin holdout.

## Preparation exit gate

Before the first P2-30 optimizer update:

- rebuild the approved 156/78 text split under the frozen 16K tokenizer
- verify roundtrip and context budgets
- verify split hashes and no train/validation leakage
- implement/test the weights-only fine-tune bridge
- produce a pre-fine-tune baseline from the P2-29 checkpoint
- freeze learning rate, task objective, sampler, maximum updates and evaluation cadence
- commit a separate training authorization

Preparation evidence now passes these checks. The owner has explicitly authorized the separate first-run contract, and the dedicated training path enforces it. **Fine-tuning itself is still unexecuted and therefore not complete.** No continuation beyond the fixed first run is authorized.

## Machine-readable contract

See:

`training/pretraining/p2-30-task-finetune-contract.json`


## Preparation tooling

P2-30 preparation now has two explicit no-training commands:

- `task-finetune-repack` — verifies the exact approved P2-02 request-following v3 dataset identity and repacks its 156/78 split using the frozen P2-27 16K tokenizer.
- `task-finetune-stage` — verifies the exact P2-29 step-500 checkpoint, loads only its model weights, creates a fresh AdamW optimizer with no carried moments, resets the task-stage step to zero, binds the task dataset/tokenizer identity, and records a `stageTransitionRecord`.

The ordinary Web `pilot`, generic runner, and `pilot-resume` paths reject task-stage checkpoints. Only the dedicated first-run path below can consume the verified P2-30 stage-zero checkpoint.

### 1. Rebuild the approved task dataset

From the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli dataset-build `
  --source-manifest training\phase2\data\authored\p2-02-request-following-v3\dataset-sources.approved.json `
  --output-dir datasets\p2-30-request-v3-v1 `
  --validation-percent 30 `
  --seed 51
```

The build must reproduce:

- dataset manifest SHA-256: `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea`
- train JSONL SHA-256: `05fb9b35277b979ef45473af5b2a2c98bef31ee2c1c3133f0af0c68d7cfba554`
- validation JSONL SHA-256: `1e999896304a92c3d39503246f08e1736dc9cbf7c91cb9e0f85d195f34aba3ce`
- 156 train / 78 validation records

### 2. Repack with the frozen Web tokenizer

```powershell
uv run --project training --no-sync python -m plex_training.cli task-finetune-repack `
  --dataset-dir training\artifacts\datasets\p2-30-request-v3-v1 `
  --tokenizer-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --output-dir task-finetune\p2-30-request-v3-16k
```

This command does **not** fit a tokenizer and does **not** train model weights.

### 3. Create the task-stage step-zero checkpoint

```powershell
uv run --project training --no-sync python -m plex_training.cli task-finetune-stage `
  --base-checkpoint training\artifacts\pilot\p2-29-web-v1-500step\pilot-checkpoint.pt `
  --bundle-dir training\artifacts\task-finetune\p2-30-request-v3-16k `
  --output-dir task-finetune\p2-30-stage0
```

This command performs **zero optimizer updates**. It creates a new task-stage checkpoint whose model weights come from P2-29 but whose optimizer/state counter are fresh.

### 4. Baseline before fine-tuning

After the stage checkpoint is verified, measure its held-out task-text loss:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-evaluate `
  --bundle-dir training\artifacts\task-finetune\p2-30-request-v3-16k `
  --checkpoint training\artifacts\task-finetune\p2-30-stage0\stage-checkpoint.pt `
  --max-batches 100 `
  --device cuda
```

A separate development-task generation/scoring baseline may then be run from the unchanged stage-zero model.

### 5. Preflight the owner-authorized first run

This performs all contract, hash, dataset, tokenizer, stage-provenance, optimizer-state, sampler-state, step/token-counter and CUDA checks. It creates no run output and performs zero optimizer updates.

```powershell
uv run --project training --no-sync python -m plex_training.cli task-finetune-preflight `
  --bundle-dir training/artifacts/task-finetune/p2-30-request-v3-16k `
  --stage-checkpoint training/artifacts/task-finetune/p2-30-stage0/stage-checkpoint.pt `
  --output-dir task-finetune/p2-30-first-run
```

### 6. Execute the single authorized first run

Run this only after preflight succeeds and the authorization/tooling change is on `master`:

```powershell
uv run --project training --no-sync python -m plex_training.cli task-finetune-run `
  --bundle-dir training/artifacts/task-finetune/p2-30-request-v3-16k `
  --stage-checkpoint training/artifacts/task-finetune/p2-30-stage0/stage-checkpoint.pt `
  --output-dir task-finetune/p2-30-first-run
```

There are deliberately no CLI overrides for steps, wall time, optimizer, sampler, learning rate, device, resume, or automatic continuation. The run validates at task steps 0/25/50/75/100, saves at 25/50/75/100 plus any early final completed step, and preserves the final project holdout as sealed. Afterward, run the existing P2-01b development generation/scoring only on the fixed final completed checkpoint and review the evidence before any further optimizer update.

The machine authorization is:

`training/pretraining/p2-30-first-finetune-contract.json`



## Closeout

P2-30 is closed after its first bounded run. The task-format learning signal is real, but the capability gate did not pass and validation worsened after step 50. The project therefore does not authorize more P2-30 updates on the same curriculum.

Next: [P2-31 Structured Coding Bridge](PHASE-2-P2-31-STRUCTURED-BRIDGE.md).
