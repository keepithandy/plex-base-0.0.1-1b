# P2-09 proposal: answer-boundary token diagnostic

## What P2-08's saved tokens show

The P2-08 tokenizer represents the generated answer separator newline as token ID `202` and the selector's leading period as token ID `17`. The model emitted both in six of the 16 held-out cases: all four exact answers and both wrong-known-selector answers began with token pieces `"\n"`, `"."`. The ten malformed outputs all began directly with a selector-name token and contained neither the separator newline nor the leading period.

| Held-out output pattern | Count | Example first token(s) |
|---|---:|---|
| Exact selector | 4/16 | `202 "\n"`, `17 "."` |
| Wrong known selector | 2/16 | `202 "\n"`, `17 "."`; `.filters` became `.actions` |
| Malformed output without answer boundary | 10/16 | Direct selector-name token; e.g. token `539` / piece `"al"` for `.alpha-panel` |

The value-specific pattern is also informative. `.alpha-panel`, `.bravo-item`, and `.echo-label` lost both prefix tokens under both layouts. `.charlie-list` and `.delta-card` lost them in the inline layout but were exact in the newline layout. `.controls` became `actions` in both layouts. `.filters` produced the well-formed but wrong `.actions` in both layouts. Thus there are at least two observed failure types: skipping the answer boundary/punctuation, and copying a different known selector.

The sole supplied-training miss was distinct: for `Repeat the selector exactly as shown:\n.filters`, the output token sequence was `202 "\n"`, `17 "."`, `202 "\n"`, `17 "."`, then the pieces for `echo-label`, followed by EOS. The expected prefix tokens are present, but duplicated before the wrong selector body. This suggests the evaluation's missing prefix is not a tokenizer inability to encode newline or period. It does not identify why the held-out prompt skips both.

## Proposed next step: frozen-checkpoint first-token audit

Before authorizing another training run, run a read-only, teacher-forced token audit against the existing P2-08 checkpoint and the same approved 64 training / 16 evaluation prompts. Do not generate new samples or update weights. Keep evaluation out of training and runtime validation loss, and do not open the final holdout.

For each prompt, score the expected completion token-by-token and record:

1. At the first answer position: rank and log probability of token `202` (newline), plus the highest-scoring alternatives.
2. Conditional on the expected newline: rank and log probability of token `17` (period).
3. Conditional on the expected newline and period: rank/log probability of the expected selector-body tokens and EOS.
4. The same measures grouped by training versus held-out wording, inline versus newline layout, and selector value.

This identifies whether the held-out errors start with a low-probability answer boundary, a low-probability period after a correct boundary, or a selector-body substitution. The four successful and two wrong-known-selector outputs provide in-run controls: both begin with the expected newline and period. The audit is descriptive and does not change P2-08's predeclared inconclusive outcome.

## Training follow-up boundary

Do not continue or resume the P2-08 checkpoint. The saved completions alone do not justify changing the training data or output contract: most malformed evaluation rows skip both the answer newline and the selector period, while the training miss duplicates both. Use the frozen-checkpoint audit to choose a single intervention before proposing another run.

Any training follow-up must be a fresh, deterministic candidate with separate train/evaluation files, a review report, exact SHA-256 hashes, and a new owner approval that pins the run bounds and evaluation-only boundary. Do not train while preparing or reviewing that candidate.
