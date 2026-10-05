# P2-08: selector copying with wording and layout controls

Status: **pending owner review**. This preparation creates a candidate and review metadata only. It does not approve or train a model.

## Question

Does selector copying remain exact across alternate instruction wording and a change in how the selector is placed after the colon, when eight selector values are fully represented in training?

P2-07 used three selector values. The held-out wording scored 1/3, with one selector copied as another known selector and one correct selector preceded by repeated periods. A score-only follow-up also found lower accuracy when the input selector moved to a new line. P2-08 expands the values and crosses wording and layout so those factors can be compared separately.

## Candidate design

- Eight selector values: three P2-07 baseline values (`.actions, .filters, .controls`) and five additional values (`.alpha-panel, .bravo-item, .charlie-list, .delta-card, .echo-label`).
- Training: 64 records; four training phrasings × two input layouts × eight selectors.
- Evaluation-only: 16 records; one held-out phrasing × two input layouts × the same eight known selectors.
- Output contract: `Return exactly the requested value and nothing else.` for every row; one selector per answer; no CSS rule composition.
- Layout levels: inline (`colon-space`) and value on the next line (`colon-newline`). Both occur in training and evaluation, so layout is not held out.

## Training phrase matrix

| Phrase ID | Request template |
|---|---|
| `return-exactly` | `Return this selector exactly: {value}` |
| `copy-unchanged` | `Copy this selector unchanged: {value}` |
| `repeat-as-shown` | `Repeat the selector exactly as shown: {value}` |
| `output-only` | `Output only the selector shown here: {value}` |

Held-out wording: `give-back-no-changes` — `Give back this selector with no changes: {value}`

Evaluation compares the held-out wording against the training phrasings at each layout while keeping selector values known. Token IDs, decoded output, exact copy, wrong-known-selector output, and extra punctuation should be recorded after approval. This tiny controlled probe cannot establish broad instruction understanding.

## Safeguards and approval boundary

- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; no refit.
- Existing model architecture and configuration are unchanged.
- Candidate rows are pending owner review; evaluation rows are evaluation-only.
- `modelTrained: false`; `finalHoldoutOpened: false`.
- No training is authorized until the owner reviews and explicitly approves the exact training and evaluation hashes.
- If approved later, use one fresh seed-1337 scratch model and the existing bounded limit of 100 updates / 10 minutes. Do not extend automatically.

## Exact files and hashes

- Training: 64 records — `feb5feb0f7b06dad372e359de3f0958603888da0989ae4982c4f93c3b4622564`
- Evaluation-only: 16 records — `4d9f4051318fcfe9f7941f4a5462b2b97998cb06f0ff0599f0a0cab00c7eb8a3`
- The matching review markdown SHA-256 is pinned in `review.json`.
- Maximum prompt / complete-record-with-EOS / answer-with-EOS token lengths: 64 / 73 / 9

Preparation tests:

```powershell
uv run --project training --no-sync python -m unittest discover -s training\tests -p test_p2_08_selector_format_probe.py -v
```
