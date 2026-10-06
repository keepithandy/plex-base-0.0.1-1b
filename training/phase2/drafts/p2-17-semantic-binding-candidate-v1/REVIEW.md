# P2-17 Semantic Edit Binding Candidate

## Status

**Pending owner review. No tokenizer fitting, checkpoint initialization, or model training is authorized by this candidate work.**

Candidate: `p2-17-semantic-binding-candidate-v1`

SHA-256:

`2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5`

## Why P2-17 exists

P2-16/P2-16b showed a specific failure mode rather than a generic inability to emit CSS.

By cumulative step 500, the supplied 120-record curriculum was nearly fitted, CSS syntax was strong on the easiest evaluation tiers, but complete held-out edits remained 0. Manual inspection showed Plex often emitted a semantically related **training selector and training value** instead of copying the literal selector/value from the current request.

P2-17 therefore targets **symbol binding** rather than broader CSS coverage.

## Candidate structure

The candidate contains **180 records** built from **80 underlying transformations**:

- 60 training scenarios;
- 20 fully held-out evaluation scenarios.

Each training scenario appears in exactly two supervised forms:

1. **extract-plan** — source CSS + natural-language edit → canonical five-field plan;
2. **apply-plan** — source CSS + explicit correct plan → final CSS.

That gives **120 training records**.

Each held-out evaluation scenario appears in three forms:

- **Tier A /20 — extraction:** source CSS + edit request → canonical edit plan;
- **Tier B /20 — application:** source CSS + explicit edit plan → final CSS;
- **Tier C /20 — chaining:** source CSS + edit request → final CSS, with no edit plan supplied.

Tier C has **no direct training analogue**. It asks whether Plex can compose the separately supervised extraction and application behaviors.

## Canonical edit plan

Every plan has exactly five lines:

```text
selector=<literal selector from current source>
operation=<replace|add|remove>
property=<requested CSS property>
old=<literal old value or <none>>
new=<literal new value or <none>>
```

This format is intentionally small and deterministic so field-level scoring can tell us whether the model failed selector binding, operation recognition, property recognition, old-value binding, or new-value binding.

## Literal holdout

Selectors contain no `train`, `eval`, or tier marker. They use the same neutral selector grammar on both sides of the split.

The candidate has:

- **0 training/evaluation selector overlap**;
- **0 training/evaluation source/target value overlap**;
- no exact duplicate requests.

Properties and operation types are intentionally familiar. P2-17 is not testing a new CSS property family. It is testing whether the current model can bind exact symbols and values from context instead of retrieving a remembered training answer.

## Training balance

The 60 training scenarios contain:

- replace: 20
- add: 20
- remove: 20

Each of six familiar properties appears in 10 scenarios:

- `border-radius`
- `opacity`
- `width`
- `padding`
- `font-size`
- `line-height`

Each scenario contributes one extraction record and one application record.

## Proposed scoring

### Tier A — request → plan

Report exact accuracy independently for:

- selector
- operation
- property
- old value
- new value
- all five fields together
- EOS

This is the primary P2-17 signal.

### Tier B — plan → CSS

Report:

- complete-task pass
- exact-string match
- selector preservation
- requested edit applied
- unrelated declaration preservation
- syntax validity
- EOS

### Tier C — request → CSS

Use the same CSS metrics as Tier B. Compare B vs C on the **same 20 underlying held-out scenarios**. If B succeeds while C fails, the bottleneck is extraction/chaining rather than edit application.

## Proposed first run

If the owner later approves this exact candidate, the first proposal is to keep the existing 27,566,080-parameter architecture and the existing optimization objective so **semantic-binding representation is the main changed variable**:

- fresh seed-1337 initialization;
- fresh tokenizer fitted on the 120 training records only;
- ordinary next-token loss over complete records;
- `complete-record-v1`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- matched step-zero scoring;
- maximum 100 updates / 10 minutes;
- no automatic extension.

P2-14 and P2-01b remain development-only. The final holdout remains closed.

## What would count as progress

P2-17 does not need Tier C to become perfect immediately.

The first meaningful result would be **nonzero Tier A full-plan accuracy with strong per-field literal accuracy**, especially selector and new-value binding. Tier B then tells us whether a known plan can already be executed. Tier C determines whether those capabilities compose.

If Tier A remains dominated by remembered training literals, the representation still has not solved the binding problem and more raw CSS pairs are unlikely to be the right next move.
