# P2-13 step-200 wording development evaluation

Date: 2026-10-05

Status: **read-only evaluation complete; 95/96 exact; not a final holdout**

## Result

The step-200 P2-12 checkpoint was scored greedily on 96 evaluation-only selector-copy requests. The set crossed six fresh instruction phrasings with inline and next-line layouts and eight selector values. The checkpoint produced the required answer newline and EOS on all 96 requests, and reproduced 95 selector strings exactly.

| Held-out development phrasing | Inline | Next-line | Total |
|---|---:|---:|---:|
| What is the exact text of this selector? | 8/8 | 8/8 | 16/16 |
| Report the selector shown here unchanged | 8/8 | 8/8 | 16/16 |
| Use this selector as the entire output | 8/8 | 8/8 | 16/16 |
| Echo the selector displayed below without alteration | 8/8 | 8/8 | 16/16 |
| Give the selector exactly as it appears here | 8/8 | 8/8 | 16/16 |
| Return the CSS selector with its punctuation intact | 8/8 | 7/8 | 15/16 |
| **Total** | **48/48** | **47/48** | **95/96** |

The single miss was `.delta-card` in the next-line layout. The generated completion was `\n.deltadelta-card`; token pieces show the `delta` fragment emitted twice. EOS was emitted, and the answer began with a newline. There were no wrong-known-selector outputs or extra trailing text. This observation identifies the visible error shape only; no teacher-forced rank audit was performed.

This set was not used for training or runtime validation loss. It is a development result because it is now disclosed and may inform future experiment choices. The repeated P2-12 evaluation score of 64/64 is also non-independent. Neither score estimates broad instruction following or coding ability. Keep the final project holdout closed.

## Pinned identities

- Evaluation-only JSONL SHA-256: `d185156b0126cecd1de7b21a6d9a5de23eda67bf14a7192dd904c654449b03c2`
- Scored checkpoint SHA-256: `e1e6821eaf5af2bfb9ddb0de7031790dc96e6d0e8f706bb4521d005219736065`
- Checkpoint step: 200
- Records: 96 (six phrasings × two layouts × eight selectors)
- Exact and whitespace/case-normalized request overlap checks passed against the P2-08, P2-10, P2-10 wider evaluation, P2-11, and P2-12 training/evaluation request sets.
- Final holdout opened: **no**.

The deterministic preparation and read-only scoring commands are:

```powershell
$env:PYTHONPATH = (Resolve-Path 'training\.venv\Lib\site-packages').Path + ';' + (Resolve-Path 'training\src').Path + ';' + (Resolve-Path 'training\phase2').Path
python training/phase2/prepare_p2_13_step200_evaluation.py --verify-only
python training/phase2/score_p2_13_step200_evaluation.py
```

The ignored local score artifacts are under `training/artifacts/experiments/p2-13-step200-evaluation-v1/`. They include all generated token IDs and pieces. The checkpoint and evaluation rows were read only during scoring; no optimizer or validation-loss path was invoked.

## Next step

Move to a different held-out task family, such as constrained CSS edits checked deterministically. Keep training, prompt tuning, and development tasks separate from an untouched final evaluation set. Do not extend this checkpoint based only on this selector-copy result.
