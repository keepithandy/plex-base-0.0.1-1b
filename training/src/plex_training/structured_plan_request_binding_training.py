"""P2-41 request-conditioned plan-binding bundle, stage, and read-only preflight.

All commands in this module perform zero optimizer updates. No P2-41 training
runner exists until a later owner-approved authorization packet is committed.
"""

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

from .artifacts import path_within_root
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
    _validation_loss,
)
from .structured_plan import canonical_text_sha256, render_plan_request_prompt
from .structured_plan_request_binding_curriculum import (
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_TOKENIZER_BUNDLE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    review_request_binding_curriculum,
)
from .structured_plan_semantic_binding_training import StructuredPlanCompleteRecordCorpus
from .telemetry import select_device
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
