<div align="center">

# Plex Base

### Repository-native coding intelligence, trained from scratch.

**Small. Local-first. Focused on making the smallest correct change.**

![Status](https://img.shields.io/badge/status-active%20research-2563eb?style=for-the-badge)
![Phase](https://img.shields.io/badge/phase-2%20%7C%20coding%20ability-7c3aed?style=for-the-badge)
![Model](https://img.shields.io/badge/model-27.6M%20parameters-0f766e?style=for-the-badge)
![Training](https://img.shields.io/badge/training-from%20scratch-111827?style=for-the-badge)

<p>
  <a href="./Plex-ROADMAP.md"><strong>Roadmap</strong></a>
  ·
  <a href="./training/README.md"><strong>Training</strong></a>
  ·
  <a href="./docs/PHASE-2-P2-17B-RESULT.md"><strong>Latest Result</strong></a>
  ·
  <a href="./CHANGELOG.md"><strong>Changelog</strong></a>
</p>

</div>

---

## What is Plex?

Plex is a compact coding-model project built **from the ground up** for repository-focused code editing.

It is not intended to become a general chatbot. The goal is a focused coding engine that can take a task, inspect an existing repository, find the relevant code, understand the local context, make a surgical edit, validate it, and return a clean patch.

> [!NOTE]
> Plex starts from **randomly initialized weights**. It does not use pretrained Qwen weights or another pretrained coding model as its initialization source.

### The core idea

```text
TASK
  ↓
INSPECT REPOSITORY
  ↓
FIND RELEVANT FILES
  ↓
BUILD FOCUSED CONTEXT
  ↓
GENERATE THE SMALLEST CORRECT EDIT
  ↓
VALIDATE
  ↓
RETURN A CLEAN DIFF
```

Plex is being built as two connected layers:

| Layer | Purpose |
|---|---|
| **Plex Base** | Model architecture, tokenizer, datasets, checkpoints, training, and evaluation |
| **Plex Code** | Repository scanning, file ranking, context construction, edit validation, proposal building, and diff generation |

---

## At a glance

| | Current state |
|---|---|
| **Research model** | 27,566,080 parameters |
| **Context window** | 512 tokens |
| **Primary scope** | HTML, CSS, JavaScript |
| **Training** | From scratch with PyTorch |
| **GPU training** | CUDA working |
| **CPU generation** | Working |
| **Checkpoint resume** | Working |
| **Repository tooling** | Working |
| **General coding ability** | Still being developed |
| **Project phase** | Phase 2 — Basic coding ability |

> [!IMPORTANT]
> Plex can learn supplied examples and its training stack is operational, but it has **not yet demonstrated reliable general coding-task completion on unseen requests**.

---

## How Plex fits together

```mermaid
flowchart LR
    A[Task] --> B[Scan Repository]
    B --> C[Rank Candidate Files]
    C --> D[Build Focused Context]
    D --> E[Plex Base]
    E --> F[Validate Proposed Edits]
    F --> G[Build Proposal]
    G --> H[Unified Diff]
```

The repository side is intentionally deterministic. Model output is treated as a **proposal**, not permission to modify files.

---

## Current research milestone

### P2-17/P2-17b — semantic binding result

Plex can now completely fit the supplied semantic-binding curriculum, but that capability does **not** transfer cleanly to unseen literals.

By cumulative step **500**:

| Measure | Result |
|---|---:|
| Supplied training complete-task passes | **120 / 120** |
| Training extraction plans | **60 / 60** |
| Training explicit-plan applications | **60 / 60** |
| Tier A full plans | **0 / 20** |
| Tier A selector exact | **0 / 20** |
| Tier A new-value exact | **3 / 20** |
| Tier A operation exact | **13 / 20** |
| Tier A property exact | **15 / 20** |
| Tier B complete | **0 / 20** |
| Tier C complete | **0 / 20** |
| Validation loss | **2.574 → 3.369** from step 100 to 500 |

The current bottleneck is narrower than "CSS generation": Plex learns categorical semantics and memorizes supplied mappings, but it has not yet demonstrated reliable **exact copying/binding of unseen repository literals**.

**Full report:** [P2-17b Semantic Binding Result](docs/PHASE-2-P2-17B-RESULT.md)

### P2-18 — literal copy primitive

P2-18 is now the active candidate milestone.

It strips away CSS transformation and tests four increasingly difficult primitives:

```text
A  direct unseen literal copy
↓
B  labeled unseen literal copy
↓
C  select one literal from several fields
↓
D  assemble a tiny selector/old/new plan
```

The candidate contains **144 training** and **72 evaluation-only** records with zero train/evaluation selector overlap and zero old/new literal-value overlap.

The model remains **27.6M parameters**. Scaling toward the long-term 0.5B–1.5B target is intentionally deferred until literal copying/reference binding is understood.

**Candidate review:** [P2-18 Literal Copy Primitive](training/phase2/drafts/p2-18-literal-copy-candidate-v1/REVIEW.md)

---

## What already works

### Repository tooling

Plex Code can already:

- safely scan supported repositories
- discover HTML, CSS, JavaScript, MJS, and CJS files
- rank likely target files from the task
- build bounded model context
- validate strict structured model responses
- validate edit paths and anchors
- build proposed buffers without modifying the original source
- generate unified diffs
- preserve UTF-8 BOMs and newline styles
- detect changed source snapshots before trusting an edit

### Training stack

Plex Base can already:

- initialize a model from random weights
- train locally with PyTorch
- run CUDA training
- save model checkpoints
- resume training from checkpoints
- preserve optimizer and RNG state
- evaluate saved checkpoints
- generate text on CPU
- track tokenizer, dataset, model, and checkpoint provenance

---

## What Plex cannot do yet

Plex is still an experimental research model.

It has **not** yet proven that it can:

- reliably solve unseen coding tasks
- complete a real repository edit end-to-end using its trained model
- pass the final held-out coding benchmark
- safely make autonomous repository changes
- replace a production coding assistant

The final project holdout remains closed while the training strategy is still being developed.

---

## Roadmap

The full plan lives in [Plex-ROADMAP.md](Plex-ROADMAP.md).

| Phase | Goal | Status |
|---|---|---|
| **Phase 1** | Build repository tooling and prove scratch training works | **Complete** |
| **Phase 2** | Develop basic coding ability and measure generalization | **Active** |
| **Phase 3** | Connect the trained Plex model to repository editing | **Next** |
| **Phase 4** | Scale, optimize, quantize, and prepare a local release | **Later** |

### Long-term direction

The intended Plex family is a lightweight local coding-model family that can scale toward roughly **0.5B–1.5B parameters** when the measured results justify it.

The release target is:

- local Windows operation
- CPU-capable inference
- optional GPU acceleration
- practical quantization, including a 4-bit candidate where useful
- no cloud dependency for normal use
- repository-native coding instead of general-purpose conversation

The current **27.6M-parameter** model is the research foundation used to prove the architecture, data strategy, evaluation process, and coding workflow before attempting that larger scale.

---

## Development

### Repository tooling

Requires **Node.js 24 LTS**.

```powershell
npm ci
npm run build
npm test
npm start -- --help
```

<details>
<summary><strong>Test the packaged CLI locally</strong></summary>

```powershell
npm pack
npm install --prefix ".test-artifacts\local install" --omit=dev --ignore-scripts --no-audit --no-fund .\plex-code-cli-0.1.0.tgz
& ".\.test-artifacts\local install\node_modules\.bin\plex.cmd" --help
```

The package is private to prevent accidental registry publication.

</details>

### Training

The separate Python training workspace lives in:

```text
training/
```

Start with [training/README.md](training/README.md) for preparation, training, evaluation, and checkpoint commands.

---

## Repository map

```text
plex-base-0.0.1-1b/
│
├── src/                 Plex Code repository tooling
├── training/            Scratch model training + evaluation
├── docs/                Experiment reports + technical notes
├── fixtures/            Small repositories used by tests
├── prompts/             Packaged model instructions
├── tests/               Tooling tests
│
├── Plex-ROADMAP.md       Full development roadmap
├── CHANGELOG.md          Historical implementation changes
└── README.md             You are here
```

---

## Design principles

Plex development follows a few strict rules:

1. **Train from scratch.**
2. **Keep the model small until measurements justify scaling.**
3. **Optimize for coding, not general conversation.**
4. **Separate training loss from actual coding-task success.**
5. **Protect final evaluation data from training decisions.**
6. **Treat generated edits as proposals until deterministic checks pass.**
7. **Preserve experiment provenance and reproducibility.**
8. **Report failed experiments instead of hiding them.**

---

## Reports

For the technical details and experiment history:

- [Full Plex roadmap](Plex-ROADMAP.md)
- [P2-17b semantic binding result](docs/PHASE-2-P2-17B-RESULT.md)
- [P2-18 literal copy candidate review](training/phase2/drafts/p2-18-literal-copy-candidate-v1/REVIEW.md)
- [P2-16 CSS generalization result](docs/PHASE-2-P2-16-RESULT.md)
- [P2-16b optimization continuation](docs/PHASE-2-P2-16B-CONTINUATION.md)
- [Phase 1 experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md)
- [Hardware and training profile](docs/HARDWARE-AND-TRAINING-PROFILE.md)
- [Training workspace](training/README.md)
- [Changelog](CHANGELOG.md)

---

<div align="center">

### Built small on purpose.

**Plex is a working scratch-training research project with a real repository-editing foundation — not yet a finished coding model.**

</div>
