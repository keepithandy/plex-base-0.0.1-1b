"""P2-30 task-format fine-tuning preparation without optimizer updates."""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
from array import array
from pathlib import Path
from typing import Any

import torch

from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, save_checkpoint
from .config import DEFAULT_CONFIG
from .pilot import inspect_pilot_bundle
from .runner import ADAMW_BETAS, ADAMW_EPSILON, ADAMW_LEARNING_RATE, ADAMW_WEIGHT_DECAY
from .tokenizer import CODEC, PlexTokenizer, sha256_file

EOS_ID = 3


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized metadata file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _split_rows(path: Path, expected_sha: str, expected_count: int) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError(f"Task split is missing, linked, or too large: {path.name}")
    if sha256_file(path) != expected_sha:
        raise ValueError(f"{path.name} SHA-256 differs from the approved P2-30 split")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Task dataset rows must be JSON objects")
            record_id, text = row.get("recordId"), row.get("text")
            if (not isinstance(record_id, str) or not record_id or record_id in ids
                    or not isinstance(text, str) or not text):
                raise ValueError("Task dataset record identity/text is invalid")
            ids.add(record_id)
            rows.append(row)
    if len(rows) != expected_count:
        raise ValueError(f"{path.name} record count differs from the approved P2-30 split")
    return rows


def prepare_task_bundle(
    dataset_dir: Path,
    tokenizer_dir: Path,
    output_dir: Path,
    *,
    contract_path: Path,
    storage_limit_bytes: int,
) -> dict[str, Any]:
    """Retokenize an already-approved task split with the frozen Web tokenizer."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    dataset_dir = dataset_dir.resolve(strict=True)
    tokenizer_dir = tokenizer_dir.resolve(strict=True)
    output_dir = output_dir.resolve(strict=False)
    contract = _json(contract_path.resolve(strict=True))
    if (contract.get("milestone") != "P2-30"
            or contract.get("status") != "active-preparation-gate"
            or contract.get("authorization", {}).get("modelTrainingAuthorized") is not False):
        raise ValueError("P2-30 preparation contract is missing or does not block training")

    curriculum = contract.get("firstCurriculum", {})
    tokenizer_contract = contract.get("tokenizer", {})
    source_manifest_path = dataset_dir / "manifest.json"
    source_manifest_hash = sha256_file(source_manifest_path)
    if source_manifest_hash != curriculum.get("existingSourceDatasetManifestSha256"):
        raise ValueError("Task dataset manifest is not the approved P2-02 request-following v3 build")
    source_manifest = _json(source_manifest_path)
    if source_manifest.get("schemaVersion") != 1 or source_manifest.get("pipelineVersion") != "p2-02.0":
        raise ValueError("P2-30 requires the approved P2-02.0 task dataset format")
    summary = source_manifest.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Task dataset summary is missing")
    expected = {
        "train": (
            curriculum.get("existingTrainJsonlSha256"),
            curriculum.get("trainRecords"),
        ),
        "validation": (
            curriculum.get("existingValidationJsonlSha256"),
            curriculum.get("validationRecords"),
        ),
    }
    rows: dict[str, list[dict[str, Any]]] = {}
    for split, (expected_sha, expected_count) in expected.items():
        if (not isinstance(expected_sha, str) or type(expected_count) is not int
                or summary.get(f"{split}JsonlSha256") != expected_sha
                or summary.get(f"{split}Records") != expected_count):
            raise ValueError("Task dataset summary differs from the approved P2-30 split")
        rows[split] = _split_rows(dataset_dir / f"{split}.jsonl", expected_sha, expected_count)

    train_ids = {row["recordId"] for row in rows["train"]}
    validation_ids = {row["recordId"] for row in rows["validation"]}
    if train_ids & validation_ids:
        raise ValueError("Task train/validation record identities overlap")

    tokenizer = PlexTokenizer.load(tokenizer_dir)
    tokenizer_settings = _json(tokenizer_dir / "tokenizer-config.json")
    tokenizer_manifest = _json(tokenizer_dir / "manifest.json")
    tokenizer_sha = tokenizer_settings.get("tokenizerSha256")
    if (tokenizer.vocabulary_size != tokenizer_contract.get("actualVocabularySize")
            or tokenizer_sha != tokenizer_contract.get("tokenizerSha256")
            or sha256_file(tokenizer_dir / "manifest.json") != tokenizer_contract.get("bundleManifestSha256")
            or tokenizer_manifest.get("modelVocabularyCapacity") != DEFAULT_CONFIG.vocab_size):
        raise ValueError("Tokenizer is not the frozen P2-27 Web tokenizer")

    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing task-token bundle")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-p2-30-bundle-", dir=output_dir.parent)).resolve()
    staging.relative_to(output_dir.parent.resolve())
    try:
        for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
            shutil.copyfile(tokenizer_dir / name, staging / name)
        shutil.copyfile(source_manifest_path, staging / "source-dataset-manifest.json")
        licenses = dataset_dir / "licenses"
        if licenses.is_dir() and not licenses.is_symlink():
            shutil.copytree(licenses, staging / "licenses")

        split_info: dict[str, Any] = {}
        for split in ("train", "validation"):
            token_path = staging / f"{split}.tokens.u16le"
            index: list[dict[str, Any]] = []
            token_count = text_bytes = 0
            with token_path.open("xb") as stream:
                for row in rows[split]:
                    text = row["text"]
                    ids = tokenizer.encode(text)
                    if tokenizer.decode(ids) != text:
                        raise ValueError("Task record failed exact tokenizer roundtrip")
                    packed_ids = ids + [EOS_ID]
                    packed = array("H", packed_ids)
                    if packed.itemsize != 2:
                        raise RuntimeError("Platform lacks uint16 arrays")
                    if sys.byteorder != "little":
                        packed.byteswap()
                    stream.write(packed.tobytes())
                    index.append({
                        "recordId": row["recordId"],
                        "startToken": token_count,
                        "tokenCount": len(packed_ids),
                    })
                    token_count += len(packed_ids)
                    text_bytes += len(text.encode("utf-8"))
            (staging / f"{split}.index.json").write_text(
                json.dumps(index, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            split_info[split] = {
                "path": token_path.name,
                "sha256": sha256_file(token_path),
                "records": len(index),
                "tokenCount": token_count,
                "textBytes": text_bytes,
                "bytesPerTextToken": text_bytes / (token_count - len(index)),
                "roundtripRecords": len(index),
                "jsonlSha256": summary[f"{split}JsonlSha256"],
            }

        manifest = {
            "schemaVersion": 1,
            "codec": CODEC,
            "storageDtype": "uint16-le",
            "sourceDatasetManifestSha256": source_manifest_hash,
            "tokenizerSha256": tokenizer_sha,
            "modelConfigSha256": sha256_file(staging / "model-config.json"),
            "actualVocabularySize": tokenizer.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "representativeRoundtrips": tokenizer_manifest.get("representativeRoundtrips", 0),
            "repackedWithFrozenTokenizer": True,
            "frozenTokenizerSourceBundleSha256": tokenizer_contract["bundleManifestSha256"],
            **split_info,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        bundle_bytes = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file())
        if bundle_bytes > storage_limit_bytes:
            raise ValueError("P2-30 task-token bundle exceeds remaining storage allocation")
        inspected = inspect_pilot_bundle(staging)
        if (inspected["tokenizer"]["tokenizerSha256"] != tokenizer_contract["tokenizerSha256"]
                or inspected["dataset"]["trainRecords"] != curriculum["trainRecords"]
                or inspected["dataset"]["validationRecords"] != curriculum["validationRecords"]):
            raise ValueError("Repacked task-token bundle failed final identity inspection")
        os.rename(staging, output_dir)
        return {
            "schemaVersion": 1,
            "milestone": "P2-30",
            "trainingPerformed": False,
            "sourceDatasetManifestSha256": source_manifest_hash,
            "tokenizerSha256": tokenizer_sha,
            "sourceTokenizerBundleManifestSha256": tokenizer_contract["bundleManifestSha256"],
            "taskBundleManifestSha256": sha256_file(output_dir / "manifest.json"),
            "train": split_info["train"],
            "validation": split_info["validation"],
            "bundleBytes": bundle_bytes,
        }
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def create_task_stage(
    base_checkpoint: Path,
    bundle_dir: Path,
    output_dir: Path,
    *,
    contract_path: Path,
    artifact_root: Path,
    storage_limit_bytes: int,
) -> dict[str, Any]:
    """Create a step-zero task stage by loading base model weights only."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    root = artifact_root.resolve()
    output_dir = path_within_root(output_dir, root)
    if output_dir.exists():
        raise FileExistsError("Task-stage output directory already exists")
    contract = _json(contract_path.resolve(strict=True))
    if contract.get("authorization", {}).get("modelTrainingAuthorized") is not False:
        raise ValueError("P2-30 task-stage creation requires training to remain blocked")
    base = contract.get("baseModel", {})
    expected_sha = base.get("checkpointSha256")
    base_checkpoint = base_checkpoint.resolve(strict=True)
    if base_checkpoint.is_symlink() or sha256_file(base_checkpoint) != expected_sha:
        raise ValueError("Base checkpoint is not the verified P2-29 step-500 checkpoint")

    bundle = inspect_pilot_bundle(bundle_dir)
    tokenizer_contract = contract.get("tokenizer", {})
    curriculum = contract.get("firstCurriculum", {})
    if (bundle["tokenizer"]["tokenizerSha256"] != tokenizer_contract.get("tokenizerSha256")
            or bundle["dataset"]["sourceDatasetManifestSha256"] != curriculum.get("existingSourceDatasetManifestSha256")
            or bundle["dataset"]["trainRecords"] != curriculum.get("trainRecords")
            or bundle["dataset"]["validationRecords"] != curriculum.get("validationRecords")):
        raise ValueError("Task bundle does not match the P2-30 preparation contract")

    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    source_tokenizer = payload.get("tokenizerRecord")
    source_dataset = payload.get("datasetRecord")
    if (model.config != DEFAULT_CONFIG or payload.get("codec") != CODEC
            or payload.get("step") != base.get("checkpointStep")
            or payload.get("seed") != 1337
            or not isinstance(source_tokenizer, dict)
            or source_tokenizer.get("tokenizerSha256") != tokenizer_contract.get("tokenizerSha256")
            or not isinstance(source_dataset, dict)
            or not isinstance(payload.get("initializationRecord"), dict)
            or payload["initializationRecord"].get("pretrainedModelWeightsLoaded") is not False):
        raise ValueError("P2-29 checkpoint provenance does not satisfy the P2-30 contract")

    seed = int(payload["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    sampling_rng = random.Random(seed)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-30 optimizer unexpectedly contains state")

    stage_record = {
        "schemaVersion": 1,
        "kind": "plex-task-finetune-stage-transition-v1",
        "milestone": "P2-30",
        "baseCheckpointSha256": expected_sha,
        "baseCheckpointStep": payload["step"],
        "baseDatasetRecord": source_dataset,
        "baseTokenizerRecord": source_tokenizer,
        "taskDatasetRecord": bundle["dataset"],
        "taskTokenizerRecord": bundle["tokenizer"],
        "modelWeightsLoadedFromBase": True,
        "pretrainingOptimizerStateReused": False,
        "pretrainingSamplerStateReused": False,
        "pretrainingStepReusedAsTaskStep": False,
        "taskStageStep": 0,
        "modelTrainingPerformed": False,
    }

    estimated = DEFAULT_CONFIG.parameter_count() * 4 + 2 * 1024 * 1024
    enforce_storage_limit(root, additional_bytes=estimated, limit_bytes=storage_limit_bytes)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    checkpoint_path = output_dir / "stage-checkpoint.pt"
    saved = save_checkpoint(
        model,
        optimizer,
        step=0,
        seed=seed,
        codec=CODEC,
        sampling_rng=sampling_rng,
        device=torch.device("cpu"),
        destination=checkpoint_path,
        artifact_root=root,
        initialization_record=payload["initializationRecord"],
        tokenizer_record=bundle["tokenizer"],
        dataset_record=bundle["dataset"],
        training_settings=None,
        schedule_state=None,
        tokens_processed_total=0,
        stage_transition_record=stage_record,
    )
    stage_sha = sha256_file(checkpoint_path)
    report = {
        "schemaVersion": 1,
        "milestone": "P2-30",
        "trainingPerformed": False,
        "baseCheckpointSha256": expected_sha,
        "stageCheckpointSha256": stage_sha,
        "stageCheckpoint": saved,
        "parameterCount": DEFAULT_CONFIG.parameter_count(),
        "tokenizer": bundle["tokenizer"],
        "dataset": bundle["dataset"],
        "optimizerStateReused": False,
        "taskStageStep": 0,
        "stageTransition": stage_record,
    }
    (output_dir / "stage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    enforce_storage_limit(root, limit_bytes=storage_limit_bytes)
    return report
