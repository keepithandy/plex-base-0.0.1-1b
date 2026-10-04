# Request-following expansion: approval and current draft

**Superseded draft:** curation is complete in a new 180-record version. See the [exact-record approval guide](PHASE-2-CURATED-DATA-APPROVAL.md) and [revised complete examples](../training/phase2/drafts/p2-02-request-following-v2/REVIEW.md). The older 360-record draft below remains unchanged as history; its diversity concerns are addressed in the smaller candidate. The revised version still needs owner approval before inclusion.

The owner approved the exact twelve samples: **“i approve of these”**. The [approval record](../training/phase2/approvals/p2-02-expansion-samples-v1.json) identifies their original JSON digest and local P2 training scope. Their original pending-review files remain unchanged as the reviewed snapshot. This approval does not extend to unseen records or assert a public license grant.

The broader candidate is now concrete: [all 360 requests and answers](../training/phase2/drafts/p2-02-request-following-v1/REVIEW.md), [canonical JSONL](../training/phase2/drafts/p2-02-request-following-v1/candidate.jsonl), and [review measurements](../training/phase2/drafts/p2-02-request-following-v1/review.json). It is **a pending draft, not an approved training corpus**. The twelve approved samples are preserved separately and are not silently replaced or duplicated in this candidate.

## What exists

| Measure | Draft result |
|---|---:|
| Records | 360 |
| HTML / CSS / JavaScript records | 120 / 120 / 120 |
| Whole topic families | 30 |
| Split groups after merging shared numeric templates | 29 |
| Declared requirement profiles | 180 |
| Related naming/text variants per profile | 2 |
| Training / validation records | 252 / 108 |
| Per-language training / validation | 84 / 36 |
| Supplied solutions passing static review | 360 / 360 |
| Static checks passed | 1,614 |

The split uses the existing seed-51, 30%-of-groups algorithm. Arithmetic and bound topics share renamed `Math.min`, `Math.max`, and absolute-difference function bodies, so they were merged into one 24-record split group. All other groups contain twelve records. The resulting count happens to match the original proposed 252/108; the split was recalculated, not forced to that count. The validator rejects renamed JavaScript bodies assigned to different groups.

Canonical candidate SHA-256: `f48ae375ca8c0bca55bbb9a4471f418909db5ec857d99473c25d91d70baad6a5`.

The draft source documents contain the unchanged inference prompt followed by a newline and code. Review checks, lineage, behavior cases, and provenance notices are excluded from source text. The [pending catalog](../training/phase2/drafts/p2-02-request-following-v1/dataset-sources.candidate.json) is intentionally rejected by the production builder.

## What the checks establish

All supplied HTML/CSS answers passed the existing static evaluator, and all JavaScript functions passed Node `--check`. Forbidden output strings were checked separately. Exact normalized requests and answers were screened against the earlier authored sets, including the approved samples; development requests were also screened for exact duplicates. No final holdout was opened. No JavaScript behavior was executed.

Four focused tests passed: changed CSS answers are rejected; renamed numeric templates cannot cross groups; pending data cannot build a training corpus; and approval remains bound to the twelve original samples. Source documents and JSONL reproduce the authored generator's current records byte-for-byte. These are preparation checks, not measurements of Plex's performance.

## Diversity review still needed

This is template-authored data. It is not 360 independent tasks. Six declared profiles per topic are not automatically six distinct structural patterns: aspect ratios, cursors, string wrappers, and some other profiles differ mainly in values or states. The draft therefore **does not yet establish the proposal's six-distinct-patterns target**. Before seeking approval for inclusion, curate or replace repetitive profiles and merge any additional shared templates found during near-duplicate review. Recompute the split and digest after edits.

CSS requests explicitly spell out declarations, so this draft emphasizes copying constraints and emitting the correct rule rather than interpreting a free-form design request. HTML prompts supply some unused text and ask for specific nesting; the static checks do not establish every nesting/content requirement. Some HTML checks match the supplied answer verbatim, which helps detect accidental edits but does not independently prove correctness. JavaScript behavior cases are unexecuted expectations. These limits must remain visible in the eventual exact-record review.

No fresh tokenizer, token budget, initialization, baseline, or training run exists for this draft. After curation and exact-record approval, build a separate corpus, fit its tokenizer on training only, verify context/EOS/answer budgets, and initialize from random weights. The proposed first experiment remains 100 steps with a ten-minute ceiling, followed by matched static development scoring. A two-hour run remains deferred.

## Reproduce without training

The [draft authoring and validation script](../training/phase2/prepare_request_following_candidate.py) is versioned. Running it again refuses to overwrite the existing draft. To validate the current in-memory authoring definitions without writing anything, from the repository root:

```powershell
uv run --project training --no-sync python -c "import sys,json; sys.path.insert(0,'training/phase2'); import prepare_request_following_candidate as c; print(json.dumps(c.validate(c.records(),json.loads(c.DEV.read_text(encoding='utf-8'))),indent=2))"
```

There is nothing the owner needs to run at this stage. Next work is the diversity and correctness curation of this concrete draft, followed by a complete review of its final exact records. No additional source material, installation, payment, or training was performed.
