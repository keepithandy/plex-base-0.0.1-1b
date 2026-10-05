# P2-02: three-example overfit probe

Plex **can reproduce three supplied training answers** when each approved example is presented as its own complete prompt-and-answer sequence. This is a narrow pipeline result. It does not establish that Plex handles unseen coding requests, that the 234-example corpus has been learned, or that a two-hour run is warranted.

The [probe script](../training/phase2/three_example_probe.py) used exactly one owner-approved v3 **training-split** record per language:

| Language | Record | Requested result |
|---|---|---|
| HTML | `gap-html-ruby-01` | Ruby annotation for “Kyoto” with its reading |
| CSS | `gap-css-logical-border-01` | Inline-start border for `.start-edge` |
| JavaScript | `gap-javascript-division-01` | `quotientTowardZero(a, b)` function |

It used the existing 1,509-entry tokenizer and step-zero 27,566,080-parameter Plex checkpoint, both from the approved v3 corpus and seed 1337. The initial checkpoint was made from random weights, with no pretrained model loaded. The three source texts and their splits were checked against the approved candidate and built training corpus. Each optimizer step presented all three complete records, averaged their ordinary full-sequence next-token losses, and used the existing AdamW settings and gradient clipping. This **record-aligned, three-example procedure differs from** the earlier 512-token random packed-window runner, its 156-record dataset, and its gradient accumulation. The comparison cannot isolate one cause of the earlier 0/156 result.

| Checkpoint step | Exact answers with EOS | Full static passes |
|---:|---:|---:|
| 0 | 0/3 | 0/3 |
| 25 | 3/3 | 3/3 |
| 50 | 3/3 | 3/3 |
| 100 | 3/3 | 3/3 |
| 200 | 3/3 | 3/3 |

The 200-step run completed in **8.12 seconds**, below the **ten-minute training cap**, with ordinary training loss declining from 7.44548 on the first step to 0.01330 on the last. The [saved report](../training/artifacts/probes/p2-three-example-v1/report.json) includes every generated completion, reference answer, EOS result, and static-check result. The step-200 checkpoint was reloaded from disk and independently reproduced 3/3 exact answers and 3/3 static passes. JavaScript was syntax-checked with Node `--check`; generated code was not executed. No corpus validation examples, development benchmark tasks, or final-holdout tasks were used for training or scoring this probe.

The saved checkpoint SHA-256 is `ef1710508535fa2b780c7a7ffc290849c1c6a68cd5ab9a47277063315277952f`; the reused step-zero checkpoint is `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5`. The approved candidate SHA-256 is `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`. The checkpoint and report are ignored local artifacts under `training/artifacts/probes/p2-three-example-v1`. The probe used CUDA and required no install, download, or paid service. All **101 training-workspace tests** passed afterward. The familiar missing-NumPy PyTorch warning did not prevent the run.

## Decision

This result rules out the strongest version of “the model can never learn a prompt-to-answer mapping” for this setup. It leaves open whether the larger corpus, packed-window sampling, limited training steps, or their combination explains the ordinary and answer-weighted 100-step failures. **Do not treat the probe checkpoint as a general coding model or extend it to two hours.** Next, audit how the existing packed-window sampler exposes complete prompts and answer tokens on the approved v3 corpus, then design one controlled, bounded comparison before another broad training run.

To reproduce this exact diagnostic, use a **fresh** `--output` path from the repository root:

```powershell
uv run --project training --no-sync python training\phase2\three_example_probe.py `
  --candidate training\phase2\drafts\p2-02-request-following-v3\candidate.jsonl `
  --approval training\phase2\approvals\p2-02-request-following-v3.json `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --bundle training\artifacts\tokenizers\p2-request-following-v3 `
  --initialization training\artifacts\initializations\p2-request-following-step-zero-v3\initialization.pt `
  --output training\artifacts\probes\p2-three-example-recheck `
  --device cuda --steps 200 --minutes 10
```

The script refuses an existing output path and caps both steps and duration. `--device cpu` is available when CUDA is unavailable, though the measured 8.12-second duration is for this CUDA run only.
