<a id="top"></a>

<p align="center">
  <img src="./docs/assets/plex-nano-banner.svg" alt="Plex Nano — Small model. Focused mission." width="1200">
</p>

<div align="center">

# Plex Nano

**A small 27.6M-parameter coding model trained from scratch.**

Request + provided code context → correct code change.

![Status](https://img.shields.io/badge/status-active%20research-3567a5?style=for-the-badge&labelColor=151933)
![Phase](https://img.shields.io/badge/phase-2%20%7C%20coding%20understanding-7257a5?style=for-the-badge&labelColor=151933)
![Model](https://img.shields.io/badge/model-27.6M%20parameters-18786c?style=for-the-badge&labelColor=151933)
![Training](https://img.shields.io/badge/training-from%20scratch-52617c?style=for-the-badge&labelColor=151933)

![Scope](https://img.shields.io/badge/scope-HTML%20%2F%20CSS%20%2F%20JavaScript-3567a5?style=flat-square&labelColor=151933)
![Context](https://img.shields.io/badge/context-512%20tokens-7257a5?style=flat-square&labelColor=151933)
![Vocabulary](https://img.shields.io/badge/vocab-16%2C384-18786c?style=flat-square&labelColor=151933)
[![License](https://img.shields.io/badge/license-MIT-18786c?style=flat-square&labelColor=151933)](LICENSE)

</div>

---

## What is Plex Nano?

Plex Nano is a compact coding model built from randomly initialized weights.

Its job is simple:

```text
natural-language coding request
+ code or file context supplied by the user
                    ↓
                Plex Nano
                    ↓
             correct code change
```

Plex is not trying to be a general chatbot. The research goal is to make a very small model unusually useful at understanding coding requests and making accurate, minimal edits to the code it is given.

The current model focuses on **HTML, CSS, and JavaScript**.

## Current model

| Item | Current value |
|---|---:|
| Parameters | **27,566,080** |
| Context length | **512 tokens** |
| Vocabulary | **16,384-token byte-level BPE** |
| Initialization | **Random / scratch** |
| Primary languages | **HTML / CSS / JavaScript** |
| Local acceleration | **CUDA supported** |
| Current phase | **Phase 2 — Coding Understanding** |

No pretrained model weights are used for the current Plex Nano research line.

## What Plex is being trained to do

Plex should learn to:

- understand a coding request
- understand supplied code
- identify what behavior or structure should change
- preserve unrelated code
- follow explicit constraints
- generate or edit HTML, CSS, and JavaScript
- generalize beyond exact training examples
- revise a code change when given useful feedback

The long-term user experience is intentionally straightforward:

```text
drop in code or a file
→ describe the change
→ Plex edits it
→ keep talking about the same code
```

## Current research status

### Phase 1 — Model foundation

Complete.

Plex has a working scratch-training stack with:

- tokenizer training
- deterministic initialization
- CUDA training
- checkpoint save/load
- bounded experiments
- validation loss tracking
- deterministic generation
- reproducible provenance and hashes

### Phase 2 — Coding understanding

Active.

Phase 2 has tested request following, literal binding, semantic roles, edit intent, target kinds, structured plans, web-code pretraining, task fine-tuning, serialization, semantic binding, and evidence-first composition.

The most recent bounded training run, **P2-44**, completed all 100 authorized optimizer updates and improved its own validation loss from:

```text
3.3981438779 → 2.1723806181
```

However, the unchanged P2-31 bridge re-evaluation in **P2-45** still failed:

| P2-45 metric | Result |
|---|---:|
| Complete semantic passes | **0 / 18** |
| Schema-valid | **12 / 18** |
| Checks passed | **78 / 162** |
| targetRole correct | **0 / 18** |
| exact constraints | **0 / 18** |
| required hint coverage | **0 / 18** |

P2-46 explained the failure more precisely: Plex shifted from replaying whole semantic templates toward recombining familiar coding components, but **the current request still did not reliably control which components were selected**.

The current milestone, **P2-47**, therefore removes `targetRole` and `searchHints` from the primary learning target and trains a simpler relationship:

```text
exact request evidence → concrete coding intent
```

This keeps Phase 2 focused on the model's coding understanding before Phase 3 introduces supplied-file conditioning.

## Roadmap

The project now follows a model-first roadmap.

| Phase | Goal | Status |
|---|---|---|
| **Phase 1 — Model Foundation** | Build and verify the scratch model/training stack | **Complete** |
| **Phase 2 — Coding Understanding** | Improve request understanding, code semantics, binding, and transfer | **Active** |
| **Phase 3 — File-Conditioned Coding** | Request + supplied file/code → correct edit | Planned |
| **Phase 4 — Stronger Coding Ability** | Harder functions, styles, logic, bug fixes, and refactors | Planned |
| **Phase 5 — Conversational Code Editing** | Iterate on supplied code across multiple user turns | Planned |
| **Phase 6 — Local Plex App** | Drop in a file, chat, preview/accept edits, save | Planned |

See [Plex-ROADMAP.md](Plex-ROADMAP.md) for milestone details.

## Phase 3 direction

Phase 3 is **file-conditioned coding**.

The file is supplied to Plex. Plex's job is to understand the request and edit that supplied context correctly.

Examples:

```text
"Change this button to say Save Changes."
+ supplied HTML
→ correct HTML edit
```

```text
"Ignore inactive items in this function."
+ supplied JavaScript
→ correct function edit
```

```text
"Make this card stack vertically below 700px."
+ supplied CSS
→ correct CSS edit
```

## Development guardrails

Project direction is pinned in [AGENTS.md](AGENTS.md).

Important rules:

1. Plex Nano is a **small coding model**.
2. The caller supplies the code/file context Plex needs.
3. New research should improve the model's coding ability, editing accuracy, debugging, or generalization.
4. Keep the current 27M architecture as the controlled baseline until a milestone explicitly changes it.
5. Preserve failed experiments and capability limits.
6. Keep training authorization separate from diagnostics, preparation, and evaluation.
7. Keep the final project holdout closed unless a milestone explicitly authorizes it.
8. Keep README, roadmap, prompts, package metadata, and current docs aligned with the same model-first direction.

Additional scoped guardrails live in:

- [training/AGENTS.md](training/AGENTS.md)
- [docs/AGENTS.md](docs/AGENTS.md)

## Training workspace

The Python training workspace lives under:

```text
training/
```

Typical environment check:

```powershell
uv run --project training --no-sync python -m plex_training.cli environment
```

The current research environment uses Python/PyTorch with optional CUDA acceleration.

For detailed experiment commands and retained results, see [training/README.md](training/README.md) and the milestone reports in [docs/](docs/).

## Project map

| Path | Purpose |
|---|---|
| `training/` | Model training, evaluation, checkpoints, datasets, and experiment tooling |
| `docs/` | Research reports, milestone results, and technical notes |
| `prompts/` | Model-facing request/edit contracts |
| `fixtures/` | Small code fixtures used by tests |
| `src/` | Auxiliary TypeScript utilities retained by the project |
| `tests/` | TypeScript/package tests |
| `AGENTS.md` | Project direction and editing guardrails |

## Research principles

- Train and evaluate honestly.
- Prefer small, controlled experiments.
- Keep numeric results and hashes reproducible.
- Do not hide failed transfer.
- Do not claim coding ability from training loss alone.
- Measure edits on unseen requests.
- Preserve unrelated code.
- Keep the model small unless evidence justifies scaling.
- Let real coding failures guide the next training work.

## Selected reports

- [P1-20 — First experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md)
- [P2-29 — Longer Plex Web run](docs/PHASE-2-P2-29-RESULT.md)
- [P2-43 — Semantic bundle reuse diagnostic](docs/PHASE-2-P2-43-SEMANTIC-BUNDLE-REUSE-DIAGNOSTIC.md)
- [P2-44 — Evidence-first semantic composition](docs/PHASE-2-P2-44-EVIDENCE-FIRST-SEMANTIC-COMPOSITION.md)
- [P2-45 — Structured bridge re-evaluation](docs/PHASE-2-P2-45-STRUCTURED-BRIDGE-REEVALUATION.md)
- [P2-46 — Semantic transfer failure diagnostic](docs/PHASE-2-P2-46-SEMANTIC-TRANSFER-DIAGNOSTIC.md)
- [P2-47 — Request-grounded coding representation](docs/PHASE-2-P2-47-REQUEST-GROUNDED-CODING.md)
- [P2-48 — Final bounded Phase 2 transfer run](docs/PHASE-2-P2-48-FINAL-TRANSFER-RUN.md)

---

<div align="center">

### Small model. Coding focus.

**Plex Nano is a working 27.6M-parameter scratch-trained coding-model research project.**

</div>

## License

MIT. See [LICENSE](LICENSE).
