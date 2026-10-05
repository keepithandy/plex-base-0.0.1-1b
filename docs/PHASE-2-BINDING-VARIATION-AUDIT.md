# P2-03: audit of requested names and values

Recorded October 5, 2026. **The approved corpus varies operations and structures much more than it demonstrates changing a requested name or value within the same operation.** This is a concrete training-data gap consistent with the completed transfer failures. It is not proof that data diversity is the only cause, or that another training run will solve it.

## Completed transfer result

The owner completed the CUDA [transfer diagnostic](PHASE-2-TRANSFER-DIAGNOSTIC.md). Step 100 reproduced 2/6 selected original answers; step 200 reproduced all 6/6. Both checkpoints passed **0/12 variations**, with **0/12 requested-binding passes**. Step 200 passed syntax on 9/12 variations, retained the old binding in 6/12, and repeated the entire original reference in 3/12. There were no empty or truncated outputs. The original controls were selected because step 200 learned them; this remains a small diagnostic with selection bias.

Examples from step 200:

- Asking for `Harbor` still produced `<p><bdi>Kyoto</bdi></p>`.
- Asking for progress maximum 200 still produced maximum 100.
- Asking for a 20px gap still returned the original `.toolbar` rule with 12px.
- Asking for `duplicateItems` produced `takeLastTwo(items)` and sliced off the last two elements. This changed the operation as well as ignoring the requested name.

Some CSS outputs passed the small evaluator's syntax check despite invalid declaration values; syntax acceptance is not browser validity. JavaScript was parsed only, never executed. Repetition is not the sole failure: other outputs substituted unrelated structures or operations.

## Measured corpus coverage

The audit verified the approved candidate hash and compared every actual built train/validation record's complete text against the candidate's rendered prompt and reference. There are 156 training records (54 HTML, 54 CSS, 48 JavaScript) and 78 validation records (24 HTML, 24 CSS, 30 JavaScript). The 26 training split groups and 12 validation split groups do not overlap. Group sizes are not assumed equal.

| Finding | Evidence | Interpretation |
|---|---|---|
| JavaScript names vary globally, but do not demonstrate rebinding the same body | 48 training functions have 48 distinct names and 48 distinct source signatures after masking only the function name and collapsing whitespace | No paired example preserves the remaining source while changing the requested function name. |
| CSS selectors vary globally, but do not demonstrate rebinding the same rule | 54 training class selector names and 54 distinct source signatures after masking class names in the selector and collapsing whitespace | Different selectors are associated with different declaration bodies or selector forms. |
| HTML `bdi` word is fixed | All six training records in `html-bidi` request `Kyoto`; wrappers change | This family supplies no second word to copy into the same structure. |
| Determinate progress numbers are fixed | Four determinate records in `html-progress` use value 35 and maximum 100; two remaining records are indeterminate | Wrappers/fallback text vary, but the determinate numeric binding does not. |
| Logical border width is fixed | All six `css-logical-border` training references use 2px | Edge/property/style changes do not teach a different requested width in the same rule. |
| Most transfer details are new to the corpus | Eleven of twelve replacement details have zero boundary-matched occurrences in training prompt/reference text | Failures include novel names and literal values; this audit is about source-text coverage, not unseen tokenizer IDs. |
| One failed value was already present | 20px occurs in `gap-css-layout-06`, a `.stack` column-flex rule | Its appearance elsewhere did not enable rebinding the `.toolbar` row's gap from 12px to 20px. |

The same-body metrics are textual measures, not proofs about semantic equivalence. Masking function names leaves parameter names, operations, constants, and formatting other than whitespace intact. Masking CSS class names leaves pseudo-classes, declarations, and values intact. Lexical occurrence counts use name/number boundaries and do not establish that a detail is taught for the relevant operation. Other HTML groups have different labels; the fixed-word finding applies to the inspected `bdi` family, not every HTML record.

## Next controlled experiment to prepare

Follow-up: the owner approved the exact [24-example candidate and separate evaluation plan](PHASE-2-BINDING-CANDIDATE-REVIEW.md). The [bounded comparison is complete](PHASE-2-BINDING-DIVERSITY-RESULT.md): the varied arm learned 20/24 supplied answers but passed 0/12 new binding requests and 0/30 development tasks. The proposal below preserves the audit's original recommendation; the candidate preparation, approval and two-arm run have since been completed.

Prepare a **small binding-diversity candidate for review**, using the six learned control operations as anchors. Include each original plus three new, independently chosen request/reference variations: 24 candidate records total, balanced eight per language. Change one requested detail per variation and keep the operation and code structure fixed. Use names and values distinct from all twelve transfer cases, the existing development requests, and the reserved evaluation prompts. Preserve the current transfer cases as evaluation-only.

Review the complete prompt, reference, and checks for each variation. Correct references must pass syntax and explicit binding checks; the original answer must fail a changed binding. Keep a separate, never-trained set of new bindings for this experiment's evaluation. Clearly label same-family unseen bindings as transfer evaluation, distinct from the existing family-separated corpus validation and 30-task development set. This candidate is proposed work; it has not been generated or approved for training.

After review and explicit approval of the exact new examples, prepare a matched, short P2-03 diagnostic: an original-only six-anchor control and a varied 24-record arm. Start both from the same existing scratch step-zero checkpoint and retain the existing tokenizer, architecture, ordinary complete-record objective, optimizer, and inference settings. Sample each of the six operations with equal probability in both arms; in the varied arm sample its four approved records uniformly. Cap each arm at 100 updates and ten minutes, record actual targets, and report that token lengths/exposures differ. Confirm each arm learned its supplied answers before interpreting transfer failure. Compare original controls, untouched transfer cases, separate new bindings, and the unchanged development tasks.

This is a small learnability/transfer experiment, not the next base-model corpus or a two-hour run. The approved broad corpus and its completed P2-02 deliverables remain recorded. P2-03 stays active because configuration/data-policy selection has not produced useful unseen-task completion. If the varied arm improves transfer, that supports preparing broader reviewed variation coverage; if not, investigate the training objective or model limitations next. Neither outcome alone passes the Phase 2 quality gate.

## Verification and reproduction

The audit runs without importing PyTorch or performing gradient updates. It checked both built splits against all 234 approved rendered examples, frozen transfer cases, checkpoint identities recorded in the report, aggregate counts recomputed from each completion, and split-group separation. An independent static rescore reproduced all recorded measures for all 36 saved completions; the transfer script and case hashes match the completed run. Python syntax and documentation links were checked. No new training or dataset build was run.

The [machine-readable audit](../training/artifacts/diagnostics/p2-binding-audit-v2/report.json) contains exact coverage counts and all 36 training prompt/reference pairs in the six inspected groups. The [completed transfer report](../training/artifacts/diagnostics/p2-transfer-v1/report.json) has SHA-256 `8f2025b39363b0726efc46dab102e37e43deda5637b5fc15c022d5900d984317`; its cases hash is `c70af62e3f954066a24dae36c613b6efb51a2a34580326d0d9400afff53e88a3`. The approved candidate hash remains `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`.

To reproduce the read-only audit with a fresh report filename:

```powershell
uv run --project training --no-sync python training\phase2\audit_binding_variation.py --report training\artifacts\diagnostics\p2-binding-audit-my-check\report.json
```

The audit refuses to overwrite a report. The existing `p2-binding-audit-v1` report predates the added built-text verification; `v2` is the complete audit. The owner does not need to rerun the audit, transfer check or completed diversity experiment. Next work is the answer-focused objective comparison preparation described in the [result report](PHASE-2-BINDING-DIVERSITY-RESULT.md).
