# P2-19 Reference-Mediated Symbol Binding — Approved First Run

## Status

**Owner approved. Preparation and one bounded first CUDA run are authorized.**

Candidate:

`p2-19-reference-binding-candidate-v1`

Approved candidate SHA-256:

`e96d6b8edd2a756a03d285f1081491232df7f79886a47d6ab02efcdb29211fa1`

## Fixed first-run policy

The approved run must use:

- **144 training records**
- **72 evaluation-only records**
- fresh tokenizer fitted on **training text only**
- fresh seed **1337** initialization
- unchanged **27,566,080-parameter** architecture
- ordinary next-token complete-record loss
- `complete-record-v1`
- micro-batch **1**
- gradient accumulation **16**
- CUDA
- matched step-zero scoring
- maximum **100 updates**
- maximum **10 minutes**
- no automatic extension
- P2-14 excluded from gradient training
- P2-01b excluded from gradient training
- final holdout closed

The P2-19 evaluation text must not be used for tokenizer fitting or gradient training.

## What P2-19 measures

P2-19 removes arbitrary raw-literal generation from most of the model's job.

The stable reference vocabulary is:

```text
R0 R1 R2 R3 R4 R5
```

### Level A — raw literal → reference lookup

The model sees a reference table and an unseen raw literal, then returns the matching reference.

This level still requires literal comparison.

### Level B — explicit field → reference selection

The model sees deterministic bindings such as:

```text
selector_ref=R0
old_ref=R2
new_ref=R4
```

and is asked for one explicit field.

This tests reference selection after deterministic prebinding.

### Level C — semantic role → reference selection

The bindings remain explicit, but the request is semantic, for example:

```text
Return the reference for the replacement value.
```

This tests whether semantic role recognition can generalize once arbitrary raw payload generation has been removed.

### Level D — three-reference plan

The model emits:

```text
selector_ref=R0
old_ref=R2
new_ref=R4
```

This tests the smallest model-side representation of a future deterministic edit plan.

## Scoring

### Levels A/B/C

For every row report:

- complete-task pass
- exact reference
- known reference output
- wrong known reference
- unknown/malformed output
- target-field breakdown
- EOS

This matters because a wrong known reference is a **binding error**, while an unknown/malformed output is still a representation/format failure.

### Level D

Report:

- format valid
- full plan exact
- selector reference exact
- old reference exact
- new reference exact
- known-reference status for each field
- EOS

## Interpretation matrix

| Outcome | Interpretation |
|---|---|
| A strong; B/C/D strong | Plex can resolve unseen literals and reason over references |
| A weak; B/C/D strong | Deterministic Plex Code prebinding is strongly supported |
| B strong; C weak | Explicit reference handling works, but semantic role mapping remains weak |
| C strong; D weak | Single-reference selection works; multi-reference composition is the next bottleneck |
| B/C/D weak after strong supplied-task fit | Reference mediation alone does not solve contextual binding at 27.6M |

Do not increase model size merely because Level A remains weak if B/C/D transfer strongly.

## Preparation

After pulling the merged approval path:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_19_approved_experiment.py `
  --output training\artifacts\experiments\p2-19-reference-binding-prepared-v1
```

The preparation wrapper must:

- verify the exact approved candidate SHA
- preserve the exact 144/72 split
- fit the tokenizer on training only
- pass the real `complete-record-v1` sampler preflight
- verify P2-19/P2-14/P2-01b token budgets
- create a fresh seed-1337 initialization
- leave `modelTrained: false`
- leave the final holdout closed

Then run read-only verification of the prepared bundle:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_19_approved_experiment.py `
  --output training\artifacts\experiments\p2-19-reference-binding-prepared-v1 `
  --verify-only
```

## First CUDA run

Only after preparation and verify-only are clean:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_19_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-19-reference-binding-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-19-reference-binding-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The wrapper rejects any request above 100 updates or 10 minutes and rejects non-CUDA execution.

## Gate after step 100

Do not automatically continue.

If the supplied curriculum remains strongly underfit and validation loss falls materially, a separately approved continuation may be justified.

If supplied fit is strong and Levels B/C/D transfer, stop treating raw-literal generation as a required model primitive and move the architecture toward deterministic Plex Code reference binding/resolution.

If supplied fit is strong but B/C/D remain near zero, reference mediation has not solved the binding problem at the current model scale.

The final holdout remains closed.
