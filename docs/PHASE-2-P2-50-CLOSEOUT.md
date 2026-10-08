# P2-50 — Phase 2 Closeout

## Status

**Complete. Phase 2 is closed. Phase 3 is next.**

## Purpose

P2-50 freezes the Phase 2 capability boundary after the final predeclared transfer evaluation.

Phase 2 ends here whether the legacy structured-plan gate passed or failed.

It failed.

That result is retained as evidence, not hidden or optimized around.

## Final Phase 2 result

P2-48 trained the request-grounded representation for the full bounded 100-update run.

Internal request-grounded validation:

| Step | Mean loss |
|---:|---:|
| 0 | 6.505710401033101 |
| 25 | **2.7775440717998303** |
| 50 | 2.913108511974937 |
| 75 | 3.1200873851776123 |
| 100 | 3.233508963333933 |

This established that the 27M model can learn the narrow request-grounded training representation and generalize within that held-out representation distribution.

The curve also showed an overfitting signal after step 25.

P2-49 then tested the fixed step-100 endpoint against the unchanged P2-31 structured-plan development gate:

| Metric | P2-45 | P2-49 |
|---|---:|---:|
| complete semantic passes | 0 / 18 | **0 / 18** |
| schema-valid | 12 / 18 | **0 / 18** |
| checks passed | 78 / 162 | **36 / 162** |
| language | 12 / 18 | **0 / 18** |
| action | 6 / 18 | **0 / 18** |
| target kind | 12 / 18 | **0 / 18** |
| target role | 0 / 18 | **0 / 18** |
| exact constraints | 0 / 18 | **0 / 18** |
| hint coverage | 0 / 18 | **0 / 18** |

P2-49 therefore failed the unchanged legacy transfer gate.

## What the 27M model reliably demonstrated in Phase 2

The current model can:

- train reproducibly from scratch,
- learn HTML/CSS/JavaScript token and code priors,
- fit narrow coding-request representations,
- improve held-out loss when validation shares the same representation contract,
- learn familiar coding intents and target concepts,
- move away from whole-template replay toward component recombination,
- condition some internal behavior on natural-language request evidence,
- produce complete non-truncated responses consistently in the final P2-49 development run.

These are research capabilities, not a claim that Plex is already a reliable coding editor.

## What still fails

Phase 2 did **not** establish reliable transfer across substantially different output representations.

Known limitations:

1. **Representation dependence**
   - P2-48 learned the request-grounded target format.
   - P2-49 did not transfer that learning into the old P2-31 structured-plan format.

2. **Unseen semantic transfer remains weak**
   - The unchanged P2-31 gate still produced 0 / 18 complete passes.

3. **Output-format stability remains weak outside the trained representation**
   - P2-49 produced 0 / 18 schema-valid old-format plans.
   - 15 responses used a field set that did not match the old schema.
   - 3 responses were invalid JSON.

4. **Small-data overfitting appears quickly**
   - P2-48 validation was best at step 25 and worsened through step 100.

5. **Phase 2 did not test real supplied-file editing**
   - The product goal is request + supplied code/file → correct edit.
   - That direct task begins in Phase 3.

## Phase 3 carry-forward limitations

Phase 3 must assume:

- request understanding is still fragile,
- output format can dominate learned behavior,
- unrelated code preservation is unproven,
- exact edit correctness on unseen files is unproven,
- multi-edit behavior is unproven,
- repair behavior from syntax/test feedback is unproven.

Phase 3 should therefore use the simplest possible input/output contract and measure actual edited code rather than abstract semantic plans.

## Model-size decision

**Keep the 27,566,080-parameter model as the controlled Phase 3 starting point.**

Reason:

P2-49 proves a transfer failure, but it does not isolate parameter count as the cause.

The next phase changes the task to the actual product target:

```text
natural-language request
+ supplied HTML/CSS/JavaScript
            ↓
         Plex Nano
            ↓
      edited code result
```

That is a materially different and more direct task than translating requests into an abstract structured-plan schema.

Changing model size now would confound the Phase 3 result.

A model-size increase should be considered only after Phase 3 directly measures unseen supplied-file editing and shows a repeatable capacity ceiling.

## Permanent regression evidence

Retain these Phase 2 evaluations:

### P2-31 unchanged structured-plan development gate

Keep as a **legacy transfer regression**, not the Phase 3 product gate.

It is useful for detecting whether future changes unexpectedly recover or damage old structured-plan transfer.

### P2-47 request-grounded held-out split

Keep as a representation-level regression for:

- request evidence binding,
- familiar coding intents in unseen combinations,
- train/validation leakage checks,
- tokenizer/context fit.

Do not treat its validation loss alone as product capability.

### P2-48 frozen endpoint

Retain:

- step-100 checkpoint SHA-256:
  `fd86d11375e547f05b2fab7a36188ca30a7ecd0b0f38198de62bcddbfba489b7`
- stage checkpoint SHA-256:
  `52aabd0c3d07125dfd89eafd1cd9ecfbb79cbf8a89dfa15c8f8334ead3f2dd60`
- training bundle manifest:
  `71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7`

These provide the Phase 3 starting baseline.

## Phase 2 final conclusion

Phase 2 improved Plex's ability to learn coding-request representations, but it did **not** solve robust semantic transfer.

That is the honest boundary.

The next research question is no longer:

> Can Plex emit the right abstract semantic plan?

It is:

> Given the exact file and a coding request, can Plex make the correct edit while preserving everything unrelated?

That question belongs to Phase 3.

## Next milestone

**P3-01 — File + Request Contract**

Define the simplest stable single-file input/output contract for HTML, CSS, and JavaScript.

No repository discovery or autonomous navigation is part of the model.

The caller supplies the code.
