# Plex hardware and training profile

Status: **awaiting owner-provided hardware results and limits**. No values below are inferred from the development host.

## Collected Windows hardware

Run [`scripts/collect-hardware.ps1`](../scripts/collect-hardware.ps1) from the repository root and paste its complete JSON output here. The script does not write a report file.

```json
{
  "status": "unknown",
  "pasteCollectorOutputHere": "unknown"
}
```

## Training requirements

- Initial weights: random initialization; do not load a pretrained checkpoint.
- Qwen: optional evaluation baseline only. Any teacher-generated training data must be recorded separately with its source and method.
- CPU model, core/thread count: `unknown`
- Installed GPU model(s): `unknown`
- Available GPU memory for training: `unknown`
- Total system RAM: `unknown`
- Free storage by local drive: `unknown`
- Storage reserved for datasets, checkpoints, and logs: `unknown`
- Compute or spending budget: `unknown`
- Acceptable training duration for the first experiment: `unknown`
- Maximum acceptable RAM/VRAM use during training: `unknown`
- First experiment configuration and estimated resource use: `unknown`; set only after hardware and budget are recorded.

## Local inference requirements

- Operating system: Windows; exact version `unknown`.
- Execution location: local machine; no cloud fallback.
- CPU inference: required.
- GPU acceleration: optional. Installed GPU and available memory `unknown` until measured.
- Offline operation: desired after software and model setup.
- Inference memory ceiling, response latency target, model size, and context length: `unknown`; measure on the target machine before setting targets.
- Inference weights must come from a Plex checkpoint trained from random initialization. Qwen may be run separately as an evaluation baseline.

## Decisions after collection

1. Review free space against the planned dataset, checkpoints, and logs.
2. Choose a small initial random-initialized model and estimate RAM/VRAM needs.
3. Run a short measured training smoke test before setting a longer run or duration estimate.
4. Record the measured training configuration, throughput, memory, and elapsed time in the experiment history.
5. Assess local CPU inference separately from training performance; optional GPU support does not replace CPU support.
