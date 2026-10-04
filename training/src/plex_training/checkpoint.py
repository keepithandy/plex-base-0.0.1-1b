"""Plex-owned, weights-only checkpoints and resume validation."""

from __future__ import annotations

import platform
import random
from pathlib import Path
from typing import Any

import torch

from .artifacts import atomic_write_checkpoint
from .config import ModelConfig
from .model import PlexLanguageModel

CHECKPOINT_FORMAT_VERSION = 1


def save_checkpoint(
    model: PlexLanguageModel,
    optimizer: torch.optim.Optimizer,
    *,
    step: int,
    seed: int,
    codec: str,
    sampling_rng: random.Random,
    device: torch.device,
    destination: Path,
    artifact_root: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    payload = {
        "formatVersion": CHECKPOINT_FORMAT_VERSION,
        "modelFamily": "plex-from-scratch",
        "modelConfig": model.config.to_dict(),
        "modelStateDict": model.state_dict(),
        "optimizerStateDict": optimizer.state_dict(),
        "step": int(step),
        "seed": int(seed),
        "codec": codec,
        "samplingRngState": sampling_rng.getstate(),
        "torchCpuRngState": torch.get_rng_state(),
        "torchCudaRngStates": torch.cuda.get_rng_state_all() if device.type == "cuda" else [],
        "pythonVersion": platform.python_version(),
        "torchVersion": str(torch.__version__),
    }
    size = atomic_write_checkpoint(
        payload,
        destination,
        artifact_root,
        overwrite=overwrite,
    )
    return {"path": destination.name, "bytes": size, "step": step}


def read_checkpoint(path: Path, device: torch.device) -> tuple[PlexLanguageModel, dict[str, Any]]:
    """Read only tensor/primitive checkpoint data; never unpickle arbitrary objects."""
    try:
        payload = torch.load(path, map_location=device, weights_only=True)
    except Exception as exc:
        raise ValueError("Checkpoint could not be loaded as a safe Plex checkpoint") from exc
    if not isinstance(payload, dict):
        raise ValueError("Checkpoint root must be an object")
    if payload.get("formatVersion") != CHECKPOINT_FORMAT_VERSION:
        raise ValueError("Unsupported checkpoint format version")
    if payload.get("modelFamily") != "plex-from-scratch":
        raise ValueError("Checkpoint is not a Plex from-scratch checkpoint")
    config = ModelConfig.from_dict(payload.get("modelConfig"))
    step = payload.get("step")
    if not isinstance(step, int) or step < 0:
        raise ValueError("Checkpoint step must be a non-negative integer")
    if not isinstance(payload.get("modelStateDict"), dict):
        raise ValueError("Checkpoint model state is missing")
    model = PlexLanguageModel(config).to(device)
    try:
        model.load_state_dict(payload["modelStateDict"], strict=True)
    except (KeyError, RuntimeError) as exc:
        raise ValueError("Checkpoint weights do not match the declared model configuration") from exc
    return model, payload


def restore_optimizer(optimizer: torch.optim.Optimizer, payload: dict[str, Any]) -> None:
    state = payload.get("optimizerStateDict")
    if not isinstance(state, dict):
        raise ValueError("Checkpoint does not contain optimizer state")
    try:
        optimizer.load_state_dict(state)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise ValueError("Checkpoint optimizer state is incompatible") from exc


def restore_random_states(
    payload: dict[str, Any],
    sampling_rng: random.Random,
    device: torch.device,
) -> None:
    sampling_state = payload.get("samplingRngState")
    cpu_state = payload.get("torchCpuRngState")
    if not isinstance(sampling_state, tuple) or not isinstance(cpu_state, torch.Tensor):
        raise ValueError("Checkpoint does not contain resumable random-generator state")
    try:
        sampling_rng.setstate(sampling_state)
        torch.set_rng_state(cpu_state.cpu())
        if device.type == "cuda":
            cuda_states = payload.get("torchCudaRngStates")
            if not isinstance(cuda_states, list) or len(cuda_states) != torch.cuda.device_count():
                raise ValueError("Checkpoint CUDA random state does not match the available devices")
            torch.cuda.set_rng_state_all(cuda_states)
    except (TypeError, RuntimeError) as exc:
        raise ValueError("Checkpoint random-generator state is incompatible") from exc
