"""Read-only P2-44 stage-source compatibility preflight.

This module verifies the exact P2-41 step-100 endpoint and frozen P2-44 bundle.
It does not create an optimizer, stage checkpoint, or training state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from .checkpoint import read_checkpoint
from .config import DEFAULT_CONFIG
from .model import parameter_count
from .structured_plan_evidence_composition_bundle import (
    inspect_evidence_composition_bundle,
)
from .structured_plan_evidence_composition_curriculum import (
    EXPECTED_BUNDLE_MANIFEST_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_SOURCE_DATASET_MANIFEST_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    EXPECTED_TRAIN_INDEX_SHA256,
    EXPECTED_TRAIN_JSONL_SHA256,
    EXPECTED_VALIDATION_INDEX_SHA256,
    EXPECTED_VALIDATION_JSONL_SHA256,
)
from .tokenizer import CODEC, sha256_file

MILESTONE = "P2-44"
CONTRACT_KIND = "plex-p2-44-stage-source-preparation-contract-v1"
DEFAULT_CONTRACT = Path("training/pretraining/p2-44-stage-source-preparation-contract.json")
DEFAULT_BASE_CHECKPOINT = Path(
    "training/artifacts/structured-plan/p2-41-first-run/checkpoints/step-0100.pt"
)
DEFAULT_BUNDLE = Path("training/artifacts/structured-plan/p2-44-training-bundle")
EXPECTED_BASE_CHECKPOINT_SHA256 = (
    "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc"
)
EXPECTED_BASE_STEP = 100
EXPECTED_BASE_TOKENS = 567311
EXPECTED_BASE_STAGE_KIND = "plex-request-conditioned-plan-binding-stage-transition-v1"
EXPECTED_BASE_TRAINING_KIND = "p2-41-authorized-request-binding-training-v1"
PROPOSED_STAGE_KIND = "plex-evidence-first-semantic-composition-stage-transition-v1"


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
        or value.get("status") != "stage-source-preflight-authorized"
        or value.get("stageSourcePreflightAuthorized") is not True
        or value.get("checkpointStagingAuthorized") is not False
        or value.get("optimizerCreationAuthorized") is not False
        or value.get("modelTrainingAuthorized") is not False
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-44 stage-source contract does not preserve read-only status")

    base = value.get("baseCheckpoint")
    if not isinstance(base, dict):
        raise ValueError("P2-44 stage-source base checkpoint identity is missing")
    if (
        base.get("sha256") != EXPECTED_BASE_CHECKPOINT_SHA256
        or base.get("step") != EXPECTED_BASE_STEP
        or base.get("milestone") != "P2-41"
        or base.get("tokensProcessedTotal") != EXPECTED_BASE_TOKENS
        or base.get("requiredProvenance")
        != {
            "stageKind": EXPECTED_BASE_STAGE_KIND,
            "stageMilestone": "P2-41",
            "trainingSettingsKind": EXPECTED_BASE_TRAINING_KIND,
        }
    ):
        raise ValueError("P2-44 base checkpoint contract identity changed")

    bundle = value.get("p244Bundle")
    if not isinstance(bundle, dict):
        raise ValueError("P2-44 stage-source bundle identity is missing")
    expected_bundle = {
        "path": "training/artifacts/structured-plan/p2-44-training-bundle",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "sourceDatasetManifestSha256": EXPECTED_SOURCE_DATASET_MANIFEST_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "trainJsonlSha256": EXPECTED_TRAIN_JSONL_SHA256,
        "validationJsonlSha256": EXPECTED_VALIDATION_JSONL_SHA256,
        "trainIndexSha256": EXPECTED_TRAIN_INDEX_SHA256,
        "validationIndexSha256": EXPECTED_VALIDATION_INDEX_SHA256,
        "trainRecords": 108,
        "validationRecords": 54,
        "trainTokenCount": 38280,
        "validationTokenCount": 19186,
    }
    if bundle != expected_bundle:
        raise ValueError("P2-44 stage-source bundle contract identity changed")

    future = value.get("proposedFutureStage")
    if future != {
        "kind": PROPOSED_STAGE_KIND,
        "milestone": "P2-44",
        "baseCheckpointStep": 100,
        "p244StageStep": 0,
        "p244TokensProcessed": 0,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP244Step": False,
    }:
        raise ValueError("P2-44 proposed stage semantics changed")
    return value


def preflight_evidence_composition_stage_source(
    *,
    base_checkpoint: Path = DEFAULT_BASE_CHECKPOINT,
    bundle_dir: Path = DEFAULT_BUNDLE,
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Verify the exact P2-41 endpoint and P2-44 bundle without creating stage state."""
    _contract(contract_path)

    if base_checkpoint.is_symlink() or not base_checkpoint.is_file():
        raise ValueError("P2-44 base checkpoint must be a regular local file")
    base_sha = sha256_file(base_checkpoint)
    if base_sha != EXPECTED_BASE_CHECKPOINT_SHA256:
        raise ValueError("P2-44 requires the exact P2-41 step-100 checkpoint")

    bundle = inspect_evidence_composition_bundle(bundle_dir)
    if (
        sha256_file(bundle["root"] / "manifest.json") != EXPECTED_BUNDLE_MANIFEST_SHA256
        or bundle["dataset"]["sourceDatasetManifestSha256"]
        != EXPECTED_SOURCE_DATASET_MANIFEST_SHA256
        or bundle["dataset"]["trainJsonlSha256"] != EXPECTED_TRAIN_JSONL_SHA256
        or bundle["dataset"]["validationJsonlSha256"] != EXPECTED_VALIDATION_JSONL_SHA256
        or bundle["dataset"]["trainIndexSha256"] != EXPECTED_TRAIN_INDEX_SHA256
        or bundle["dataset"]["validationIndexSha256"] != EXPECTED_VALIDATION_INDEX_SHA256
        or bundle["tokenizer"]["tokenizerSha256"] != EXPECTED_TOKENIZER_SHA256
    ):
        raise ValueError("P2-44 frozen bundle differs from the reviewed preflight")

    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    transition = payload.get("stageTransitionRecord")
    training = payload.get("trainingSettings")
    tokenizer = payload.get("tokenizerRecord")

    if (
        model.config != DEFAULT_CONFIG
        or parameter_count(model) != DEFAULT_CONFIG.parameter_count()
        or payload.get("step") != EXPECTED_BASE_STEP
        or payload.get("tokensProcessedTotal") != EXPECTED_BASE_TOKENS
        or payload.get("seed") != 1337
        or payload.get("codec") != CODEC
        or not isinstance(payload.get("initializationRecord"), dict)
        or payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False
        or payload["initializationRecord"].get("pretrainedModelWeightsLoaded") is not False
        or not isinstance(transition, dict)
        or transition.get("kind") != EXPECTED_BASE_STAGE_KIND
        or transition.get("milestone") != "P2-41"
        or not isinstance(training, dict)
        or training.get("kind") != EXPECTED_BASE_TRAINING_KIND
        or not isinstance(tokenizer, dict)
        or tokenizer.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer.get("actualVocabularySize") != 16384
    ):
        raise ValueError("P2-41 endpoint provenance does not satisfy P2-44 stage-source contract")

    proposed_transition = {
        "schemaVersion": 1,
        "kind": PROPOSED_STAGE_KIND,
        "milestone": MILESTONE,
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "baseCheckpointStep": EXPECTED_BASE_STEP,
        "baseMilestone": "P2-41",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP244Step": False,
        "p244StageStep": 0,
        "p244TokensProcessed": 0,
        "modelTrainingPerformed": False,
    }

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "stage-source-preflight-passed-awaiting-stage-authorization",
        "baseCheckpointSha256": base_sha,
        "baseCheckpointStep": payload["step"],
        "baseTokensProcessedTotal": payload["tokensProcessedTotal"],
        "baseParameterCount": parameter_count(model),
        "baseStageKind": transition["kind"],
        "baseTrainingSettingsKind": training["kind"],
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "proposedStageTransition": proposed_transition,
        "weightsSourceVerified": True,
        "bundleCompatibilityVerified": True,
        "stageCheckpointCreated": False,
        "optimizerCreated": False,
        "modelTrainingAuthorized": False,
        "checkpointStagingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
