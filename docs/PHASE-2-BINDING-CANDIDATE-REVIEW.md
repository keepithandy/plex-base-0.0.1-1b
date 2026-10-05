# P2-03: review the binding-diversity candidate

Prepared October 5, 2026. **The owner approved these exact 24 training examples, and the bounded original-only/varied comparison is complete.** The [approval record](../training/phase2/approvals/p2-03-binding-diversity-v1.json) authorizes six originals plus eighteen new variations for local diagnostic training. A separate twelve-example set remains evaluation-only. The [result report](PHASE-2-BINDING-DIVERSITY-RESULT.md) records 20/24 supplied answers learned by the varied arm, 0/12 new transfer passes and 0/30 development passes.

## Approved content

These examples teach Plex to keep the requested operation while changing the detail you specify. For example, both `copyItems(items)` and `shallowClone(items)` should return `items.slice()` when the request asks for a shallow copy. Different names should not cause the model to choose a different operation.

The six originals anchor the operations Plex already reproduced. Each gets three new training variations. There are eight candidate records per language:

| Operation | Original detail | Three new training details |
|---|---|---|
| HTML word isolated by `bdi` inside a paragraph | Kyoto | Lisbon, Seoul, Nairobi |
| HTML progress with maximum 100 | Value 35 | Values 18, 47, 83 |
| CSS dashed block-start border, 2px and color `#334155` | `.top-edge` | `.card-edge`, `.banner-edge`, `.notice-edge` |
| CSS centered flex row using `.toolbar` | Gap 12px | Gaps 6px, 14px, 28px |
| JavaScript integer quotient rounded toward zero | `quotientTowardZero` | `integerQuotient`, `quotientTruncated`, `divideTowardZero` |
| JavaScript shallow array copy | `copyItems` | `copyValues`, `shallowClone`, `copyList` |

For example, the proposed `shallowClone` reference is:

```javascript
function shallowClone(items) {
  return items.slice();
}
```

The [exact review](../training/phase2/drafts/p2-03-binding-diversity-v1/REVIEW.md) shows all 24 full requests and code answers, followed by the twelve evaluation-only examples. The [candidate JSONL](../training/phase2/drafts/p2-03-binding-diversity-v1/candidate.jsonl) is the canonical proposed training content. New references are simple transformations of the approved, Codex-authored originals; no external source text was introduced. Approval concerns local diagnostic training and does not grant a public license or establish model ability.

## Evaluation stays separate

The new [evaluation-only JSONL](../training/phase2/drafts/p2-03-binding-diversity-v1/evaluation-only.jsonl) contains two further changes per operation: Riga/Tallinn, values 27/74, `.summary-edge`/`.widget-edge`, gaps 10px/22px, `truncatedDivide`/`wholeQuotient`, and `cloneList`/`duplicateArray`. These bindings do not occur in the proposed training text. They measure new details within the same learned operation; they are not the existing family-separated corpus validation or the final benchmark.

The previous twelve transfer requests remain evaluation-only, including Osaka, Harbor, value 62, maximum 200, `.panel-edge`, 5px, `.command-bar`, 20px, and their four changed function names. None of those replacement bindings occurs in this candidate's training text. Original transfer controls deliberately overlap the six training anchors. The 30 development tasks are unchanged; no exact normalized candidate request duplicates a development prompt. Semantic skill overlap is expected, and this screen does not prove absence of all semantic leakage. The final holdout remains closed.

## Reviewed comparison, now complete

Compare an original-only six-anchor arm with the varied 24-record arm. Both must start from matching randomly initialized step-zero weights, retain the same existing 1,509-entry tokenizer and architecture, and use ordinary complete-record loss with the recorded AdamW settings. Each operation has equal sampling probability in both arms; the varied arm samples four records per operation. Six-anchor sampling is therefore a control for concentration on these operations, separate from the previous broad 156-record run.

Cap each arm at **100 updates and ten minutes**. Report actual target counts and exposure per operation: equal updates/operation probabilities do not imply identical token budgets, sequence lengths, or dropout draws. Confirm supplied answers are learned before drawing conclusions from transfer failures. Compare original answers, previous transfer variations, the separate new bindings, and the unchanged 30 development tasks. All are static/exact checks; generated JavaScript is never executed. This is a small diagnostic, not a two-hour base-model run or a complete coding benchmark.

The candidate is now built into separate diagnostic inputs, with distinct dataset identities and the unchanged tokenizer. The runner verifies exactly equal scratch starting parameter tensors and retains standard compatibility checks. Both arms completed 100 updates in about fourteen seconds each. Commands and artifact links are in the [completed report](PHASE-2-BINDING-DIVERSITY-RESULT.md); no repeat is required.

## Original preparation checks, before approval

- All 36 references (24 candidate plus 12 evaluation-only) passed syntax, existing static checks, and requested-binding checks. All 30 changed requests rejected the unchanged source answer.
- Training/evaluation request and reference duplicates were rejected. Reserved evaluation bindings were excluded from candidate training text; development request duplicates were checked.
- The immutable draft records retain `pending-owner-review` from the original preparation. The separate exact-hash approval record now authorizes their use; the diagnostic inputs were built without rewriting that reviewed snapshot. Existing source corpus, tokenizer, and checkpoints were preserved.
- The existing tokenizer represents every case within the fixed limits: maximum 84 prompt tokens, 110 complete-record tokens including EOS, and 28 answer tokens including EOS. No new tokenizer was fitted.
- Four focused tests passed, including held-out binding rejection, incorrect reference rejection, pending status/source preservation, byte-identical repeated preparation, and overwrite refusal. These checks validate data preparation, not model performance.

The [machine-readable preparation report](../training/phase2/drafts/p2-03-binding-diversity-v1/review.json) records:

| File | SHA-256 |
|---|---|
| Proposed 24-record training candidate | `8f3fc7dfc21c4ebb5ce5b40391e9b123521d13df50b2d349e5d6b7c3faf37c2f` |
| Separate 12-record evaluation set | `ea8699efc997c0b4a5cdeb55c0da1d5be1b0d27a8ae9ad6b5164476c0d82ca7c` |
| Approved source candidate | `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016` |
| Existing tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |

The [preparer](../training/phase2/prepare_binding_candidate.py) can reproduce the four draft files into a fresh directory. No dataset download, installation, paid service, model inference, or training was performed in this preparation.

## Recorded decision and next work

The owner approved: **“Approve the 24 binding-diversity examples for local diagnostic training.”** The eighteen new variations and six originals were used only for the bounded P2-03 diagnostic; the twelve evaluation-only examples remain excluded from training. This does not approve a long run or public release.

P2-03 remains active. Next prepare the answer-focused complete-record comparison described in the [result report](PHASE-2-BINDING-DIVERSITY-RESULT.md), using the same approved examples. No training is currently running and no additional data approval is needed for that preparation.
