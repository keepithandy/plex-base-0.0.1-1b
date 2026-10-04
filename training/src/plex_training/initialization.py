"""Create an auditable, randomly initialized step-zero Plex checkpoint."""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import random
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .artifacts import artifact_bytes, enforce_storage_limit
from .checkpoint import save_checkpoint
from .config import DEFAULT_CONFIG
from .model import INITIALIZATION_SCHEME, INITIALIZATION_SCHEME_VERSION, PlexLanguageModel, parameter_count
from .tokenizer import CODEC, PlexTokenizer, sha256_file


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _tokenizer_metadata(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    settings_path = directory / "tokenizer-config.json"
    bundle_manifest_path = directory / "manifest.json"
    if settings_path.is_symlink() or bundle_manifest_path.is_symlink():
        raise ValueError("Tokenizer metadata must be regular files")
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict) or not isinstance(bundle, dict):
        raise ValueError("Tokenizer settings and manifest must be JSON objects")
    PlexTokenizer.load(directory)
    actual_vocab = settings.get("actualVocabularySize")
    if (settings.get("codec") != CODEC or type(actual_vocab) is not int
            or actual_vocab < 260 or actual_vocab > DEFAULT_CONFIG.vocab_size
            or settings.get("modelVocabularyCapacity") != DEFAULT_CONFIG.vocab_size
            or bundle.get("codec") != CODEC
            or bundle.get("tokenizerSha256") != settings.get("tokenizerSha256")):
        raise ValueError("Tokenizer artifact is incompatible with the P1-12 model vocabulary")
    model_config = json.loads((directory / "model-config.json").read_text(encoding="utf-8"))
    if model_config != DEFAULT_CONFIG.to_dict():
        raise ValueError("Tokenizer model configuration does not match the current Plex model")
    return settings, {
        "codec": CODEC,
        "actualVocabularySize": actual_vocab,
        "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
        "tokenizerSha256": settings["tokenizerSha256"],
        "bundleManifestSha256": sha256_file(bundle_manifest_path),
        "modelConfigSha256": sha256_file(directory / "model-config.json"),
    }


def _weights_sha256(model: PlexLanguageModel) -> str:
    # PyTorch writes the raw tensor storage in native code. Converting 110 MiB
    # storage objects to Python bytes one element at a time is prohibitively slow.
    buffer = io.BytesIO()
    state = {name: value.detach().cpu().contiguous()
             for name, value in sorted(model.state_dict().items())}
    torch.save(state, buffer, _use_new_zipfile_serialization=False)
    return hashlib.sha256(buffer.getbuffer()).hexdigest()


def initialize_model(tokenizer_dir: Path, output_dir: Path, *, seed: int = 1337,
                     artifact_root: Path, storage_limit_bytes: int = 200 * 1024**3) -> dict[str, Any]:
    if type(seed) is not int or seed < 0 or seed > 2**63 - 1:
        raise ValueError("seed must be an integer from 0 through 2^63-1")
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    artifact_root = artifact_root.resolve()
    output_dir = output_dir.resolve(strict=False)
    output_dir.relative_to(artifact_root)
    tokenizer_dir = tokenizer_dir.resolve(strict=True)
    if output_dir == tokenizer_dir or tokenizer_dir in output_dir.parents or output_dir in tokenizer_dir.parents:
        raise ValueError("Initialization output must be separate from the tokenizer bundle")
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing initialization")
    tokenizer_settings, tokenizer_record = _tokenizer_metadata(tokenizer_dir)

    # CPU initialization gives the seed one consistent meaning independent of CUDA availability.
    random.seed(seed)
    previous_threads = torch.get_num_threads()
    try:
        # Keep tiny per-layer initialization ops from paying for a large host
        # thread pool; training thread settings are a separate experiment.
        torch.set_num_threads(1)
        torch.random.default_generator.manual_seed(seed)
        model = PlexLanguageModel(DEFAULT_CONFIG).cpu()
        weights_hash = _weights_sha256(model)
    finally:
        torch.set_num_threads(previous_threads)
    count = parameter_count(model)
    if count != DEFAULT_CONFIG.parameter_count():
        raise RuntimeError("Model parameter count differs from its declared configuration")

    record: dict[str, Any] = {
        "schemaVersion": 1,
        "purpose": "fresh-random-initialization",
        "modelFamily": "plex-from-scratch",
        "initializationSchemeVersion": INITIALIZATION_SCHEME_VERSION,
        "initializationScheme": INITIALIZATION_SCHEME,
        "seed": seed,
        "seededGenerator": "PyTorch global CPU generator",
        "initializationDevice": "cpu",
        "initializationThreadCount": 1,
        "deviceIndependentTraining": "Training may later select CPU or CUDA; this records the CPU-created initial tensors.",
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "torchVersion": str(torch.__version__),
        "modelConfig": DEFAULT_CONFIG.to_dict(),
        "parameterCount": count,
        "actualTokenizerVocabularySize": tokenizer_settings["actualVocabularySize"],
        "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
        "tokenizer": tokenizer_record,
        "pretrainedCheckpointLoaded": False,
        "pretrainedModelWeightsLoaded": False,
        "initialModelWeightsSha256": weights_hash,
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-initialization-", dir=output_dir.parent)).resolve()
    staging.relative_to(output_dir.parent.resolve())
    try:
        enforce_storage_limit(artifact_root, limit_bytes=storage_limit_bytes)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(0.9, 0.95), weight_decay=0.1)
        checkpoint_info = save_checkpoint(
            model, optimizer, step=0, seed=seed, codec=CODEC,
            sampling_rng=random.Random(seed), device=torch.device("cpu"),
            destination=staging / "initialization.pt", artifact_root=artifact_root,
            initialization_record=record, tokenizer_record=tokenizer_record,
        )
        _write_json(staging / "initialization.json", record)
        checkpoint_sha = sha256_file(staging / "initialization.pt")
        record["checkpointSha256"] = checkpoint_sha
        # The checkpoint embeds the pre-checkpoint portion of this record; the sidecar
        # adds its own file hash without introducing a circular hash dependency.
        _write_json(staging / "result.json", {
            "schemaVersion": 1,
            "checkpoint": checkpoint_info,
            "checkpointSha256": checkpoint_sha,
            "initializationRecordSha256": sha256_file(staging / "initialization.json"),
            "initialModelWeightsSha256": weights_hash,
            "tokenizer": tokenizer_record,
        })
        enforce_storage_limit(artifact_root, limit_bytes=storage_limit_bytes)
        os.rename(staging, output_dir)
        return {
            "outputDirectory": str(output_dir.relative_to(artifact_root)),
            "checkpoint": str((output_dir / "initialization.pt").relative_to(artifact_root)),
            "checkpointBytes": checkpoint_info["bytes"],
            "checkpointSha256": checkpoint_sha,
            "initialModelWeightsSha256": weights_hash,
            "seed": seed,
            "initializationSchemeVersion": INITIALIZATION_SCHEME_VERSION,
            "parameterCount": count,
            "actualTokenizerVocabularySize": tokenizer_settings["actualVocabularySize"],
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "pretrainedCheckpointLoaded": False,
            "storageUsedBytes": artifact_bytes(artifact_root),
            "storageLimitBytes": storage_limit_bytes,
        }
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
