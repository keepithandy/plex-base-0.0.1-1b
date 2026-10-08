# P2-46 — Semantic Transfer Failure Diagnostic

## Status

**Planned diagnostic. No model training is authorized.**

## Purpose

Explain why P2-44 improved strongly on its own validation distribution while P2-45 still failed the unchanged bridge.

The question is:

> What representation or binding failure prevents the 27M Plex Nano model from transferring request understanding to independently worded coding tasks?

## Frozen evidence

P2-44 endpoint:

- checkpoint step: **100**
- checkpoint SHA-256: `69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e`
- validation loss: **2.172380618146948**

P2-45:

- responses SHA-256: `ca1e8c8abb8dc419ef2fd2d2c3834964e5baad448b3dd439678decadbf1919a9`
- complete passes: **0 / 18**
- schema-valid: **12 / 18**
- checks passed: **78 / 162**
- targetRole: **0 / 18**
- exact constraints: **0 / 18**
- required hint coverage: **0 / 18**

## Diagnostic questions

P2-46 should measure:

1. What target roles did P2-45 actually emit?
2. Are those roles copied from P2-44 training examples, recombined from familiar atoms, or novel?
3. Which P2-44 constraint atoms appear in failed P2-45 responses?
4. Are search hints grounded in the request but mismatched to the evaluator, or are they unrelated?
5. Which six outputs became schema-invalid, and why?
6. Why did action accuracy fall to **6 / 18**?
7. Which tasks improved, stayed unchanged, or regressed from P2-43 to P2-45?
8. How similar is each P2-45 request/output pair to its nearest P2-44 training example?

## Rules

- No optimizer creation.
- No gradient updates.
- No checkpoint selection.
- No new curriculum until the diagnostic is complete.
- No final-holdout access.
- Do not alter the P2-31 development task set or thresholds.
- Preserve P2-43, P2-44, and P2-45 evidence exactly.

## Completion condition

P2-46 is complete when it produces a concrete failure taxonomy and a narrow recommendation for P2-47.

P2-47 must target **transferable coding understanding**, not simply lower loss on another isolated representation.
