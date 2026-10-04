# P2-02: development failures and next data candidate

**Update:** The owner approved this exact v3 candidate for local training. Its build, tokenizer, fresh initialization, 100-step run, and matched development scores are recorded in the [v3 result report](PHASE-2-FAILURE-GAP-100-STEP-REPORT.md). The review guide and pending catalog below remain the immutable pre-approval snapshot; training used the separate approved source catalog.

The [approved 180-example run](PHASE-2-CURATED-100-STEP-REPORT.md) improved held-out next-token loss but passed **0 of 30** unchanged development tasks. It produced no truncated answers. That combination makes a longer run on the same corpus a poor next test of coding ability. This review uses the saved [30 responses](../training/artifacts/evaluation/p2-request-following-100step-v2/responses.jsonl), [score](../training/artifacts/evaluation/p2-request-following-100step-v2/score.json), and the exact [approved-v2 candidate](../training/phase2/drafts/p2-02-request-following-v2/candidate.jsonl). The final 60-task holdout was not opened.

| Language | Observed failure in the 100-step responses | Relevant training-set concentration |
|---|---|---|
| HTML | A navigation request yielded `\n<p><p><p><p><p><p>`; other requests similarly produced unclosed or unrelated fragments. Neither required structures nor complete-task checks passed. | The 42 HTML training records cover seven topic groups: abbreviation, description, disclosure, heading-group, meter, progress, and ruby. They do not train navigation, forms, or multi-part content. |
| CSS | Responses reused `.rf-alpha` / `.rf-whitespace-alpha` fragments and malformed declarations instead of the requested selectors and layouts. | The 42 CSS training records use only **seven distinct selectors**, repeated across property profiles. They do not teach flex/grid composition or interaction-state selectors. |
| JavaScript | Answers repeatedly declared `transformAlpha` even when the task required `clamp`, `countWords`, or another name; many bodies were incomplete or unrelated. JavaScript was parsed, never executed. | **All 36** JavaScript training records declare `transformAlpha`. Numeric comparison relatives were in validation, leaving six topic groups in training. |

These are observed associations, not proof that changing data alone will fix the model. The small corpus is still prompt-heavy: answer text including its leading newline is 22.6% of training token positions. The development set may guide this iteration, but improvement on that same set will be a development result, not an independent final score.

## Prepared candidate

The [v3 exact-record guide](../training/phase2/drafts/p2-02-request-following-v3/REVIEW.md) was the pre-approval review snapshot. Its [canonical JSONL](../training/phase2/drafts/p2-02-request-following-v3/candidate.jsonl) has SHA-256 `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`. It leaves the approved v2 source and all previous datasets/checkpoints intact.

It carries the 180 reviewed records into a new version, replacing repeated CSS selectors and JavaScript function names with meaningful names tied to each operation. It also adds **54 new, original examples**: six each in navigation, forms, multi-part content, layout, state, sizing, arrays, strings, and objects. The new requests do not exactly duplicate any development request. No external source text is included.

For a quick review, compare these records in the full guide:

- [JavaScript `addNumbers`](../training/phase2/drafts/p2-02-request-following-v3/REVIEW.md): the old arithmetic request/answer both used `transformAlpha`; the revised pair asks for and declares `addNumbers`. New `keepEven(items)` asks for a filtered array and supplies an arrow callback.
- [CSS `.toolbar`](../training/phase2/drafts/p2-02-request-following-v3/REVIEW.md): the answer combines `display: flex`, a 12px gap, and centered items instead of repeating one `.rf-...-alpha` selector across six profiles.
- [HTML Resources navigation](../training/phase2/drafts/p2-02-request-following-v3/REVIEW.md): the answer nests two links in a labeled `nav`, rather than supplying only an isolated element.

The whole-group split is 156 training / 78 validation records. The 54 new examples contribute 12 training and six validation records per language. Across all 234 records, there are 78 distinct CSS selectors and 78 distinct JavaScript function names. Related examples remain in one split group; the candidate has 38 groups. The pending [source catalog](../training/phase2/drafts/p2-02-request-following-v3/dataset-sources.candidate.json) must not be used for training until approval.

The [read-only candidate check](../training/phase2/check_failure_gap_candidate.py) reproduced all 234 source files from their canonical rows, verified the SHA-256 and pending catalog, and checked the split. All 234 supplied answers passed 1,007 static checks. Four focused tests passed, including rejection of a reused JavaScript name, a cross-split move, and an attempted build from the pending catalog. The HTML tree and CSS declaration checks compare against authored expectations. Node parsed the JavaScript answers without calling them. These checks verify preparation consistency; they do **not** establish browser behavior, JavaScript correctness for every input, or Plex coding ability.

The approved comparison is now complete; see the [result report](PHASE-2-FAILURE-GAP-100-STEP-REPORT.md). It passed no complete task after 100 steps, so the two-hour run remains deferred. The $0 paid-services and 200 GiB storage limits remain in force.
