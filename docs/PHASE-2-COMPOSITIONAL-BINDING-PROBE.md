# P2-04: compositional-binding probe

Prepared October 5, 2026.

## Why this exists

The answer-focused P2-03 comparison improved supplied-answer reproduction from 20/24 to 23/24, but both objective arms remained at 0/12 on new bindings, 0/12 on reserved transfer requests, and 0/30 on the broader development tasks.

That separates two questions that were previously mixed together:

1. Can Plex learn the supplied request-to-answer mappings? Increasingly yes.
2. Can Plex recombine already-learned binding pieces into an unseen request? Not yet demonstrated.

P2-04 targets only the second question.

## Step 1: identify the remaining supplied failure

The completed local run already wrote record-level completions to:

`training/artifacts/experiments/p2-answer-focused-run-v1/answer-focused/completion-score.json`

Run:

```powershell
uv run --project training --no-sync python training\phase2\inspect_answer_focused_failure.py `
  --score training\artifacts\experiments\p2-answer-focused-run-v1\answer-focused\completion-score.json
```

The command prints the exact failed candidate, expected answer, generated completion, and its `sourceId`. The P2-03 aggregate result proves the remaining miss is in CSS, but the uncommitted local completion artifact is the authoritative source for which CSS operation failed.

## Step 2: prepare a tiny recombination matrix

The candidate preparer supports the two CSS operations that can explain the remaining 5/6 CSS result:

- `gap-css-logical-border-03`
- `gap-css-layout-01`

Use the `recommendedSourceId` printed by Step 1.

```powershell
uv run --project training --no-sync python training\phase2\prepare_compositional_binding_candidate.py `
  --source-id gap-css-layout-01 `
  --output training\phase2\drafts\p2-04-compositional-binding-probe-v1
```

Replace the example source id if the inspector reports the logical-border operation instead.

## Experimental design

The probe has exactly two independent binding slots and a 3 x 3 combination space.

Six combinations are proposed for training and three combinations are evaluation-only. The split is constructed so that:

- every value for slot A appears at least twice in training,
- every value for slot B appears at least twice in training,
- every individual slot value is therefore familiar,
- no evaluation pair appears in training,
- every held-out example requires only recombination of already-seen pieces.

Training pair indices:

`(0,0), (0,1), (1,1), (1,2), (2,0), (2,2)`

Held-out pair indices:

`(0,2), (1,0), (2,1)`

This is intentionally much narrower than another broad data expansion. If Plex succeeds here, it is evidence for compositional binding within one operation. If it fails while fitting all six training combinations, the next bottleneck is not prompt loss and not simple exposure count; it is the model's ability to represent and recombine bindings.

## Approval boundary

`prepare_compositional_binding_candidate.py` creates a **pending-owner-review** candidate only. It does not train a model, alter the tokenizer, open the final holdout, or authorize a longer run.

The next training comparison should not be wired until the generated `REVIEW.md`, candidate hash, and evaluation-only hash have been reviewed and approved.
