# P2-30 — Task-Format Fine-Tuning Preparation

## Status

**Active — preparation gate. No model training is authorized yet.**

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

Until those checks pass, **P2-30 training is blocked**.

## Machine-readable contract

See:

`training/pretraining/p2-30-task-finetune-contract.json`


## Preparation tooling

P2-30 preparation now has two explicit no-training commands:

- `task-finetune-repack` — verifies the exact approved P2-02 request-following v3 dataset identity and repacks its 156/78 split using the frozen P2-27 16K tokenizer.
- `task-finetune-stage` — verifies the exact P2-29 step-500 checkpoint, loads only its model weights, creates a fresh AdamW optimizer with no carried moments, resets the task-stage step to zero, binds the task dataset/tokenizer identity, and records a `stageTransitionRecord`.

The ordinary Web `pilot` command explicitly rejects a checkpoint carrying a task-stage transition record. This prevents accidental task training through the pretraining path.

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

No fine-tuning command is authorized by this document.
