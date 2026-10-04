# Plex hardware and training profile

Status: **hardware and owner-set training limits recorded; ten-minute synthetic resource-fit test passed; real-data pilot pending**. Hardware values below were provided by the owner, not inferred from the development host.

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
- Free storage at collection time: C: 745,373,954,048 bytes (694.18 GiB) free of 998,951,038,976 bytes (930.35 GiB) total. The owner allocated 200 GiB to Plex.
- Plex storage allocation: 200 GiB total for datasets, checkpoints, and logs. This is an initial allocation and can be revised after P1-12 measures actual use.
- Paid services, datasets, APIs, or cloud compute budget: $0.
- Training duration: run a 10-minute smoke test, followed by a pilot capped at two hours. After those checks, longer training runs may continue without a fixed time cap, with resumable checkpoints and progress monitoring.
- Local electricity cost allowance: `unknown`; no separate allowance was specified.
- Maximum acceptable RAM/VRAM use during training: `unknown`
- First experiment: 27,566,080 parameters, FP32 AdamW, with an estimated 420 MiB for parameters, gradients, and optimizer moments before activations/runtime overhead. See [`FIRST-EXPERIMENT.md`](FIRST-EXPERIMENT.md). The runner's original 13 tests and ten-minute CUDA smoke test passed on the owner's Windows machine with PyTorch 2.14.0+cu126 and CUDA 12.6. The [observed smoke result](SMOKE-TEST-2026-10-03.md) was 734 MiB peak GPU reservation, about 1.30 GiB process peak RAM, and 57,327.61 synthetic token positions/second. Real-data pilot resource use and CPU inference remain unmeasured.

## Local inference requirements

- Operating system: Windows; exact version `unknown`.
- Execution location: local machine; no cloud fallback.
- CPU inference: required.
- GPU acceleration: optional. Installed GPU is an NVIDIA GeForce RTX 4080 SUPER; 14,532 MiB was free at collection time.
- Offline operation: desired after software and model setup.
- Inference memory ceiling, response latency target, model size, and context length: `unknown`; measure on the target machine before setting targets.
- Inference weights must come from a Plex checkpoint trained from random initialization. Qwen may be run separately as an evaluation baseline.

## Decisions after collection

1. Fit the first model and dataset within the 200 GiB allocation; revise the allocation only if measured needs justify it.
2. Choose a small initial random-initialized model and estimate RAM/VRAM needs.
3. Run the 10-minute smoke test and the two-hour pilot before authorizing longer training.
4. Save resumable checkpoints and record the measured training configuration, throughput, memory, and elapsed time in the experiment history.
5. Assess local CPU inference separately from training performance; optional GPU support does not replace CPU support.
