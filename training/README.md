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

The [36-example request-to-code candidate](../docs/PHASE-2-CODE-PAIR-CANDIDATE.md) is prepared for owner review, with 24 training and 12 validation records and the same prompt template. All supplied answers passed static checks; no model was trained from them. Its pending catalog is rejected by the production builder until the agreed review is complete. The proposal includes validation-only commands and the bounded experiment to run after acceptance.

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

## Run checks

```powershell
uv run --project training --no-sync python -m unittest discover -s training/tests -v
```

All 46 training-workspace tests pass. They use temporary files and a tiny model, including exact CPU BPE resume equivalence, settings/schedule and overwrite rejection, and generation controls; they do not rerun the ten-minute smoke test or two-hour pilot. The real P1-19 one-step CUDA continuation and separate CPU completion were checked independently.
