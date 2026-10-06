# Plex Base

Plex Base is a small coding-model project being trained **from scratch** for repository-focused code editing.

The long-term goal is simple:

> Give Plex a coding task and a repository, let it find the right code, understand the local context, make the smallest correct change, validate the result, and return a clean patch.

Plex is not meant to become a general chatbot. It is being built as a focused coding engine.

## What Plex is

Plex combines two parts:

1. **Plex Base** — the model, tokenizer, training data, checkpoints, and evaluation work.
2. **Plex Code tooling** — repository scanning, file ranking, context building, edit validation, proposed buffers, and unified diff generation.

The repository tooling is already well developed. The model is still in research and training.

Plex uses randomly initialized weights. It does **not** start from pretrained Qwen weights or another pretrained coding model.

## Current status

**Updated: October 6, 2026**

The current research model has:

- **27,566,080 parameters**
- **512-token context**
- its own tokenizer and checkpoints
- working CUDA training
- checkpoint save/resume support
- CPU text generation
- bounded HTML, CSS, and JavaScript evaluation tooling

The current model can learn supplied examples, but it has **not yet demonstrated reliable general coding ability on unseen tasks**.

### Latest training result

P2-16 expanded the CSS training curriculum to:

- 120 training examples
- 60 evaluation examples
- fresh tokenizer
- fresh seed-1337 model initialization

After 100 updates:

| Measure | Result |
|---|---:|
| Training complete-task passes | 3 / 120 |
| Training syntax-valid outputs | 45 / 120 |
| Training EOS completion | 120 / 120 |
| Tier A complete passes | 0 / 24 |
| Tier B complete passes | 0 / 12 |
| Tier C complete passes | 0 / 12 |
| Tier D complete passes | 0 / 12 |
| Validation loss | 6.71646 → 3.38711 |

The model learned much better output formatting and CSS syntax, but exact held-out edit completion is still at zero.

See [P2-16 result](docs/PHASE-2-P2-16-RESULT.md).

### Current milestone — P2-16b

P2-16b continues the exact P2-16 step-100 checkpoint instead of starting over.

The approved continuation scores the same model at cumulative steps:

- 200
- 300
- 400
- 500

No automatic training beyond step 500 is authorized.

The goal is to find out whether the larger P2-16 curriculum simply needs more optimization or whether the model needs a different training approach.

See [P2-16b continuation plan](docs/PHASE-2-P2-16B-CONTINUATION.md).

## What already works

### Repository tooling

Plex can already:

- scan supported repositories safely
- discover HTML, CSS, and JavaScript files
- rank likely target files from a task
- build bounded model context
- validate structured model responses
- validate edit paths and anchors
- build proposed edited buffers without changing the original file
- generate unified diffs
- preserve important file properties such as UTF-8 BOMs and newline styles

These systems were built during Phase 1 and are intended to become the client around the trained Plex model.

### Training system

The training workspace can:

- initialize Plex from random weights
- train locally with PyTorch
- run on CUDA
- save checkpoints
- resume checkpoints
- preserve optimizer and RNG state
- evaluate saved checkpoints
- generate text on CPU
- track tokenizer, dataset, model, and checkpoint provenance

## What Plex cannot do yet

Plex should still be treated as an experimental model.

It has **not** yet proven that it can:

- reliably solve unseen coding tasks
- edit a real repository end-to-end using its own trained model
- pass the final held-out coding benchmark
- safely make autonomous repository changes
- replace a production coding assistant

The final project holdout remains closed while the training approach is still being developed.

## Project roadmap

The full roadmap is in [Plex-ROADMAP.md](Plex-ROADMAP.md).

The project is divided into four broad stages:

| Phase | Goal |
|---|---|
| **Phase 1** | Build the repository tooling and prove scratch training works |
| **Phase 2** | Develop basic coding ability and measure generalization |
| **Phase 3** | Connect the trained Plex model to repository editing |
| **Phase 4** | Scale, optimize, quantize, and prepare a lightweight local release |

Plex is currently in **Phase 2**.

## Development setup

### JavaScript / repository tooling

Requires Node.js 24 LTS.

```powershell
npm ci
npm run build
npm test
npm start -- --help
```

To test the packaged CLI locally:

```powershell
npm pack
npm install --prefix ".test-artifacts\local install" --omit=dev --ignore-scripts --no-audit --no-fund .\plex-code-cli-0.1.0.tgz
& ".\.test-artifacts\local install\node_modules\.bin\plex.cmd" --help
```

The package is private to prevent accidental registry publication.

### Training

The Python training workspace is in:

```text
training/
```

Training experiments, preparation scripts, evaluation tools, and reports are kept separate from the TypeScript repository tooling.

Start with [training/README.md](training/README.md) for training commands.

## Repository layout

```text
src/                 Plex Code repository tooling
training/            Scratch model training and evaluation
docs/                Experiment reports and technical notes
fixtures/            Small repositories used by tests
prompts/             Packaged model instructions
tests/               Tooling tests
Plex-ROADMAP.md       Full project roadmap
CHANGELOG.md          Historical implementation changes
```

## Design principles

Plex development follows a few strict rules:

- train from scratch
- keep the model small until measurements justify scaling
- prefer focused coding ability over general conversation
- separate training loss from actual coding-task success
- protect final evaluation data from training decisions
- keep repository edits constrained and deterministic
- validate generated edits before applying anything
- preserve experiment provenance and reproducibility
- report failed experiments instead of hiding them

## Long-term target

The intended Plex family is a lightweight local coding-model family that can eventually scale toward roughly **0.5B–1.5B parameters** where justified by measured results.

The release goal is a model that can run locally on Windows, remain CPU-capable, optionally use GPU acceleration, and operate without a cloud dependency for normal use.

The current 27.6M-parameter model is the research foundation used to prove the training and coding approach before that larger scale is attempted.

## Detailed reports

The README intentionally stays high level. Detailed experiment history lives in the documentation:

- [Plex roadmap](Plex-ROADMAP.md)
- [P2-16 result](docs/PHASE-2-P2-16-RESULT.md)
- [P2-16b continuation](docs/PHASE-2-P2-16B-CONTINUATION.md)
- [Phase 1 experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md)
- [Hardware and training profile](docs/HARDWARE-AND-TRAINING-PROFILE.md)
- [Training workspace](training/README.md)
- [Changelog](CHANGELOG.md)

---

**Plex is currently a working scratch-training research project with strong repository tooling, not yet a finished coding model.**
