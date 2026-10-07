# P2-30 — First Task-Format Fine-Tuning Result

## Status

**First bounded run complete — October 7, 2026. Learning signal confirmed; coding capability gate not passed. No continuation is authorized.**

P2-30 executed exactly the previously approved first-run contract from the verified task-stage checkpoint. The run completed **100/100 CUDA optimizer updates** in **21.606 seconds**, processed **181,849 real target positions**, sampled **1,600 complete records**, and selected all **156** training records at least three times.

The immutable authorization contract remains:

`training/pretraining/p2-30-first-finetune-contract.json`

The machine-readable execution result is:

`training/pretraining/p2-30-first-finetune-result.json`

## Identity

- stage-zero checkpoint SHA-256: `d987606e97fd99e7dfcab0f52d29da82b9771d01809abf363ffe0188f8ec02a4`
- frozen tokenizer SHA-256: `2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697`
- task bundle manifest SHA-256: `7753b1518b737e7f6b8e0b64f4f829b027ed3aad5b33a7613b3715481448eec5`
- final step-100 checkpoint SHA-256: `28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e`

No automatic continuation or resume occurred. The final project holdout remained sealed.

## Validation trajectory

| Task step | Validation loss |
|---:|---:|
| 0 | 6.821033537387848 |
| 25 | 3.1708500385284424 |
| 50 | **3.0633289515972137** |
| 75 | 3.1765616685152054 |
| 100 | 3.431293249130249 |

The lowest observed development validation loss was at step 50, but the contract explicitly fixed the official endpoint at step 100 rather than retrospectively selecting the lowest-validation checkpoint. Step 50 is therefore diagnostic evidence only.

The curve demonstrates rapid task-format learning followed by degradation after step 50 while recent training loss continued to fall. That is consistent with increasing overfit pressure on the small 156-record training split.

## P2-01b development evaluation

The official step-100 endpoint generated deterministic responses for all 30 P2-01b development tasks.

- complete tasks passed: **0 / 30**
- static assertions passed: **41 / 151**
- truncated outputs: **0 / 30**
- empty outputs: **0**
- missing outputs: **0**
- response SHA-256: `7389e7b69774297f80d1004970b13e0423578aa0d2827781b7eaa91a93130e3d`

This is a meaningful failure-mode shift from the stage-zero baseline, where all 30 responses truncated. Plex now consistently produces bounded code-shaped outputs and earns partial static credit, but it does not reliably satisfy all requested constraints in one solution.

Common failures include malformed HTML fragments, invented or duplicated CSS declarations, JavaScript syntax failures, and syntactically valid outputs that still miss requested semantic behavior.

## Decision

P2-30 establishes:

1. the P2-29 Web-pretrained weights can rapidly adapt to the task-format corpus;
2. held-out task-text loss improves materially;
3. completion truncation is eliminated;
4. partial syntax/contract behavior improves.

P2-30 does **not** establish reliable complete coding-task execution.

No further P2-30 optimizer updates are authorized. Repeating the same small task corpus is not justified by the rising post-step-50 validation loss and unchanged 0/30 complete-task result.

The next milestone is **P2-31 — Structured Coding Bridge**, which evaluates whether Plex Nano can normalize repository-style requests into bounded semantic edit plans while deterministic Plex Code retains exact repository lookup, state resolution, mutation, validation, and diff generation.
