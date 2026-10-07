"""Verified, bounded BPE training and held-out evaluation for P1-18."""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
from array import array
from pathlib import Path
from typing import Any

import torch

from .answer_weighting import AnswerWeightedTokenCorpus
from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, restore_optimizer
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .record_sampling import CompleteRecordTokenCorpus, RecordStartTokenCorpus
from .runner import _bpe_training_settings, _verify_bpe_resume_policy, evaluate_checkpoint, run_training
from .tokenizer import CODEC, PlexTokenizer, sha256_file

STORAGE_LIMIT_BYTES = 200 * 1024**3


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Pilot metadata file is missing, linked, or too large: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Pilot metadata must be a JSON object: {path.name}")
    return value


def _validate_token_file(path: Path, expected: dict[str, Any], actual_vocab: int) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Pilot token files must be regular files")
    if sha256_file(path) != expected.get("sha256"):
        raise ValueError(f"{path.name} does not match the reviewed tokenizer bundle hash")
    byte_count = path.stat().st_size
    if byte_count % 2 or byte_count // 2 != expected.get("tokenCount") or byte_count < 1026:
        raise ValueError(f"{path.name} has an invalid token count")
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            tokens = array("H")
            tokens.frombytes(chunk)
            if sys.byteorder != "little":
                tokens.byteswap()
            if min(tokens) < 3 or max(tokens) >= actual_vocab:
                raise ValueError(f"{path.name} contains reserved or out-of-vocabulary token IDs")


def inspect_pilot_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Pin the two reviewed, disjoint splits and the exact trained tokenizer."""
    root = bundle_dir.resolve(strict=True)
    settings = _json(root / "tokenizer-config.json")
    manifest_path = root / "manifest.json"
    manifest = _json(manifest_path)
    source_manifest_path = root / "source-dataset-manifest.json"
    source_manifest = _json(source_manifest_path)
    tokenizer = PlexTokenizer.load(root)
    actual_vocab = tokenizer.vocabulary_size
    model_config_path = root / "model-config.json"
    if (_json(model_config_path) != DEFAULT_CONFIG.to_dict()
            or sha256_file(model_config_path) != manifest.get("modelConfigSha256")):
        raise ValueError("Tokenizer bundle model configuration does not match P1-12")
    if (manifest.get("schemaVersion") != 1 or manifest.get("codec") != CODEC
            or manifest.get("tokenizerSha256") != settings.get("tokenizerSha256")
            or manifest.get("actualVocabularySize") != actual_vocab
            or manifest.get("modelVocabularyCapacity") != DEFAULT_CONFIG.vocab_size
            or settings.get("fitSplit") != "train" or settings.get("fitField") != "text"
            or sha256_file(source_manifest_path) != manifest.get("sourceDatasetManifestSha256")):
        raise ValueError("Tokenizer bundle metadata is incomplete or mismatched")
    summary = source_manifest.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Curated source summary is missing")
    split_info: dict[str, dict[str, Any]] = {}
    for split in ("train", "validation"):
        info = manifest.get(split)
        if not isinstance(info, dict) or info.get("path") != f"{split}.tokens.u16le":
            raise ValueError(f"Tokenizer {split} split is missing")
        if (type(info.get("records")) is not int or info["records"] <= 0
                or info["records"] != summary.get(f"{split}Records")
                or info.get("jsonlSha256") != summary.get(f"{split}JsonlSha256")):
            raise ValueError(f"Tokenizer {split} records do not match curated provenance")
        token_path = root / info["path"]
        _validate_token_file(token_path, info, actual_vocab)
        split_info[split] = info
    if (split_info["train"]["sha256"] == split_info["validation"]["sha256"]
            or split_info["train"]["jsonlSha256"] == split_info["validation"]["jsonlSha256"]):
        raise ValueError("Training and held-out validation splits must be distinct")
    tokenizer_record = {
        "codec": CODEC,
        "actualVocabularySize": actual_vocab,
        "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
        "tokenizerSha256": settings["tokenizerSha256"],
        "bundleManifestSha256": sha256_file(manifest_path),
        "modelConfigSha256": sha256_file(model_config_path),
    }
    dataset_record = {
        "sourceDatasetManifestSha256": manifest["sourceDatasetManifestSha256"],
        "trainJsonlSha256": split_info["train"]["jsonlSha256"],
        "validationJsonlSha256": split_info["validation"]["jsonlSha256"],
        "trainTokensSha256": split_info["train"]["sha256"],
        "validationTokensSha256": split_info["validation"]["sha256"],
        "trainTokenCount": split_info["train"]["tokenCount"],
        "validationTokenCount": split_info["validation"]["tokenCount"],
        "trainRecords": split_info["train"]["records"],
        "validationRecords": split_info["validation"]["records"],
    }
    return {
        "root": root,
        "trainPath": root / "train.tokens.u16le",
        "validationPath": root / "validation.tokens.u16le",
        "tokenizer": tokenizer_record,
        "dataset": dataset_record,
    }


def _initialization_seed(path: Path, tokenizer_record: dict[str, Any]) -> int:
    if path.is_symlink() or not path.is_file():
        raise ValueError("P1-16 initialization checkpoint must be a regular file")
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise ValueError("P1-16 initialization checkpoint could not be read safely") from exc
    if (not isinstance(payload, dict) or payload.get("modelFamily") != "plex-from-scratch"
            or payload.get("modelConfig") != DEFAULT_CONFIG.to_dict()
            or payload.get("step") != 0 or payload.get("codec") != CODEC
            or payload.get("tokenizerRecord") != tokenizer_record
            or payload.get("stageTransitionRecord") is not None
            or not isinstance(payload.get("optimizerStateDict"), dict)
            or not isinstance(payload.get("initializationRecord"), dict)
            or payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False
            or type(payload.get("seed")) is not int):
        raise ValueError("Starting checkpoint is not the matching P1-16 random initialization")
    return payload["seed"]


def run_pilot(*, bundle_dir: Path, initialization: Path, output_dir: Path,
              artifact_root: Path, minutes: float, steps: int | None = None,
              device_name: str = "auto", micro_batch: int = 1,
              gradient_accumulation: int = 16,
              checkpoint_every_minutes: float = 5.0,
              dataset_dir: Path | None = None, answer_weight: int = 1,
              sampling_policy: str = "random-window-v1") -> dict[str, Any]:
    if not math.isfinite(minutes) or not 0 < minutes <= 120:
        raise ValueError("P1-18 run duration must be greater than 0 and no more than 120 minutes")
    if steps is not None and (type(steps) is not int or steps <= 0):
        raise ValueError("steps must be positive")
    if micro_batch <= 0 or gradient_accumulation <= 0:
        raise ValueError("batch and accumulation settings must be positive")
    if type(answer_weight) is not int or answer_weight not in (1, 4):
        raise ValueError("answer weight must be 1 or the controlled value 4")
    if sampling_policy not in ("random-window-v1", "record-start-v1", "complete-record-v1"):
        raise ValueError("Unsupported pilot sampling policy")
    record_start = sampling_policy == "record-start-v1"
    complete_record = sampling_policy == "complete-record-v1"
    if (record_start or complete_record) and (answer_weight != 1 or minutes > 10 or steps is None or steps > 100):
        raise ValueError("Record sampling comparison requires ordinary loss, at most 100 steps and ten minutes")
    if (answer_weight == 4 or record_start or complete_record) != (dataset_dir is not None):
        raise ValueError("The controlled comparison requires its matching dataset directory")
    root = artifact_root.resolve()
    output_dir = path_within_root(output_dir, root)
    if output_dir.exists():
        raise FileExistsError("Pilot output directory already exists; choose a fresh path")
    bundle = inspect_pilot_bundle(bundle_dir)
    if dataset_dir is not None:
        if (not dataset_dir.is_dir() or dataset_dir.is_symlink()
                or sha256_file(dataset_dir / "manifest.json") != bundle["dataset"]["sourceDatasetManifestSha256"]):
            raise ValueError("Comparison dataset manifest differs from the tokenizer bundle")
    seed = _initialization_seed(initialization, bundle["tokenizer"])
    # Saving a replacement checkpoint briefly keeps both copies on disk.
    estimated_checkpoint = DEFAULT_CONFIG.parameter_count() * 12 + 1024 * 1024
    enforce_storage_limit(root, additional_bytes=2 * estimated_checkpoint + 1024 * 1024,
                          limit_bytes=STORAGE_LIMIT_BYTES)
    if answer_weight == 4:
        train_source = AnswerWeightedTokenCorpus(
            bundle["trainPath"], dataset_jsonl=dataset_dir / "train.jsonl",
            index_path=bundle["root"] / "train.index.json",
            tokenizer=PlexTokenizer.load(bundle["root"]),
            expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
            answer_weight=answer_weight,
        )
    elif record_start or complete_record:
        source_type = CompleteRecordTokenCorpus if complete_record else RecordStartTokenCorpus
        train_source = source_type(
            bundle["trainPath"], dataset_jsonl=dataset_dir / "train.jsonl",
            index_path=bundle["root"] / "train.index.json",
            tokenizer=PlexTokenizer.load(bundle["root"]),
            expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
        )
    else:
        train_source = TokenCorpus(bundle["trainPath"])
    with train_source as train, TokenCorpus(bundle["validationPath"]) as validation:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(exist_ok=False)
        result = run_training(
            train_source=train, validation=validation,
            device_name=device_name, minutes=minutes, step_limit=steps,
            output_checkpoint=output_dir / "pilot-checkpoint.pt",
            metrics_path=output_dir / "metrics.jsonl", artifact_root=root,
            seed=seed, micro_batch=micro_batch,
            accumulation_steps=gradient_accumulation,
            checkpoint_interval_minutes=checkpoint_every_minutes,
            resume_from=initialization, config=DEFAULT_CONFIG,
            codec=CODEC, tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
            answer_weight=answer_weight,
        )
    report = {
        "schemaVersion": 1,
        "milestone": "bounded real-corpus pilot",
        "runKind": "preflight" if steps is not None else "pilot",
        "requestedMinutes": minutes,
        "requestedSteps": steps,
        "answerObjective": result["trainingSettings"].get("answerObjective"),
        "samplingPolicy": sampling_policy,
        "samplingAudit": train_source.sampling_audit() if record_start or complete_record else None,
        "initializationCheckpointSha256": sha256_file(initialization),
        "tokenizer": bundle["tokenizer"],
        "dataset": bundle["dataset"],
        "checkpointSha256": sha256_file(output_dir / "pilot-checkpoint.pt"),
        "validationImproved": (
            result["validationLossAfter"] < result["validationLossBefore"]
            if result["validationLossAfter"] is not None else None
        ),
        "training": result,
    }
    report_path = output_dir / "pilot-report.json"
    with report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    enforce_storage_limit(root, limit_bytes=STORAGE_LIMIT_BYTES)
    return {"report": str(report_path.relative_to(root)), **report}


def resume_pilot(*, bundle_dir: Path, checkpoint_path: Path, output_dir: Path,
                 artifact_root: Path, minutes: float = 10.0, steps: int = 1,
                 device_name: str = "auto", micro_batch: int = 1,
                 gradient_accumulation: int = 16,
                 checkpoint_every_minutes: float = 5.0,
                 dataset_dir: Path | None = None) -> dict[str, Any]:
    """Make a short, isolated continuation without changing the pilot checkpoint."""
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P1-19 resume check must be greater than 0 and no more than 10 minutes")
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P1-19 resume check requires 1 through 100 additional steps")
    root = artifact_root.resolve()
    output_dir = path_within_root(output_dir, root)
    if output_dir.exists():
        raise FileExistsError("Resume output directory already exists; choose a fresh path")
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise ValueError("Resume checkpoint must be a regular file")
    checkpoint_path = checkpoint_path.resolve(strict=True)
    if output_dir in checkpoint_path.parents:
        raise ValueError("Resume output cannot contain its source checkpoint")
    bundle = inspect_pilot_bundle(bundle_dir)
    source_model, source_payload = read_checkpoint(checkpoint_path, torch.device("cpu"))
    if (source_model.config != DEFAULT_CONFIG or source_payload.get("codec") != CODEC
            or type(source_payload.get("step")) is not int or source_payload["step"] <= 0
            or type(source_payload.get("seed")) is not int
            or source_payload.get("tokenizerRecord") != bundle["tokenizer"]
            or source_payload.get("datasetRecord") != bundle["dataset"]
            or source_payload.get("stageTransitionRecord") is not None
            or not isinstance(source_payload.get("optimizerStateDict"), dict)
            or not isinstance(source_payload.get("initializationRecord"), dict)
            or source_payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False):
        raise ValueError("Resume source is not the matching scratch-trained Plex pilot checkpoint")
    source_step = source_payload["step"]
    seed = source_payload["seed"]
    source_settings = source_payload.get("trainingSettings")
    if source_settings is not None and not isinstance(source_settings, dict):
        raise ValueError("Resume training settings must be an object")
    policy = (source_settings or {}).get("samplingPolicy")
    if policy is not None and (not isinstance(policy, dict) or policy.get("kind") != "complete-record-v1"):
        raise ValueError("Resume supports ordinary packed or verified complete-record sampling only")
    complete_record = policy is not None
    if complete_record != (dataset_dir is not None):
        raise ValueError("Complete-record resume requires its matching built dataset directory")
    if dataset_dir is not None:
        if (not dataset_dir.is_dir() or dataset_dir.is_symlink()
                or sha256_file(dataset_dir / "manifest.json") != bundle["dataset"]["sourceDatasetManifestSha256"]):
            raise ValueError("Resume dataset manifest differs from the tokenizer bundle")

    def train_source(verified_bundle: dict[str, Any]) -> TokenCorpus:
        if not complete_record:
            return TokenCorpus(verified_bundle["trainPath"])
        return CompleteRecordTokenCorpus(
            verified_bundle["trainPath"], dataset_jsonl=dataset_dir / "train.jsonl",
            index_path=verified_bundle["root"] / "train.index.json",
            tokenizer=PlexTokenizer.load(verified_bundle["root"]),
            expected_jsonl_sha256=verified_bundle["dataset"]["trainJsonlSha256"],
        )

    # Reject incompatible data, sampler, batch, optimizer and progress before
    # reserving an output directory. No optimizer update is performed here.
    optimizer = torch.optim.AdamW(source_model.parameters())
    restore_optimizer(optimizer, source_payload)
    with train_source(bundle) as preflight:
        settings = _bpe_training_settings(
            DEFAULT_CONFIG, micro_batch, gradient_accumulation,
            bundle["tokenizer"]["actualVocabularySize"], 100,
            sampling_policy=getattr(preflight, "sampler_record", None),
        )
        source_positions = _verify_bpe_resume_policy(source_payload, optimizer, settings, preflight)
    del source_model, source_payload, optimizer
    source_hash = sha256_file(checkpoint_path)
    bundle_files = list(bundle["root"].rglob("*"))
    if (any(path.is_symlink() for path in bundle_files)
            or sum(path.stat().st_size for path in bundle_files if path.is_file()) > 16 * 1024**2):
        raise ValueError("Tokenizer bundle contains a link or exceeds the 16 MiB packaging limit")
    estimated_checkpoint = DEFAULT_CONFIG.parameter_count() * 12 + 1024 * 1024
    enforce_storage_limit(root, additional_bytes=2 * estimated_checkpoint + 16 * 1024**2,
                          limit_bytes=STORAGE_LIMIT_BYTES)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    shutil.copytree(bundle["root"], output_dir / "tokenizer")
    copied_bundle = inspect_pilot_bundle(output_dir / "tokenizer")
    if (copied_bundle["tokenizer"] != bundle["tokenizer"]
            or copied_bundle["dataset"] != bundle["dataset"]):
        raise ValueError("Packaged tokenizer bundle differs from the approved source")
    with train_source(copied_bundle) as train, TokenCorpus(copied_bundle["validationPath"]) as validation:
        result = run_training(
            train_source=train, validation=validation,
            device_name=device_name, minutes=minutes, step_limit=steps,
            output_checkpoint=output_dir / "resumed-checkpoint.pt",
            metrics_path=output_dir / "metrics.jsonl", artifact_root=root,
            seed=seed, micro_batch=micro_batch,
            accumulation_steps=gradient_accumulation,
            checkpoint_interval_minutes=checkpoint_every_minutes,
            resume_from=checkpoint_path, config=DEFAULT_CONFIG,
            codec=CODEC, tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
        )
    checkpoint = output_dir / "resumed-checkpoint.pt"
    if sha256_file(checkpoint_path) != source_hash:
        raise ValueError("Source checkpoint changed during continuation")
    report = {
        "schemaVersion": 1,
        "milestone": "P2-03 complete-record learning curve" if complete_record else "P1-19 save-resume-generate gate",
        "sourceCheckpointSha256": source_hash,
        "sourceCheckpointUnchanged": True,
        "sourceStep": source_step,
        "sourceTokensProcessed": source_positions,
        "samplingPolicy": "complete-record-v1" if complete_record else "random-window-v1",
        "samplingAudit": train.sampling_audit() if complete_record else None,
        "resumedCheckpointSha256": sha256_file(checkpoint),
        "tokenizerBundle": str((output_dir / "tokenizer").relative_to(root)),
        "tokenizer": bundle["tokenizer"],
        "dataset": bundle["dataset"],
        "resumedExpectedSteps": steps,
        "resumedStepsCompleted": result["stepsThisRun"],
        "resumeCheckPassed": (
            result["stepsThisRun"] == steps and result["step"] == source_step + steps
            and not result["interrupted"] and result["trainingSettings"] is not None
            and result["scheduleState"]["step"] == result["step"]
        ),
        "training": result,
    }
    report_path = output_dir / "resume-report.json"
    with report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    enforce_storage_limit(root, limit_bytes=STORAGE_LIMIT_BYTES)
    return {"report": str(report_path.relative_to(root)), **report}


def evaluate_pilot(*, bundle_dir: Path, checkpoint_path: Path,
                   device_name: str = "auto", maximum_batches: int = 100) -> dict[str, Any]:
    bundle = inspect_pilot_bundle(bundle_dir)
    if maximum_batches <= 0 or maximum_batches > 1000:
        raise ValueError("evaluation maximum batches must be from 1 through 1000")
    result = evaluate_checkpoint(
        checkpoint_path, bundle["validationPath"], device_name=device_name,
        maximum_batches=maximum_batches, codec=CODEC,
        tokenizer_record=bundle["tokenizer"], dataset_record=bundle["dataset"],
        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
    )
    return {**result, "split": "held-out-validation", "dataset": bundle["dataset"],
            "tokenizer": bundle["tokenizer"]}
