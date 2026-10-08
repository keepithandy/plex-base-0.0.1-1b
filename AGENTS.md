# AGENTS.md

## Project identity

Plex Nano is a **small coding model**.

Current controlled model:
- 27,566,080 parameters
- 512-token context
- 16,384-token byte-level BPE vocabulary
- HTML, CSS, and JavaScript focus
- trained from scratch

The product contract is:

```text
coding request + user-provided code/file context
                    ↓
                 Plex Nano
                    ↓
              correct code change
```

Do not reframe Plex as a repository agent, project-discovery system, autonomous coding agent, Git workflow manager, or repository navigation product.

Plex does not need to discover files or projects. The caller supplies the code context Plex is expected to reason about.

## Direction rules

1. Keep the model itself central. New work should improve coding understanding, code generation, code editing, debugging, or reliability.
2. Prefer evaluations that measure whether Plex correctly changes supplied HTML, CSS, or JavaScript from a natural-language request.
3. Do not add repository discovery, repository search, autonomous Git operations, automatic commits, or project-wide agent loops unless the owner explicitly changes the product direction.
4. File support means Plex can receive supplied file contents as context and reason about/edit them. It does not imply file discovery.
5. Preserve the current 27M model as the controlled research baseline until a roadmap milestone explicitly authorizes a size change.
6. Keep claims evidence-based. Do not describe an experiment as solved when the recorded evaluation failed.
7. Historical reports may describe earlier architecture ideas. Treat those as historical context, not current product direction.
8. Keep README.md, Plex-ROADMAP.md, package metadata, prompts, and current docs aligned with this file.
9. Existing TypeScript project-discovery utilities are legacy research scaffolding. Maintain them only when necessary; do not treat them as Plex Nano's product direction or expand them into new product features.

## Roadmap discipline

- Phase 1: model foundation.
- Phase 2: coding understanding and semantic transfer.
- Phase 3: file-conditioned coding using **provided** file/code context.
- Later phases: harder coding, conversational iteration, and a local app around the model.

Do not skip an unfinished Phase 2 milestone merely to make the roadmap look more advanced. Phase 2 can close with documented limitations after its predeclared closeout work is complete.

## Change discipline

- Make the smallest coherent change.
- Preserve unrelated behavior.
- Update tests when behavior changes.
- Preserve experiment hashes, results, and provenance.
- Do not silently rewrite historical numeric results.
- Do not open the final project holdout unless a milestone explicitly authorizes it.
- Training authorization must remain separate from data preparation, diagnostics, and evaluation.

## Before finishing an edit

Check:
- Does this still describe Plex as a small coding model?
- Does the change assume the user supplies the relevant code/file context?
- Did any wording accidentally turn Plex into a repository or autonomous agent product?
- Are model capability claims supported by recorded results?
- Are README, roadmap, and current docs still consistent?
