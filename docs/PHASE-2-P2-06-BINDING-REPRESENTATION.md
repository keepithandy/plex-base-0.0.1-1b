# P2-06: binding-representation probe

Prepared October 5, 2026.

## Why this exists

P2-05 established a clean bottleneck. All three folds learned every supplied selector-gap combination (18/18 total), yet only 1/9 fold-local held-out combinations composed correctly. All nine held-out outputs were syntactically valid CSS, selectors were preserved 6/9 times, gaps only 2/9 times, and six held-out outputs replayed a supplied training solution.

That means another exposure-count or prompt-masking experiment would answer the wrong question. P2-06 asks where binding information is first lost.

## Three-level ladder

P2-06 uses three independent arms. Each arm must start from fresh seed-1337 scratch weights if training is later approved. The arms do not train sequentially and do not share checkpoints.

### Level 1 — single-copy

Question: can Plex preserve one requested binding through prompt → answer?

Training exposes each of the three selectors and three gaps once. Evaluation uses the same six values with alternate request wording.

Examples:

```text
Return this selector exactly: .controls
```

Expected:

```text
.controls
```

and:

```text
Return this gap exactly: 14px
```

Expected:

```text
14px
```

The Level-1 evaluation is intentionally **not a novel-value holdout**. It is a narrow representation/instruction probe: the value is known, but the exact request wording is not.

### Level 2 — dual-binding

Question: can Plex preserve two independent bindings simultaneously when code generation is removed?

Example:

```text
Selector: .controls
Gap: 14px
Return exactly two lines: selector=<selector> then gap=<gap>.
```

Expected:

```text
selector=.controls
gap=14px
```

Six selector-gap combinations are proposed for training and three are held out. Every selector and every gap appears exactly twice in the six training records.

### Level 3 — CSS composition

Question: if Plex can preserve both bindings, can it insert them into the learned CSS structure?

Example:

```text
Selector: .controls
Gap: 14px
Write one flex-row rule with centered items using exactly that selector and gap.
```

Expected:

```css
.controls { display: flex; gap: 14px; align-items: center; }
```

Level 3 uses the **identical binding split** as Level 2. Only the answer complexity changes.

## Shared 3×3 split for Levels 2 and 3

Training:

- `.actions + 6px`
- `.actions + 14px`
- `.filters + 14px`
- `.filters + 28px`
- `.controls + 6px`
- `.controls + 28px`

Held out:

- `.actions + 28px`
- `.filters + 6px`
- `.controls + 14px`

This is deliberately the same Fold-A split that reproduced the P2-04 1/3 composition result. The point is not to create another broad transfer benchmark; it is to compare representation difficulty while holding the binding geometry fixed.

## Interpretation gate

The planned interpretation is hierarchical:

1. **Level 1 fails** → basic prompt-bound copying/token representation is already unstable. Do not diagnose multi-binding composition yet.
2. **Level 1 passes, Level 2 fails** → Plex can preserve one binding but not reliably maintain two independent requested values at once.
3. **Level 2 passes, Level 3 fails** → the bindings survive, but code-generation composition collapses them back toward memorized solutions.
4. **All three pass** → P2-05's 1/9 result is more likely tied to training distribution/competition than to a hard representational limit.

A level should not be interpreted as transfer-capable unless it first fits its supplied training records.

## Candidate size

The preparer creates:

| Level | Training | Evaluation |
|---|---:|---:|
| Single-copy | 6 | 6 |
| Dual-binding | 6 | 3 |
| CSS composition | 6 | 3 |
| **Total** | **18** | **12** |

All records are original diagnostic text. No external source text is introduced.

## Objective and run shape after approval

The intended follow-up, **not yet authorized by this preparation patch**, is:

- three independent fresh scratch initializations,
- seed 1337 for each arm,
- answer/EOS-only complete-record objective,
- the existing frozen tokenizer unless review discovers a reason to change it,
- bounded diagnostic training only,
- evaluation rows excluded from gradient training and runtime validation loss,
- no final project holdout access,
- no automatic long-run extension.

The exact step/time cap should be recorded in the approval artifact rather than assumed by the candidate preparer.

## Approval boundary

`prepare_binding_representation_probe.py` only materializes the candidate and review artifacts. All 18 proposed training examples remain `pending-owner-review`. The 12 evaluation examples are marked `evaluation-only-never-train`.

Run locally:

```powershell
uv run --project training --no-sync python training\phase2\prepare_binding_representation_probe.py `
  --output training\phase2\drafts\p2-06-binding-representation-v1
```

Review the generated `REVIEW.md`, `review.json`, and exact JSONL hashes before recording any training approval.
