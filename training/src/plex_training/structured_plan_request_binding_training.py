"""P2-41 request-conditioned plan-binding bundle, stage, and read-only preflight.

All commands in this module perform zero optimizer updates. No P2-41 training
runner exists until a later owner-approved authorization packet is committed.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, save_checkpoint
from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .model import parameter_count
from .runner import (
    ADAMW_BETAS,
    ADAMW_EPSILON,
    ADAMW_LEARNING_RATE,
    ADAMW_WEIGHT_DECAY,
    SCHEDULE_KIND,
    _validation_loss,
    seed_everything,
)
from .structured_plan import canonical_text_sha256, render_plan_request_prompt
from .structured_plan_request_binding_curriculum import (
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_TOKENIZER_BUNDLE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    review_request_binding_curriculum,
)
from .structured_plan_semantic_binding_training import (
    StructuredPlanCompleteRecordCorpus,
    _structured_plan_training_step,
)
from .telemetry import environment_report, peak_gpu_memory, reset_peak_gpu_memory, select_device
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-41"
STAGE_KIND = "plex-request-conditioned-plan-binding-stage-transition-v1"
BASE_CHECKPOINT_SHA256 = "9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6"
BASE_CHECKPOINT_STEP = 100
SEED = 1337
MAXIMUM_STEPS = 100
MAXIMUM_WALL_SECONDS = 600
MICRO_BATCH = 1
GRADIENT_ACCUMULATION = 16
VALIDATION_MAXIMUM_BATCHES = 100
AUTHORIZED_OUTPUT_DIRECTORY = "structured-plan/p2-41-first-run"
AUTHORIZATION_KIND = "plex-p2-41-first-request-binding-run-contract-v1"
AUTHORIZED_STATUS = "owner-approved-first-run"
AUTHORIZED_APPROVER = "keepithandy"
VALIDATION_STEPS = (0, 25, 50, 75, 100)
CHECKPOINT_STEPS = (25, 50, 75, 100)
DEFAULT_AUTHORIZATION_CONTRACT = Path("training/pretraining/p2-41-first-run-contract.json")
DEFAULT_PREPARATION_CONTRACT = Path(
    "training/pretraining/p2-41-request-conditioned-plan-binding-preparation-contract.json"
)


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _preparation_contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind")
        != "plex-p2-41-request-conditioned-plan-binding-preparation-contract-v1"
        or value.get("status") != "design-preparation-only"
        or value.get("dataPreparationAuthorized") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("automaticTrainingExtension") is not False
        or value.get("trainingCommand") is not None
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
        or value.get("baseCheckpoint", {}).get("milestone") != "P2-38"
        or value.get("baseCheckpoint", {}).get("step") != BASE_CHECKPOINT_STEP
        or value.get("baseCheckpoint", {}).get("sha256") != BASE_CHECKPOINT_SHA256
        or value.get("candidateIdentity", {}).get("sha256") != EXPECTED_CANDIDATE_SHA256
        or value.get("tokenizerPreflight", {}).get("checked") is not True
        or value.get("tokenizerPreflight", {}).get("tokenizerSha256")
        != EXPECTED_TOKENIZER_SHA256
        or value.get("tokenizerPreflight", {}).get("bundleManifestSha256")
        != EXPECTED_TOKENIZER_BUNDLE_SHA256
        or value.get("tokenizerPreflight", {}).get("maximumRecordTokensIncludingEos") != 374
        or value.get("tokenizerPreflight", {}).get("trainTokenCount") != 25599
        or value.get("tokenizerPreflight", {}).get("validationTokenCount") != 12798
    ):
        raise ValueError("P2-41 preparation contract is invalid or no longer zero-update")
    return value


def _candidate_rows(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-41 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    if canonical_text_sha256(raw) != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("P2-41 candidate differs from the frozen reviewed candidate")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-41 JSONL line {number}")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"P2-41 line {number} is not an object")
        rows.append(value)
    return rows


def _render_training_text(row: dict[str, Any]) -> str:
    return render_plan_request_prompt(row["language"], row["request"]) + row["solution"]


def prepare_request_binding_bundle(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    source_bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Pack the frozen P2-41 candidate with the frozen tokenizer without training."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    _preparation_contract(preparation_contract_path)
    review = review_request_binding_curriculum(
        candidate_path=candidate_path,
        review_path=review_path,
        development_task_set_path=development_task_set_path,
        contract_path=preparation_contract_path,
        bundle_dir=source_bundle_dir,
    )
    if review.get("status") != "candidate-review-passed":
        raise ValueError("P2-41 candidate review has not passed")
    preflight = review.get("tokenizerPreflight", {})
    if (
        preflight.get("checked") is not True
        or preflight.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or preflight.get("maximumRecordTokensIncludingEos") != 374
        or preflight.get("trainTokenCount") != 25599
        or preflight.get("validationTokenCount") != 12798
    ):
        raise ValueError("P2-41 frozen-tokenizer preflight differs from the reviewed result")

    tokenizer, source_identity = _completion_tokenizer(source_bundle_dir)
    if (
        source_identity.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or source_identity.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
        or tokenizer.vocabulary_size != 16384
    ):
        raise ValueError("P2-41 requires the exact frozen 16,384-token tokenizer bundle")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-41 packed bundle already exists; choose a fresh output")
    rows = _candidate_rows(candidate_path)
    by_split = {
        split: [row for row in rows if row.get("candidateSplit") == split]
        for split in ("train", "validation")
    }
    if len(by_split["train"]) != 72 or len(by_split["validation"]) != 36:
        raise ValueError("P2-41 candidate split changed after review")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-p2-41-bundle-", dir=output.parent)).resolve()
    try:
        for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
            source = source_bundle_dir.resolve(strict=True) / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Frozen tokenizer source is missing {name}")
            shutil.copyfile(source, staging / name)

        split_info: dict[str, dict[str, Any]] = {}
        summary: dict[str, Any] = {}
        for split in ("train", "validation"):
            jsonl_path = staging / f"{split}.jsonl"
            token_path = staging / f"{split}.tokens.u16le"
            index_path = staging / f"{split}.index.json"
            index: list[dict[str, Any]] = []
            token_count = 0
            maximum = 0
            with jsonl_path.open("x", encoding="utf-8", newline="\n") as text_stream, \
                    token_path.open("xb") as token_stream:
                for row in by_split[split]:
                    record_id = row["id"]
                    text = _render_training_text(row)
                    ids = tokenizer.encode(text)
                    if tokenizer.decode(ids) != text:
                        raise ValueError(f"P2-41 tokenizer roundtrip failed: {record_id}")
                    packed_ids = ids + [3]
                    if len(packed_ids) > DEFAULT_CONFIG.context_length:
                        raise ValueError(f"P2-41 record exceeds context: {record_id}")
                    text_stream.write(
                        json.dumps(
                            {"recordId": record_id, "text": text},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    packed = array("H", packed_ids)
                    if sys.byteorder != "little":
                        packed.byteswap()
                    token_stream.write(packed.tobytes())
                    index.append(
                        {
                            "recordId": record_id,
                            "startToken": token_count,
                            "tokenCount": len(packed_ids),
                        }
                    )
                    token_count += len(packed_ids)
                    maximum = max(maximum, len(packed_ids))

            index_path.write_text(
                json.dumps(index, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            summary[f"{split}Records"] = len(index)
            summary[f"{split}JsonlSha256"] = sha256_file(jsonl_path)
            split_info[split] = {
                "path": token_path.name,
                "sha256": sha256_file(token_path),
                "records": len(index),
                "tokenCount": token_count,
                "jsonlSha256": sha256_file(jsonl_path),
                "maximumRecordTokensIncludingEos": maximum,
                "contextLength": DEFAULT_CONFIG.context_length,
                "contextLimitPassed": True,
            }

        if (
            split_info["train"]["tokenCount"] != 25599
            or split_info["validation"]["tokenCount"] != 12798
            or max(
                split_info["train"]["maximumRecordTokensIncludingEos"],
                split_info["validation"]["maximumRecordTokensIncludingEos"],
            )
            != 374
        ):
            raise ValueError("P2-41 packed token accounting differs from frozen preflight")

        source_manifest = {
            "schemaVersion": 1,
            "pipelineVersion": "p2-41-request-conditioned-plan-binding-v1",
            "recordFormat": "JSONL recordId/text rendered from frozen P2-41 full-plan candidate",
            "normalization": "UTF-8; canonical repository text",
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "reviewStatus": review["status"],
            "summary": summary,
        }
        source_manifest_path = staging / "source-dataset-manifest.json"
        source_manifest_path.write_text(
            json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "codec": CODEC,
            "actualVocabularySize": tokenizer.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "modelConfigSha256": sha256_file(staging / "model-config.json"),
            "sourceDatasetManifestSha256": sha256_file(source_manifest_path),
            "sourceTokenizerBundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "repackedWithFrozenTokenizer": True,
            **split_info,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if size > storage_limit_bytes:
            raise ValueError("P2-41 bundle exceeds remaining artifact storage allocation")
        os.rename(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    inspected = inspect_request_binding_bundle(output, preparation_contract_path)
    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(output / "manifest.json"),
        "tokenizerSha256": inspected["tokenizer"]["tokenizerSha256"],
        "trainRecords": inspected["dataset"]["trainRecords"],
        "validationRecords": inspected["dataset"]["validationRecords"],
        "trainTokenCount": inspected["dataset"]["trainTokenCount"],
        "validationTokenCount": inspected["dataset"]["validationTokenCount"],
        "maximumRecordTokensIncludingEos": max(
            inspected["manifest"]["train"]["maximumRecordTokensIncludingEos"],
            inspected["manifest"]["validation"]["maximumRecordTokensIncludingEos"],
        ),
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }


def inspect_request_binding_bundle(
    bundle_dir: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
) -> dict[str, Any]:
    """Verify P2-41 packed text, tokens, indices, candidate, and tokenizer identity."""
    _preparation_contract(preparation_contract_path)
    root = bundle_dir.resolve(strict=True)
    if root.is_symlink():
        raise ValueError("P2-41 bundle may not be a symlink")
    manifest = _json(root / "manifest.json")
    source = _json(root / "source-dataset-manifest.json")
    tokenizer, tokenizer_record = _completion_tokenizer(root)
    if (
        manifest.get("schemaVersion") != 1
        or manifest.get("milestone") != MILESTONE
        or manifest.get("codec") != CODEC
        or manifest.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or manifest.get("sourceTokenizerBundleManifestSha256")
        != EXPECTED_TOKENIZER_BUNDLE_SHA256
        or manifest.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer.vocabulary_size != 16384
        or source.get("pipelineVersion") != "p2-41-request-conditioned-plan-binding-v1"
        or source.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or sha256_file(root / "source-dataset-manifest.json")
        != manifest.get("sourceDatasetManifestSha256")
    ):
        raise ValueError("P2-41 packed bundle identity is invalid")

    summary = source.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("P2-41 source dataset summary is missing")
    dataset: dict[str, Any] = {
        "sourceDatasetManifestSha256": manifest["sourceDatasetManifestSha256"],
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
    }
    ids_by_split: dict[str, set[str]] = {}
    for split, expected_records, expected_tokens in (
        ("train", 72, 25599),
        ("validation", 36, 12798),
    ):
        info = manifest.get(split)
        if (
            not isinstance(info, dict)
            or info.get("records") != expected_records
            or info.get("tokenCount") != expected_tokens
        ):
            raise ValueError(f"P2-41 {split} split accounting is invalid")
        jsonl_path = root / f"{split}.jsonl"
        token_path = root / f"{split}.tokens.u16le"
        index_path = root / f"{split}.index.json"
        if any(
            path.is_symlink() or not path.is_file()
            for path in (jsonl_path, token_path, index_path)
        ):
            raise ValueError("P2-41 bundle contains missing or linked split files")
        if (
            sha256_file(jsonl_path) != info.get("jsonlSha256")
            or info.get("jsonlSha256") != summary.get(f"{split}JsonlSha256")
            or sha256_file(token_path) != info.get("sha256")
        ):
            raise ValueError(f"P2-41 {split} split hash differs from manifest")

        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len(entries) != expected_records:
            raise ValueError(f"P2-41 {split} token index is invalid")
        tokens = array("H")
        tokens.frombytes(token_path.read_bytes())
        if sys.byteorder != "little":
            tokens.byteswap()
        offset = 0
        ids: set[str] = set()
        lines = list(jsonl_path.open(encoding="utf-8"))
        if len(lines) != expected_records:
            raise ValueError(f"P2-41 {split} JSONL row count changed")
        for line, entry in zip(lines, entries):
            row = json.loads(line)
            record_id = row.get("recordId")
            text = row.get("text")
            if (
                not isinstance(record_id, str)
                or not record_id
                or record_id in ids
                or not isinstance(text, str)
                or not text.startswith(
                    "Convert the repository-style request into one semantic edit plan.\n"
                )
                or "\nJSON:{" not in text
            ):
                raise ValueError("P2-41 packed text shape is invalid")
            expected = tokenizer.encode(text) + [3]
            if (
                entry.get("recordId") != record_id
                or entry.get("startToken") != offset
                or entry.get("tokenCount") != len(expected)
                or list(tokens[offset : offset + len(expected)]) != expected
            ):
                raise ValueError("P2-41 packed text/index/tokens differ")
            ids.add(record_id)
            offset += len(expected)
        if offset != len(tokens) or offset != expected_tokens:
            raise ValueError("P2-41 packed token accounting differs")
        ids_by_split[split] = ids
        dataset[f"{split}JsonlSha256"] = info["jsonlSha256"]
        dataset[f"{split}TokensSha256"] = info["sha256"]
        dataset[f"{split}TokenCount"] = info["tokenCount"]
        dataset[f"{split}Records"] = info["records"]
        dataset[f"{split}IndexSha256"] = sha256_file(index_path)

    if ids_by_split["train"] & ids_by_split["validation"]:
        raise ValueError("P2-41 train/validation record identities overlap")
    return {
        "root": root,
        "manifest": manifest,
        "trainPath": root / "train.tokens.u16le",
        "validationPath": root / "validation.tokens.u16le",
        "tokenizer": tokenizer_record,
        "dataset": dataset,
    }


def create_request_binding_stage(
    *,
    base_checkpoint: Path,
    bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Create an untouched P2-41 step-zero stage from the official P2-38 endpoint."""
    _preparation_contract(preparation_contract_path)
    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-41 stage output already exists")
    if (
        base_checkpoint.is_symlink()
        or not base_checkpoint.is_file()
        or sha256_file(base_checkpoint) != BASE_CHECKPOINT_SHA256
    ):
        raise ValueError("P2-41 stage requires the exact P2-38 step-100 checkpoint")

    bundle = inspect_request_binding_bundle(bundle_dir, preparation_contract_path)
    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    transition = payload.get("stageTransitionRecord")
    training_settings = payload.get("trainingSettings")
    if (
        model.config != DEFAULT_CONFIG
        or parameter_count(model) != DEFAULT_CONFIG.parameter_count()
        or payload.get("step") != BASE_CHECKPOINT_STEP
        or payload.get("seed") != SEED
        or payload.get("codec") != CODEC
        or not isinstance(payload.get("initializationRecord"), dict)
        or payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False
        or payload["initializationRecord"].get("pretrainedModelWeightsLoaded") is not False
        or not isinstance(transition, dict)
        or transition.get("kind") != "plex-semantic-binding-stage-transition-v1"
        or transition.get("milestone") != "P2-38"
        or not isinstance(training_settings, dict)
        or training_settings.get("kind") != "p2-38-authorized-semantic-binding-training-v1"
    ):
        raise ValueError("P2-38 endpoint provenance does not satisfy the P2-41 stage contract")
    source_tokenizer = payload.get("tokenizerRecord")
    if (
        not isinstance(source_tokenizer, dict)
        or source_tokenizer.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or source_tokenizer.get("actualVocabularySize") != 16384
    ):
        raise ValueError("P2-38 endpoint tokenizer identity differs from P2-41")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-41 optimizer unexpectedly contains state")
    rng = random.Random(SEED)
    stage_transition = {
        "schemaVersion": 1,
        "kind": STAGE_KIND,
        "milestone": MILESTONE,
        "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
        "baseCheckpointStep": BASE_CHECKPOINT_STEP,
        "baseMilestone": "P2-38",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP241Step": False,
        "p241StageStep": 0,
        "modelTrainingPerformed": False,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    checkpoint = output / "stage-checkpoint.pt"
    try:
        save_checkpoint(
            model,
            optimizer,
            step=0,
            seed=SEED,
            codec=CODEC,
            sampling_rng=rng,
            device=torch.device("cpu"),
            destination=checkpoint,
            artifact_root=root,
            initialization_record=payload["initializationRecord"],
            stage_transition_record=stage_transition,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            training_settings=None,
            schedule_state=None,
            tokens_processed_total=0,
        )
        saved_model, saved = read_checkpoint(checkpoint, torch.device("cpu"))
        weights_equal = all(
            torch.equal(value, saved_model.state_dict()[name])
            for name, value in model.state_dict().items()
        )
        if (
            not weights_equal
            or saved.get("optimizerStateDict", {}).get("state") != {}
            or saved.get("step") != 0
            or saved.get("tokensProcessedTotal") != 0
            or saved.get("samplingRngState") != random.Random(SEED).getstate()
            or saved.get("stageTransitionRecord") != stage_transition
            or saved.get("tokenizerRecord") != bundle["tokenizer"]
            or saved.get("datasetRecord") != bundle["dataset"]
        ):
            raise ValueError("Saved P2-41 stage failed weights/state verification")
        report = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "trainingPerformed": False,
            "researchOptimizerUpdates": 0,
            "finalHoldoutOpened": False,
            "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
            "stageCheckpointSha256": sha256_file(checkpoint),
            "stageCheckpoint": "stage-checkpoint.pt",
            "parameterCount": parameter_count(model),
            "modelWeightsPreserved": weights_equal,
            "modelWeightEqualityMethod": "torch.equal for every model-state tensor after reload",
            "optimizerStateReused": False,
            "samplerStateReset": True,
            "p241StageStep": 0,
            "p241TokensProcessed": 0,
            "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
            "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "stageTransition": stage_transition,
        }
        (output / "stage-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > storage_limit_bytes:
            raise ValueError("P2-41 stage exceeds remaining artifact storage allocation")
        return report
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def _verify_stage(
    stage_checkpoint: Path,
    bundle: dict[str, Any],
) -> tuple[torch.nn.Module, dict[str, Any]]:
    if stage_checkpoint.is_symlink() or not stage_checkpoint.is_file():
        raise ValueError("P2-41 stage checkpoint must be a regular file")
    model, payload = read_checkpoint(stage_checkpoint, torch.device("cpu"))
    transition = payload.get("stageTransitionRecord")
    if (
        model.config != DEFAULT_CONFIG
        or payload.get("step") != 0
        or payload.get("tokensProcessedTotal") != 0
        or payload.get("seed") != SEED
        or payload.get("codec") != CODEC
        or payload.get("optimizerStateDict", {}).get("state") != {}
        or payload.get("trainingSettings") is not None
        or payload.get("scheduleState") is not None
        or payload.get("samplingRngState") != random.Random(SEED).getstate()
        or payload.get("tokenizerRecord") != bundle["tokenizer"]
        or payload.get("datasetRecord") != bundle["dataset"]
        or not isinstance(transition, dict)
        or transition.get("kind") != STAGE_KIND
        or transition.get("milestone") != MILESTONE
        or transition.get("baseCheckpointSha256") != BASE_CHECKPOINT_SHA256
        or transition.get("baseCheckpointStep") != BASE_CHECKPOINT_STEP
        or transition.get("baseMilestone") != "P2-38"
        or transition.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or transition.get("modelWeightsLoadedFromBase") is not True
        or transition.get("baseOptimizerStateReused") is not False
        or transition.get("baseSamplerStateReused") is not False
        or transition.get("baseTrainingStepReusedAsP241Step") is not False
        or transition.get("p241StageStep") != 0
        or transition.get("modelTrainingPerformed") is not False
    ):
        raise ValueError("P2-41 stage checkpoint is not an untouched step-zero transition")
    return model, payload


def preflight_request_binding_training(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Measure the frozen P2-41 stage/data packet without updating model weights."""
    _preparation_contract(preparation_contract_path)
    bundle = inspect_request_binding_bundle(bundle_dir, preparation_contract_path)
    model, _ = _verify_stage(stage_checkpoint, bundle)

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / AUTHORIZED_OUTPUT_DIRECTORY, root)
    if output != expected_output:
        raise ValueError("P2-41 proposed first run must use the locked output directory")
    if output.exists():
        raise FileExistsError("P2-41 proposed first-run output already exists")
    if require_cuda:
        select_device("cuda")

    tokenizer = PlexTokenizer.load(bundle["root"])
    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train:
        expected_positions, _ = train.replay_progress(
            SEED, MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION
        )
        sampler = train.sampler_record

    device = select_device("cuda") if require_cuda else torch.device("cpu")
    model = model.to(device)
    with TokenCorpus(bundle["validationPath"]) as validation:
        baseline_loss = _validation_loss(
            model,
            validation,
            device,
            maximum_batches=VALIDATION_MAXIMUM_BATCHES,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
        )
    del model

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "preflight-passed-awaiting-owner-authorization",
        "authorized": False,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "stageCheckpointSha256": sha256_file(stage_checkpoint),
        "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "trainRecords": 72,
        "validationRecords": 36,
        "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "trainIndexSha256": bundle["dataset"]["trainIndexSha256"],
        "validationIndexSha256": bundle["dataset"]["validationIndexSha256"],
        "trainTokenCount": bundle["dataset"]["trainTokenCount"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "sampler": sampler,
        "expectedExamplesAt100Steps": MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION,
        "expectedRealTargetPositionsAt100Steps": expected_positions,
        "baselineValidationLoss": baseline_loss,
        "baselineValidationBatches": min(
            VALIDATION_MAXIMUM_BATCHES,
            bundle["dataset"]["validationTokenCount"] // DEFAULT_CONFIG.context_length,
        ),
        "proposedMaximumSteps": MAXIMUM_STEPS,
        "proposedMaximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "proposedValidationSteps": [0, 25, 50, 75, 100],
        "proposedCheckpointSteps": [25, 50, 75, 100],
        "proposedDevice": "cuda" if require_cuda else "cpu",
        "outputWouldBe": str(output.relative_to(root)),
    }


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"P2-41 contract mismatch: {label}")


def _validate_authorization(contract: dict[str, Any]) -> None:
    _require_exact(contract.get("schemaVersion"), 1, "schemaVersion")
    _require_exact(contract.get("milestone"), MILESTONE, "milestone")
    _require_exact(contract.get("kind"), AUTHORIZATION_KIND, "kind")
    _require_exact(contract.get("status"), AUTHORIZED_STATUS, "status")
    _require_exact(contract.get("approvalPacketComplete"), True, "approvalPacketComplete")
    _require_exact(contract.get("modelTrainingAuthorized"), True, "modelTrainingAuthorized")
    _require_exact(contract.get("approvedBy"), AUTHORIZED_APPROVER, "approvedBy")
    _require_exact(contract.get("approvedDate"), "2026-10-07", "approvedDate")
    _require_exact(contract.get("outputDirectory"), AUTHORIZED_OUTPUT_DIRECTORY, "outputDirectory")
    execution = contract.get("executionState")
    if not isinstance(execution, dict):
        raise ValueError("P2-41 execution state is missing")
    for key, expected in {
        "trainingExecuted": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }.items():
        _require_exact(execution.get(key), expected, f"executionState.{key}")

    base = contract.get("baseStage")
    if not isinstance(base, dict):
        raise ValueError("P2-41 base stage is missing")
    for key, expected in {
        "checkpointSha256": "763920474516488e5bc68d00e77320916c95d9c67253752c03f48f9da36b67fd",
        "p241Step": 0,
        "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
        "parameterCount": DEFAULT_CONFIG.parameter_count(),
    }.items():
        _require_exact(base.get(key), expected, f"baseStage.{key}")

    data = contract.get("data")
    if not isinstance(data, dict):
        raise ValueError("P2-41 data authorization is missing")
    for key, expected in {
        "bundleManifestSha256": "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "trainJsonlSha256": "458de009e4ef227361e2813c7380bfa2d42739f36335ed333ea3b6a250800db3",
        "validationJsonlSha256": "020324cb8d4b5d4fc0737fd741e498640d3636c326a58d25428db88279a3bd16",
        "trainRecords": 72,
        "validationRecords": 36,
        "trainIndexSha256": "0ab27caccc5ba11d9d321660197794cff8d2c074fdb843f0149204234a328104",
        "validationIndexSha256": "70f546c7d3b9c3a99c0e2efc4d16335ea7d1e9fdab90ee7e4f7d1017a8d29c5",
    }.items():
        _require_exact(data.get(key), expected, f"data.{key}")

    training = contract.get("training")
    if not isinstance(training, dict):
        raise ValueError("P2-41 training authorization is missing")
    expected_training = {
        "objective": "ordinary-next-token-v1",
        "optimizer": "AdamW",
        "learningRate": ADAMW_LEARNING_RATE,
        "betas": list(ADAMW_BETAS),
        "epsilon": ADAMW_EPSILON,
        "weightDecay": ADAMW_WEIGHT_DECAY,
        "gradientClippingNorm": 1.0,
        "schedule": SCHEDULE_KIND,
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "device": "cuda",
        "seed": SEED,
        "contextLength": DEFAULT_CONFIG.context_length,
        "dropout": DEFAULT_CONFIG.dropout,
        "expectedExamplesAt100Steps": MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION,
        "expectedRealTargetPositionsAt100Steps": 567311,
        "resumeAllowed": False,
        "automaticContinuation": False,
    }
    for key, expected in expected_training.items():
        _require_exact(training.get(key), expected, f"training.{key}")

    evaluation = contract.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("P2-41 evaluation authorization is missing")
    _require_exact(evaluation.get("method"), "sequential-packed-next-token-loss", "evaluation.method")
    _require_exact(evaluation.get("steps"), list(VALIDATION_STEPS), "evaluation.steps")
    _require_exact(evaluation.get("maximumBatches"), VALIDATION_MAXIMUM_BATCHES, "evaluation.maximumBatches")
    _require_exact(evaluation.get("checkpointSteps"), list(CHECKPOINT_STEPS), "evaluation.checkpointSteps")
    if not math.isclose(
        float(evaluation.get("baselineLoss")),
        3.0144005020459494,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("P2-41 contract mismatch: evaluation.baselineLoss")

    protected = contract.get("protectedEvaluation")
    if not isinstance(protected, dict):
        raise ValueError("P2-41 protected evaluation contract is missing")
    for key in (
        "validationExcludedFromGradients",
        "p231DevelopmentExcludedFromGradients",
        "finalProjectHoldoutMustRemainClosed",
    ):
        _require_exact(protected.get(key), True, f"protectedEvaluation.{key}")


def _training_settings(contract_sha: str, sampler: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "kind": "p2-41-authorized-request-binding-training-v1",
        "authorizationContractSha256": contract_sha,
        "objective": "ordinary-next-token-v1",
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "optimizer": {
            "kind": "AdamW",
            "learningRate": ADAMW_LEARNING_RATE,
            "betas": list(ADAMW_BETAS),
            "epsilon": ADAMW_EPSILON,
            "weightDecay": ADAMW_WEIGHT_DECAY,
        },
        "gradientClippingNorm": 1.0,
        "learningRateSchedule": SCHEDULE_KIND,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "resumeAllowed": False,
        "automaticContinuation": False,
        "samplingPolicy": sampler,
    }


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _save_run_checkpoint(
    *,
    path: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    step: int,
    rng: random.Random,
    device: torch.device,
    artifact_root: Path,
    payload: dict[str, Any],
    bundle: dict[str, Any],
    settings: dict[str, Any],
    tokens_processed: int,
) -> dict[str, Any]:
    saved = save_checkpoint(
        model,
        optimizer,
        step=step,
        seed=SEED,
        codec=CODEC,
        sampling_rng=rng,
        device=device,
        destination=path,
        artifact_root=artifact_root,
        initialization_record=payload["initializationRecord"],
        stage_transition_record=payload["stageTransitionRecord"],
        tokenizer_record=bundle["tokenizer"],
        dataset_record=bundle["dataset"],
        training_settings=settings,
        schedule_state={"kind": SCHEDULE_KIND, "step": step, "learningRate": ADAMW_LEARNING_RATE},
        tokens_processed_total=tokens_processed,
    )
    _, checked = read_checkpoint(path, torch.device("cpu"))
    if (
        checked.get("step") != step
        or checked.get("tokensProcessedTotal") != tokens_processed
        or checked.get("stageTransitionRecord") != payload["stageTransitionRecord"]
        or checked.get("trainingSettings") != settings
        or checked.get("datasetRecord") != bundle["dataset"]
        or checked.get("tokenizerRecord") != bundle["tokenizer"]
    ):
        raise ValueError("Saved P2-41 checkpoint failed identity verification")
    return {**saved, "sha256": sha256_file(path)}


def run_request_binding_training(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path = DEFAULT_AUTHORIZATION_CONTRACT,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    output_dir: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Execute the single bounded owner-authorized P2-41 first run."""
    auth = _json(authorization_contract_path)
    _validate_authorization(auth)

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / AUTHORIZED_OUTPUT_DIRECTORY, root)
    if output != expected_output:
        raise ValueError("P2-41 first run must use the approved output directory")
    if output.exists():
        raise FileExistsError("P2-41 first-run output already exists; resume/overwrite are not supported")

    preflight = preflight_request_binding_training(
        bundle_dir=bundle_dir,
        stage_checkpoint=stage_checkpoint,
        preparation_contract_path=preparation_contract_path,
        output_dir=output_dir,
        artifact_root=artifact_root,
        require_cuda=True,
    )
    for key, expected in {
        "bundleManifestSha256": auth["data"]["bundleManifestSha256"],
        "stageCheckpointSha256": auth["baseStage"]["checkpointSha256"],
        "candidateSha256": auth["data"]["candidateSha256"],
        "tokenizerSha256": auth["data"]["tokenizerSha256"],
        "trainJsonlSha256": auth["data"]["trainJsonlSha256"],
        "validationJsonlSha256": auth["data"]["validationJsonlSha256"],
        "trainIndexSha256": auth["data"]["trainIndexSha256"],
        "validationIndexSha256": auth["data"]["validationIndexSha256"],
        "expectedRealTargetPositionsAt100Steps": auth["training"]["expectedRealTargetPositionsAt100Steps"],
    }.items():
        _require_exact(preflight.get(key), expected, f"preflight.{key}")
    if not math.isclose(
        float(preflight["baselineValidationLoss"]),
        float(auth["evaluation"]["baselineLoss"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("P2-41 baseline validation loss changed before training")

    bundle = inspect_request_binding_bundle(bundle_dir, preparation_contract_path)
    model, payload = _verify_stage(stage_checkpoint, bundle)
    tokenizer = PlexTokenizer.load(bundle["root"])
    device = select_device("cuda")
    enforce_storage_limit(root, additional_bytes=2 * 1024**3)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    checkpoints_dir = output / "checkpoints"
    checkpoints_dir.mkdir()
    metrics_path = output / "metrics.jsonl"

    seed_everything(SEED)
    rng = random.Random(SEED)
    model = model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-41 optimizer unexpectedly contains state")

    auth_sha = sha256_file(authorization_contract_path)
    source_sha = sha256_file(stage_checkpoint)

    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train, TokenCorpus(bundle["validationPath"]) as validation:
        _require_exact(train.sampler_record, auth["training"]["sampler"], "runtime sampler")
        settings = _training_settings(auth_sha, train.sampler_record)
        reset_peak_gpu_memory(device)

        baseline = _validation_loss(
            model,
            validation,
            device,
            maximum_batches=VALIDATION_MAXIMUM_BATCHES,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
        )
        if not math.isclose(
            baseline,
            float(auth["evaluation"]["baselineLoss"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("P2-41 stage-zero baseline changed before training")

        started = time.perf_counter()
        deadline = started + MAXIMUM_WALL_SECONDS
        validations = [{"step": 0, "meanLoss": baseline}]
        losses: list[float] = []
        tokens_seen = 0
        padding_seen = 0
        saved_checkpoints: list[dict[str, Any]] = []
        interrupted = False

        _append_jsonl(
            metrics_path,
            {
                "event": "run_started",
                "startedAtUtc": datetime.now(timezone.utc).isoformat(),
                "authorizationContractSha256": auth_sha,
                "stageCheckpointSha256": source_sha,
                "trainingSettings": settings,
                "environment": environment_report(device),
            },
        )

        try:
            while len(losses) < MAXIMUM_STEPS and time.perf_counter() < deadline:
                loss, real_positions, padding_positions = _structured_plan_training_step(
                    model,
                    optimizer,
                    train,
                    rng,
                    device,
                    micro_batch=MICRO_BATCH,
                    accumulation_steps=GRADIENT_ACCUMULATION,
                    loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                )
                step = len(losses) + 1
                losses.append(loss)
                tokens_seen += real_positions
                padding_seen += padding_positions
                _append_jsonl(
                    metrics_path,
                    {
                        "event": "training_progress",
                        "step": step,
                        "loss": loss,
                        "tokensProcessedTotal": tokens_seen,
                        "elapsedSeconds": time.perf_counter() - started,
                    },
                )

                if step in VALIDATION_STEPS:
                    value = _validation_loss(
                        model,
                        validation,
                        device,
                        maximum_batches=VALIDATION_MAXIMUM_BATCHES,
                        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                    )
                    validations.append({"step": step, "meanLoss": value})
                    _append_jsonl(
                        metrics_path,
                        {"event": "validation", "step": step, "meanLoss": value},
                    )

                if step in CHECKPOINT_STEPS:
                    saved = _save_run_checkpoint(
                        path=checkpoints_dir / f"step-{step:04d}.pt",
                        model=model,
                        optimizer=optimizer,
                        step=step,
                        rng=rng,
                        device=device,
                        artifact_root=root,
                        payload=payload,
                        bundle=bundle,
                        settings=settings,
                        tokens_processed=tokens_seen,
                    )
                    saved_checkpoints.append(saved)
                    _append_jsonl(metrics_path, {"event": "checkpoint_saved", **saved})
        except KeyboardInterrupt:
            interrupted = True

        completed_steps = len(losses)
        final = next((item for item in saved_checkpoints if item["step"] == completed_steps), None)
        if final is None:
            final = _save_run_checkpoint(
                path=checkpoints_dir / f"step-{completed_steps:04d}-final.pt",
                model=model,
                optimizer=optimizer,
                step=completed_steps,
                rng=rng,
                device=device,
                artifact_root=root,
                payload=payload,
                bundle=bundle,
                settings=settings,
                tokens_processed=tokens_seen,
            )
            saved_checkpoints.append(final)

        if sha256_file(stage_checkpoint) != source_sha:
            raise ValueError("P2-41 stage source changed during training")

        result = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "kind": "p2-41-first-request-binding-run-result-v1",
            "trainingPerformed": completed_steps > 0,
            "researchOptimizerUpdates": completed_steps,
            "authorizedMaximumSteps": MAXIMUM_STEPS,
            "authorizedMaximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
            "automaticContinuation": False,
            "resumeAllowed": False,
            "continuationAuthorized": False,
            "finalHoldoutOpened": False,
            "interrupted": interrupted,
            "elapsedSeconds": time.perf_counter() - started,
            "stageCheckpointSha256": source_sha,
            "authorizationContractSha256": auth_sha,
            "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
            "completedSteps": completed_steps,
            "tokensProcessed": tokens_seen,
            "paddingTargetPositions": padding_seen,
            "meanRecentLoss": sum(losses[-20:]) / len(losses[-20:]) if losses else None,
            "validation": validations,
            "samplingAudit": train.sampling_audit(),
            "checkpoints": saved_checkpoints,
            "finalCheckpoint": final,
            "peakGpuMemory": peak_gpu_memory(device),
            "p231DevelopmentEvaluationPending": True,
        }

    result_path = output / "run-result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    enforce_storage_limit(root)
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "result": str(result_path.relative_to(root)),
        "metrics": str(metrics_path.relative_to(root)),
    }
