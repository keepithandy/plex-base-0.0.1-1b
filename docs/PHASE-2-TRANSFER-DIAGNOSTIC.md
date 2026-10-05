# P2-03: request-following transfer diagnostic

Recorded October 5, 2026. **The owner completed CUDA checkpoint inference: step 200 reproduced all six original answers but passed none of the twelve changed requests.** Step 100 reproduced two originals and also passed none of the variations. The [binding-variation audit](PHASE-2-BINDING-VARIATION-AUDIT.md) verifies the completed report, inspects training coverage, and records the next experiment to prepare. Windows Application Control had blocked the earlier agent-side PyTorch import; the user-terminal run succeeded. No new training occurred.

The [step-200 comparison](PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md) learned 52/156 supplied answers exactly but still passed 0/30 development tasks. This small check asks whether modest changes to a learned request already cause failure. It uses six controls known to be exact at step 200 and two independent variations of each: 18 prompts per checkpoint, 36 generations total across steps 100 and 200.

| Original control | Variation 1 | Variation 2 |
|---|---|---|
| HTML `gap-html-bidi-02` | Word Kyoto → Osaka | Word Kyoto → Harbor |
| HTML `gap-html-progress-01` | Progress value 35 → 62 | Maximum 100 → 200 |
| CSS `gap-css-logical-border-03` | Selector `.top-edge` → `.panel-edge` | Border width 2px → 5px |
| CSS `gap-css-layout-01` | Selector `.toolbar` → `.command-bar` | Gap 12px → 20px |
| JavaScript `gap-javascript-division-01` | Function name → `truncateQuotient` | Function name → `divideIntegers` |
| JavaScript `gap-javascript-array-copy-01` | Function name → `cloneItems` | Function name → `duplicateItems` |

Each variation changes one detail in the prompt, reference answer, and corresponding static assertions. The underlying requested operation and structure stay fixed. The cases were fixed before new checkpoint generation. None of the variation prompts or complete reference answers duplicates an approved corpus record. These cases are **evaluation-only** and must not enter training or tokenizer data. The final holdout is untouched.

## Measures and limits

The runner reports exact reference text plus EOS, static checks plus the requested binding, syntax, old bindings still present, repetition of the original reference, and empty/truncated responses. Binding checks require the replacement text and reject the old text. They are narrow textual checks, not semantic equivalence. Static checks do not prove JavaScript behavior or browser rendering; generated code is never executed. Installed Node is used only with `--check`.

Decoding retains greedy temperature 0, seed 1337, the existing prompt template, and caps of 192 tokens for HTML/JavaScript and 128 for CSS. Both saved checkpoint hashes and the approved candidate/development settings hashes are pinned. Checkpoints are read and verified again after inference; reports go into a new directory. No gradient updates occur.

The six controls were selected because step 200 already learned them. This is a deliberately selected diagnostic, not an unbiased capability benchmark or a substitute for the 30 development tasks. Twelve variations cannot establish broad generalization. If originals remain correct but changed requests fail, inspect the binding failures before selecting another bounded training configuration. If variations pass, the next investigation should address the broader structures represented in development tasks. Neither outcome alone completes P2-03 or justifies a two-hour run.

## Verified preparation

- Five focused tests passed: balanced/unique cases and unchanged source data; correct references accepted; stale answers and missing EOS rejected; validation-source/no-op changes rejected; overwrite protection; and preparation without importing PyTorch.
- The real preparation accepted all 18 references and rejected all 12 unchanged answers against their changed requests.
- Independent tokenization confirmed a maximum of 83 prompt tokens and 30 reference tokens including EOS. Every case fits the unchanged limits.
- Both source checkpoint hashes still match the completed step-100/step-200 comparison.
- Preparation saved [cases.json](../training/artifacts/diagnostics/p2-transfer-preflight-v1/cases.json), SHA-256 `c70af62e3f954066a24dae36c613b6efb51a2a34580326d0d9400afff53e88a3`.

The initial test attempt failed while importing PyTorch because of the Windows policy block. Pure case preparation/scoring was then separated from model imports, and all five focused tests passed. The complete training suite and actual checkpoint inference were not rerun in this session. The previous 116-test result belongs to the completed continuation, not this diagnostic run.

## Completed execution and reproduction

This run is complete and does not need repeating. The original PowerShell command was:

```powershell
uv run --project training --no-sync python training\phase2\diagnose_transfer.py --device cuda --output training\artifacts\diagnostics\p2-transfer-v1
```

The [completed report](../training/artifacts/diagnostics/p2-transfer-v1/report.json) contains aggregate counts and each generated answer; [cases.json](../training/artifacts/diagnostics/p2-transfer-v1/cases.json) records the exact evaluated prompts and references. Both steps had zero empty/truncated outputs. Step 200 retained old details in 6/12 variations and exactly repeated three original references. All 36 saved outputs were independently rescored with identical results. To reproduce, choose a different unused output directory; `p2-transfer-v1` already exists.

The earlier Windows policy block remains part of the attempt history. This implementation did not alter security settings, install dependencies, or substitute model weights. P2-03 remains active; next work is the candidate/evaluation preparation described in the audit.
