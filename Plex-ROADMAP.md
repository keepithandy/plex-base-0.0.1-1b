# Plex — Updated Development Roadmap

Updated October 3, 2026.

## Core goal

Build Plex’s own small coding model from randomly initialized weights, then connect it to the repository tools already built.

Plex will have its own training history and checkpoints. Established transformer designs and training tools may be reused. Pretrained Qwen weights are not the starting point for Plex. Qwen and other models may serve as evaluation baselines; any teacher-generated training data must be documented.

The eventual target is roughly 0.5B–1.5B parameters, with quantized local Windows inference, CPU support, and optional GPU acceleration. Paid services budget is $0; model size, local compute capacity, and actual training duration will be validated through experiments. Normal operation should work offline after setup.

## Starting point: P1-10 completed

| Task | Status |
|---|---|
| P1-01–09: CLI, repository discovery, file ranking, context construction, response parsing, and edit checks | Completed |
| **P1-10: Proposed file buffers and unified diffs** | **Completed** |

The repository has groundwork for inspecting projects and checking proposed edits. No Plex model has been trained, and model inference has not been demonstrated.

The tasks below replace the previous roadmap from P1-11 onward. Existing repository tooling remains the eventual client and evaluation support for the trained model.

## Phase 1 — First Plex training pipeline

The first milestone is a small model that learns from data, saves a checkpoint, and generates output. Initial coding ability will be limited. Passing a training smoke test does not establish useful coding performance.

| Task | Work | Completion check |
|---|---|---|
| **P1-11 — Record hardware and training limits** | Provide a read-only Windows hardware collector and profile; record GPU, VRAM, RAM, available storage, training budget, and acceptable duration. Separate local inference requirements from training requirements. | Owner hardware and training limits are recorded; first-experiment resource fit is checked as part of P1-12 before longer training. |
| **P1-12 — Define the first model experiment** | Choose a small transformer configuration, context length, and training settings. Start substantially below the eventual 0.5B–1.5B target. | Configuration records parameter count; fit against hardware and the 200 GiB allocation is checked in the 10-minute smoke test and two-hour pilot before longer training. |
| **P1-13 — Add model training tools** | Introduce a Python training workspace alongside the CLI, with commands for preparing data, training, evaluating, and generating output. | Commands run with a tiny test dataset; environment and dependency versions are recorded. |
| **P1-14 — Build the dataset pipeline** | Collect suitable code and programming explanations. Record sources and permissions; remove duplicates, secrets, and broken examples. | Reproducible dataset manifest and training/validation splits exist. Split related repositories or examples together to reduce leakage. |
| **P1-15 — Train the Plex tokenizer** | Create a tokenizer suited to programming text and package its files with the model configuration. Fit it using training data only. | Encode/decode checks preserve representative HTML, CSS, JavaScript, and ordinary text. Vocabulary and special-token settings are recorded. |
| **P1-16 — Initialize Plex weights** | Construct the model with random weights. Record initialization settings and seed. | Initialization loads no pretrained checkpoint. |
| **P1-17 — Prove the model can learn** | Train on a deliberately tiny sample to check that the training machinery works. | Training loss falls and the model can reproduce the small sample. This proves learning machinery, not general coding ability. |
| **P1-18 — Run the first real experiment** | Run the two-hour-capped pilot on the prepared dataset and measure performance on withheld data. | Training remains stable within the two-hour limit and allocated resources; validation improves over the untrained model; tokens processed and throughput are recorded. |
| **P1-19 — Save, resume, and generate** | Save weights, tokenizer, optimizer state, schedule, random-generator state, settings, and training progress. Add a basic completion command. | Training resumes correctly; a saved checkpoint generates output independently. This gate must pass before any uncapped longer training run. |
| **P1-20 — Write the experiment report** | Record data, tokens processed, hardware, elapsed time, validation results, and sample outputs. | Results explain what Plex learned and where it fails. |

P1-11 status: **complete**. The owner-provided hardware inventory and training limits are recorded in [`docs/HARDWARE-AND-TRAINING-PROFILE.md`](docs/HARDWARE-AND-TRAINING-PROFILE.md): 200 GiB allocated storage, $0 paid-services budget, a 10-minute smoke test, and a two-hour pilot.

P1-12 status: **started**. A proposed 27,566,080-parameter configuration, training settings, and analytic state-memory estimate are documented in [`docs/FIRST-EXPERIMENT.md`](docs/FIRST-EXPERIMENT.md). Measured GPU/RAM use and throughput remain pending the ten-minute smoke test and two-hour-capped pilot. P1-19 must verify checkpoint resumption before any uncapped longer run.

P1-13 status: **implementation started**. The local workspace, randomly initialized GPT model, bounded smoke/train commands, byte-v1 corpus packing, evaluation, generation, checkpoint writing, and environment telemetry are in [`training/`](training/README.md). Dependency resolution and runtime tests remain pending because this environment cannot reach the official PyTorch wheel index; do not treat its available Python runtime as the owner's installed Python or hardware. The two-hour pilot waits for P1-14/P1-15 data and tokenizer work.

**Phase 1 gate:** A reproducible Plex checkpoint trained from random initialization, with evidence that it learned.

## Phase 2 — Basic coding ability

| Task | Work | Completion check |
|---|---|---|
| **P2-01 — Build coding evaluations** | Add withheld completion tasks for HTML, CSS, and JavaScript, including syntax and behavior checks. | Evaluation distinguishes plausible output from working code. |
| **P2-02 — Improve training data** | Adjust the mixture of code, explanations, and examples using observed development-set failures. | Changes improve withheld development results without leaking evaluation examples into training. |
| **P2-03 — Compare training configurations** | Test context length, model size, and training settings through bounded experiments. | Choose settings from measured quality, memory use, and speed; record experiment budgets. |
| **P2-04 — Train the next Plex base checkpoint** | Increase the training run after the pipeline and smaller experiments work. | Coding results improve enough to justify the extra compute. |
| **P2-05 — Document capability limits** | Identify supported languages, task sizes, and recurring failures. | Model report includes examples and measured limitations. |

**Phase 2 gate:** Plex produces useful code on tasks it did not train on. Freeze a final evaluation set and reserve it for milestone decisions.

## Phase 3 — Repository editing

| Task | Work | Completion check |
|---|---|---|
| **P3-01 — Build editing examples** | Prepare task → relevant source → correct edits examples, including no-change and insufficient-context cases. | Examples have verified expected behavior and controlled edit scope; development and held-out cases are separate. |
| **P3-02 — Instruction-tune Plex Base** | Train our own base checkpoint to follow the coding workflow and output contract. | Held-out requests produce usable edits with measured format reliability, task success, and unrelated-change rates. |
| **P3-03 — Finish proposal validation** | Implement the proposed HTML checks originally planned as P1-11. Expand CSS and JavaScript checks as needed. | Incorrect proposals fail checks; original files remain intact. |
| **P3-04 — Connect Plex inference to the CLI** | Feed selected repository context to the trained Plex checkpoint through a model adapter. Use the Plex tokenizer for actual context accounting. | A real Plex run completes the title-change fixture and produces the expected diff. |
| **P3-05 — Add one repair attempt** | Return concrete validation failures to Plex and check its revised proposal against the original snapshot. | Measure successful repairs, regressions, and unchanged source files. |

**Phase 3 gate:** Plex’s own trained model completes small repository edits through the existing tools. Begin with one-file edits while reading the relevant supplied context.

## Phase 4 — Lightweight release

| Task | Work | Completion check |
|---|---|---|
| **P4-01 — Decide release model size** | Evaluate whether a 0.5B–1.5B training run is justified by results and available compute. | Document quality targets, hardware, data, and training budget before beginning the run. |
| **P4-02 — Train and evaluate the chosen model** | Train the selected configuration and complete instruction tuning. | Frozen evaluation results meet thresholds defined before the final run. |
| **P4-03 — Prepare local inference builds** | Export to a supported inference format and prepare quantized variants, including a 4-bit candidate where practical. | Exported models load successfully; quality loss is measured against the original checkpoint. |
| **P4-04 — Verify Windows operation** | Measure CPU speed, RAM use, and optional GPU acceleration. Test installation and offline operation. | Publish measured hardware requirements and working setup instructions. |
| **P4-05 — Release Plex Code v0.1** | Package model artifacts, tokenizer, configuration, client, provenance, benchmarks, and limitations. | A clean setup can run documented tasks using the released Plex checkpoint. |

**Phase 4 gate:** A reproducible local release with measured coding capability and resource requirements.

## Development rules

- Preserve completed P1-01–10 tooling and its tests.
- Validate each phase before increasing model size or training budget.
- Keep training loss, coding benchmarks, repository task success, and tooling tests as separate measurements.
- Record data provenance and training configuration for every checkpoint.
- Use only development cases for prompt, data, and training adjustments; protect final evaluation cases.
- Treat generated edits as proposals until deterministic checks pass.
- Report failed, unavailable, and unrun checks accurately.
- Keep initial scope focused on HTML, CSS, and JavaScript.
- Defer GUI, IDE integration, autonomous loops, broader languages, and automatic commits until the model and coding workflow demonstrate useful reliability.
- Set training schedules from measured throughput and available hardware; avoid calendar promises before measurement.

## Next task

**P1-11 — Establish the hardware and training budget.**

This determines a realistic first model size and training run. The first success is a small, demonstrably learned Plex checkpoint; the eventual release must earn its capability claims through evaluation.
