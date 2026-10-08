"""P2-48 stage-source verification and zero-update stage creation."""

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
from .request_grounded_coding_bundle import inspect_request_grounded_bundle
from .runner import ADAMW_BETAS, ADAMW_EPSILON, ADAMW_LEARNING_RATE, ADAMW_WEIGHT_DECAY
from .tokenizer import CODEC, sha256_file

MILESTONE = "P2-48"
SOURCE_CONTRACT_KIND = "plex-p2-48-stage-source-preparation-contract-v1"
STAGE_CONTRACT_KIND = "plex-p2-48-step-zero-stage-contract-v1"
DEFAULT_SOURCE_CONTRACT = Path(
    "training/pretraining/p2-48-stage-source-preparation-contract.json"
)
DEFAULT_STAGE_CONTRACT = Path(
    "training/pretraining/p2-48-step-zero-stage-contract.json"
)
DEFAULT_BASE_CHECKPOINT = Path(
    "training/artifacts/structured-plan/p2-44-first-run/checkpoints/step-0100.pt"
)
DEFAULT_BUNDLE = Path(
    "training/artifacts/request-grounded/p2-48-training-bundle"
)
DEFAULT_STAGE_OUTPUT = Path(
    "training/artifacts/request-grounded/p2-48-stage0"
)

EXPECTED_BASE_CHECKPOINT_SHA256 = (
    "69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e"
)
EXPECTED_BASE_STEP = 100
EXPECTED_BASE_TOKENS = 565641
EXPECTED_BASE_STAGE_KIND = "plex-evidence-first-semantic-composition-stage-transition-v1"
EXPECTED_BASE_TRAINING_KIND = "p2-44-authorized-evidence-composition-training-v1"

EXPECTED_CANDIDATE_SHA256 = (
    "6e39259cc8fc1646fb7a16d2056706312f8736d330f94a642690aaf9d1c1489a"
)
EXPECTED_BUNDLE_MANIFEST_SHA256 = (
    "71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7"
)
EXPECTED_SOURCE_DATASET_MANIFEST_SHA256 = (
    "6cab42b964f4d11680c4109cf4787f9074ba62a9cbff23f92b301d497f77771c"
)
EXPECTED_TOKENIZER_SHA256 = (
    "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
)
EXPECTED_TRAIN_JSONL_SHA256 = (
    "39879c1199e975096ba962fcad023b3b112c2c8b6444c0a3a9f35971a945d530"
)
EXPECTED_VALIDATION_JSONL_SHA256 = (
    "9f9514e0feda3e29eb63ee4308e87b94666f05229cfbd26a619a5a35a9708226"
)
EXPECTED_TRAIN_TOKENS_SHA256 = (
    "2aa8cb0d7970ae8ac329f71fd5d2df00df2345181ae9e8e79534f44409b46785"
)
EXPECTED_VALIDATION_TOKENS_SHA256 = (
    "8e8307953e2c1c4afcb7dc20c32f5a797611bf2371912a2480312f2094fc004c"
)
EXPECTED_TRAIN_INDEX_SHA256 = (
    "5d94bf9c3f0a0867cf945abd965f763c800444cba7162d6cbc522d5de049235f"
)
EXPECTED_VALIDATION_INDEX_SHA256 = (
    "2151edd14d340377feb42e2f1baa8fcbefe02aad070429e2dbf9ba519a79f52a"
)
PROPOSED_STAGE_KIND = "plex-request-grounded-coding-stage-transition-v1"


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _bundle_identity(value: dict[str, Any]) -> bool:
    return value == {
        "path": "training/artifacts/request-grounded/p2-48-training-bundle",
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
        "trainRecords": 72,
        "validationRecords": 36,
        "trainTokenCount": 19377,
        "validationTokenCount": 9763,
    }


def _source_contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != SOURCE_CONTRACT_KIND
        or value.get("status") != "stage-source-preflight-authorized"
        or value.get("stageSourcePreflightAuthorized") is not True
        or value.get("checkpointStagingAuthorized") is not False
        or value.get("optimizerCreationAuthorized") is not False
        or value.get("modelTrainingAuthorized") is not False
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-48 stage-source contract violates read-only boundary")

    base = value.get("baseCheckpoint")
    if base != {
        "path": "training/artifacts/structured-plan/p2-44-first-run/checkpoints/step-0100.pt",
        "sha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "step": 100,
        "milestone": "P2-44",
        "tokensProcessedTotal": EXPECTED_BASE_TOKENS,
        "requiredProvenance": {
            "stageKind": EXPECTED_BASE_STAGE_KIND,
            "stageMilestone": "P2-44",
            "trainingSettingsKind": EXPECTED_BASE_TRAINING_KIND,
        },
    }:
        raise ValueError("P2-48 stage-source base identity changed")
    if not isinstance(value.get("p248Bundle"), dict) or not _bundle_identity(
        value["p248Bundle"]
    ):
        raise ValueError("P2-48 stage-source bundle identity changed")
    if value.get("samplerPreflight") != {
        "status": "bundle-preflight-passed-awaiting-stage-decision",
        "seed": 1337,
        "examples": 1600,
        "recordsSelected": 72,
        "minimumRecordSelections": 12,
        "maximumRecordSelections": 33,
        "expectedRealTargetPositions": 429375,
    }:
        raise ValueError("P2-48 sampler preflight identity changed")
    if value.get("proposedFutureStage") != {
        "kind": PROPOSED_STAGE_KIND,
        "milestone": MILESTONE,
        "baseCheckpointStep": 100,
        "p248StageStep": 0,
        "p248TokensProcessed": 0,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP248Step": False,
    }:
        raise ValueError("P2-48 proposed stage semantics changed")
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
        raise ValueError("P2-48 stage contract is invalid")

    base = value.get("baseCheckpoint")
    if base != {
        "path": "training/artifacts/structured-plan/p2-44-first-run/checkpoints/step-0100.pt",
        "sha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "step": 100,
        "milestone": "P2-44",
        "tokensProcessedTotal": EXPECTED_BASE_TOKENS,
        "parameterCount": DEFAULT_CONFIG.parameter_count(),
        "stageKind": EXPECTED_BASE_STAGE_KIND,
        "trainingSettingsKind": EXPECTED_BASE_TRAINING_KIND,
    }:
        raise ValueError("P2-48 stage base identity changed")
    if not isinstance(value.get("p248Bundle"), dict) or not _bundle_identity(
        value["p248Bundle"]
    ):
        raise ValueError("P2-48 stage bundle identity changed")
    if value.get("stageSourcePreflight") != {
        "status": "stage-source-preflight-passed-awaiting-stage-authorization",
        "weightsSourceVerified": True,
        "bundleCompatibilityVerified": True,
        "stageCheckpointCreated": False,
        "optimizerCreated": False,
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "baseCheckpointStep": 100,
        "baseTokensProcessedTotal": EXPECTED_BASE_TOKENS,
        "baseParameterCount": DEFAULT_CONFIG.parameter_count(),
        "baseStageKind": EXPECTED_BASE_STAGE_KIND,
        "baseTrainingSettingsKind": EXPECTED_BASE_TRAINING_KIND,
    }:
        raise ValueError("P2-48 stage-source preflight contract changed")
    if value.get("stage") != {
        "outputDirectory": "request-grounded/p2-48-stage0",
        "checkpointName": "stage-checkpoint.pt",
        "transitionKind": PROPOSED_STAGE_KIND,
        "seed": 1337,
        "p248StageStep": 0,
        "p248TokensProcessed": 0,
        "modelWeightsLoadedFromBase": True,
        "modelWeightsMustMatchBaseExactly": True,
        "baseOptimizerStateReused": False,
        "freshOptimizerStateMustBeEmpty": True,
        "baseSamplerStateReused": False,
        "samplerStateMustResetToSeed": True,
        "baseTrainingStepReusedAsP248Step": False,
        "trainingSettingsMustBeNull": True,
        "scheduleStateMustBeNull": True,
    }:
        raise ValueError("P2-48 zero-stage semantics changed")
    if value.get("optimizerSerialization") != {
        "kind": "AdamW",
        "learningRate": ADAMW_LEARNING_RATE,
        "betas": list(ADAMW_BETAS),
        "epsilon": ADAMW_EPSILON,
        "weightDecay": ADAMW_WEIGHT_DECAY,
        "gradientUpdatesAuthorized": 0,
    }:
        raise ValueError("P2-48 serialization optimizer settings changed")
    return value


def _verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle = inspect_request_grounded_bundle(bundle_dir)
    if (
        sha256_file(bundle["root"] / "manifest.json") != EXPECTED_BUNDLE_MANIFEST_SHA256
        or bundle["dataset"]["sourceDatasetManifestSha256"]
        != EXPECTED_SOURCE_DATASET_MANIFEST_SHA256
        or bundle["dataset"]["trainJsonlSha256"] != EXPECTED_TRAIN_JSONL_SHA256
        or bundle["dataset"]["validationJsonlSha256"] != EXPECTED_VALIDATION_JSONL_SHA256
        or bundle["dataset"]["trainTokensSha256"] != EXPECTED_TRAIN_TOKENS_SHA256
        or bundle["dataset"]["validationTokensSha256"]
        != EXPECTED_VALIDATION_TOKENS_SHA256
        or bundle["dataset"]["trainIndexSha256"] != EXPECTED_TRAIN_INDEX_SHA256
        or bundle["dataset"]["validationIndexSha256"]
        != EXPECTED_VALIDATION_INDEX_SHA256
        or bundle["tokenizer"]["tokenizerSha256"] != EXPECTED_TOKENIZER_SHA256
        or bundle["dataset"]["trainRecords"] != 72
        or bundle["dataset"]["validationRecords"] != 36
        or bundle["dataset"]["trainTokenCount"] != 19377
        or bundle["dataset"]["validationTokenCount"] != 9763
    ):
        raise ValueError("P2-48 bundle differs from frozen real preflight")
    return bundle


def preflight_request_grounded_stage_source(
    *,
    base_checkpoint: Path = DEFAULT_BASE_CHECKPOINT,
    bundle_dir: Path = DEFAULT_BUNDLE,
    contract_path: Path = DEFAULT_SOURCE_CONTRACT,
) -> dict[str, Any]:
    """Verify exact P2-44 endpoint and P2-48 bundle without creating stage state."""
    _source_contract(contract_path)
    if base_checkpoint.is_symlink() or not base_checkpoint.is_file():
        raise ValueError("P2-48 base checkpoint must be a regular local file")
    if sha256_file(base_checkpoint) != EXPECTED_BASE_CHECKPOINT_SHA256:
        raise ValueError("P2-48 requires the exact P2-44 step-100 endpoint")

    bundle = _verify_bundle(bundle_dir)
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
        or transition.get("milestone") != "P2-44"
        or not isinstance(training, dict)
        or training.get("kind") != EXPECTED_BASE_TRAINING_KIND
        or not isinstance(tokenizer, dict)
        or tokenizer.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer.get("actualVocabularySize") != 16384
    ):
        raise ValueError("P2-44 endpoint provenance does not satisfy P2-48")

    proposed_transition = {
        "schemaVersion": 1,
        "kind": PROPOSED_STAGE_KIND,
        "milestone": MILESTONE,
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "baseCheckpointStep": EXPECTED_BASE_STEP,
        "baseMilestone": "P2-44",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP248Step": False,
        "p248StageStep": 0,
        "p248TokensProcessed": 0,
        "modelTrainingPerformed": False,
    }

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "stage-source-preflight-passed-awaiting-stage-authorization",
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
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
        "checkpointStagingAuthorized": False,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }


def create_request_grounded_stage(
    *,
    base_checkpoint: Path = DEFAULT_BASE_CHECKPOINT,
    bundle_dir: Path = DEFAULT_BUNDLE,
    output_dir: Path = DEFAULT_STAGE_OUTPUT,
    artifact_root: Path = Path("training/artifacts"),
    source_contract_path: Path = DEFAULT_SOURCE_CONTRACT,
    stage_contract_path: Path = DEFAULT_STAGE_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Create one untouched P2-48 step-zero stage; perform zero optimizer updates."""
    _stage_contract(stage_contract_path)
    source = preflight_request_grounded_stage_source(
        base_checkpoint=base_checkpoint,
        bundle_dir=bundle_dir,
        contract_path=source_contract_path,
    )
    if (
        source.get("status")
        != "stage-source-preflight-passed-awaiting-stage-authorization"
        or source.get("weightsSourceVerified") is not True
        or source.get("bundleCompatibilityVerified") is not True
        or source.get("stageCheckpointCreated") is not False
        or source.get("optimizerCreated") is not False
    ):
        raise ValueError("P2-48 stage-source preflight no longer matches authorization")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(
        root / "request-grounded/p2-48-stage0", root
    )
    if output != expected_output:
        raise ValueError("P2-48 stage must use the locked stage0 output directory")
    if output.exists():
        raise FileExistsError("P2-48 stage0 output already exists")
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")

    bundle = _verify_bundle(bundle_dir)
    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    base_state = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-48 stage optimizer unexpectedly contains state")

    transition = source["proposedStageTransition"]
    rng = random.Random(1337)

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
            raise ValueError("Saved P2-48 stage failed zero-update identity verification")

        report = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "status": "stage-created-training-not-authorized",
            "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
            "baseCheckpointStep": EXPECTED_BASE_STEP,
            "stageCheckpoint": "stage-checkpoint.pt",
            "stageCheckpointSha256": sha256_file(checkpoint),
            "parameterCount": parameter_count(saved_model),
            "modelWeightsPreserved": weights_equal,
            "modelWeightEqualityMethod":
                "torch.equal for every model-state tensor after reload",
            "freshOptimizerCreatedForSerialization": True,
            "optimizerStateReused": False,
            "optimizerStateEmpty":
                saved.get("optimizerStateDict", {}).get("state") == {},
            "samplerStateReset": True,
            "p248StageStep": 0,
            "p248TokensProcessed": 0,
            "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "trainingSettings": None,
            "scheduleState": None,
            "stageTransition": transition,
            "checkpointStagingAuthorized": True,
            "modelTrainingAuthorized": False,
            "trainingPerformed": False,
            "researchOptimizerUpdates": 0,
            "finalHoldoutOpened": False,
        }
        (output / "stage-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        size = sum(
            path.stat().st_size for path in output.rglob("*") if path.is_file()
        )
        if size > storage_limit_bytes:
            raise ValueError("P2-48 stage exceeds remaining artifact storage allocation")
        return report
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise
