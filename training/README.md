# Local Plex training workspace

This workspace adds a separate Python runner alongside the existing Node.js CLI. It trains only Plex-owned weights initialized from random values. The `byte-v1` codec remains a bootstrap format for runner checks. P1-14 built reviewed train/validation text splits, and P1-15 fitted Plex's own byte-level BPE tokenizer on the training split only. The BPE path now supports a bounded real-data pilot, checked checkpoint resumption, held-out evaluation, and independent completion from saved weights and a matching tokenizer bundle.

## Set up and inspect the runtime

Install [uv](https://docs.astral.sh/uv/) if it is not already available, then run these commands from the repository root in PowerShell:

```powershell
uv sync --project training
uv run --project training python -m plex_training.cli environment
```

The project selects Python 3.12 and pins PyTorch 2.14.0 to the official CUDA 12.6 wheel index. `uv` keeps the environment under `training/.venv`; it does not change a system-wide Python install. PyTorch documents Windows support for Python 3.10–3.14. Its 2.14 release keeps CUDA 12.6 wheels available for systems that need an older driver-compatible build ([Windows install guide](https://pytorch.org/get-started/locally/), [2.14 release notes](https://github.com/pytorch/pytorch/releases/tag/v2.14.0)). The wheel still supports CPU execution; `environment` reports whether this process can access CUDA. `uv sync` creates or refreshes `training/uv.lock` from the pinned project configuration; commit that generated lock file with the training workspace.

If the `plex-train` console command fails to load a PyTorch DLL, run Plex through `python -m plex_training.cli` as shown below. Your test log shows that PyTorch imported under `python.exe`, so this checks whether the failure is specific to the generated console launcher. If the module command also reports `torchVersion: "unavailable"`, keep its JSON report; Windows Application Control may be blocking the DLL for Python as well.

## Run the bounded smoke test

The smoke test uses an in-memory, deterministic byte pattern and downloads no dataset. It is capped at ten minutes and writes its checkpoint and JSONL metrics under `training/artifacts`:

```powershell
uv run --project training python -m plex_training.cli smoke --minutes 10 --device cuda
```

Use `--device cpu` for a CPU-only plumbing check. Use `--device auto` to allow CPU fallback. A tiny one-step command for software plumbing is:

```powershell
uv run --project training python -m plex_training.cli smoke --steps 1 --tiny-test-model --device cpu
```

The tiny configuration is not the P1-12 model and cannot measure its hardware fit. The regular smoke test reports the instantiated parameter count, Python/PyTorch/CUDA versions, elapsed time, token throughput, peak CUDA allocation/reservation, and process peak working set where Windows exposes it.

The owner completed the regular ten-minute CUDA test on October 3, 2026. It saved a checkpoint after 4,199 steps, with 734 MiB peak GPU reservation and about 1.30 GiB process peak RAM. See the [retained smoke report](../docs/SMOKE-TEST-2026-10-03.md). No repeat smoke run is needed for this source-selection step.

## Prepare and use a small local corpus

The bootstrap `prepare` command takes separate train and validation files so the same file cannot accidentally be used for both. It streams UTF-8 file bytes into little-endian uint16 token IDs and records source hashes without writing full source paths. These examples are bootstrap plumbing checks; use the separate `pilot`, `pilot-resume`, `pilot-evaluate`, and `complete` commands below for the approved BPE data and checkpoint. The bootstrap runner rejects BPE token files to prevent mislabeled checkpoints.

```powershell
uv run --project training python -m plex_training.cli prepare `
  --train-input .\path\to\train.txt `
  --validation-input .\path\to\validation.txt
uv run --project training python -m plex_training.cli train `
  --train-tokens training\artifacts\data\train.tokens.u16le `
  --validation-tokens training\artifacts\data\validation.tokens.u16le `
  --checkpoint pilot\checkpoint.pt `
  --minutes 1 --steps 1 `
  --device cuda
uv run --project training python -m plex_training.cli evaluate `
  --checkpoint training\artifacts\pilot\checkpoint.pt `
  --tokens training\artifacts\data\validation.tokens.u16le
uv run --project training python -m plex_training.cli generate `
  --checkpoint training\artifacts\pilot\checkpoint.pt `
  --prompt "function add(a, b) {" `
  --device cuda
```

Output paths for `prepare`, `smoke`, and `train` are relative to the artifact root (default `training/artifacts`). `train` defaults to ten minutes and accepts at most the two-hour pilot duration; it remains the byte-v1 plumbing command. The runner enforces the owner's 200 GiB storage allocation and saves a checkpoint every five minutes and on normal completion or Ctrl+C. P1-19 verified BPE resume, but uncapped training is still unavailable. Use the BPE commands below for the approved data.

## Curate a reproducible dataset (P1-14)

P1-14 reads local source checkouts only. It requires a source catalog with an immutable revision, license evidence, and an explicit rights-review status; it does not fetch or approve external data. Copy [`dataset-sources.example.json`](dataset-sources.example.json) to `dataset-sources.local.json`, place reviewed source trees beneath `training/data/raw`, and follow [`docs/DATASET-PIPELINE.md`](../docs/DATASET-PIPELINE.md) before building. The catalog and raw source trees are ignored by Git.

The owner-approved starter corpus is built and verified: 34 training records, 54 validation records, and both MIT notices, totaling 746,848 bytes. Its [source/build review](../docs/DATASET-SOURCE-REVIEW.md) records the exact scopes, approved catalog, build hashes, and reproduction instructions. The separate download helper reads the source lock, retains original license notices, checks upstream blob hashes, and downloads at most 20 MiB of selected text without running it:

```powershell
uv run --project training python -m plex_training.source_fetch
```

```powershell
uv run --project training python -m plex_training.cli dataset-build `
  --source-manifest training\dataset-sources.local.json `
  --output-dir datasets\p1-14 `
  --validation-percent 10 `
  --seed 1337
```

The command creates `train.jsonl`, `validation.jsonl`, and a provenance manifest under `training/artifacts/datasets/p1-14`. Exact duplicates, detected secret patterns, invalid UTF-8, oversized files, and detectable syntax failures are skipped with reason counts. Train/validation assignment is grouped by the catalog's `groupId`, so related repositories remain together. P1-15 consumes the training split to fit the tokenizer.

## Phase 2 source collection (P2-02)

The owner approved re-splitting the exact Microsoft P1-14 selection by project and a small MDN `learning-area` path selection. The pinned lock is [`phase2/dataset-source-lock.json`](phase2/dataset-source-lock.json); the original source catalog is [`phase2/dataset-sources.phase2-v1.json`](phase2/dataset-sources.phase2-v1.json). The new [`phase2/dataset-sources.phase2-v2.json`](phase2/dataset-sources.phase2-v2.json) preserves both source entries and adds the nine newly owner-approved local examples with explicit provenance. Raw external snapshots stay beneath `training/phase2/data/raw` and are ignored by Git. See the [collection report](../docs/PHASE-2-DATA-COLLECTION-REVIEW.md) for the external files, license notices, and exclusions.

The existing [P2-02 v2 baseline](artifacts/datasets/p2-02-data-v2) remains unchanged. The approved nine-example supplement is recorded in [`phase2/drafts/p2-02-authored-examples-v1.jsonl`](phase2/drafts/p2-02-authored-examples-v1.jsonl), materialized beneath `phase2/data/authored`, and included with the pinned Microsoft/MDN sources in the built [P2-02 v3 corpus](artifacts/datasets/p2-02-data-v3). Its new tokenizer was fit on training text only at [`tokenizers/p2-02-data-v3`](artifacts/tokenizers/p2-02-data-v3). The user-run build counts, token totals, hashes, and limits are in the [v3 report](../docs/PHASE-2-DATASET-V3-REPORT.md). The v2 direct-code-extension shares (23.9% training and 8.7% development) remain historical measurements; v3's code/explanation mix has not yet been decomposed by language, source family, or fenced-code content.

```powershell
uv run --project training --no-sync python training\phase2\materialize_authored_examples.py
uv run --project training --no-sync python -m plex_training.cli dataset-build `
  --source-manifest training\phase2\dataset-sources.phase2-v2.json `
  --output-dir datasets\p2-02-data-v3 `
  --validation-percent 30 `
  --seed 51
uv run --project training --no-sync python -m plex_training.cli tokenizer-train `
  --dataset-dir training\artifacts\datasets\p2-02-data-v3 `
  --output-dir tokenizers\p2-02-data-v3
```

The v3 build produced 36 training and 20 development records with no skipped files. The tokenizer encoded and round-tripped both splits. To reproduce from the already materialized sources, use fresh output paths; the materializer refuses to overwrite its existing versioned source directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli dataset-build `
  --source-manifest training\phase2\dataset-sources.phase2-v2.json `
  --output-dir datasets\p2-02-data-v3-rebuild `
  --validation-percent 30 `
  --seed 51
uv run --project training --no-sync python -m plex_training.cli tokenizer-train `
  --dataset-dir training\artifacts\datasets\p2-02-data-v3-rebuild `
  --output-dir tokenizers\p2-02-data-v3-rebuild
```

Before training, initialize fresh random weights tied to this tokenizer and run the static development evaluation; keep its JavaScript behavior limitation visible.

## Score coding-task responses (P2-01)

P2-01a records the owner-approved final-set gate: at least 11/20 complete tasks per language and at least a 10-percentage-point overall improvement above the matching step-zero checkpoint. P2-01b includes 30 owner-authored development tasks and a static local evaluator; the 60-task final holdout has not been built. The JavaScript checks parse syntax with `node --check` but never execute generated code. HTML and CSS checks are structural only; see the [evaluation design](../docs/PHASE-2-EVALUATION-DESIGN.md) for limitations and remaining gates.

The owner has initialized matching step-zero random weights with seed 1337 at `training/artifacts/initializations/p2-step-zero-v3/`; the [v3 report](../docs/PHASE-2-DATASET-V3-REPORT.md) records the checkpoint and weight hashes. To reproduce the initialization, choose a fresh output directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizers\p2-02-data-v3 `
  --output-dir initializations\p2-step-zero-v3-rebuild `
  --seed 1337
```

Then generate the development responses into a fresh directory:

```powershell
uv run --project training --locked python -m plex_training.cli task-generate `
  --checkpoint training\artifacts\initializations\p2-step-zero-v3\initialization.pt `
  --bundle-dir training\artifacts\tokenizers\p2-02-data-v3 `
  --output-dir evaluation\p2-dev-step-zero-v3 `
  --device cuda
```

The owner generated and scored all 30 development responses with the matching v3 step-zero checkpoint and tokenizer. The baseline scored 0/30 complete tasks; 29 outputs were truncated. The response hash, task-set hash, per-language results, and limitations are recorded in the [v3 report](../docs/PHASE-2-DATASET-V3-REPORT.md). A 10-minute v3 training check reduced held-out language-model loss from 9.1694 to 6.4759, but its matched coding-task score was 0/30, with 20/181 checks passed versus step-zero's 40/180; all 30 trained outputs were truncated. Do not start the two-hour pilot yet. The measured v3 train split is 76.3% Markdown by tokenizer positions, and the six authored task/solution records contribute 0.7%. Prepare a reviewed request-to-code data mix before training again; details are in the [data-mix review](../docs/PHASE-2-DATA-MIX-REVIEW.md) and [training check report](../docs/PHASE-2-TRAINING-CHECK-V3-REPORT.md).

The owner approved the [36-example request-to-code candidate](../docs/PHASE-2-CODE-PAIR-CANDIDATE.md) for local training. Its separate corpus is built with 24 training and 12 validation records, a fresh training-fitted tokenizer, verified context/EOS budgets, and random initialization. Its matching step-zero baseline scored 0/30 complete tasks. The completed ten-minute run scored 0/30 complete tasks with no truncated responses and worsening held-out loss. See the [matched diagnostic report](../docs/PHASE-2-CODE-PAIR-10M-REPORT.md). The owner subsequently approved the [curated 180-example version](../docs/PHASE-2-CURATED-DATA-APPROVAL.md). Its separate corpus, tokenizer, scratch initialization, 100-step run, and matched evaluation are complete. The [100-step report](../docs/PHASE-2-CURATED-100-STEP-REPORT.md) records lower held-out loss but still 0/30 complete tasks. Further data work should target the failed requests before longer training.

The [failure audit and v3 review](../docs/PHASE-2-FAILURE-GAP-REVIEW.md) records what the 30 unsuccessful responses exposed. The owner approved the exact [234-record v3 candidate](phase2/drafts/p2-02-request-following-v3/REVIEW.md). Its separate corpus, tokenizer, scratch initialization, 100-step diagnostic, and matched development scores are recorded in the [v3 result report](../docs/PHASE-2-FAILURE-GAP-100-STEP-REPORT.md). Held-out text loss improved, but complete tasks remained 0/30; do not extend this checkpoint to a longer run on that evidence. The approved 180-record source and previous runs remain available for comparison.

The [saved-checkpoint prompt diagnostic](../docs/PHASE-2-SAVED-CHECKPOINT-DIAGNOSTIC.md) ran inference only on the approved v3 examples. Ordinary and answer-weighted 100-step checkpoints each scored 0/156 exact or full-static training examples and 0/78 exact or full-static corpus validation examples. The answer-weighted model improved syntax passes but did not yet learn complete supplied answers. This led to a three-example overfit probe, with one already-approved training example per language and a ten-minute/200-step cap.

The [three-example overfit probe](../docs/PHASE-2-THREE-EXAMPLE-PROBE-REPORT.md) is now complete. Using the v3 scratch initialization and tokenizer, it learned all three approved training answers exactly by step 25 and retained 3/3 through step 200, finishing in 8.12 seconds. Its complete-record training procedure differs from the packed-window full-corpus runner, and the subsequent sampler-exposure audit and record-start comparison are recorded below. The final holdout remains closed.

The [packed-window exposure audit](../docs/PHASE-2-PACKED-WINDOW-EXPOSURE-AUDIT.md) replayed the exact 1,600 window starts used by the 100-step v3 run. It found 7,157 full prompt-and-answer exposures across the corpus, with prompts at position zero only 14 times. The [completed P2-03 comparison](../docs/PHASE-2-RECORD-START-COMPARISON.md) sampled 512-token windows at verified record starts with the same 100-step target-position budget and optimizer. It still passed 0/30 development tasks. P2-02 data preparation is complete; P2-03 is now the active milestone.

The `pilot` command accepts `--answer-weight 4` together with `--dataset-dir` for a controlled answer-focused comparison. It verifies the built dataset and tokenizer index before assigning weight 4 to answer/EOS targets and weight 1 to prompt targets; ordinary `pilot` runs keep their prior loss. The [100-step comparison](../docs/PHASE-2-ANSWER-WEIGHTED-100-STEP-REPORT.md) used the same v3 initialization and development tasks and still passed 0/30 complete tasks. Its checkpoint records the weight map and cannot be resumed under the ordinary objective. A longer run remains deferred.

For a manually supplied response, create a newline-delimited JSON file with one object per task:

```jsonl
{"taskId":"p2dev-js-01-clamp","text":"function clamp(value, minimum, maximum) { return Math.min(maximum, Math.max(minimum, value)); }","truncated":false}
```

Score a generated response file, choosing a report path that does not already exist:

```powershell
uv run --project training --locked python -m plex_training.cli task-evaluate `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --responses training\artifacts\evaluation\p2-dev-step-zero-v3\responses.jsonl `
  --report training\artifacts\evaluation\p2-dev-step-zero-v3\score.json
```

`truncated` records whether generation reached its token cap; truncated responses do not pass. The evaluator refuses to overwrite an existing report.

The owner completed this matched comparison on 2026-10-04. The output and score report already exist at `training/artifacts/evaluation/p2-dev-v3-10m-v1`; the evaluator refuses to overwrite `score.json`. If the run must be reproduced, use fresh output and report directory names while keeping the checkpoint, tokenizer, task set, and decode defaults fixed:

```powershell
uv run --project training --no-sync python -m plex_training.cli task-generate `
  --checkpoint training\artifacts\pilot\p2-v3-10m-v1\pilot-checkpoint.pt `
  --bundle-dir training\artifacts\tokenizers\p2-02-data-v3 `
  --output-dir evaluation\p2-dev-v3-10m-v1 `
  --device cuda
uv run --project training --no-sync python -m plex_training.cli task-evaluate `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --responses training\artifacts\evaluation\p2-dev-v3-10m-v1\responses.jsonl `
  --report training\artifacts\evaluation\p2-dev-v3-10m-v1\score.json
```

The trained report recorded 0/30 complete tasks, 20/181 checks passed, 30/30 truncated outputs, HTML syntax pass 10/10, CSS syntax pass 0/10, and JavaScript syntax pass 0/10. Compare pass counts, truncation, and per-language results with the step-zero report. These static scores do not execute JavaScript behavior.

## Train Plex's tokenizer (P1-15)

The approved starter bundle is built at `training/artifacts/tokenizers/p1-15-starter-v1`. It contains a new byte-level BPE tokenizer, settings, the model configuration, encoded train/validation corpora, record indexes, provenance, and license notices. It has 9,976 learned token entries within the unchanged 16,384 model capacity. All 88 records preserve their text exactly. See the [tokenizer report](../docs/PLEX-TOKENIZER.md) for hashes, settings, limits, and results.

The new pinned dependency is `tokenizers==0.23.2`; no pretrained tokenizer or weights are loaded. From the repository root, reproduce into a fresh directory:

```powershell
uv sync --project training --locked
uv run --project training --no-sync python -m plex_training.cli tokenizer-train `
  --dataset-dir training\artifacts\datasets\p1-14-starter-v1 `
  --output-dir tokenizers\p1-15-my-rebuild
```

The command fits only training records' `text`, then encodes both splits. Every record gets one EOS boundary. It validates source/hash/group separation and remaining artifact storage and refuses existing outputs. It does not run model training. P1-16 created and recorded fresh random weights tied to this tokenizer; P1-17's one-record learning check is complete. The historical byte-v1 smoke checkpoint uses different token meanings and cannot be resumed with this tokenizer.

## Initialize fresh Plex weights (P1-16)

The P1-16 command creates a safe, step-zero Plex checkpoint with CPU-initialized random weights and records the seed, initializer, model settings, tokenizer hash, weight hash, and Python/PyTorch versions. It does not train or use a pretrained model. The [initialization report](../docs/PLEX-INITIALIZATION.md) has the recorded hashes and limitations.

```powershell
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizers\p1-15-starter-v1 `
  --output-dir initializations\p1-16-my-run `
  --seed 1337
```

Use a new output directory for each initialization. Output is kept under `training/artifacts` and counted against the 200 GiB allocation. P1-17 used these weights to check learning with a deliberately tiny real-text sample. The general `train` command still accepts only `byte-v1` corpora; the approved BPE training path uses `pilot` and `pilot-resume`.

## Prove the model can learn (P1-17)

P1-17's one-record overfit check is implemented by `learn-check`. The successful run reduced loss from 9.437925 to 0.00002242 and reproduced all 16 sample tokens from a two-token prompt in 250 steps. The checkpoint preserves the tokenizer identity and optimizer state. See the [P1-17 report](../docs/PLEX-LEARNING-CHECK.md).

```powershell
uv run --project training --no-sync python -m plex_training.cli learn-check `
  --initialization training\artifacts\initializations\p1-16-starter-v1\initialization.pt `
  --tokenizer-dir training\artifacts\tokenizers\p1-15-starter-v1 `
  --train-tokens training\artifacts\tokenizers\p1-15-starter-v1\train.tokens.u16le `
  --train-index training\artifacts\tokenizers\p1-15-starter-v1\train.index.json `
  --output-dir learning\p1-17-my-run `
  --steps 250 --sample-tokens 16 --minutes 10 --device auto
```

Choose an unused output path. The command is capped at 500 optimizer steps and ten minutes; it uses one real training record and no validation text. Exact reproduction here is an overfit plumbing check only. P1-18's separate bounded BPE path is documented below.

## Prepare and run the held-out pilot (P1-18)

`pilot` verifies both packed BPE splits, their reviewed source hashes, the tokenizer/model configuration, and the step-zero P1-16 checkpoint before training. It records the baseline and final held-out validation losses, throughput, memory use, tokenizer/data identities, and periodic checkpoints. The owner's full two-hour CUDA run passed the bounded pilot gate: held-out loss improved from 9.33937 to 6.53100, independently confirmed from its checkpoint. See the [pilot report](../docs/PLEX-PILOT.md).

To reproduce the short preflight in a fresh output directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --minutes 1 --steps 1 --device auto `
  --output-dir pilot\p1-18-my-preflight
```

To independently re-evaluate the completed run:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-evaluate `
  --checkpoint training\artifacts\pilot\p1-18-full-v2\pilot-checkpoint.pt `
  --device cuda
```

Training uses the approved train split; evaluation reads the distinct held-out split. The command refuses to overwrite an output directory and enforces a 120-minute maximum and the 200 GiB artifact allocation. No further long run is needed for P1-18. The small starter corpus and large train/validation loss gap limit quality claims. P1-19's one-step resumption and independent completion passed; the result and current bounds are below.

## Resume the pilot and complete a prompt (P1-19)

`pilot-resume` validates the approved BPE bundle and the trained Plex checkpoint, restores model/optimizer and random-generator state, and continues into a **new** directory without changing the original pilot. The command is limited to ten minutes and 1–100 additional steps. It saves the resumed checkpoint, JSONL metrics, a JSON report, and a copy of the matching tokenizer bundle. The new checkpoint records immutable training settings, a `constant-v1` learning-rate schedule at its saved step, total sampled token positions, and scratch/data/tokenizer provenance. The legacy P1-18 checkpoint predates explicit settings and schedule fields; the resume path accepts it only with the recorded pilot's fixed settings. The [P1-19 report](../docs/PLEX-RESUME-AND-COMPLETION.md) records the verified one-step CUDA result and checkpoint hashes.

The verified output path `pilot\p1-19-resume-v2` already exists. To repeat the bounded check, choose an unused output path from the repository root:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-resume `
  --checkpoint training\artifacts\pilot\p1-18-full-v2\pilot-checkpoint.pt `
  --output-dir pilot\p1-19-my-resume `
  --minutes 10 --steps 1 --device cuda
```

`complete` loads a trained Plex BPE checkpoint and matching tokenizer in a separate process. For P1-19's resumed checkpoint, it finds the copied `tokenizer/` sidecar automatically; `--bundle-dir` can select another matching bundle. It bounds the prompt to 4,096 UTF-8 bytes and generation to 256 tokens, uses at most the model's 512-token context, masks reserved and unused vocabulary IDs, and stops at EOS. Temperature `0` is greedy; positive values use seeded sampling. The verified CPU command was:

```powershell
uv run --project training --no-sync python -m plex_training.cli complete `
  --checkpoint training\artifacts\pilot\p1-19-resume-v2\resumed-checkpoint.pt `
  --prompt 'function add(a, b) {' `
  --max-new-tokens 32 --temperature 0 --device cpu
```

The saved checkpoint generated text, but its example was incomplete and did not correctly implement the function. This verifies local CPU loading and tokenization, not useful coding ability or a CPU speed/memory target. The current CLI keeps `pilot` at 120 minutes, `pilot-resume` at ten minutes, and general `train` at 120 minutes; no uncapped training command is enabled. The [P1-20 experiment report](../docs/PLEX-EXPERIMENT-REPORT-P1-20.md) records the run and its failures. Broader reviewed data and functional evaluation should be planned before considering a longer run.

## P2-03 record-start comparison

This comparison is already run and scored; the owner need not repeat it. See the [result and milestone review](../docs/PHASE-2-RECORD-START-COMPARISON.md). To reproduce into a new directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --initialization training\artifacts\initializations\p2-request-following-step-zero-v3\initialization.pt `
  --output-dir pilot\p2-record-start-my-comparison `
  --sampling-policy record-start-v1 --answer-weight 1 `
  --minutes 10 --steps 100 --device cuda
```

The experimental option requires ordinary loss, the matching dataset, at most 100 steps, and at most ten minutes. It verifies every indexed record and wraps only through training EOS boundaries. The sampler identity is saved in checkpoints; the `pilot-resume` command reconstructs ordinary sampling for packed checkpoints and verified complete-record sampling when that policy is saved. Record-start packed continuation remains unsupported. Runner-level resume is tested with the identical verified sampler. Record-start packed CLI continuation is not enabled. The [complete-record follow-up](../docs/PHASE-2-COMPLETE-RECORD-COMPARISON.md) is now implemented and run; no longer run is needed now.

## P2-03 complete-record comparison

The comparison is complete: three seen answers were reproduced exactly, four training examples passed static checks, and development tasks remained 0/30. See the [report](../docs/PHASE-2-COMPLETE-RECORD-COMPARISON.md). There is no need to repeat this run. To reproduce into an unused directory:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --initialization training\artifacts\initializations\p2-request-following-step-zero-v3\initialization.pt `
  --output-dir pilot\p2-complete-record-my-comparison `
  --sampling-policy complete-record-v1 --answer-weight 1 `
  --minutes 10 --steps 100 --device cuda
```

Each row contains one complete record with fresh context and position zero. Right-padding targets have zero loss weight; micro-batch 1 needs no padding. Actual non-padding target counts are saved and checked rather than inferred from the 512-token maximum context. The experimental option requires ordinary loss, its matching dataset, at most 100 updates, and at most ten minutes. The `pilot-resume` CLI now detects saved complete-record sampling and requires the matching `--dataset-dir`. It verifies the sampler, optimizer, RNG, and real-token progress before creating output, and packages a copy of the matching tokenizer. Ordinary packed continuation remains available without `--dataset-dir`. The [step-100/step-200 learning comparison](../docs/PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md) is complete: 3 → 52 exact seen answers, but development remains 0/30; the final holdout remains closed.

## Bounded complete-record continuation

The continuation is already run and scored; the owner does not need to repeat it. It restored the saved sampler automatically and finished 100 additional updates in 500.47 seconds, reaching step 200 and 299,959 cumulative real targets. The source checkpoint and all 12 copied tokenizer files were independently verified. See the [learning-curve report](../docs/PHASE-2-COMPLETE-RECORD-LEARNING-CURVE.md). To reproduce, use the matching built dataset and a new output path. The command permits 1–100 additional updates and at most ten minutes, preserves the source checkpoint, and counts only real target positions. No run is extended automatically.

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-resume `
  --bundle-dir training\artifacts\tokenizers\p2-request-following-v3 `
  --dataset-dir training\artifacts\datasets\p2-request-following-v3 `
  --checkpoint training\artifacts\pilot\p2-complete-record-100step-v1\pilot-checkpoint.pt `
  --output-dir pilot\p2-complete-record-my-continuation `
  --steps 100 --minutes 10 --device cuda
```

Non-capturable, non-fused AdamW restores scalar step counters to CPU while retaining its moment tensors on the parameter device. This matches fresh optimizer state placement and avoids unnecessary CUDA scalar reads introduced by checkpoint mapping. Fused or capturable optimizer counters retain their own placement.

## P2-03 transfer diagnostic

The owner completed the [P2-03 transfer diagnostic](../docs/PHASE-2-TRANSFER-DIAGNOSTIC.md): step 200 passed six original requests and none of twelve variations. It used the saved step-100/step-200 checkpoints with no training. The following is the already-run command; choose a fresh directory only if reproducing:

```powershell
uv run --project training --no-sync python training\phase2\diagnose_transfer.py --device cuda --output training\artifacts\diagnostics\p2-transfer-v1
```

Add `--prepare-only` to validate/save cases without loading PyTorch. Five focused diagnostic tests passed; the full training-suite result below is from the prior continuation. Windows Application Control blocked the initial agent-side import; the user-terminal inference subsequently succeeded. The [binding audit](../docs/PHASE-2-BINDING-VARIATION-AUDIT.md) verifies the completed outputs and records the next candidate to prepare. No repeat or new training is required now.

## Run checks

The [24-example binding-diversity candidate](../docs/PHASE-2-BINDING-CANDIDATE-REVIEW.md) is prepared for owner review. It includes eighteen new training variations and twelve separate evaluation-only records. All reference and stale-answer checks passed; four focused tests verified candidate preparation and byte-identical reproduction. It remains pending approval and has not been built into training inputs.

```powershell
uv run --project training --no-sync python -m unittest discover -s training/tests -v
```

All 116 training-workspace tests passed, including complete-record CLI continuation, rejection before output creation, ordinary-pilot compatibility, padding exclusion, actual target accounting, exact variable-length resume, and GPU optimizer-state placement with an identical next update. They use temporary files and a tiny model, including exact CPU BPE resume equivalence, settings/schedule and overwrite rejection, generation controls, answer-weighted span and checkpoint checks, and verified record-start sampling, circular targets, sampler identity, and experiment bounds; they do not rerun the ten-minute smoke test or two-hour pilot. The real P1-19 one-step CUDA continuation and separate CPU completion were checked independently.
