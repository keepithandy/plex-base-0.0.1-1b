"""P2-48 read-only CUDA training preflight for request-grounded coding."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import torch

from .artifacts import path_within_root
from .checkpoint import read_checkpoint
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .model import parameter_count
from .request_grounded_coding_bundle import inspect_request_grounded_bundle
from .request_grounded_coding_stage import (
    EXPECTED_BASE_CHECKPOINT_SHA256,
    EXPECTED_BUNDLE_MANIFEST_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_SOURCE_DATASET_MANIFEST_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    EXPECTED_TRAIN_INDEX_SHA256,
    EXPECTED_TRAIN_JSONL_SHA256,
    EXPECTED_TRAIN_TOKENS_SHA256,
    EXPECTED_VALIDATION_INDEX_SHA256,
    EXPECTED_VALIDATION_JSONL_SHA256,
    EXPECTED_VALIDATION_TOKENS_SHA256,
    PROPOSED_STAGE_KIND,
)
from .runner import (
    ADAMW_BETAS,
    ADAMW_EPSILON,
    ADAMW_LEARNING_RATE,
    ADAMW_WEIGHT_DECAY,
    SCHEDULE_KIND,
    _validation_loss,
)
from .structured_plan_semantic_binding_training import (
    StructuredPlanCompleteRecordCorpus,
)
from .telemetry import select_device
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-48"
CONTRACT_KIND = "plex-p2-48-training-preflight-contract-v1"
DEFAULT_CONTRACT = Path(
    "training/pretraining/p2-48-training-preflight-contract.json"
)
DEFAULT_STAGE_CHECKPOINT = Path(
    "training/artifacts/request-grounded/p2-48-stage0/stage-checkpoint.pt"
)
DEFAULT_BUNDLE = Path(
    "training/artifacts/request-grounded/p2-48-training-bundle"
)
DEFAULT_OUTPUT = Path(
    "training/artifacts/request-grounded/p2-48-first-run"
)

EXPECTED_STAGE_CHECKPOINT_SHA256 = (
    "52aabd0c3d07125dfd89eafd1cd9ecfbb79cbf8a89dfa15c8f8334ead3f2dd60"
)
SEED = 1337
MAXIMUM_STEPS = 100
MAXIMUM_WALL_SECONDS = 600
MICRO_BATCH = 1
GRADIENT_ACCUMULATION = 16
VALIDATION_MAXIMUM_BATCHES = 100
VALIDATION_STEPS = (0, 25, 50, 75, 100)
CHECKPOINT_STEPS = (25, 50, 75, 100)
EXPECTED_EXAMPLES = MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION
EXPECTED_REAL_TARGET_POSITIONS = 429375
AUTHORIZED_OUTPUT_DIRECTORY = "request-grounded/p2-48-first-run"
EXPECTED_TRAIN_RECORDS = 72
EXPECTED_VALIDATION_RECORDS = 36
EXPECTED_TRAIN_TOKEN_COUNT = 19377
EXPECTED_VALIDATION_TOKEN_COUNT = 9763
EXPECTED_VALIDATION_BATCHES = 19
EXPECTED_TEXT_PREFIX = (
    "Map the coding request to one request-grounded change record.\n"
)


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != CONTRACT_KIND
        or value.get("status")
        != "training-preflight-authorized-training-not-authorized"
        or value.get("trainingPreflightAuthorized") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("optimizerStepAuthorized") is not False
        or value.get("checkpointWriteAuthorized") is not False
        or value.get("automaticContinuation") is not False
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-48 training preflight contract violates zero-update boundary")

    if value.get("stage") != {
        "path": "training/artifacts/request-grounded/p2-48-stage0/stage-checkpoint.pt",
        "sha256": EXPECTED_STAGE_CHECKPOINT_SHA256,
        "step": 0,
        "tokensProcessed": 0,
        "parameterCount": DEFAULT_CONFIG.parameter_count(),
        "modelWeightsPreserved": True,
        "optimizerStateEmpty": True,
        "samplerStateReset": True,
        "transitionKind": PROPOSED_STAGE_KIND,
    }:
        raise ValueError("P2-48 preflight stage identity changed")

    if value.get("data") != {
        "bundlePath": "training/artifacts/request-grounded/p2-48-training-bundle",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "sourceDatasetManifestSha256": EXPECTED_SOURCE_DATASET_MANIFEST_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "trainJsonlSha256": EXPECTED_TRAIN_JSONL_SHA256,
        "validationJsonlSha256": EXPECTED_VALIDATION_JSONL_SHA256,
        "trainTokensSha256": EXPECTED_TRAIN_TOKENS_SHA256,
        "validationTokensSha256": EXPECTED_VALIDATION_TOKENS_SHA256,
        "trainIndexSha256": EXPECTED_TRAIN_INDEX_SHA256,
        "validationIndexSha256": EXPECTED_VALIDATION_INDEX_SHA256,
        "trainRecords": EXPECTED_TRAIN_RECORDS,
        "validationRecords": EXPECTED_VALIDATION_RECORDS,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
    }:
        raise ValueError("P2-48 training preflight data identity changed")

    if value.get("proposal") != {
        "outputDirectory": AUTHORIZED_OUTPUT_DIRECTORY,
        "device": "cuda",
        "seed": SEED,
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
        "validationMaximumBatches": VALIDATION_MAXIMUM_BATCHES,
        "validationSteps": list(VALIDATION_STEPS),
        "checkpointSteps": list(CHECKPOINT_STEPS),
        "expectedExamplesAt100Steps": EXPECTED_EXAMPLES,
        "expectedRealTargetPositionsAt100Steps": EXPECTED_REAL_TARGET_POSITIONS,
        "resumeAllowed": False,
        "automaticContinuation": False,
    }:
        raise ValueError("P2-48 proposed training schedule changed")

    if value.get("protectedEvaluation") != {
        "validationExcludedFromGradients": True,
        "p231DevelopmentExcludedFromGradients": True,
        "p242ResponsesExcludedFromGradients": True,
        "p243DiagnosticExcludedFromGradients": True,
        "p245ResponsesExcludedFromGradients": True,
        "p246DiagnosticExcludedFromGradients": True,
        "finalProjectHoldoutMustRemainClosed": True,
    }:
        raise ValueError("P2-48 protected evaluation boundary changed")
    return value


def _verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle = inspect_request_grounded_bundle(bundle_dir)
    if (
        sha256_file(bundle["root"] / "manifest.json") != EXPECTED_BUNDLE_MANIFEST_SHA256
        or bundle["dataset"]["sourceDatasetManifestSha256"]
        != EXPECTED_SOURCE_DATASET_MANIFEST_SHA256
        or bundle["dataset"]["trainJsonlSha256"] != EXPECTED_TRAIN_JSONL_SHA256
        or bundle["dataset"]["validationJsonlSha256"]
        != EXPECTED_VALIDATION_JSONL_SHA256
        or bundle["dataset"]["trainTokensSha256"] != EXPECTED_TRAIN_TOKENS_SHA256
        or bundle["dataset"]["validationTokensSha256"]
        != EXPECTED_VALIDATION_TOKENS_SHA256
        or bundle["dataset"]["trainIndexSha256"] != EXPECTED_TRAIN_INDEX_SHA256
        or bundle["dataset"]["validationIndexSha256"]
        != EXPECTED_VALIDATION_INDEX_SHA256
        or bundle["tokenizer"]["tokenizerSha256"] != EXPECTED_TOKENIZER_SHA256
        or bundle["dataset"]["trainRecords"] != EXPECTED_TRAIN_RECORDS
        or bundle["dataset"]["validationRecords"] != EXPECTED_VALIDATION_RECORDS
        or bundle["dataset"]["trainTokenCount"] != EXPECTED_TRAIN_TOKEN_COUNT
        or bundle["dataset"]["validationTokenCount"] != EXPECTED_VALIDATION_TOKEN_COUNT
    ):
        raise ValueError("P2-48 bundle differs from frozen preflight identity")
    return bundle


def _verify_stage(
    stage_checkpoint: Path,
    bundle: dict[str, Any],
) -> tuple[torch.nn.Module, dict[str, Any]]:
    if stage_checkpoint.is_symlink() or not stage_checkpoint.is_file():
        raise ValueError("P2-48 stage checkpoint must be a regular local file")
    if sha256_file(stage_checkpoint) != EXPECTED_STAGE_CHECKPOINT_SHA256:
        raise ValueError("P2-48 training preflight requires the exact stage0 checkpoint")

    model, payload = read_checkpoint(stage_checkpoint, torch.device("cpu"))
    transition = payload.get("stageTransitionRecord")
    if (
        model.config != DEFAULT_CONFIG
        or parameter_count(model) != DEFAULT_CONFIG.parameter_count()
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
        or transition.get("kind") != PROPOSED_STAGE_KIND
        or transition.get("milestone") != MILESTONE
        or transition.get("baseCheckpointSha256") != EXPECTED_BASE_CHECKPOINT_SHA256
        or transition.get("baseCheckpointStep") != 100
        or transition.get("baseMilestone") != "P2-44"
        or transition.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or transition.get("bundleManifestSha256") != EXPECTED_BUNDLE_MANIFEST_SHA256
        or transition.get("modelWeightsLoadedFromBase") is not True
        or transition.get("baseOptimizerStateReused") is not False
        or transition.get("baseSamplerStateReused") is not False
        or transition.get("baseTrainingStepReusedAsP248Step") is not False
        or transition.get("p248StageStep") != 0
        or transition.get("p248TokensProcessed") != 0
        or transition.get("modelTrainingPerformed") is not False
    ):
        raise ValueError("P2-48 stage checkpoint is not the untouched frozen stage")
    return model, payload


def preflight_request_grounded_training(
    *,
    bundle_dir: Path = DEFAULT_BUNDLE,
    stage_checkpoint: Path = DEFAULT_STAGE_CHECKPOINT,
    contract_path: Path = DEFAULT_CONTRACT,
    output_dir: Path = DEFAULT_OUTPUT,
    artifact_root: Path = Path("training/artifacts"),
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Verify the P2-48 packet and measure step-zero validation loss without training."""
    _contract(contract_path)
    bundle = _verify_bundle(bundle_dir)
    model, _ = _verify_stage(stage_checkpoint, bundle)

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / AUTHORIZED_OUTPUT_DIRECTORY, root)
    if output != expected_output:
        raise ValueError("P2-48 proposed run must use the locked output directory")
    if output.exists():
        raise FileExistsError("P2-48 proposed first-run output already exists")

    tokenizer = PlexTokenizer.load(bundle["root"])
    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
        expected_text_prefix=EXPECTED_TEXT_PREFIX,
    ) as train:
        expected_positions, _ = train.replay_progress(SEED, EXPECTED_EXAMPLES)
        sampler = train.sampler_record
    if expected_positions != EXPECTED_REAL_TARGET_POSITIONS:
        raise ValueError("P2-48 sampler replay differs from frozen accounting")

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
        "status": "training-preflight-passed-awaiting-owner-authorization",
        "authorized": False,
        "trainingPreflightAuthorized": True,
        "modelTrainingAuthorized": False,
        "optimizerStepAuthorized": False,
        "checkpointWriteAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "stageCheckpointSha256": EXPECTED_STAGE_CHECKPOINT_SHA256,
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "sourceDatasetManifestSha256": EXPECTED_SOURCE_DATASET_MANIFEST_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "trainRecords": EXPECTED_TRAIN_RECORDS,
        "validationRecords": EXPECTED_VALIDATION_RECORDS,
        "trainJsonlSha256": EXPECTED_TRAIN_JSONL_SHA256,
        "validationJsonlSha256": EXPECTED_VALIDATION_JSONL_SHA256,
        "trainTokensSha256": EXPECTED_TRAIN_TOKENS_SHA256,
        "validationTokensSha256": EXPECTED_VALIDATION_TOKENS_SHA256,
        "trainIndexSha256": EXPECTED_TRAIN_INDEX_SHA256,
        "validationIndexSha256": EXPECTED_VALIDATION_INDEX_SHA256,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
        "sampler": sampler,
        "expectedExamplesAt100Steps": EXPECTED_EXAMPLES,
        "expectedRealTargetPositionsAt100Steps": expected_positions,
        "baselineValidationLoss": baseline_loss,
        "baselineValidationBatches": EXPECTED_VALIDATION_BATCHES,
        "proposedMaximumSteps": MAXIMUM_STEPS,
        "proposedMaximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "proposedValidationSteps": list(VALIDATION_STEPS),
        "proposedCheckpointSteps": list(CHECKPOINT_STEPS),
        "proposedMicroBatch": MICRO_BATCH,
        "proposedGradientAccumulation": GRADIENT_ACCUMULATION,
        "proposedDevice": "cuda" if require_cuda else "cpu",
        "outputWouldBe": str(output.relative_to(root)),
        "automaticContinuation": False,
        "resumeAllowed": False,
    }
