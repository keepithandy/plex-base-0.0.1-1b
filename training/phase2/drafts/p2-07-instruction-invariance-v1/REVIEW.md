# P2-07: instruction invariance / paraphrase generalization
Status: **pending owner review**. This preparer creates candidates and review metadata only; it does not train a model or create an approval artifact.
## Why this probe exists
P2-06 learned all six supplied single-copy examples but scored 0/6 when the same known selectors and gaps were requested with alternate wording. The dual-binding and CSS-composition levels also learned 6/6 supplied examples and scored 0/3 held out. P2-07 isolates the earlier single-value wording question before reintroducing multi-binding or code composition.
## Controlled design
Training contains 24 records: four instruction phrasings crossed with all three values for each of selector-copy and gap-copy. Evaluation contains six records: one never-trained phrasing per family applied to the same three known values. No new values, CSS generation, or multiple bindings are introduced; the only intended novelty is instruction wording.
This tiny probe is not evidence of broad language understanding. A transfer score applies only to these operation families and phrasings. Exact training convergence is required before interpreting evaluation failures.
## Training phrasing matrix
### selector-copy

Values: .actions, .filters, .controls

- `return-exactly`: `Return this selector exactly: {value}`
- `copy-unchanged`: `Copy this selector unchanged: {value}`
- `repeat-as-shown`: `Repeat the selector exactly as shown: {value}`
- `output-only`: `Output only the selector shown here: {value}`

Held out: `give-back-no-changes` — `Give back this selector with no changes: {value}`

### gap-copy

Values: 6px, 14px, 28px

- `return-exactly`: `Return this gap exactly: {value}`
- `copy-unchanged`: `Copy this gap value unchanged: {value}`
- `repeat-as-shown`: `Repeat the gap value exactly as shown: {value}`
- `output-only`: `Output only the gap value shown here: {value}`

Held out: `give-back-no-changes` — `Give back this gap value with no changes: {value}`

## Interpretation criteria
Interpret held-out wording only after all 24 training rows pass. If training does not converge, report `inconclusive-instruction-invariance: supplied paraphrase matrix did not fully converge`. At 6/6, report `instruction-invariance-demonstrated-within-single-copy-probe`; at 4–5/6, partial; at 1–3/6, limited; at 0/6, no held-out paraphrase transfer after supplied convergence. Do not generalize beyond this probe.
## Safeguards and approval boundary
The frozen reference tokenizer must match the expected SHA-256; it is not refitted. The final project holdout is not opened, generated, imported, or scored. Candidate records remain pending owner review, evaluation records are evaluation-only, `modelTrained` is false, and `finalHoldoutOpened` is false. No training is authorized until the owner approves the exact generated candidate hashes.
## Candidate files

- Training records: 24 (`ed0bee7c2c7f99ffaa7c349ba4e644d8c26d33266976fbe3fb8e96af1095245f`)
- Evaluation-only records: 6 (`01a861a3343c58f68f269fc9dc4fbf1f7bf77ce7e6ba0764e85d752b7f706414`)
- Frozen tokenizer: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`

Run the focused preparation tests with:

```powershell
uv run --project training --no-sync python -m unittest discover -s training\tests -p test_p2_07_instruction_invariance_probe.py -v
```
