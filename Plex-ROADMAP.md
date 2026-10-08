# Plex Nano — Development Roadmap

## Core goal

Build **Plex Nano**, a small coding model that takes a natural-language coding request plus code/file context supplied by the user and produces the correct code change.

```text
request + supplied code/file
          ↓
      Plex Nano
          ↓
   correct code change
```

Plex is not being developed as a general chatbot. The current research target is a compact model that becomes increasingly reliable at HTML, CSS, and JavaScript coding tasks while remaining small enough for practical local use.

## Current controlled model

| Item | Value |
|---|---:|
| Parameters | **27,566,080** |
| Context | **512 tokens** |
| Vocabulary | **16,384-token byte-level BPE** |
| Initialization | **Scratch / random weights** |
| Languages | **HTML / CSS / JavaScript** |
| Current phase | **Phase 3 — File-Conditioned Coding** |

The 27M model remains the controlled baseline until a roadmap milestone explicitly authorizes a model-size change.

---

# Phase 1 — Model Foundation

**Status: COMPLETE**

Phase 1 established that Plex can be trained from scratch and operated locally.

Completed capabilities include:

- deterministic model configuration
- scratch initialization
- tokenizer training
- reproducible dataset builds
- CPU/CUDA environment reporting
- bounded training runs
- checkpoint save/load
- checkpoint resume
- validation loss measurement
- deterministic generation
- training provenance and hashes
- local Windows workflow

Phase 1 proved the training system works. It did **not** prove useful coding ability by itself.

---

# Phase 2 — Coding Understanding

**Status: COMPLETE**

## Phase 2 purpose

Teach Plex to understand coding requests and map them to the intended change.

Phase 2 research covers:

- request following
- code syntax
- literal binding
- semantic roles
- edit intent
- target kinds
- constraints
- structured output
- task-format fine-tuning
- web-code pretraining
- semantic transfer
- generalization beyond exact training examples

Phase 2 is intentionally about the **model's understanding**, not application UI.

## Phase 2 completed research

The full experiment history remains in [docs/](docs/) and [training/](training/). Important findings include:

| Milestone range | Main finding |
|---|---|
| **P2-01–P2-16** | Basic request-to-code plumbing works, but early data was too small and transfer remained weak |
| **P2-17–P2-19** | Plex can fit semantic/literal/reference tasks, but unseen exact binding remains difficult |
| **P2-20–P2-23** | Broader semantic classes transfer better than exact state/literal relations |
| **P2-24–P2-29** | Plex Web corpus/tokenizer/pretraining established stronger HTML/CSS/JS priors |
| **P2-30–P2-36** | Task-format and structured-plan work improved output structure but not reliable semantics |
| **P2-37–P2-43** | Diagnostics showed training-template retrieval and weak semantic binding were major bottlenecks |
| **P2-44** | Evidence-first training improved internal validation from **3.39814 → 2.17238** over 100 updates |
| **P2-45** | Unchanged bridge evaluation still failed: **0/18 complete**, **12/18 schema-valid**, **78/162 checks** |

## P2-45 conclusion

P2-44 learned its own curriculum well, but that learning did not transfer reliably enough to independently worded coding-plan tasks.

P2-45 field results:

| Field | Correct |
|---|---:|
| response present | **18 / 18** |
| not truncated | **18 / 18** |
| schema valid | **12 / 18** |
| language | **12 / 18** |
| action | **6 / 18** |
| target kind | **12 / 18** |
| target role | **0 / 18** |
| exact constraints | **0 / 18** |
| required hint coverage | **0 / 18** |

This is a **semantic transfer failure**, not a reason to keep optimizing the unchanged P2-44 dataset.

## Remaining Phase 2 milestones

### P2-46 — Semantic Transfer Failure Diagnostic

**Status: COMPLETE**

P2-46 confirmed that P2-44 changed Plex from frequent whole-template replay toward recombining familiar semantic components, but the current request still did not reliably control which components were selected.

Key evidence:

- targetRole grounded in request: **0 / 18**
- all search hints grounded in request: **0 / 18**
- P2-44 training targetRole reuse: **17 / 18**
- P2-44 training search-hint reuse: **16 / 18**
- exact semantic-bundle reuse fell **8 → 3**
- component recombination rose **2 → 8**
- **9** tasks regressed, **2** improved

**Conclusion:** composition improved; request-conditioned composition did not.

### P2-47 — Request-Grounded Coding Representation

**Status: COMPLETE**

**Goal:** design one final Phase 2 representation specifically around transferable request-to-change understanding.

Requirements:

- grounded directly in the user's wording
- map exact request evidence to concrete coding intent
- no targetRole/searchHints as primary learning targets
- no opaque synthetic labels
- explicit train/validation combination holdouts
- validation must reuse familiar coding intents in unseen combinations
- no P2-31 development leakage
- file context remains deferred to Phase 3

**Completion:** achieved. The 108-record candidate passed real tokenizer review at **286/512 max tokens**, with **19,377 / 9,763** train/validation tokens and zero exact request/solution/non-empty binding-set overlap.

### P2-48 — Final Bounded Phase 2 Transfer Run

**Status: COMPLETE**

**Goal:** run one bounded experiment on the P2-47 representation.

Requirements:

- frozen seed/data/tokenizer/checkpoint identities
- bounded optimizer updates
- predeclared validation cadence
- no automatic continuation
- final holdout closed

**Completion:** fixed endpoint recorded with transfer metrics.

### P2-49 — Unchanged Bridge Re-evaluation

**Goal:** run the unchanged development bridge on the fixed P2-48 endpoint.

Use the same P2-31 task set and thresholds so the result is comparable with P2-39, P2-42, and P2-45.

**Completion:** recorded. The fixed P2-48 step-100 endpoint produced **0/18 complete passes, 0/18 schema-valid, and 36/162 checks** on the unchanged P2-31 gate. All 18 responses were present and non-truncated; 15 used a field set that did not match the old schema and 3 were invalid JSON.

### P2-50 — Phase 2 Closeout

**Status: COMPLETE**

**Goal:** close Phase 2 whether the final bridge fully passes or not.

Document:

- what the 27M model reliably understands
- what still fails
- which weaknesses move into Phase 3 as known limitations
- whether model size should remain 27M for Phase 3
- which evaluations become permanent regression tests

**Phase 2 ended at P2-50.** No P2-51+ continuation is planned.

Closeout decision:

- request-grounded learning improved substantially inside its own representation,
- the unchanged legacy structured-plan transfer gate still failed,
- supplied-file editing remains unproven,
- the **27,566,080-parameter model remains the controlled Phase 3 baseline**,
- model-size changes wait for direct Phase 3 editing evidence.

## Phase 2 exit condition

Phase 2 does **not** require pretending all semantic transfer is solved.

It requires:

1. completing P2-46 through P2-50,
2. running the final predeclared transfer evaluation honestly,
3. freezing the capability boundary,
4. carrying unresolved limitations forward explicitly.

The final project holdout remains closed unless separately authorized.

---

# Phase 3 — File-Conditioned Coding

**Status: ACTIVE**

## Phase 3 purpose

Make Plex useful when the user supplies a file or code block and asks for a change.

The model receives the relevant context directly.

### P3-01 — File + Request Contract

Define the simplest stable input/output format for:

```text
request + supplied file/code → edited result
```

Support one supplied HTML, CSS, or JavaScript file first.

### P3-02 — Exact Small Replacements

Examples:

- change button text
- rename a supplied variable
- change a CSS value
- replace an attribute

Measure correctness and preservation of unrelated code.

### P3-03 — Insert and Delete

Teach:

- add requested markup
- add a CSS rule/property
- add a JavaScript condition
- remove requested code

### P3-04 — Modify Existing Logic

Handle bounded changes to:

- functions
- event handlers
- DOM code
- CSS components
- HTML structures

### P3-05 — Preserve Unrelated Code

Add explicit regression tests for accidental edits outside the requested scope.

### P3-06 — Multiple Changes in One Supplied File

Support two or more related requested changes without damaging untouched sections.

### P3-07 — Edited-File and Patch Output

Measure both:

- full-file generation/editing
- bounded patch/edit output

Choose the more reliable default from evidence.

### P3-08 — Validation-Aware Correction

Given a concrete syntax/test failure from the caller, let Plex make one corrected attempt.

No open-ended retry loop.

### P3-09 — Unseen File Benchmark

Freeze a development benchmark using code files excluded from training.

Measure:

- correct requested behavior
- syntax
- scope preservation
- unnecessary changes
- repair success

### P3-10 — Phase 3 Closeout

Record what kinds of supplied-file edits Plex can actually perform reliably.

**Phase 3 gate:** Plex can make useful, measured edits to unseen supplied HTML/CSS/JavaScript files from natural-language requests.

---

# Phase 4 — Stronger Coding Ability

**Status: PLANNED**

Move beyond simple edits.

Targets include:

- more complex JavaScript logic
- bug fixes
- refactoring
- state changes
- DOM behavior
- CSS interactions
- larger supplied files
- longer dependencies within supplied context
- better explanations of changes
- stronger error correction

Model-size changes may be considered here only if 27M limitations are clearly measured.

---

# Phase 5 — Conversational Code Editing

**Status: PLANNED**

Support an ongoing conversation about supplied code.

Examples:

```text
"Make this button smaller."
"Actually keep the width but reduce the padding."
"Also add a disabled state."
"Why did you change this selector?"
```

Goals:

- retain relevant supplied-code context across turns
- understand revisions to earlier instructions
- modify previous edits
- explain changes when asked
- avoid drifting into unrelated code

---

# Phase 6 — Local Plex App

**Status: PLANNED**

Wrap the coding model in a simple local experience.

Target interaction:

```text
drop in a file
→ chat about the code
→ request a change
→ preview the result
→ accept/save
```

The app exists to make the model easy to use. The model remains the product focus.

---

# Development Rules

1. **Plex Nano is a small coding model.**
2. The user/caller supplies relevant code or file context.
3. Keep the 27M model as the controlled baseline until a milestone explicitly changes it.
4. Prioritize coding ability over infrastructure expansion.
5. Preserve failed experiments and negative results.
6. Keep training authorization separate from preparation/evaluation.
7. Do not optimize indefinitely on a failed representation.
8. Keep development and final holdouts separate.
9. Do not claim capability from training loss alone.
10. Prefer unseen request/code tests over memorized training checks.
11. Preserve unrelated code in editing evaluations.
12. Keep HTML/CSS/JavaScript as the initial language scope.
13. Update README, roadmap, package metadata, prompts, and AGENTS files together when product direction changes.

Project-wide guardrails are defined in [AGENTS.md](AGENTS.md).

---

# Current task

## P3-01 — File + Request Contract

Phase 2 is complete.

The next task is to define the smallest stable model contract for:

```text
natural-language coding request
+ one supplied HTML/CSS/JavaScript file
                ↓
             Plex Nano
                ↓
        correct edited result
```

Start with **one supplied file**, one bounded requested change, and a deterministic target representation that can be scored for:

- requested behavior correctness,
- syntax validity,
- preservation of unrelated code,
- unnecessary changes.

Keep the current **27,566,080-parameter** model as the controlled baseline.

Do not add repository discovery, autonomous navigation, or application-agent behavior. The caller supplies the code context.
