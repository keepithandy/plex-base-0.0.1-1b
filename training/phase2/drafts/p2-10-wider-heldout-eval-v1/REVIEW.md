# P2-10 wider held-out wording evaluation

Status: **prepared and reviewed for read-only scoring of the frozen P2-10 checkpoint**.

## Purpose and scope

The original P2-10 evaluation crossed one held-out wording with eight selectors and two input layouts (16 prompts). This separate evaluation-only set crosses four additional held-out wording templates with the same selectors and layouts (64 prompts). The output contract, selector targets, frozen tokenizer, checkpoint, and greedy decoding settings are unchanged. No prompts from this set are used for training or runtime validation loss.

This is a narrow selector-copy diagnostic. It does not open the final project holdout and does not authorize or start training. The set is additive: the original 16-row P2-10 evaluation remains separately reported.

## Wording matrix

| Phrase ID | Request template |
|---|---|
| `transcribe-css-selector` | `Transcribe this CSS selector: {value}` |
| `reproduce-selector-verbatim` | `Reproduce the selector below verbatim: {value}` |
| `preserve-selector-spelling` | `Preserve every character in this selector: {value}` |
| `write-selector-character-for-character` | `Write this selector again, character for character: {value}` |

Each wording is tested in inline (`: {value}`) and next-line (`:\n{value}`) input layouts for the same eight selectors: `.actions, .filters, .controls, .alpha-panel, .bravo-item, .charlie-list, .delta-card, .echo-label`. Each request differs from every P2-10 train/evaluation request.

## Exact identities

- Evaluation-only JSONL SHA-256: `da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a`
- Existing P2-10 checkpoint SHA-256: `28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb`
- Frozen tokenizer SHA-256: `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573`; no refit.
- Evaluation rows: 64; training rows: **0**.
- Maximum prompt / expected completion-plus-EOS length: 82 / 9 tokens.
- Evaluation use for training: false. Evaluation use for runtime validation loss: false.
- No training run or weight updates. Scoring uses deterministic greedy inference. Final holdout opened: false.

## Review decision

The four templates ask for the same exact selector-copy operation while varying the verb and wording. The design adds wording coverage without changing the task target, input layout, output contract, or checkpoint. Score this set only against the pinned existing checkpoint and report phrase/layout cells as descriptive small samples.
