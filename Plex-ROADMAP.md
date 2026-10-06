# Plex — Updated Development Roadmap

Updated October 6, 2026.

## Core goal

Build Plex’s own small coding model from randomly initialized weights, then connect it to the repository tools already built.

Plex will have its own training history and checkpoints. Established transformer designs and training tools may be reused. Pretrained Qwen weights are not the starting point for Plex. Qwen and other models may serve as evaluation baselines; any teacher-generated training data must be documented.

The eventual target is roughly 0.5B–1.5B parameters, with quantized local Windows inference, CPU support, and optional GPU acceleration. Paid services budget is $0; model size, local compute capacity, and actual training duration will be validated through experiments. Normal operation should work offline after setup.

## Starting point: P1-10 completed

| Task | Status |
|---|---|
| P1-01–09: CLI, repository discovery, file ranking, context construction, response parsing, and edit checks | Completed |
| **P1-10: Proposed file buffers and unified diffs** | **Completed** |

At the completed P1-10 starting point, the repository had groundwork for inspecting projects and checking proposed edits, with no trained Plex model. The owner has since completed the P1-13 synthetic CUDA smoke test and saved a scratch-initialized checkpoint; useful coding inference remains to be demonstrated.

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

P1-20 status: **complete**. The [first experiment report](docs/PLEX-EXPERIMENT-REPORT-P1-20.md) records the two-hour scratch-trained run, checkpoint resume, held-out results, resource measurements, and incorrect generated code. Training loss and held-out next-token loss improved, but the 34-record training corpus, distinct-source split, and failed completion do not demonstrate coding ability. Keep the CLI duration cap while preparing a broader corpus and functional evaluation plan.

P1-11 status: **complete**. The owner-provided hardware inventory and training limits are recorded in [`docs/HARDWARE-AND-TRAINING-PROFILE.md`](docs/HARDWARE-AND-TRAINING-PROFILE.md): 200 GiB allocated storage, $0 paid-services budget, a 10-minute smoke test, and a two-hour pilot.

P1-12 status: **configuration defined; ten-minute resource fit and two-hour real-data pilot passed**. The instantiated 27,566,080-parameter configuration, training settings, and analytic state-memory estimate are documented in [`docs/FIRST-EXPERIMENT.md`](docs/FIRST-EXPERIMENT.md). The [owner's smoke result](docs/SMOKE-TEST-2026-10-03.md) records 734 MiB peak GPU reservation, about 1.30 GiB process peak RAM, and 57,327.61 synthetic token positions/second. The [P1-18 pilot](docs/PLEX-PILOT.md) records 878,706,688 bytes peak GPU reservation, 1,397,129,216 bytes peak process working set, and improved held-out loss. The [P1-19 resume check](docs/PLEX-RESUME-AND-COMPLETION.md) passed; uncapped longer training remains disabled pending a reviewed experiment plan.

P1-13 status: **implementation complete and owner-verified, including the ten-minute smoke test**. The local workspace, randomly initialized GPT model, bounded smoke/train commands, byte-v1 corpus packing, evaluation, generation, checkpoint writing, and environment telemetry are in [`training/`](training/README.md). On the owner's Windows machine, Python 3.12.10, PyTorch 2.14.0+cu126, and CUDA 12.6 detected the RTX 4080 SUPER; the original 13 training tests pass. The [smoke run](docs/SMOKE-TEST-2026-10-03.md) completed 600.03 seconds and 4,199 steps without interruption and saved a 330,894,811-byte checkpoint. Later milestones completed the corpus, tokenizer, initialization, learning check, and two-hour pilot.

P1-14 status: **complete for the approved starter corpus**. The owner approved the pinned MIT subsets of Microsoft Web Dev for Beginners and Traversy's 50 Projects in 50 Days. The corpus contains 34 training and 54 validation records, a provenance manifest, and both original license notices; its total size is 746,848 bytes. Checks verified separate groups/content hashes and an identical second build; all 25 training-workspace tests passed at that milestone. Sources, approval, scopes, hashes, limitations, and reproduction instructions are recorded in the [source/build review](docs/DATASET-SOURCE-REVIEW.md). See [`docs/DATASET-PIPELINE.md`](docs/DATASET-PIPELINE.md).

P1-15 status: **complete for the approved starter corpus**. Plex's byte-level BPE tokenizer fitted only training records' text and learned 9,976 entries within the unchanged 16,384 model capacity. The package retains model/settings/provenance/license files and encodes 147,948 training and 18,394 validation tokens including record EOS boundaries. All 88 records and representative code/ordinary-text samples round-trip exactly; a separate rebuild matched all 11 bundle files. The package occupies 1,039,201 bytes. See the [tokenizer report](docs/PLEX-TOKENIZER.md).

P1-16 status: **complete**. Created a 27,566,080-parameter, step-zero Plex checkpoint from random weights, tied to the P1-15 tokenizer (9,976 learned IDs in the 16,384 model capacity). Seed 1337, initialization recipe/version, CPU initialization device, PyTorch/Python versions, full model settings, initial weights SHA-256, tokenizer/config hashes, and `pretrainedCheckpointLoaded: false` are recorded with the 110,303,036-byte checkpoint. The weights live at `training/artifacts/initializations/p1-16-starter-v1/initialization.pt`; the ignored artifact can be recreated with the command in [`docs/PLEX-INITIALIZATION.md`](docs/PLEX-INITIALIZATION.md). This step performed no training. The regular runner remains byte-v1; P1-17 must add tokenizer-aware training to prove learning on a tiny real-text sample.

P1-17 status: **complete for the tiny learning check**. Starting from the P1-16 checkpoint, the new `learn-check` command trained on the first 16 ordinary BPE tokens of one approved training record. Over 250 updates, loss fell from 9.437925 to 0.0000224 and token accuracy rose from 0% to 100%. Greedy decoding reproduced all 16 tokens from a two-token prompt. The run took 5.66 seconds on the selected CUDA device and saved a 330,897,243-byte checkpoint with optimizer state and tokenizer identity. The [learning report](docs/PLEX-LEARNING-CHECK.md) records hashes and details. This verifies one-sample overfitting only.

P1-18 status: **complete for the bounded real-data pilot**. The `pilot` command verified the approved tokenizer, both data splits, starting P1-16 scratch checkpoint, token IDs, and storage/time bounds. The owner's 120-minute CUDA run completed uninterrupted at 43,632 steps and 357,433,344 sampled token positions. Held-out loss improved from 9.33937 to 6.53100; `pilot-evaluate` independently reproduced the final value over 17,920 targets, and the checkpoint hash matched the report. Peak GPU reservation was 878,706,688 bytes and peak process working set was 1,397,129,216 bytes. The small corpus and large train/validation loss gap limit quality claims. See the [P1-18 pilot report](docs/PLEX-PILOT.md). P1-19 later verified one-step resumption from this saved checkpoint.

P1-19 status: **technical gate complete**. A bounded CUDA `pilot-resume` advanced the completed pilot from step 43,632 to 43,633 without modifying its source checkpoint; the original SHA-256 remained unchanged. The new 330,899,291-byte checkpoint records weights, AdamW state, RNG, fixed learning-rate schedule, training settings, total 357,441,536 sampled positions, tokenizer/dataset identity, and scratch provenance; a copy of the tokenizer bundle accompanies it. Held-out loss changed from 6.530996513366699 to 6.530651337759835, independently reproduced. A separate CPU `complete` command generated text from the saved checkpoint and tokenizer. All 46 training tests passed. The generated code was incomplete; this checks plumbing, not coding ability. See the [P1-19 report](docs/PLEX-RESUME-AND-COMPLETION.md). No uncapped longer-training command is enabled.

**Phase 1 gate:** A reproducible Plex checkpoint trained from random initialization, with evidence that it learned.

## Phase 2 — Basic coding ability

| Task | Work | Completion check |
|---|---|---|
| **P2-01 — Build coding evaluations** | Add withheld completion tasks for HTML, CSS, and JavaScript, including syntax and behavior checks. The owner approved a 30-task development set, a 60-task final set, at least 11/20 final tasks passed per language, and at least +10 percentage points overall over the matching step-zero checkpoint. | P2-01a and the static development-only P2-01b harness/set are complete. The final set remains sealed; safe JavaScript behavior and browser-backed checks still need resolution or must be reported unavailable. |
| **P2-02 — Improve training data** | Build a family-stratified train/development corpus from approved source groups, then adjust the code/explanation mix using measured development failures. | **Complete for the bounded pilot data scope.** Source approvals, group-separated builds, measured data mix, failure-driven revisions, and the approved 234-example v3 corpus (156 train / 78 validation) are recorded, with tokenizer and EOS/context checks. Data sufficiency for useful coding remains unproven. |
| **P2-03 — Compare training configurations** | Test context length, model size, training settings, and representation choices through bounded experiments. | **In progress.** P2-16 and P2-17 established that the current 27.6M model can fit supplied CSS/edit mappings while failing exact unseen literal transfer. P2-18 now isolates literal copying/reference binding before any model-size increase or return to full CSS editing. |
| **P2-04 — Train the next Plex base checkpoint** | Increase the training run after the pipeline and smaller experiments work. | Coding results improve enough to justify the extra compute. |
| **P2-05 — Document capability limits** | Identify supported languages, task sizes, and recurring failures. | Model report includes examples and measured limitations. |

### Current status — October 5, 2026

**The Phase 2 coding-quality gate remains unmet.** Plex has not demonstrated successful general coding-task completion, and the final project holdout remains closed. The current narrow investigation follows P2-07's selector-copy transfer gap:

- **P2-07:** learned 24/24 supplied copies and passed 4/6 held-out wording cases (1/3 selectors, 3/3 gaps).
- **P2-08:** the approved 100-update selector wording/layout run learned 63/64 supplied records. Because it missed the predeclared 64/64 convergence gate, its 4/16 held-out score is descriptive and formally inconclusive.
- **P2-09 audit:** teacher-forced scoring of the existing checkpoint found the expected answer newline top-ranked on 64/64 training prompts but only 6/16 held-out prompts. Once the expected newline is supplied, the period is top-ranked on 16/16 evaluation prompts. Selector-body choice is also inconsistent after the expected prefix (11/16 top-ranked).

The [P2-08 run report](docs/PHASE-2-P2-08-SELECTOR-FORMAT-RUN.md) and [P2-09 answer-boundary audit](docs/PHASE-2-P2-09-ANSWER-BOUNDARY-DIAGNOSTIC.md) record the earlier evidence. P2-10 was owner-approved against exact candidate hashes and completed one fresh seed-1337 run within 100 updates / 10 minutes. It learned 64/64 supplied selectors and scored 7/16 on its original held-out wording. A separate 64-row, four-phrase evaluation-only set scored 43/64 on the unchanged checkpoint, ranging from 5/16 to 16/16 by wording. The wider result shows substantial phrasing sensitivity; the [run report](docs/PHASE-2-P2-10-EXPLICIT-ANSWER-START-RUN.md) and [wider evaluation report](docs/PHASE-2-P2-10-WIDER-WORDING-EVALUATION.md) record scope and limits. The final project holdout remains closed.

**Current milestone: P2-03 configuration research, focused on diagnosing transfer.** P2-02 data preparation is complete at the approved pilot scale. The roadmap had kept configuration experiments under P2-02 while treating the overall coding-quality gate as a data completion requirement. The [milestone review and record-start comparison](docs/PHASE-2-RECORD-START-COMPARISON.md) explains the correction and records the completed 100-step experiment. Passing 0/30 tasks keeps the Phase 2 quality gate unmet; it does not erase completed data deliverables.

**Historical P2-03 result:** the owner-approved [binding-diversity comparison](docs/PHASE-2-BINDING-DIVERSITY-RESULT.md) completed both 100-update CUDA runs in about fourteen seconds each. The varied arm learned 20/24 supplied answers; both arms passed 0/12 new binding requests, 0/12 reserved transfer requests and 0/30 development tasks. Three focused tests passed; exact scratch tensor equality, unchanged tokenizer/provenance, sampler accounting and all 96 diagnostic completions were independently verified. Four supplied answers still failed, so this result did not establish ineffective diversity after convergence. The later answer-focused and selector-copy experiments are recorded above. The final holdout remains closed and a two-hour run remains deferred.

**Earlier P2-03 learning curve:** the [bounded complete-record continuation](docs/PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md) advanced the preserved step-100 checkpoint to step 200 in 500.47 seconds. Exact seen answers rose from 3/156 to 52/156 across all languages, but corpus validation stayed 0/78 and development stayed 0/30. Cumulative real target positions reached 299,959; held-out text loss rose from 4.32042 to 4.47331. All 116 training tests passed at that milestone, including CLI continuation and CUDA optimizer placement/update equivalence.

**Phase 2 gate:** Plex produces useful code on tasks it did not train on. Freeze a final evaluation set and reserve it for milestone decisions. The development-only static evaluator does not establish JavaScript behavior.

The accepted source decisions, family-stratified split, corpus/tokenizer hashes, and measured data mix are recorded in the [Phase 2 data collection review](docs/PHASE-2-DATA-COLLECTION-REVIEW.md). **Historical source-corpus result: the approved v3 corpus (56 records), matching tokenizer, step-zero baseline, 10-minute training check, matched coding-task comparison, and exact file-format token mix are recorded. The trained checkpoint passed 0/30 tasks and fewer checks than step-zero; the owner-approved [36-example corpus](docs/PHASE-2-CODE-PAIR-BUILD-REPORT.md) now has a fresh tokenizer, verified budgets, random initialization, and matching step-zero score. Its ten-minute diagnostic scored 0/30 complete tasks with zero truncations and worsening held-out loss; see the [matched report](docs/PHASE-2-CODE-PAIR-10M-REPORT.md).** The [P2-02 data-mix review](docs/PHASE-2-DATA-MIX-REVIEW.md) records the v2 measurements, v3 composition, matched scores, and safe-JavaScript execution gate. The [v3 report](docs/PHASE-2-DATASET-V3-REPORT.md) and [10-minute training report](docs/PHASE-2-TRAINING-CHECK-V3-REPORT.md) record the user-run counts, hashes, initialization, and results; the [authored-example guide](training/phase2/drafts/README.md) records provenance. P2-01's approved numeric threshold, versioned development tasks, static evaluator, and remaining behavior-check limits are recorded in the [evaluation design](docs/PHASE-2-EVALUATION-DESIGN.md). Subsequent bounded experiments are recorded below; no Phase 2 two-hour run has started.

**Historical 36-example result:** the owner approved the exact 36-example candidate for local training. The [approved corpus and baseline report](docs/PHASE-2-CODE-PAIR-BUILD-REPORT.md) records the completed preparation and next run. Preparation is complete; the matching random baseline passed 0/30 tasks. The ten-minute run and matched scoring are complete: 0/30 tasks, no truncated responses, and worsening held-out loss. Next: a broader reviewed data candidate; a longer run is not justified by these results.

**Historical 180-example result:** the owner approved the [180-example request-following candidate](docs/PHASE-2-CURATED-DATA-APPROVAL.md). Its 120/60 corpus, training-fitted tokenizer, scratch initialization, 100-step CUDA check, and matched development scores are recorded in the [result report](docs/PHASE-2-CURATED-100-STEP-REPORT.md). Held-out loss improved from 7.08 to 2.70, but complete tasks remained 0/30. Next: inspect failed responses and broaden independent coding data before another bounded experiment. A longer run is not justified yet.

**P2-02 failure review and v3 result:** the [30-response audit and v3 data review](docs/PHASE-2-FAILURE-GAP-REVIEW.md) identifies missing structures, seven repeated CSS selectors, and the single JavaScript function name across all 36 prior training examples. The owner approved the exact 234-record v3 candidate. Its separate corpus, training-fitted tokenizer, random initialization, 100-step CUDA run, and matched development scores are recorded in the [v3 result report](docs/PHASE-2-FAILURE-GAP-100-STEP-REPORT.md). Held-out text loss fell, but complete-task passes remained **0/30**. The approved v2 record remains intact; a longer run is not justified by these results.

**P2-03 objective comparison (previously tracked under P2-02):** the [controlled answer-weighted result](docs/PHASE-2-ANSWER-WEIGHTED-100-STEP-REPORT.md) used the same approved v3 corpus, tokenizer, random initialization, 100 steps, and development tasks. Giving code-answer/EOS targets four times the prompt weight still passed **0/30** tasks (34/151 static checks versus 35/151 for ordinary loss). This does not justify a two-hour run.

**P2-03 saved-checkpoint diagnostic:** [read-only inference on the approved v3 examples](docs/PHASE-2-SAVED-CHECKPOINT-DIAGNOSTIC.md) found 0/156 exact or full-static passes on seen training prompts and 0/78 on corpus validation prompts for both existing 100-step checkpoints. Answer weighting raised syntax-pass counts without complete answers. No new training was run for this diagnostic.

**P2-03 three-example probe:** the [bounded result](docs/PHASE-2-THREE-EXAMPLE-PROBE-REPORT.md) reproduced one approved training answer per language exactly by step 25 using complete-record training, with 3/3 retained at step 200. The scratch checkpoint was reloaded and checked. This supports prompt-to-answer learnability for three seen examples only; it does not justify a two-hour run.

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

**P2-15 CSS request-to-code diagnostic complete.** The approved fresh seed-1337 CUDA run reached its 100-update ceiling. Supplied training edits moved from **0/24 to 24/24 complete passes and exact-string matches**, while the four withheld semantic property families remained **0/12**. P2-14 remained **0/12** and P2-01b remained **0/30**. The model did learn bounded completion behavior: EOS moved to 12/12 on P2-15 validation and 30/30 across the P2-01b CSS/HTML/JavaScript tasks. Treat that as behavioral-format transfer, not coding-task generalization. The final owner-controlled holdout remained closed. See the [P2-15 result](docs/PHASE-2-P2-15-RESULT.md).

**P2-16 first run complete.** The approved fresh seed-1337 CUDA run reached step 100. Supplied training complete-task passes moved from **0/120 to 3/120**, training syntax validity from **0/120 to 45/120**, and EOS to **120/120**. Tier A-D complete-task passes remained zero, but syntax-valid outputs rose to **19/24, 6/12, 4/12 and 3/12** respectively. P2-14 remained **0/12** and P2-01b remained **0/30**. Held-out next-token validation loss fell from **6.71646 to 3.38711** while the supplied training curriculum was still clearly underfit. See the [P2-16 result](docs/PHASE-2-P2-16-RESULT.md).

**P2-16b optimization continuation complete.** Training fit rose from **3/120 at step 100 to 98/120 at 200, 105/120 at 300, 116/120 at 400 and 114/120 at 500**, while Tier A/B/C/D complete-task passes remained **0 throughout**. Held-out validation loss worsened after its step-100 minimum (**3.387 -> 3.946 -> 4.084 -> 4.658 -> 4.620**) even as recent training loss fell to about **0.045**. Tier A and B nevertheless reached **24/24** and **12/12 syntax-valid CSS** by step 500. Manual Tier A inspection showed Plex frequently retrieving remembered training selectors and values instead of binding the literal selector/value from the current request. Additional optimization on the unchanged P2-16 curriculum is not justified. See the [P2-16b result](docs/PHASE-2-P2-16B-RESULT.md).

**P2-17/P2-17b complete and closed.** The v2 trajectory reached **120/120 supplied complete-task passes** by step 500, including 60/60 exact extraction plans and 60/60 exact explicit-plan applications. Held-out transfer remained **0/20 complete** on Tiers A, B and C. Tier A still showed partial categorical transfer (operation **13/20**, property **15/20**) but literal binding remained weak (old **6/20**, new **3/20**, selector **0/20**). Validation loss worsened after the step-100 minimum (**2.574 -> 2.910 -> 3.110 -> 3.206 -> 3.369**) while recent training loss fell to about **0.041**. Additional optimization on the unchanged P2-17 representation is not justified. See the [P2-17b result](docs/PHASE-2-P2-17B-RESULT.md).

**P2-18 first run complete.** The fresh v3 CUDA trajectory reached step 100 with only **4/144 supplied complete-task passes**: Level A **2/36**, B **1/36**, C **1/36**, D **0/36**. Held-out Tier A/B/C/D complete-task transfer remained zero. Structural behavior nevertheless emerged strongly: Level B reached **34/36 format-valid** and **33/36 label-exact** outputs, while Tier B reached **18/18 format-valid** and **10/18 label-exact**. Exact held-out literal copying remained **0/18** on Tier A and **0/18** on Tier B. Validation loss fell sharply from **6.82816 to 2.87668** while recent training loss remained **0.54936**, so the run is still underfit rather than diagnostically overfit. See the [P2-18 first-run result](docs/PHASE-2-P2-18-RESULT.md).

**Current milestone: P2-18b Literal Copy Continuation — approved.** Continue the exact P2-18 v3 step-100 checkpoint through cumulative step **500** in four isolated **+100-update** CUDA increments. Preserve the exact 144/72 dataset, tokenizer SHA `44756dc5700e4ac4d258403429358c0d4783b55fccb0271d695e29ed0bd54533`, 27,566,080-parameter architecture, optimizer state, sampler state, seed/RNG trajectory, ordinary next-token complete-record objective, `complete-record-v1`, micro-batch 1 and gradient accumulation 16. Score at steps **200, 300, 400 and 500** using the existing Level A/B/C/D metrics. No automatic continuation beyond 500 is authorized. See the [P2-18b continuation plan](docs/PHASE-2-P2-18B-CONTINUATION.md).

**P2-18 gate:** do not increase model size and do not return to full CSS editing until unseen literal copying is measured after sufficient supplied-task fit. If supplied Level A becomes strong while held-out Tier A remains near zero and validation loss rises, move to **reference-mediated symbol handling**. If Tier A/B become strong but Tier C accumulates wrong-field retrievals, literal copying is established and variable/reference binding becomes the next isolated target.

**Next task:** run the committed P2-18b continuation wrapper against `p2-18-literal-copy-prepared-v3` and `p2-18-literal-copy-run-v3`, then inspect the full 100→500 literal-copy learning curve before authorizing any further optimization or representation change. P2-14 and P2-01b remain development-only; the final project holdout remains closed.
