# P2-02: packed-window exposure audit

The approved v3 training examples **were repeatedly present in the 100-step packed training windows**. The main mismatch visible in the sampler is where an example's prompt starts: the packed runner usually trains it well inside a 512-token context, while inference begins the prompt at position zero. This is a plausible explanation for the three-example probe succeeding while the earlier packed run produced no complete answers; this audit alone cannot establish causality.

The [audit script](../training/phase2/audit_packed_window_exposure.py) verified the owner-approved candidate SHA, built dataset and tokenizer hashes, all 156 JSONL records, the record token index, and each record's packed uint16 token span. It then replayed the production Python `random.Random(1337).randint(0, N - 512 - 1)` start sequence for 100 steps. The existing runner makes 16 batch-one samples per optimizer step (gradient accumulation 16), giving **1,600 sampled 512-token windows**. The replay audits sampled positions, not model updates, dropout, gradients, or optimizer state.

| Measure across the 100-step sampler replay | Result |
|---|---:|
| Approved training examples | 156 |
| Packed token stream | 14,770 tokens |
| Mean record length | 94.679 tokens, including EOS |
| Possible random window starts | 14,258 |
| Windows containing the full prompt context and all answer/EOS targets for a record | 7,157 record-window events (45.878 per record on average) |
| Records with no such complete window in this specific seeded replay | 2 |
| Sampled windows starting exactly at a record prompt | 14 of 1,600 |
| Mean prompt position when its full prompt and answer were in the same window | 209.69 of 512 |
| Mean answer/EOS target-token presentations per record | 1,268.391 |

The two records without a complete prompt-and-answer window are `gap-css-aspect-01` at the very beginning of the packed stream and `gap-javascript-string-slice-06` at its end. Both still had some answer tokens included in sampled targets. The random sampler does not fail to expose the corpus generally: most records fit wholly inside many windows, but their prompt positions vary. The diagnostic's three-example procedure put each prompt at position zero on every update, matching inference's starting position.

The ordinary and answer-weighted 100-step runs each used 100 × 16 × 512 = **819,200 target positions**. The answer-weighted run reuses the same seeded start sequence, so it has the same position exposure. Answer weighting changes the loss weights at answer positions; it does not align prompts with position zero.

## One bounded comparison to prepare

Use the same approved 156-record corpus, tokenizer, seed-1337 scratch initialization, ordinary next-token loss, AdamW settings, 100 optimizer steps, 16-sample accumulation, and 512-token windows. Change only the sampled start positions: select uniformly from the 156 verified record starts instead of all 14,258 token offsets, and take the next 512 tokens from that point, wrapping to the first packed record at end-of-stream. Each sampled window then begins with a training prompt at position zero while keeping the window length, update count, and target-position budget fixed. Other records in that window remain at later positions, so this is a first test of boundary alignment rather than perfect per-record isolation.

Score the new checkpoint on the same fixed 30-task development set and on the 156 seen training prompts. Compare with the saved ordinary 100-step checkpoint. Keep corpus validation out of training, leave the final holdout closed, and use the existing ten-minute ceiling. Save to a fresh probe directory. If the sampler change fails to improve seen-answer or development results, do not continue to a two-hour run; inspect prompt/position treatment or target loss before changing several things together.

The [local machine-readable audit](../training/artifacts/diagnostics/p2-v3-window-exposure-v2/report.json) contains per-record starts, token lengths, replay counts, and a hash of the replayed start sequence. To recreate it, use a fresh output path:

```powershell
uv run --project training --no-sync python training\phase2\audit_packed_window_exposure.py `
  --candidate training\phase2\drafts\p2-02-request-following-v3\candidate.jsonl `
  --approval training\phase2\approvals\p2-02-request-following-v3.json `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --output training\artifacts\diagnostics\p2-v3-window-exposure-recheck `
  --steps 100 --seed 1337
```

The audit command reads approved corpus and checkpoint-support files only. It does not train, rewrite data, or change a checkpoint.
