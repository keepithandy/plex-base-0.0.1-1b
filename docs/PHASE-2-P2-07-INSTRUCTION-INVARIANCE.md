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

The preparer verifies the development contract and the frozen tokenizer SHA-256 (`a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`), checks context and answer token limits, writes `candidate.jsonl`, `evaluation-only.jsonl`, `REVIEW.md`, and `review.json`, and refuses to overwrite an existing output directory. Training remains pending owner review and evaluation rows remain evaluation-only. It does not create an approval artifact or run training.

The candidate-preparation step does not open, generate, import, or score against the final project holdout. It does not refit the tokenizer. No training run or long-run authorization is included. Training would require explicit owner approval of the exact generated candidate hashes, followed by a separately bounded approved runner.

The focused tests are:

```powershell
uv run --project training --no-sync python -m unittest discover -s training\tests -p test_p2_07_instruction_invariance_probe.py -v
```

After training is separately authorized, the intended supplied-convergence gate and score interpretation are recorded in the candidate `REVIEW.md` alongside the exact reviewed wording and hashes.
