# Plex hardware and training profile

Status: **hardware inventory received; awaiting training limits and first-experiment sizing**. Hardware values below were provided by the owner, not inferred from the development host.

## Collected Windows hardware

Collected on **2026-10-03 22:52:18 UTC** with [`scripts/collect-hardware.ps1`](../scripts/collect-hardware.ps1). Available GPU memory is a point-in-time free-memory reading and may change as applications use the GPU. The script prints JSON and does not write a report file; rerun it after hardware changes and replace this dated snapshot.

```json
{
  "schemaVersion": 1,
  "collectedAtUtc": "2026-10-03T22:52:18.6346950Z",
  "collection": "Read-only Windows CIM; nvidia-smi used only when already installed.",
  "cpu": {
    "status": "available",
    "models": ["Intel(R) Core(TM) i9-14900KF"],
    "logicalProcessorCount": 32
  },
  "memory": {
    "status": "available",
    "totalBytes": 34034339840,
    "totalGiB": 31.7
  },
  "gpuNames": {
    "status": "available",
    "names": ["NVIDIA GeForce RTX 4080 SUPER"]
  },
  "gpuMemory": {
    "status": "available",
    "units": "MiB",
    "devices": [{
      "name": "NVIDIA GeForce RTX 4080 SUPER",
      "totalMiB": 16376,
      "availableMiB": 14532,
      "status": "available"
    }]
  },
  "fixedDrives": {
    "status": "available",
    "drives": [{
      "drive": "C:",
      "freeBytes": 745373954048,
      "freeGiB": 694.18,
      "totalBytes": 998951038976,
      "totalGiB": 930.35
    }]
  },
  "userInputs": {
    "trainingBudget": "unknown",
    "acceptableTrainingDuration": "unknown",
    "inferenceRequirements": "Windows local inference; CPU support required; optional GPU acceleration."
  }
}
```

## Training requirements

- Initial weights: random initialization; do not load a pretrained checkpoint.
- Qwen: optional evaluation baseline only. Any teacher-generated training data must be recorded separately with its source and method.
- CPU model and logical processors: Intel Core i9-14900KF; 32 logical processors.
- Installed GPU model(s): NVIDIA GeForce RTX 4080 SUPER.
- GPU memory: 16,376 MiB total; 14,532 MiB free at collection time. The free amount is transient.
- Total system RAM: 34,034,339,840 bytes (31.7 GiB reported).
- Free storage by local drive: C: 745,373,954,048 bytes (694.18 GiB) free of 998,951,038,976 bytes (930.35 GiB) total. Amount available to dedicate to Plex: `unknown`.
- Storage reserved for datasets, checkpoints, and logs: `unknown`
- Compute or spending budget: `unknown`
- Acceptable training duration for the first experiment: `unknown`
- Maximum acceptable RAM/VRAM use during training: `unknown`
- First experiment configuration and estimated resource use: `unknown`; set after dedicated storage, training budget, and acceptable duration are known.

## Local inference requirements

- Operating system: Windows; exact version `unknown`.
- Execution location: local machine; no cloud fallback.
- CPU inference: required.
- GPU acceleration: optional. Installed GPU is an NVIDIA GeForce RTX 4080 SUPER; 14,532 MiB was free at collection time.
- Offline operation: desired after software and model setup.
- Inference memory ceiling, response latency target, model size, and context length: `unknown`; measure on the target machine before setting targets.
- Inference weights must come from a Plex checkpoint trained from random initialization. Qwen may be run separately as an evaluation baseline.

## Decisions after collection

1. Confirm how much free space may be allocated to Plex, then review it against the planned dataset, checkpoints, and logs.
2. Choose a small initial random-initialized model and estimate RAM/VRAM needs.
3. Run a short measured training smoke test before setting a longer run or duration estimate.
4. Record the measured training configuration, throughput, memory, and elapsed time in the experiment history.
5. Assess local CPU inference separately from training performance; optional GPU support does not replace CPU support.
