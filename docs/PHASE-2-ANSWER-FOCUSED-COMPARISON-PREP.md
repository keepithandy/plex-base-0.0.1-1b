# P2-03: answer-focused complete-record comparison preparation

Prepared October 5, 2026. This comparison reuses the exact owner-approved 24-example binding-diversity candidate and the existing frozen tokenizer. It adds no training examples, opens no final holdout, and does not authorize a longer run.

## Question

The previous binding-diversity run learned 20/24 supplied answers but completed 0/12 new bindings, 0/12 reserved transfer requests, and 0/30 development tasks. Four seen failures substituted another taught binding. Before interpreting that transfer failure as a generalization limit, compare the current ordinary complete-record objective with an objective that keeps the entire prompt in causal context but applies loss only to answer/EOS targets.

The comparison variable is therefore only the target mask:

| Target type | Ordinary arm | Answer-focused arm |
|---|---:|---:|
| Prompt targets | 1 | 0 |
| Answer targets | 1 | 1 |
| EOS target | 1 | 1 |
| Right padding | 0 | 0 |

Both arms use the same approved 24 records, record-selection policy, frozen tokenizer, 27,566,080-parameter architecture, seed-1337 scratch initialization tensors, AdamW settings, 100-update cap, ten-minute cap, inference settings, transfer requests, and 30-task development set.

## Implementation

`plex_training.answer_focused_records.AnswerFocusedCompleteRecordTokenCorpus` subclasses the existing verified complete-record source. It revalidates the approved JSONL, token index, tokenizer prefix boundary, packed token bytes, and EOS. Sampling remains uniform by complete record. The full prompt remains in the input sequence, but its shifted target positions receive zero loss weight.

The source records both the unchanged sampler identity and an explicit objective identity:

```json
{
  "kind": "answer-eos-only-complete-record-v1",
  "promptTargetWeight": 0,
  "answerAndEosTargetWeight": 1,
  "paddingTargetWeight": 0
}
```

Its audit separates:

- real context target positions,
- supervised answer/EOS target positions,
- excluded prompt target positions,
- right-padding target positions.

This avoids interpreting zero-weight prompt targets as actual padding in the experiment report.

`training/phase2/run_answer_focused_experiment.py` uses the already reviewed `p2-binding-v1` prepared inputs and specifically requires the 24-record `varied` arm. It creates two matching seed-1337 initializations, verifies exact parameter-tensor equality against each other and the preserved original scratch initialization, trains both bounded arms, checks matching complete-record exposure, then scores the same supplied, reserved-transfer, new-binding, and development requests.

The runner refuses automatic extension. A partial arm produces an incomplete comparison report rather than continuing training.

## Reproduction

If the previous prepared binding input is not present locally, recreate it from the unchanged approved source snapshot:

```powershell
uv run --project training --no-sync python training\phase2\prepare_binding_experiment.py `
  --output training\artifacts\experiments\p2-answer-focused-inputs-v1
```

Then run the objective comparison:

```powershell
uv run --project training --no-sync python training\phase2\run_answer_focused_experiment.py `
  --prepared training\artifacts\experiments\p2-answer-focused-inputs-v1 `
  --output-dir training\artifacts\experiments\p2-answer-focused-run-v1 `
  --steps 100 --minutes 10 --device cuda
```

The default `--prepared` path remains `training/artifacts/experiments/p2-binding-v1` for the machine that produced the preceding binding-diversity report.

## Interpretation rule

Check supplied-answer learning before interpreting transfer behavior.

- If answer-focused training still fails several of the 24 supplied answers, loss focus is not sufficient evidence of a binding solution.
- If it reaches 24/24 but transfer remains at zero, Plex can reproduce the supplied bindings under this objective but still has no demonstrated same-operation transfer.
- If supplied learning and new-binding transfer improve while all other controls remain fixed, prompt-target loss was likely interfering with binding in this bounded setup.
- Development movement above 0/30 would be stronger evidence, but the static development evaluator still does not establish JavaScript behavior or browser-backed HTML/CSS behavior.

No result from this diagnostic alone justifies the deferred two-hour run or a capability claim. The final holdout remains closed.
