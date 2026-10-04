"""Bounded training, evaluation, generation, and smoke-test operations."""

from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import torch
from torch import Tensor

from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, restore_optimizer, restore_random_states, save_checkpoint
from .config import DEFAULT_CONFIG, ModelConfig
from .data import BYTE_VOCABULARY_SIZE, SyntheticTokenSource, TokenCorpus
from .limits import MAX_PILOT_MINUTES, MAX_SMOKE_MINUTES
from .model import PlexLanguageModel, parameter_count
from .telemetry import environment_report, peak_gpu_memory, reset_peak_gpu_memory, select_device

DEFAULT_ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "artifacts"
ADAMW_LEARNING_RATE = 3e-4
ADAMW_BETAS = (0.9, 0.95)
ADAMW_WEIGHT_DECAY = 0.1
ADAMW_EPSILON = 1e-8
SCHEDULE_KIND = "constant-v1"


class BatchSource(Protocol):
    token_count: int

    def sample_batch(
        self, rng: random.Random, batch_size: int, sequence_length: int
    ) -> tuple[Tensor, Tensor]: ...


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _write_event(metrics_path: Path, artifact_root: Path, event: dict[str, Any]) -> None:
    metrics_path = path_within_root(metrics_path, artifact_root)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    enforce_storage_limit(artifact_root, additional_bytes=2048)
    with metrics_path.open("a", encoding="utf-8", newline="\n") as stream:
        json.dump(event, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()


def _training_step(
    model: PlexLanguageModel,
    optimizer: torch.optim.Optimizer,
    source: BatchSource,
    rng: random.Random,
    device: torch.device,
    *,
    micro_batch: int,
    accumulation_steps: int,
    loss_vocabulary_size: int | None = None,
) -> float:
    optimizer.zero_grad(set_to_none=True)
    total_loss = 0.0
    for _ in range(accumulation_steps):
        inputs, targets = source.sample_batch(
            rng,
            batch_size=micro_batch,
            sequence_length=model.config.context_length,
        )
        _, loss = model(
            inputs.to(device), targets.to(device), loss_vocabulary_size=loss_vocabulary_size
        )
        if loss is None:
            raise RuntimeError("Model did not produce a training loss")
        (loss / accumulation_steps).backward()
        total_loss += float(loss.detach().item())
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    return total_loss / accumulation_steps


def _validation_loss(
    model: PlexLanguageModel,
    validation: TokenCorpus,
    device: torch.device,
    *,
    maximum_batches: int = 16,
    loss_vocabulary_size: int | None = None,
) -> float:
    model.eval()
    weighted_loss = 0.0
    token_count = 0
    with torch.no_grad():
        batches = validation.sequential_batches(
            model.config.context_length, maximum_batches
        )
        for inputs, targets in batches:
            _, loss = model(
                inputs.to(device), targets.to(device), loss_vocabulary_size=loss_vocabulary_size
            )
            if loss is None:
                raise RuntimeError("Model did not produce a validation loss")
            amount = int(targets.numel())
            weighted_loss += float(loss.item()) * amount
            token_count += amount
    model.train()
    if token_count == 0:
        raise ValueError("Validation corpus has no complete context windows")
    return weighted_loss / token_count


def _bpe_training_settings(
    config: ModelConfig, micro_batch: int, accumulation_steps: int,
    loss_vocabulary_size: int, validation_maximum_batches: int,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "codec": "plex-byte-bpe-v1",
        "modelConfig": config.to_dict(),
        "microBatch": micro_batch,
        "gradientAccumulation": accumulation_steps,
        "lossVocabularySize": loss_vocabulary_size,
        "validationMaximumBatches": validation_maximum_batches,
        "optimizer": {
            "kind": "AdamW", "learningRate": ADAMW_LEARNING_RATE,
            "betas": list(ADAMW_BETAS), "weightDecay": ADAMW_WEIGHT_DECAY,
            "epsilon": ADAMW_EPSILON,
        },
        "learningRateSchedule": SCHEDULE_KIND,
    }


def _schedule_state(step: int) -> dict[str, Any]:
    return {"kind": SCHEDULE_KIND, "step": step, "learningRate": ADAMW_LEARNING_RATE}


def _verify_bpe_resume_policy(
    payload: dict[str, Any], optimizer: torch.optim.Optimizer,
    settings: dict[str, Any],
) -> int:
    """Validate explicit settings, or the known fixed-policy P1-18 checkpoint."""
    step = int(payload["step"])
    if step == 0:
        return 0
    saved_settings = payload.get("trainingSettings")
    saved_schedule = payload.get("scheduleState")
    if saved_settings is None:
        # P1-18 checkpoints predate settings metadata. The owner's pilot used
        # these defaults; reject changes we cannot prove are a continuation.
        if (settings["microBatch"] != 1 or settings["gradientAccumulation"] != 16
                or settings["validationMaximumBatches"] != 100):
            raise ValueError("Legacy P1-18 checkpoint requires its original batch and validation settings")
        if saved_schedule is not None:
            raise ValueError("Legacy checkpoint has inconsistent schedule metadata")
    elif saved_settings != settings or saved_schedule != _schedule_state(step):
        raise ValueError("Resume checkpoint training settings or learning-rate schedule do not match")
    groups = optimizer.param_groups
    if (len(groups) != 1 or groups[0].get("lr") != ADAMW_LEARNING_RATE
            or tuple(groups[0].get("betas", ())) != ADAMW_BETAS
            or groups[0].get("weight_decay") != ADAMW_WEIGHT_DECAY
            or groups[0].get("eps") != ADAMW_EPSILON):
        raise ValueError("Resume checkpoint optimizer policy does not match")
    positions_per_step = (settings["microBatch"] * settings["gradientAccumulation"]
                          * settings["modelConfig"]["context_length"])
    expected_positions = step * positions_per_step
    saved_positions = payload.get("tokensProcessedTotal")
    if saved_positions is not None and saved_positions != expected_positions:
        raise ValueError("Resume checkpoint token progress does not match its settings")
    return expected_positions


def run_training(
    *,
    train_source: BatchSource,
    validation: TokenCorpus | None,
    device_name: str,
    minutes: float,
    step_limit: int | None,
    output_checkpoint: Path,
    metrics_path: Path,
    artifact_root: Path,
    seed: int = 1337,
    micro_batch: int = 1,
    accumulation_steps: int = 16,
    checkpoint_interval_minutes: float = 5.0,
    resume_from: Path | None = None,
    config: ModelConfig = DEFAULT_CONFIG,
    allow_tiny_config: bool = False,
    codec: str = "byte-v1",
    tokenizer_record: dict[str, Any] | None = None,
    dataset_record: dict[str, Any] | None = None,
    loss_vocabulary_size: int | None = None,
    validation_maximum_batches: int = 16,
) -> dict[str, Any]:
    if codec not in {"byte-v1", "plex-byte-bpe-v1"}:
        raise ValueError("Unsupported training codec")
    if codec == "byte-v1":
        for source in (train_source, validation):
            if isinstance(source, TokenCorpus):
                source.require_byte_codec()
        if tokenizer_record is not None or dataset_record is not None or loss_vocabulary_size is not None:
            raise ValueError("byte-v1 runs cannot claim a Plex BPE tokenizer or dataset")
    else:
        if (not isinstance(train_source, TokenCorpus) or not isinstance(validation, TokenCorpus)
                or not isinstance(tokenizer_record, dict) or not isinstance(dataset_record, dict)
                or type(loss_vocabulary_size) is not int
                or tokenizer_record.get("actualVocabularySize") != loss_vocabulary_size
                or tokenizer_record.get("codec") != codec):
            raise ValueError("BPE training needs separate verified corpora and tokenizer/dataset identities")
    if validation_maximum_batches <= 0:
        raise ValueError("validation batch limit must be positive")
    if not math.isfinite(minutes) or minutes <= 0:
        raise ValueError("minutes must be a positive finite number")
    if minutes > MAX_PILOT_MINUTES:
        raise ValueError("Training is capped at the two-hour pilot until the P1-19 gate passes")
    if step_limit is not None and step_limit <= 0:
        raise ValueError("steps must be positive")
    if micro_batch <= 0 or accumulation_steps <= 0:
        raise ValueError("batch and accumulation settings must be positive")
    if not math.isfinite(checkpoint_interval_minutes) or checkpoint_interval_minutes <= 0:
        raise ValueError("checkpoint interval must be a positive finite number")
    if config != DEFAULT_CONFIG and not allow_tiny_config:
        raise ValueError("Non-default model configurations are only allowed in tests")

    training_settings = (
        _bpe_training_settings(config, micro_batch, accumulation_steps,
                               loss_vocabulary_size, validation_maximum_batches)
        if codec != "byte-v1" else None
    )

    artifact_root = artifact_root.resolve()
    output_checkpoint = path_within_root(output_checkpoint, artifact_root)
    metrics_path = path_within_root(metrics_path, artifact_root)
    if resume_from is None and (output_checkpoint.exists() or metrics_path.exists()):
        raise FileExistsError("Run outputs already exist; choose a fresh path or resume explicitly")
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    seed_everything(seed)
    rng = random.Random(seed)
    device = select_device(device_name)
    start_positions = 0
    if resume_from is None:
        model = PlexLanguageModel(config).to(device)
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=ADAMW_LEARNING_RATE,
            betas=ADAMW_BETAS,
            weight_decay=ADAMW_WEIGHT_DECAY,
            eps=ADAMW_EPSILON,
        )
        start_step = 0
    else:
        model, payload = read_checkpoint(resume_from, device)
        if model.config != config:
            if not allow_tiny_config or config != model.config:
                raise ValueError("Resume checkpoint configuration does not match this run")
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=ADAMW_LEARNING_RATE,
            betas=ADAMW_BETAS,
            weight_decay=ADAMW_WEIGHT_DECAY,
            eps=ADAMW_EPSILON,
        )
        restore_optimizer(optimizer, payload)
        if payload.get("codec") != codec:
            raise ValueError("Starting checkpoint codec does not match this run")
        if codec != "byte-v1":
            if (payload.get("step") != 0
                    and bool(payload.get("torchCudaRngStates")) != (device.type == "cuda")):
                raise ValueError("BPE resume must use the checkpoint's training device type")
            if payload.get("seed") != seed:
                raise ValueError("Starting checkpoint seed does not match this run")
            if payload.get("tokenizerRecord") != tokenizer_record:
                raise ValueError("Starting checkpoint tokenizer does not match this run")
            if payload.get("step") != 0 and payload.get("datasetRecord") != dataset_record:
                raise ValueError("Starting checkpoint dataset does not match this run")
            start_positions = _verify_bpe_resume_policy(payload, optimizer, training_settings)
        if (codec != "byte-v1" and payload.get("step") == 0 and device.type == "cuda"
                and payload.get("torchCudaRngStates") == []):
            restore_random_states(payload, rng, torch.device("cpu"))
            torch.cuda.manual_seed_all(seed)
        else:
            restore_random_states(payload, rng, device)
        start_step = int(payload.get("step", 0))
        initialization_record = payload.get("initializationRecord")
    if resume_from is None:
        initialization_record = None

    actual_parameters = parameter_count(model)
    if config == DEFAULT_CONFIG and actual_parameters != 27_566_080:
        raise RuntimeError(f"Model parameter count mismatch: expected 27566080, got {actual_parameters}")
    model.train()
    reset_peak_gpu_memory(device)
    started = time.perf_counter()
    deadline = started + minutes * 60.0
    last_checkpoint = started
    step = start_step
    losses: list[float] = []
    event = {
        "event": "run_started",
        "startedAtUtc": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "parameterCount": actual_parameters,
        "device": str(device),
        "environment": environment_report(device),
        "seed": seed,
        "resumedFromStep": start_step,
        "timeLimitSeconds": int(minutes * 60),
        "datasetTokens": train_source.token_count,
        "codec": codec,
        "tokenizerRecord": tokenizer_record,
        "datasetRecord": dataset_record,
        "lossVocabularySize": loss_vocabulary_size,
        "validationMaximumBatches": validation_maximum_batches,
        "trainingSettings": training_settings,
        "scheduleState": _schedule_state(start_step) if training_settings is not None else None,
        "tokensProcessedTotal": start_positions if training_settings is not None else None,
    }
    if validation is not None:
        event["validationLossBefore"] = _validation_loss(
            model, validation, device, maximum_batches=validation_maximum_batches,
            loss_vocabulary_size=loss_vocabulary_size,
        )
    _write_event(metrics_path, artifact_root, event)

    interrupted = False
    try:
        while time.perf_counter() < deadline and (step_limit is None or step - start_step < step_limit):
            loss = _training_step(
                model,
                optimizer,
                train_source,
                rng,
                device,
                micro_batch=micro_batch,
                accumulation_steps=accumulation_steps,
                loss_vocabulary_size=loss_vocabulary_size,
            )
            step += 1
            losses.append(loss)
            elapsed = time.perf_counter() - started
            if len(losses) == 1 or step % 10 == 0:
                tokens_seen = (step - start_step) * micro_batch * accumulation_steps * config.context_length
                _write_event(metrics_path, artifact_root, {
                    "event": "training_progress",
                    "step": step,
                    "loss": loss,
                    "elapsedSeconds": elapsed,
                    "tokensPerSecond": tokens_seen / max(elapsed, 1e-9),
                    "peakGpuMemory": peak_gpu_memory(device),
                })
            now = time.perf_counter()
            if now - last_checkpoint >= checkpoint_interval_minutes * 60.0:
                saved = save_checkpoint(
                    model,
                    optimizer,
                    step=step,
                    seed=seed,
                    codec=codec,
                    sampling_rng=rng,
                    device=device,
                    destination=output_checkpoint,
                    artifact_root=artifact_root,
                    overwrite=output_checkpoint.exists(),
                    initialization_record=initialization_record,
                    tokenizer_record=tokenizer_record,
                    dataset_record=dataset_record,
                    training_settings=training_settings,
                    schedule_state=_schedule_state(step) if training_settings is not None else None,
                    tokens_processed_total=(start_positions + (step - start_step) * micro_batch
                                            * accumulation_steps * config.context_length)
                    if training_settings is not None else None,
                )
                _write_event(metrics_path, artifact_root, {"event": "checkpoint_saved", **saved})
                last_checkpoint = now
    except KeyboardInterrupt:
        interrupted = True

    elapsed = time.perf_counter() - started
    validation_loss_after = (
        _validation_loss(
            model, validation, device, maximum_batches=validation_maximum_batches,
            loss_vocabulary_size=loss_vocabulary_size,
        ) if validation is not None else None
    )
    final_checkpoint = save_checkpoint(
        model,
        optimizer,
        step=step,
        seed=seed,
        codec=codec,
        sampling_rng=rng,
        device=device,
        destination=output_checkpoint,
        artifact_root=artifact_root,
        overwrite=output_checkpoint.exists(),
        initialization_record=initialization_record,
        tokenizer_record=tokenizer_record,
        dataset_record=dataset_record,
        training_settings=training_settings,
        schedule_state=_schedule_state(step) if training_settings is not None else None,
        tokens_processed_total=(start_positions + (step - start_step) * micro_batch
                                * accumulation_steps * config.context_length)
        if training_settings is not None else None,
    )
    summary = {
        "event": "run_finished",
        "step": step,
        "stepsThisRun": step - start_step,
        "elapsedSeconds": elapsed,
        "meanRecentLoss": sum(losses[-20:]) / len(losses[-20:]) if losses else None,
        "tokensPerSecond": ((step - start_step) * micro_batch * accumulation_steps * config.context_length)
        / max(elapsed, 1e-9),
        "peakGpuMemory": peak_gpu_memory(device),
        "processPeakWorkingSetBytes": environment_report(device)["processPeakWorkingSetBytes"],
        "checkpoint": final_checkpoint,
        "validationPending": validation is None,
        "validationLossAfter": validation_loss_after,
        "validationLossBefore": event.get("validationLossBefore"),
        "validationTokens": validation.token_count if validation is not None else None,
        "codec": codec,
        "tokensProcessedThisRun": (step - start_step) * micro_batch * accumulation_steps * config.context_length,
        "tokensProcessedTotal": start_positions + (step - start_step) * micro_batch * accumulation_steps * config.context_length,
        "trainingSettings": training_settings,
        "scheduleState": _schedule_state(step) if training_settings is not None else None,
        "tokenizerRecord": tokenizer_record,
        "datasetRecord": dataset_record,
        "interrupted": interrupted,
    }
    _write_event(metrics_path, artifact_root, summary)
    return summary


def evaluate_checkpoint(
    checkpoint_path: Path,
    token_path: Path,
    *,
    device_name: str = "auto",
    maximum_batches: int = 100,
    codec: str = "byte-v1",
    tokenizer_record: dict[str, Any] | None = None,
    dataset_record: dict[str, Any] | None = None,
    loss_vocabulary_size: int | None = None,
) -> dict[str, Any]:
    if maximum_batches <= 0:
        raise ValueError("maximum_batches must be positive")
    if codec == "byte-v1":
        with TokenCorpus(token_path) as corpus:
            corpus.require_byte_codec()
        if tokenizer_record is not None or dataset_record is not None or loss_vocabulary_size is not None:
            raise ValueError("byte-v1 evaluation cannot claim a Plex BPE tokenizer or dataset")
    elif (codec != "plex-byte-bpe-v1" or not isinstance(tokenizer_record, dict)
          or not isinstance(dataset_record, dict) or type(loss_vocabulary_size) is not int):
        raise ValueError("BPE evaluation requires verified tokenizer and dataset identities")
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint_path, device)
    if (payload.get("codec") != codec or
            (codec != "byte-v1" and (
                payload.get("tokenizerRecord") != tokenizer_record
                or payload.get("datasetRecord") != dataset_record
                or tokenizer_record.get("actualVocabularySize") != loss_vocabulary_size))):
        raise ValueError("Checkpoint codec, tokenizer, or dataset does not match the evaluation corpus")
    model.eval()
    weighted_loss = 0.0
    token_count = 0
    with TokenCorpus(token_path) as corpus, torch.no_grad():
        for inputs, targets in corpus.sequential_batches(
            model.config.context_length, maximum_batches
        ):
            _, loss = model(
                inputs.to(device), targets.to(device), loss_vocabulary_size=loss_vocabulary_size
            )
            if loss is None:
                raise RuntimeError("Model did not produce an evaluation loss")
            amount = int(targets.numel())
            weighted_loss += float(loss.item()) * amount
            token_count += amount
    return {
        "checkpointStep": int(payload.get("step", 0)),
        "batches": math.ceil(token_count / model.config.context_length),
        "tokens": token_count,
        "meanLoss": weighted_loss / token_count,
        "device": str(device),
        "codec": codec,
    }


def generate_bytes(
    checkpoint_path: Path,
    prompt: str,
    *,
    device_name: str = "auto",
    max_new_tokens: int = 128,
    temperature: float = 0.8,
    seed: int = 1337,
) -> str:
    if not 1 <= max_new_tokens <= 512:
        raise ValueError("max_new_tokens must be in the range 1..512")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be a positive finite number")
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint_path, device)
    if payload.get("codec") != "byte-v1":
        raise ValueError("This runner can generate text only from byte-v1 checkpoints")
    seed_everything(seed)
    model.eval()
    prompt_ids = list(prompt.encode("utf-8")) or [10]
    context = torch.tensor(
        prompt_ids[-model.config.context_length :], dtype=torch.long, device=device
    )[None, :]
    generator = torch.Generator(device=device)
    generator.manual_seed(seed)
    generated: list[int] = []
    with torch.no_grad():
        for _ in range(max_new_tokens):
            visible = context[:, -model.config.context_length :]
            logits, _ = model(visible)
            scores = logits[0, -1, :BYTE_VOCABULARY_SIZE] / temperature
            next_id = int(torch.multinomial(torch.softmax(scores, dim=-1), 1, generator=generator).item())
            generated.append(next_id)
            context = torch.cat(
                [context, torch.tensor([[next_id]], dtype=torch.long, device=device)], dim=1
            )[:, -model.config.context_length :]
    return bytes(prompt_ids + generated).decode("utf-8", errors="replace")


def default_run_directory(kind: str, artifact_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return artifact_root / kind / timestamp
