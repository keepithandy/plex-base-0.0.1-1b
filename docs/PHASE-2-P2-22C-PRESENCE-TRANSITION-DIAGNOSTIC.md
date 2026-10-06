# P2-22c Presence Transition Diagnostic

## Status

**Owner-authorized evaluation-only diagnostic.**

P2-22c does not train Plex.

It scores the existing P2-22b cumulative step-500 checkpoint on a new 45-record state-transition diagnostic.

Diagnostic SHA-256:

`4d445110d7688e2c9e3d1ba83eb9597eb3320550b71ac9324bf970f6bc1fa479`

## Question

P2-22b showed a narrow INSERT defect after perfect supplied fit.

At step 500, held-out INSERT predictions were:

- DELETE: 6
- REPLACE: 3
- RENAME: 2
- TOGGLE: 2
- INSERT: 2

Tier A was especially clean: all five held-out INSERT paraphrases were predicted as DELETE.

P2-22c tests whether explicitly exposing before/after state direction resolves that confusion.

## Diagnostic labels

Only three labels are relevant:

```text
INSERT
DELETE
REPLACE
```

Canonical transitions:

```text
INSERT   ABSENT  -> PRESENT
DELETE   PRESENT -> ABSENT
REPLACE  PRESENT -> PRESENT with changed content
```

## Dataset

45 evaluation-only records:

| Tier | Records | INSERT | DELETE | REPLACE |
|---|---:|---:|---:|---:|
| A — explicit state transition | 15 | 5 | 5 | 5 |
| B — minimal matched contrasts | 15 | 5 | 5 | 5 |
| C — repository state transition | 15 | 5 | 5 | 5 |

Chance is **5/15 = 33.3% per tier**.

There is zero exact request overlap with the P2-22 candidate.

The maximum word-Jaccard similarity to P2-22 is 0.432432.

High similarity within matched P2-22c contrast groups is intentional: the before/after transition should be the principal changing semantic feature.

## Source checkpoint gate

The scorer requires the reviewed P2-22b step-500 source:

- cumulative step 500;
- supplied fit 150/150;
- train A/B/C = 50/50 each;
- Tier A/B/C = 16/25, 16/25, 18/25;
- tokenizer SHA `8f09812c2165cb928c1908f7a81ef59d5e8b6f3f8acb185e083bf1324ed23e5a`;
- 27,566,080 parameters;
- the exact reviewed final per-intent tier breakdown;
- the exact reviewed held-out INSERT confusion pattern;
- actual step-500 checkpoint SHA matching the step-500 candidate score and P2-22b result.

## Metrics

P2-22c reports:

- overall exact /45;
- Tier A/B/C exact /15;
- INSERT /15;
- DELETE /15;
- REPLACE /15;
- full expected-to-predicted confusion matrix;
- INSERT<->DELETE reverse-polarity errors;
- combined presence-polarity accuracy for INSERT + DELETE;
- known P2-22 intent outputs;
- outputs outside the three-label diagnostic vocabulary;
- malformed/unknown outputs;
- EOS.

## Interpretation

### Strong INSERT and DELETE

If explicit state transitions produce strong INSERT and DELETE accuracy, the P2-22 defect is primarily a semantic-normalization problem.

That supports a future Plex interface where tooling or the model first normalizes:

```text
presence_before
presence_after
content_relation
```

and intent is derived from that semantic state.

### DELETE strong, INSERT weak

If INSERT remains weak even when ABSENT -> PRESENT is explicit, the model has a deeper polarity/binding defect.

P2-23 should then avoid assuming presence-direction classification is solved.

### Both INSERT and DELETE weak

The model does not reliably use the explicit state representation. Redesign should happen before composing this primitive into larger semantic plans.

### REPLACE strong, presence directions weak

The model can reason about in-place mutation but not existence transitions.

That would isolate presence semantics as the next representation problem.

## Verify

```powershell
uv run --project training --no-sync python training\phase2\verify_p2_22c_presence_transition_diagnostic.py
```

## Run

```powershell
uv run --project training --no-sync python training\phase2\run_p2_22c_presence_transition_diagnostic.py `
  --prepared training\artifacts\experiments\p2-22-edit-intent-prepared-v1 `
  --source-run training\artifacts\experiments\p2-22b-edit-intent-continuation-v1 `
  --output-dir training\artifacts\experiments\p2-22c-presence-transition-diagnostic-v1 `
  --device cuda
```

This command performs scoring only.

It does not fit a tokenizer, initialize a model, update optimizer state, resume training, or modify model weights.

The final project holdout remains closed.
