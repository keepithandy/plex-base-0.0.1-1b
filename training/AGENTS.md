# AGENTS.md

This directory contains Plex Nano model research and training code.

## Scope

Training work exists to improve the **small coding model** itself:
- request understanding
- code understanding
- semantic binding
- code generation
- code editing from supplied context
- debugging and repair ability
- generalization

Do not introduce repository discovery, autonomous project navigation, Git automation, or agent-loop behavior as a model requirement.

## Research rules

- Keep the 27,566,080-parameter model as the controlled baseline unless a milestone explicitly changes model size.
- Separate preparation, evaluation, diagnostics, staging, training authorization, and training execution.
- Never infer training authorization from a successful preflight.
- Keep the final project holdout closed unless a milestone explicitly authorizes it.
- Preserve exact hashes, seeds, tokenizer identities, dataset identities, checkpoint identities, and recorded numeric results.
- Do not retrospectively select a checkpoint unless the experiment contract allows it.
- Prefer bounded experiments with explicit stop rules.
- Failed transfer results are valid results and must remain visible.

## Evaluation direction

Prefer tests shaped like:

```text
natural-language coding request
+ supplied code/file context
→ expected code change
```

Structured intermediate representations may be used as diagnostics or training aids, but they are not the product goal.
