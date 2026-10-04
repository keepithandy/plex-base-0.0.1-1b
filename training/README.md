# Local Plex training workspace

This workspace adds a separate Python runner alongside the existing Node.js CLI. It trains only Plex-owned weights initialized from random values. The current `byte-v1` codec is a small bootstrap format for runner checks; P1-14/P1-15 replace it with a documented dataset and a tokenizer trained from that dataset.

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

## Prepare and use a small local corpus

The bootstrap `prepare` command takes separate train and validation files so the same file cannot accidentally be used for both. It streams UTF-8 file bytes into little-endian uint16 token IDs and records source hashes without writing full source paths. Keep this format for pipeline checks only; the corpus pipeline and trained tokenizer come in P1-14/P1-15.

```powershell
uv run --project training python -m plex_training.cli prepare `
  --train-input .\path\to\train.txt `
  --validation-input .\path\to\validation.txt
uv run --project training python -m plex_training.cli train `
  --train-tokens training\artifacts\data\train.tokens.u16le `
  --validation-tokens training\artifacts\data\validation.tokens.u16le `
  --checkpoint pilot\checkpoint.pt `
  --minutes 120 `
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

## Run checks

```powershell
uv run --project training python -m unittest discover -s training/tests -v
```

Tests use temporary files and a tiny in-memory model. They do not run the ten-minute smoke test or two-hour pilot.
