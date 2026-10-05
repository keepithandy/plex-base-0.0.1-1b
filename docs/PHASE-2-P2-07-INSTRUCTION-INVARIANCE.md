# P2-07: instruction invariance / paraphrase generalization

## Question

Can Plex preserve a single-value copy operation when the instruction is phrased differently from its training requests?

P2-06 made this the next narrow question. Its single-copy level learned all six supplied requests but scored 0/6 on the same six known values under alternate wording. The dual-binding and CSS-composition levels learned 6/6 supplied records each and scored 0/3 held out. P2-07 focuses only on the single-copy wording issue; it does not mix in code composition or multi-binding.

## Candidate design

The deterministic preparer creates 24 proposed training records and six evaluation-only records. Four phrasings are fully crossed with all values in each operation family:

| Family | Values | Training phrasings |
|---|---|---|
| Selector copy | `.actions`, `.filters`, `.controls` | “Return this selector exactly”; “Copy this selector unchanged”; “Repeat the selector exactly as shown”; “Output only the selector shown here” |
| Gap copy | `6px`, `14px`, `28px` | “Return this gap exactly”; “Copy this gap value unchanged”; “Repeat the gap value exactly as shown”; “Output only the gap value shown here” |

Each value occurs under all four training phrasings, so phrase identity is not confounded with value. Evaluation applies one never-trained phrasing per family (“Give back this selector/gap value with no changes”) to all three values already seen during training. No unseen values, CSS syntax generation, or dual-binding requests are included. The only intended novelty is the instruction surface form.

This probe is intentionally small. Even a 6/6 evaluation result supports only transfer within these operation families and phrasings; it is not evidence of broad natural-language understanding. Interpret evaluation only if all 24 training rows are learned sufficiently; otherwise report the result as inconclusive.

## Preparation and approval boundary

Run candidate preparation with:

```powershell
uv run --project training --no-sync python training\phase2\prepare_instruction_invariance_probe.py
```

The preparer verifies the development contract and the frozen tokenizer SHA-256 (`a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`), checks context and answer token limits, writes `candidate.jsonl`, `evaluation-only.jsonl`, `REVIEW.md`, and `review.json`, and refuses to overwrite an existing output directory. The training rows were initially pending review; the owner has since approved the exact candidate hashes for one bounded run. The approval artifact is `training/phase2/approvals/p2-07-instruction-invariance-v1.json`.

The immutable experiment preparer is:

```powershell
uv run --project training --no-sync python training\phase2\prepare_instruction_invariance_experiment.py `
  --output training\artifacts\experiments\p2-07-instruction-invariance-inputs-v1
```

It rechecks the exact approved train, evaluation, review, tokenizer, and development-contract identities, materializes packed training inputs, and keeps evaluation out of training and runtime validation loss.

The bounded approved runner is:

```powershell
uv run --project training --no-sync python training\phase2\run_instruction_invariance_experiment.py `
  --prepared training\artifacts\experiments\p2-07-instruction-invariance-inputs-v1 `
  --output-dir training\artifacts\experiments\p2-07-instruction-invariance-run-v1 `
  --steps 100 --minutes 10 --device cuda
```

The approved ceiling is **100 optimizer updates / 10 minutes total** for one fresh seed-1337 scratch model, microbatch 1, accumulation 16. There is no automatic continuation. The runner checks tensorwise equality against the recorded seed-1337 scratch initialization and scores only after training.

The P2-07 candidate and runner do not open, generate, import, or score against the final project holdout. The tokenizer remains frozen. Ordinary validation-loss telemetry uses the existing P2 request-following validation split; the six P2-07 evaluation rows are used only for post-training scoring. Training and evaluation outputs are recorded separately, including request, expected value, completion, phrase family, operation family, generated token count, and EOS status.

Training convergence is required before interpreting the held-out score. At 24/24 supplied passes, report 6/6 as `instruction-invariance-demonstrated-within-single-copy-probe`, 4–5/6 as partial, 1–3/6 as limited, and 0/6 as no transfer after convergence. Below 24/24, report the result as inconclusive.

## Recorded P2-07 result

The explicitly approved single-arm run completed **100/100 updates** in **15.82 seconds** on CUDA. It processed **8,307 supervised answer/EOS target tokens**. Supplied learning converged at **24/24 exact representation passes**. The frozen tokenizer matched the approved SHA-256; initial tensors were verified equal to the recorded seed-1337 scratch initialization. The final holdout remained closed.

The replay-verified sampler accounting was 1,600 record draws across 100 updates, all 24 records selected (55–83 selections each), 94,517 real context targets, 8,307 supervised answer/EOS targets, 86,210 excluded prompt targets, and zero padding targets.

| Measure | Result |
|---|---:|
| Training exact / representation pass | 24/24 |
| Evaluation exact / representation pass | 4/6 |
| Selector-copy evaluation | 1/3 |
| Gap-copy evaluation | 3/3 |
| Evaluation EOS | 6/6 |
| Evaluation outputs matching a seen training answer | 5/6 |
| Evaluation generated tokens, total | 34 |

The controlled interpretation is `partial-instruction-invariance-within-single-copy-probe`. Gap copying transferred to all three known values under the held-out wording. Selector copying transferred for `.actions`, returned the previously trained `.controls` value for `.filters`, and emitted repeated selector punctuation before `.controls` for the `.controls` case. Thus the model handled the held-out gap phrase consistently in this run but remained inconsistent for selector copying. This result applies only to the one held-out wording and values in this tiny probe; it does not establish broad paraphrase understanding.

Detailed record outputs, optimizer telemetry, memory readings, checkpoint hashes, and run accounting are in the local ignored artifact `training/artifacts/experiments/p2-07-instruction-invariance-run-v1/result.json` and `completion-score.json`. The approved immutable inputs are in `training/artifacts/experiments/p2-07-instruction-invariance-inputs-v1/experiment.json`. The approval pins the candidate SHA-256 `ed0bee7c2c7f99ffaa7c349ba4e644d8c26d33266976fbe3fb8e96af1095245f` and evaluation SHA-256 `01a861a3343c58f68f269fc9dc4fbf1f7bf77ce7e6ba0764e85d752b7f706414`. Neither evaluation records nor final-holdout data entered gradient training or runtime validation loss.

The focused tests are:

```powershell
uv run --project training --no-sync python -m unittest discover -s training\tests -p test_p2_07_instruction_invariance_*.py -v
```

The actual run summary belongs in the local experiment artifact's `result.json`; any report committed afterward must separate measured outcomes from this pre-run design and preserve the final-holdout boundary.
