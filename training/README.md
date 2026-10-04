# Local Plex training workspace

This workspace adds a separate Python runner alongside the existing Node.js CLI. It trains only Plex-owned weights initialized from random values. The `byte-v1` codec remains a bootstrap format for runner checks. P1-14 builds reviewed train/validation text splits, and P1-15 has fitted Plex's own byte-level BPE tokenizer on the training split only. Its bundle and encoded corpora are ready; tokenizer-aware model/checkpoint integration follows in the initialization and learning milestones.

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

The bootstrap `prepare` command takes separate train and validation files so the same file cannot accidentally be used for both. It streams UTF-8 file bytes into little-endian uint16 token IDs and records source hashes without writing full source paths. These examples are bootstrap plumbing checks; use the P1-15 tokenizer bundle for the upcoming real-text experiment after tokenizer-aware runner integration. The bootstrap runner rejects BPE token files to prevent mislabeled checkpoints.

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

Output paths for `prepare`, `smoke`, and `train` are relative to the artifact root (default `training/artifacts`). `train` defaults to ten minutes and accepts at most the two-hour pilot duration. The runner enforces the owner's 200 GiB storage allocation and saves a checkpoint every five minutes and on normal completion or Ctrl+C. Uncapped training stays unavailable until P1-19 verifies resume, and the two-hour pilot must wait for the documented dataset and tokenizer.

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

## Train Plex's tokenizer (P1-15)

The approved starter bundle is built at `training/artifacts/tokenizers/p1-15-starter-v1`. It contains a new byte-level BPE tokenizer, settings, the model configuration, encoded train/validation corpora, record indexes, provenance, and license notices. It has 9,976 learned token entries within the unchanged 16,384 model capacity. All 88 records preserve their text exactly. See the [tokenizer report](../docs/PLEX-TOKENIZER.md) for hashes, settings, limits, and results.

The new pinned dependency is `tokenizers==0.23.2`; no pretrained tokenizer or weights are loaded. From the repository root, reproduce into a fresh directory:

```powershell
uv sync --project training --locked
uv run --project training --no-sync python -m plex_training.cli tokenizer-train `
  --dataset-dir training\artifacts\datasets\p1-14-starter-v1 `
  --output-dir tokenizers\p1-15-my-rebuild
```

The command fits only training records' `text`, then encodes both splits. Every record gets one EOS boundary. It validates source/hash/group separation and remaining artifact storage and refuses existing outputs. It does not run model training. P1-16 has created and recorded fresh random weights tied to this tokenizer; P1-17 must add tokenizer-aware tiny-sample learning before the two-hour real-data pilot in P1-18. The historical byte-v1 smoke checkpoint uses different token meanings and cannot be resumed with this tokenizer.

## Initialize fresh Plex weights (P1-16)

The P1-16 command creates a safe, step-zero Plex checkpoint with CPU-initialized random weights and records the seed, initializer, model settings, tokenizer hash, weight hash, and Python/PyTorch versions. It does not train or use a pretrained model. The [initialization report](../docs/PLEX-INITIALIZATION.md) has the recorded hashes and limitations.

```powershell
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizers\p1-15-starter-v1 `
  --output-dir initializations\p1-16-my-run `
  --seed 1337
```

Use a new output directory for each initialization. Output is kept under `training/artifacts` and counted against the 200 GiB allocation. P1-17 will use these weights to check learning with a deliberately tiny real-text sample; the existing training runner still accepts only `byte-v1` corpora.

## Run checks

```powershell
uv run --project training python -m unittest discover -s training/tests -v
```

Tests use temporary files and a tiny in-memory model. They do not run the ten-minute smoke test or two-hour pilot.
