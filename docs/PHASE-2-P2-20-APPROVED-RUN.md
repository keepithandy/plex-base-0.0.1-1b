# P2-20 Semantic Role + Reference Lookup Decomposition — Approved First Run

## Status

**Owner approved. Preparation and one bounded first CUDA run are authorized.**

Candidate:

`p2-20-role-decomposition-candidate-v1`

Approved candidate SHA-256:

`8d7c54ceed8a0c90a437626e504e2ba39582f0ca5c57c243db5c564e2c02985d`

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

The P2-20 evaluation text must not be used for tokenizer fitting or gradient training.

## Levels

### Level A — semantic wording -> role label

Expected outputs are one of:

```text
SELECTOR
OLD
NEW
```

Report:

- complete task / exact role
- known-role output
- wrong-known-role output
- unknown/malformed role
- target-role breakdown
- EOS

Chance baseline: **1/3**.

### Level B — explicit role + bindings -> reference

Example:

```text
BINDINGS:
SELECTOR=R0
OLD=R2
NEW=R4

ROLE: NEW
```

Expected:

```text
R4
```

Report:

- complete task / exact reference
- known-reference output
- wrong-known-reference output
- unknown/malformed reference
- target-role breakdown
- EOS

Chance baseline: **1/6**.

### Level C — semantic wording + bindings -> reference

This recombines Level A semantics with Level B lookup.

Report the same reference metrics as Level B.

## Interpretation

| Result | Interpretation |
|---|---|
| A strong, B strong, C strong | role semantics + lookup + composition transfer |
| A weak, B strong | semantic classification bottleneck |
| A strong, B weak | symbolic lookup bottleneck |
| A strong, B strong, C weak | composition bottleneck |
| A/B/C weak after strong train fit | current model/data regime still does not generalize the isolated primitives |

## Preparation

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_20_approved_experiment.py `
  --output training\artifacts\experiments\p2-20-role-decomposition-prepared-v1
```

Then verify:

```powershell
uv run --project training --no-sync python training\phase2\prepare_p2_20_approved_experiment.py `
  --output training\artifacts\experiments\p2-20-role-decomposition-prepared-v1 `
  --verify-only
```

## First CUDA run

Only after preparation and verify-only are clean:

```powershell
uv run --project training --no-sync python training\phase2\run_p2_20_approved_experiment.py `
  --prepared training\artifacts\experiments\p2-20-role-decomposition-prepared-v1 `
  --output-dir training\artifacts\experiments\p2-20-role-decomposition-run-v1 `
  --device cuda `
  --steps 100 `
  --minutes 10
```

The wrapper rejects requests above 100 updates or 10 minutes and rejects non-CUDA execution.

## Gate after step 100

Do not automatically continue.

If supplied fit remains materially incomplete while validation loss falls, a separately approved continuation may be justified.

If supplied fit is strong, use the A/B/C decomposition to decide whether the next bottleneck is semantic classification, symbolic lookup, or composition.

Do not scale the model on the basis of this experiment alone.

The final holdout remains closed.
