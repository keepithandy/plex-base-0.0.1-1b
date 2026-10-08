"""Read-only P2-44 stage-source compatibility preflight.

This module verifies the exact P2-41 step-100 endpoint and frozen P2-44 bundle.
It does not create an optimizer, stage checkpoint, or training state.
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Any

import torch

from .artifacts import path_within_root
from .checkpoint import read_checkpoint, save_checkpoint
from .config import DEFAULT_CONFIG
from .model import parameter_count
from .runner import ADAMW_BETAS, ADAMW_EPSILON, ADAMW_LEARNING_RATE, ADAMW_WEIGHT_DECAY
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
DEFAULT_STAGE_CONTRACT = Path("training/pretraining/p2-44-step-zero-stage-contract.json")
DEFAULT_STAGE_OUTPUT = Path("training/artifacts/structured-plan/p2-44-stage0")
STAGE_CONTRACT_KIND = "plex-p2-44-step-zero-stage-contract-v1"
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


def _stage_contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != STAGE_CONTRACT_KIND
        or value.get("status") != "stage-authorized-training-not-authorized"
        or value.get("checkpointStagingAuthorized") is not True
        or value.get("optimizerCreationAuthorized") is not True
        or value.get("optimizerUseAuthorizedForSerializationOnly") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
        or value.get("approvedBy") != "keepithandy"
        or value.get("approvedDate") != "2026-10-08"
    ):
        raise ValueError("P2-44 step-zero stage contract is invalid")

    base = value.get("baseCheckpoint")
    if base != {
        "path": "training/artifacts/structured-plan/p2-41-first-run/checkpoints/step-0100.pt",
        "sha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "step": 100,
        "milestone": "P2-41",
        "tokensProcessedTotal": 567311,
        "parameterCount": 27566080,
        "stageKind": EXPECTED_BASE_STAGE_KIND,
        "trainingSettingsKind": EXPECTED_BASE_TRAINING_KIND,
    }:
        raise ValueError("P2-44 stage base checkpoint identity changed")

    stage = value.get("stage")
    if stage != {
        "outputDirectory": "structured-plan/p2-44-stage0",
        "checkpointName": "stage-checkpoint.pt",
        "transitionKind": PROPOSED_STAGE_KIND,
        "seed": 1337,
        "p244StageStep": 0,
        "p244TokensProcessed": 0,
        "modelWeightsLoadedFromBase": True,
        "modelWeightsMustMatchBaseExactly": True,
        "baseOptimizerStateReused": False,
        "freshOptimizerStateMustBeEmpty": True,
        "baseSamplerStateReused": False,
        "samplerStateMustResetToSeed": True,
        "baseTrainingStepReusedAsP244Step": False,
        "trainingSettingsMustBeNull": True,
        "scheduleStateMustBeNull": True,
    }:
        raise ValueError("P2-44 step-zero stage semantics changed")

    optimizer = value.get("optimizerSerialization")
    if optimizer != {
        "kind": "AdamW",
        "learningRate": ADAMW_LEARNING_RATE,
        "betas": list(ADAMW_BETAS),
        "epsilon": ADAMW_EPSILON,
        "weightDecay": ADAMW_WEIGHT_DECAY,
        "gradientUpdatesAuthorized": 0,
    }:
        raise ValueError("P2-44 stage optimizer serialization settings changed")
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


def create_evidence_composition_stage(
    *,
    base_checkpoint: Path = DEFAULT_BASE_CHECKPOINT,
    bundle_dir: Path = DEFAULT_BUNDLE,
    output_dir: Path = DEFAULT_STAGE_OUTPUT,
    artifact_root: Path = Path("training/artifacts"),
    source_contract_path: Path = DEFAULT_CONTRACT,
    stage_contract_path: Path = DEFAULT_STAGE_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Create one untouched P2-44 step-zero stage. Performs zero optimizer updates."""
    _stage_contract(stage_contract_path)
    source = preflight_evidence_composition_stage_source(
        base_checkpoint=base_checkpoint,
        bundle_dir=bundle_dir,
        contract_path=source_contract_path,
    )
    if (
        source.get("status") != "stage-source-preflight-passed-awaiting-stage-authorization"
        or source.get("baseCheckpointSha256") != EXPECTED_BASE_CHECKPOINT_SHA256
        or source.get("weightsSourceVerified") is not True
        or source.get("bundleCompatibilityVerified") is not True
        or source.get("stageCheckpointCreated") is not False
        or source.get("optimizerCreated") is not False
    ):
        raise ValueError("P2-44 stage-source preflight no longer matches authorization")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / "structured-plan/p2-44-stage0", root)
    if output != expected_output:
        raise ValueError("P2-44 stage must use the locked stage0 output directory")
    if output.exists():
        raise FileExistsError("P2-44 stage0 output already exists")
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")

    bundle = inspect_evidence_composition_bundle(bundle_dir)
    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    base_state = {name: value.detach().clone() for name, value in model.state_dict().items()}

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-44 stage optimizer unexpectedly contains state")

    rng = random.Random(1337)
    transition = {
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

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    checkpoint = output / "stage-checkpoint.pt"
    try:
        save_checkpoint(
            model,
            optimizer,
            step=0,
            seed=1337,
            codec=CODEC,
            sampling_rng=rng,
            device=torch.device("cpu"),
            destination=checkpoint,
            artifact_root=root,
            initialization_record=payload["initializationRecord"],
            stage_transition_record=transition,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            training_settings=None,
            schedule_state=None,
            tokens_processed_total=0,
        )
        saved_model, saved = read_checkpoint(checkpoint, torch.device("cpu"))
        weights_equal = all(
            torch.equal(value, saved_model.state_dict()[name])
            for name, value in base_state.items()
        )
        if (
            not weights_equal
            or saved.get("optimizerStateDict", {}).get("state") != {}
            or saved.get("step") != 0
            or saved.get("tokensProcessedTotal") != 0
            or saved.get("samplingRngState") != random.Random(1337).getstate()
            or saved.get("stageTransitionRecord") != transition
            or saved.get("tokenizerRecord") != bundle["tokenizer"]
            or saved.get("datasetRecord") != bundle["dataset"]
            or saved.get("trainingSettings") is not None
            or saved.get("scheduleState") is not None
        ):
            raise ValueError("Saved P2-44 stage failed zero-update identity verification")

        report = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "status": "stage-created-training-not-authorized",
            "trainingPerformed": False,
            "researchOptimizerUpdates": 0,
            "finalHoldoutOpened": False,
            "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
            "baseCheckpointStep": EXPECTED_BASE_STEP,
            "stageCheckpoint": "stage-checkpoint.pt",
            "stageCheckpointSha256": sha256_file(checkpoint),
            "parameterCount": parameter_count(saved_model),
            "modelWeightsPreserved": weights_equal,
            "modelWeightEqualityMethod": "torch.equal for every model-state tensor after reload",
            "freshOptimizerCreatedForSerialization": True,
            "optimizerStateReused": False,
            "optimizerStateEmpty": saved.get("optimizerStateDict", {}).get("state") == {},
            "samplerStateReset": True,
            "p244StageStep": 0,
            "p244TokensProcessed": 0,
            "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "trainingSettings": None,
            "scheduleState": None,
            "stageTransition": transition,
            "checkpointStagingAuthorized": True,
            "modelTrainingAuthorized": False,
        }
        (output / "stage-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
        if size > storage_limit_bytes:
            raise ValueError("P2-44 stage exceeds remaining artifact storage allocation")
        return report
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise
