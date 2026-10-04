"""Bounded P1-17 overfit check on one real training record."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from torch.nn import functional as F

from .artifacts import artifact_bytes, enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, restore_optimizer, save_checkpoint
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .tokenizer import CODEC, PlexTokenizer, sha256_file
from .telemetry import select_device


def _loss_and_accuracy(model: torch.nn.Module, sample: torch.Tensor, actual_vocab: int,
                       device: torch.device) -> tuple[float, float]:
    model.eval()
    with torch.no_grad():
        inputs = sample[:-1].unsqueeze(0).to(device)
        targets = sample[1:].unsqueeze(0).to(device)
        logits, _ = model(inputs)
        logits = logits[:, :, :actual_vocab]
        loss = F.cross_entropy(logits.reshape(-1, actual_vocab), targets.reshape(-1))
        accuracy = (logits.argmax(dim=-1) == targets).float().mean()
    return float(loss.item()), float(accuracy.item())


def _greedy_completion(model: torch.nn.Module, sample: torch.Tensor, actual_vocab: int,
                       device: torch.device, prompt_tokens: int = 2) -> list[int]:
    model.eval()
    generated = sample[:prompt_tokens].tolist()
    with torch.no_grad():
        while len(generated) < len(sample):
            context = torch.tensor(generated[-model.config.context_length:], dtype=torch.long,
                                   device=device).unsqueeze(0)
            logits, _ = model(context)
            next_logits = logits[0, -1, :actual_vocab].clone()
            # PAD, UNK, and BOS are reserved controls, never plain-text output.
            next_logits[:3] = -torch.inf
            generated.append(int(next_logits.argmax().item()))
    return generated


def run_learning_check(*, initialization_path: Path, tokenizer_dir: Path,
                       training_tokens: Path, training_index: Path,
                       output_dir: Path, artifact_root: Path,
                       steps: int = 250, sample_tokens: int = 16,
                       minutes: float = 10.0, device_name: str = "auto",
                       storage_limit_bytes: int = 200 * 1024**3) -> dict[str, Any]:
    if type(steps) is not int or not 1 <= steps <= 500:
        raise ValueError("P1-17 steps must be from 1 through 500")
    if type(sample_tokens) is not int or not 3 <= sample_tokens <= 64:
        raise ValueError("sample-tokens must be from 3 through 64")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P1-17 duration must be greater than 0 and no more than 10 minutes")
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    artifact_root = artifact_root.resolve()
    output_dir = path_within_root(output_dir, artifact_root)
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing P1-17 run directory")
    tokenizer_dir = tokenizer_dir.resolve(strict=True)
    settings_path = tokenizer_dir / "tokenizer-config.json"
    tokenizer = PlexTokenizer.load(tokenizer_dir)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    actual_vocab = int(settings["actualVocabularySize"])
    tokenizer_record = {
        "codec": CODEC,
        "actualVocabularySize": actual_vocab,
        "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
        "tokenizerSha256": settings["tokenizerSha256"],
        "bundleManifestSha256": sha256_file(tokenizer_dir / "manifest.json"),
        "modelConfigSha256": sha256_file(tokenizer_dir / "model-config.json"),
    }
    try:
        model, initial_payload = read_checkpoint(initialization_path, torch.device("cpu"))
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("P1-17 requires a valid P1-16 initialization checkpoint") from exc
    initialization_record = initial_payload.get("initializationRecord")
    if (initial_payload.get("step") != 0 or initial_payload.get("codec") != CODEC
            or initial_payload.get("tokenizerRecord") != tokenizer_record
            or not isinstance(initialization_record, dict)
            or initialization_record.get("pretrainedCheckpointLoaded") is not False
            or model.config != DEFAULT_CONFIG):
        raise ValueError("P1-16 checkpoint is not tied to this tokenizer and model configuration")

    index_path = training_index.resolve(strict=True)
    if index_path.is_symlink() or index_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Training index must be a regular file no larger than 4 MiB")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index, list) or not index:
        raise ValueError("Training index is empty or invalid")
    sample_entry = next((entry for entry in index
                         if isinstance(entry, dict) and type(entry.get("tokenCount")) is int
                         and entry["tokenCount"] >= 4), None)
    if sample_entry is None:
        raise ValueError("No training record has enough tokens for a learning check")
    with TokenCorpus(training_tokens.resolve(strict=True)) as corpus:
        # The tokenizer bundle manifest next to the token file identifies BPE data.
        token_manifest_path = corpus.path.parent / "manifest.json"
        if (not token_manifest_path.is_file() or token_manifest_path.is_symlink()
                or token_manifest_path.stat().st_size > 1024 * 1024):
            raise ValueError("BPE token bundle manifest is missing or invalid")
        token_manifest = json.loads(token_manifest_path.read_text(encoding="utf-8"))
        train_manifest = token_manifest.get("train") if isinstance(token_manifest, dict) else None
        if (not isinstance(token_manifest, dict) or not isinstance(train_manifest, dict)
                or token_manifest.get("codec") != CODEC
                or token_manifest.get("tokenizerSha256") != tokenizer_record["tokenizerSha256"]
                or sha256_file(corpus.path) != train_manifest.get("sha256")):
            raise ValueError("Training tokens do not match the selected tokenizer")
        if corpus.path.name != train_manifest.get("path"):
            raise ValueError("P1-17 can only use the declared training token file")
        start, count = sample_entry.get("startToken"), sample_entry["tokenCount"]
        if type(start) is not int or start < 0 or start + count > corpus.token_count:
            raise ValueError("Training index points outside the training token file")
        record_ids = corpus._window(start, count).tolist()
        if not record_ids or record_ids[-1] != 3:
            raise ValueError("Indexed training record is missing its EOS boundary")
        text_token_ids = record_ids[:-1][:sample_tokens]
        if len(text_token_ids) < 3 or any(value < 4 or value >= actual_vocab for value in text_token_ids):
            raise ValueError("Selected record has too few ordinary tokens or invalid token IDs")
        sample = torch.tensor(text_token_ids, dtype=torch.long)

    sample_text = tokenizer.decode(text_token_ids)
    sample_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
    device = select_device(device_name)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(0.9, 0.95), weight_decay=0.1)
    restore_optimizer(optimizer, initial_payload)
    sampling_rng = random.Random(int(initial_payload["seed"]))
    try:
        sampling_rng.setstate(initial_payload["samplingRngState"])
        torch.set_rng_state(initial_payload["torchCpuRngState"].cpu())
    except (KeyError, TypeError, RuntimeError) as exc:
        raise ValueError("P1-16 checkpoint is missing reproducible random-generator state") from exc
    if device.type == "cuda":
        # P1-16 intentionally saves CPU-created initial weights, not host-specific
        # CUDA RNG states. Seed this training session's CUDA generator separately.
        torch.cuda.manual_seed_all(int(initial_payload["seed"]))

    initial_loss, initial_accuracy = _loss_and_accuracy(model, sample, actual_vocab, device)
    target = sample[1:].to(device).unsqueeze(0)
    inputs = sample[:-1].to(device).unsqueeze(0)
    model.train()
    started = time.perf_counter()
    deadline = started + minutes * 60
    losses: list[float] = []
    completed_steps = 0
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits, _ = model(inputs)
        loss = F.cross_entropy(logits[:, :, :actual_vocab].reshape(-1, actual_vocab), target.reshape(-1))
        if not torch.isfinite(loss):
            raise RuntimeError("P1-17 training loss became non-finite")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        completed_steps += 1
        losses.append(float(loss.detach().item()))
        if time.perf_counter() >= deadline:
            break

    elapsed = time.perf_counter() - started
    final_loss, final_accuracy = _loss_and_accuracy(model, sample, actual_vocab, device)
    generated_ids = _greedy_completion(model, sample, actual_vocab, device)
    reproduced = generated_ids == text_token_ids
    run_seed = int(initial_payload["seed"])
    checkpoint_path = output_dir / "tiny-learning.pt"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = save_checkpoint(
        model, optimizer, step=completed_steps, seed=run_seed, codec=CODEC,
        sampling_rng=sampling_rng, device=device, destination=checkpoint_path,
        artifact_root=artifact_root,
        initialization_record=initialization_record, tokenizer_record=tokenizer_record,
    )
    report = {
        "schemaVersion": 1,
        "milestone": "P1-17 tiny real-text learning check",
        "completedAtUtc": datetime.now(timezone.utc).isoformat(),
        "initializationCheckpointSha256": sha256_file(initialization_path),
        "initializationSeed": run_seed,
        "cudaTrainingGeneratorSeed": run_seed if device.type == "cuda" else None,
        "trainingSteps": completed_steps,
        "requestedSteps": steps,
        "elapsedSeconds": elapsed,
        "device": str(device),
        "trainingRecordId": sample_entry.get("recordId"),
        "sampleTextSha256": sample_hash,
        "sampleTokenCount": len(sample),
        "promptTokenCount": min(2, len(sample) - 1),
        "initialLoss": initial_loss,
        "finalLoss": final_loss,
        "initialTokenAccuracy": initial_accuracy,
        "finalTokenAccuracy": final_accuracy,
        "lossDecreased": final_loss < initial_loss,
        "greedySampleReproduced": reproduced,
        "generatedTokenIds": generated_ids,
        "expectedTokenIds": text_token_ids,
        "tokenizer": tokenizer_record,
        "checkpoint": result,
        "checkpointSha256": sha256_file(checkpoint_path),
        "interpretation": "One-record overfit plumbing check; this is not a coding ability evaluation.",
    }
    report_path = output_dir / "learning-report.json"
    with report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
    enforce_storage_limit(artifact_root, limit_bytes=storage_limit_bytes)
    report["outputDirectory"] = str(output_dir.relative_to(artifact_root))
    report["storageUsedBytes"] = artifact_bytes(artifact_root)
    report["storageLimitBytes"] = storage_limit_bytes
    return report
