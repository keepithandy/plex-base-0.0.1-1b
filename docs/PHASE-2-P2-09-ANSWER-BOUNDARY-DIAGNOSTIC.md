# P2-09: answer-boundary token diagnostic

Status: **read-only audit complete; no training run proposed or started here**.

## What P2-08's saved tokens show

The P2-08 tokenizer represents the generated answer separator newline as token ID `202` and the selector's leading period as token ID `17`. In greedy decoding, the model emitted both in six of the 16 held-out cases: all four exact answers and both wrong-known-selector answers began with token pieces `"\n"`, `"."`. The ten malformed outputs all began directly with a selector-name token and contained neither the separator newline nor the leading period.

| Held-out output pattern | Count | Example first token(s) |
|---|---:|---|
| Exact selector | 4/16 | `202 "\n"`, `17 "."` |
| Wrong known selector | 2/16 | `202 "\n"`, `17 "."`; `.filters` became `.actions` |
| Malformed output without answer boundary | 10/16 | Direct selector-name token; e.g. token `539` / piece `"al"` for `.alpha-panel` |

The value-specific pattern is also informative. `.alpha-panel`, `.bravo-item`, and `.echo-label` lost both prefix tokens under both layouts. `.charlie-list` and `.delta-card` lost them in the inline layout but were exact in the newline layout. `.controls` became `actions` in both layouts. `.filters` produced the well-formed but wrong `.actions` in both layouts. Thus there are at least two observed failure types: skipping the answer boundary/punctuation, and copying a different known selector.

The sole supplied-training miss was distinct: for `Repeat the selector exactly as shown:\n.filters`, the output token sequence was `202 "\n"`, `17 "."`, `202 "\n"`, `17 "."`, then the pieces for `echo-label`, followed by EOS. Teacher-forced scoring gives the expected initial newline rank 1 and period rank 1. At the expected selector-body token `fil`, however, `fil` ranks second and another newline ranks first. This matches the duplicated prefix in greedy decoding: after the correct `\n.`, the next predicted token is another newline. The expected prefix tokens are available to the model; the failure occurs later in this answer.

## Frozen-checkpoint teacher-forced audit

The read-only audit used the existing P2-08 checkpoint and the same approved 64 training / 16 evaluation prompts. It scored the expected answer tokens under teacher forcing; it did not generate samples or update weights. Evaluation remained outside training and runtime validation loss, and the final holdout stayed closed. The checkpoint SHA-256 before and after the audit was `a79571d3180bd6f2c8bff74a0b4e93eac47accc31e9494f221c29cd70913d956`.

| Expected token position | Training | Held-out evaluation |
|---|---:|---:|
| Answer newline `202` top-ranked | 64/64 | 6/16 |
| Selector period `17` top-ranked after the expected newline | 64/64 | 16/16 |
| First selector-body token top-ranked after expected `\n.` | 63/64 | 11/16 |
| EOS top-ranked after the expected full answer | 64/64 | 16/16 |

For evaluation, the expected newline's mean log probability was **−4.40** and mean rank was **3.50**. By input layout it was top-ranked in 2/8 inline cases (mean log probability −5.71) and 4/8 newline cases (−3.09). These tiny descriptive cells do not establish a reliable layout effect. Once the expected newline was supplied, the period was top-ranked in all 16 evaluation cases (mean log probability −0.0028). The expected first selector-body token was top-ranked in 11/16. In the five remaining cases, the top alternative was `actions`: both `.filters` rows, both `.controls` rows, and `.alpha-panel` in the newline layout. The first four are the observed wrong-selector outputs; the fifth generated the expected selector body during greedy decoding only because it skipped the answer prefix.

The primary shared evaluation error is therefore at the **first answer token**: under the held-out wording, the newline is top-ranked in only 6/16 cases, and the other ten greedy outputs skip directly to selector-name pieces. The period is strongly preferred when evaluated after the expected newline. Teacher-forced body/EOS scores condition on the correct preceding tokens; they do not claim the model would reach those positions during free generation. These measurements do not change P2-08's predeclared inconclusive outcome.

The complete per-record expected-token ranks, log probabilities, and top-five alternatives are in the local ignored artifact `training/artifacts/experiments/p2-08-selector-format-run-v1/answer-boundary-token-audit-v1.json`. It records `weightUpdate: false`, `newSamplesGenerated: false`, and `finalHoldoutOpened: false`.

## Training follow-up boundary

Do not continue or resume the P2-08 checkpoint. The audit narrows the next experiment's target from period tokenization to answer-start prediction and, secondarily, selector-body choice after the correct prefix. It does not justify changing training data or the output contract by itself.

Any training follow-up must be a fresh, deterministic candidate with separate train/evaluation files, a review report, exact SHA-256 hashes, and a new owner approval that pins the run bounds and evaluation-only boundary. Do not train while preparing or reviewing that candidate.
