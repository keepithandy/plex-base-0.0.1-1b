"""Contract-enforced P2-30 first task-format fine-tuning run.

This module is intentionally separate from the generic pilot/runner resume paths.
The only research run it can execute is the single owner-authorized P2-30 first run.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, save_checkpoint
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .model import parameter_count
from .record_sampling import CompleteRecordTokenCorpus
from .runner import (
    ADAMW_BETAS,
    ADAMW_EPSILON,
    ADAMW_LEARNING_RATE,
    ADAMW_WEIGHT_DECAY,
    SCHEDULE_KIND,
    _training_step,
    _validation_loss,
    seed_everything,
)
from .task_finetune import inspect_task_bundle
from .telemetry import environment_report, peak_gpu_memory, reset_peak_gpu_memory, select_device
from .tokenizer import CODEC, PlexTokenizer, sha256_file

AUTHORIZED_KIND = "plex-p2-30-first-task-finetune-contract-v1"
AUTHORIZED_STATUS = "owner-approved-first-run"
AUTHORIZED_APPROVER = "keepithandy"
MAXIMUM_STEPS = 100
MAXIMUM_WALL_SECONDS = 600
VALIDATION_STEPS = (0, 25, 50, 75, 100)
CHECKPOINT_STEPS = (25, 50, 75, 100)
MICRO_BATCH = 1
GRADIENT_ACCUMULATION = 16
SEED = 1337
VALIDATION_MAXIMUM_BATCHES = 100
GRADIENT_CLIP_NORM = 1.0
AUTHORIZED_OUTPUT_DIRECTORY = "task-finetune/p2-30-first-run"


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized metadata file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"P2-30 first-run contract mismatch: {label}")


def _validate_authorization(contract: dict[str, Any]) -> None:
    _require_exact(contract.get("schemaVersion"), 1, "schemaVersion")
    _require_exact(contract.get("milestone"), "P2-30", "milestone")
    _require_exact(contract.get("kind"), AUTHORIZED_KIND, "kind")
    _require_exact(contract.get("status"), AUTHORIZED_STATUS, "status")
    _require_exact(contract.get("modelTrainingAuthorized"), True, "modelTrainingAuthorized")
    _require_exact(contract.get("approvedBy"), AUTHORIZED_APPROVER, "approvedBy")
    _require_exact(contract.get("outputDirectory"), AUTHORIZED_OUTPUT_DIRECTORY, "outputDirectory")

    execution = contract.get("executionState")
    if not isinstance(execution, dict):
        raise ValueError("P2-30 execution-state gate is missing")
    _require_exact(execution.get("trainingExecuted"), False, "executionState.trainingExecuted")
    _require_exact(execution.get("researchOptimizerUpdates"), 0,
                   "executionState.researchOptimizerUpdates")
    _require_exact(execution.get("finalHoldoutOpened"), False,
                   "executionState.finalHoldoutOpened")

    base = contract.get("baseStage")
    if not isinstance(base, dict):
        raise ValueError("P2-30 base-stage contract is missing")
    _require_exact(base.get("taskStep"), 0, "baseStage.taskStep")

    data = contract.get("data")
    if not isinstance(data, dict):
        raise ValueError("P2-30 task-data authorization is missing")
    _require_exact(data.get("additionalCurricula"), [], "data.additionalCurricula")

    training = contract.get("training")
    if not isinstance(training, dict):
        raise ValueError("P2-30 first-run training contract is missing")
    expected_training = {
        "objective": "ordinary-next-token-v1",
        "answerWeight": 1,
        "optimizer": "AdamW",
        "optimizerStatePolicy": "fresh-empty-task-stage-optimizer; never P2-29 moments",
        "learningRate": ADAMW_LEARNING_RATE,
        "betas": list(ADAMW_BETAS),
        "epsilon": ADAMW_EPSILON,
        "weightDecay": ADAMW_WEIGHT_DECAY,
        "gradientClippingNorm": GRADIENT_CLIP_NORM,
        "schedule": SCHEDULE_KIND,
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "device": "cuda",
        "seed": SEED,
        "contextLength": DEFAULT_CONFIG.context_length,
        "dropout": DEFAULT_CONFIG.dropout,
        "tokenAccounting": "nonpadding-next-token-targets-v1",
        "resumeAllowed": False,
        "automaticContinuation": False,
        "expectedSamplesAt100Steps": 1600,
        "expectedRealTargetPositionsAt100Steps": 181849,
        "timeLimitPolicy": "Stop before the next optimizer update when the run deadline is reached; save/report completed updates only.",
    }
    for key, expected in expected_training.items():
        _require_exact(training.get(key), expected, f"training.{key}")

    sampler = training.get("sampler")
    if not isinstance(sampler, dict):
        raise ValueError("P2-30 complete-record sampler contract is missing")
    for key, expected in {
        "kind": "complete-record-v1",
        "selection": "uniform-record-with-replacement",
        "endPolicy": "stop-at-record-eos-v1",
        "records": 156,
        "paddingPolicy": "right-pad-to-batch-longest-zero-target-weight-v1",
        "tokenAccounting": "nonpadding-next-token-targets-v1",
        "lossReduction": "mean-real-targets-per-microbatch-then-mean-accumulation-v1",
    }.items():
        _require_exact(sampler.get(key), expected, f"training.sampler.{key}")

    evaluation = contract.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("P2-30 evaluation contract is missing")
    task_validation = evaluation.get("taskValidation")
    if not isinstance(task_validation, dict):
        raise ValueError("P2-30 task validation contract is missing")
    _require_exact(task_validation.get("method"), "sequential-packed-next-token-loss",
                   "evaluation.taskValidation.method")
    _require_exact(task_validation.get("maximumBatches"), VALIDATION_MAXIMUM_BATCHES,
                   "evaluation.taskValidation.maximumBatches")
    _require_exact(task_validation.get("steps"), list(VALIDATION_STEPS),
                   "evaluation.taskValidation.steps")
    _require_exact(evaluation.get("checkpointSteps"), list(CHECKPOINT_STEPS),
                   "evaluation.checkpointSteps")
    _require_exact(evaluation.get("alwaysSaveFinalCompletedStep"), True,
                   "evaluation.alwaysSaveFinalCompletedStep")
    _require_exact(
        evaluation.get("checkpointSelection"),
        "Report fixed step-100 endpoint or early-stop endpoint; do not select the lowest-validation checkpoint",
        "evaluation.checkpointSelection",
    )
    development = evaluation.get("development")
    if not isinstance(development, dict):
        raise ValueError("P2-30 development-evaluation contract is missing")
    expected_development = {
        "taskSet": "training/phase2/evaluation/p2-01b-dev-v1.json",
        "taskSetSha256": "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4",
        "runAt": "final completed step only; existing stage-zero baseline retained",
        "temperature": 0,
        "seed": SEED,
        "maxNewTokens": {"css": 128, "html": 192, "javascript": 192},
        "baselinePassed": 0,
        "baselineTasks": 30,
        "baselineTruncated": 30,
    }
    for key, expected in expected_development.items():
        _require_exact(development.get(key), expected, f"evaluation.development.{key}")

    protected = contract.get("protectedEvaluation")
    if not isinstance(protected, dict):
        raise ValueError("P2-30 protected-evaluation contract is missing")
    for key in (
        "validationExcludedFromGradients",
        "p2_01bExcludedFromGradients",
        "finalProjectHoldoutMustRemainClosed",
        "developmentBaselineMustNotBeUsedForOptimization",
    ):
        _require_exact(protected.get(key), True, f"protectedEvaluation.{key}")


def _verify_stage(
    *,
    checkpoint_path: Path,
    bundle: dict[str, Any],
    contract: dict[str, Any],
) -> tuple[torch.nn.Module, dict[str, Any]]:
    base = contract.get("baseStage")
    if not isinstance(base, dict):
        raise ValueError("P2-30 base-stage contract is missing")
    expected_sha = base.get("checkpointSha256")
    if (not isinstance(expected_sha, str) or checkpoint_path.is_symlink()
            or not checkpoint_path.is_file() or sha256_file(checkpoint_path) != expected_sha):
        raise ValueError("P2-30 first run requires the exact authorized stage-zero checkpoint")

    model, payload = read_checkpoint(checkpoint_path, torch.device("cpu"))
    if model.config != DEFAULT_CONFIG or parameter_count(model) != base.get("parameterCount"):
        raise ValueError("P2-30 stage-zero model architecture differs from authorization")
    if (payload.get("step") != 0 or payload.get("tokensProcessedTotal") != 0
            or payload.get("seed") != SEED or payload.get("codec") != CODEC):
        raise ValueError("P2-30 first run requires untouched task step zero")
    optimizer_state = payload.get("optimizerStateDict")
    if not isinstance(optimizer_state, dict) or optimizer_state.get("state") != {}:
        raise ValueError("P2-30 stage-zero optimizer must be fresh and empty")
    if payload.get("trainingSettings") is not None or payload.get("scheduleState") is not None:
        raise ValueError("P2-30 stage-zero checkpoint already carries training progress")
    if payload.get("tokenizerRecord") != bundle["tokenizer"] or payload.get("datasetRecord") != bundle["dataset"]:
        raise ValueError("P2-30 stage-zero tokenizer or task dataset differs from authorization")
    if payload.get("samplingRngState") != random.Random(SEED).getstate():
        raise ValueError("P2-30 stage-zero task sampler is not reset")
    if payload.get("torchCudaRngStates") != []:
        raise ValueError("P2-30 stage-zero checkpoint must precede CUDA task optimization")

    initialization = payload.get("initializationRecord")
    if (not isinstance(initialization, dict)
            or initialization.get("pretrainedCheckpointLoaded") is not False
            or initialization.get("pretrainedModelWeightsLoaded") is not False):
        raise ValueError("P2-30 stage-zero scratch provenance is invalid")

    transition = payload.get("stageTransitionRecord")
    if not isinstance(transition, dict):
        raise ValueError("P2-30 stage-zero transition provenance is missing")
    expected_transition = {
        "kind": "plex-task-finetune-stage-transition-v1",
        "milestone": "P2-30",
        "baseCheckpointSha256": base.get("baseWebCheckpointSha256"),
        "baseCheckpointStep": 500,
        "modelWeightsLoadedFromBase": True,
        "pretrainingOptimizerStateReused": False,
        "pretrainingSamplerStateReused": False,
        "pretrainingStepReusedAsTaskStep": False,
        "taskStageStep": 0,
        "modelTrainingPerformed": False,
    }
    for key, expected in expected_transition.items():
        _require_exact(transition.get(key), expected, f"stageTransitionRecord.{key}")
    if (transition.get("taskDatasetRecord") != bundle["dataset"]
            or transition.get("taskTokenizerRecord") != bundle["tokenizer"]):
        raise ValueError("P2-30 stage transition is not bound to the authorized task bundle")
    return model, payload


def _training_settings(contract_sha: str, sampler_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "kind": "p2-30-authorized-task-finetune-v1",
        "authorizationContractSha256": contract_sha,
        "codec": CODEC,
        "modelConfig": DEFAULT_CONFIG.to_dict(),
        "objective": "ordinary-next-token-v1",
        "answerWeight": 1,
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "lossVocabularySize": 16384,
        "validationMaximumBatches": VALIDATION_MAXIMUM_BATCHES,
        "optimizer": {
            "kind": "AdamW",
            "learningRate": ADAMW_LEARNING_RATE,
            "betas": list(ADAMW_BETAS),
            "weightDecay": ADAMW_WEIGHT_DECAY,
            "epsilon": ADAMW_EPSILON,
        },
        "gradientClippingNorm": GRADIENT_CLIP_NORM,
        "learningRateSchedule": SCHEDULE_KIND,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "resumeAllowed": False,
        "automaticContinuation": False,
        "samplingPolicy": sampler_record,
    }


def _schedule_state(step: int) -> dict[str, Any]:
    return {"kind": SCHEDULE_KIND, "step": step, "learningRate": ADAMW_LEARNING_RATE}


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _save_verified_checkpoint(
    *,
    path: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    step: int,
    rng: random.Random,
    device: torch.device,
    artifact_root: Path,
    initialization_record: dict[str, Any],
    transition_record: dict[str, Any],
    tokenizer_record: dict[str, Any],
    dataset_record: dict[str, Any],
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
        initialization_record=initialization_record,
        stage_transition_record=transition_record,
        tokenizer_record=tokenizer_record,
        dataset_record=dataset_record,
        training_settings=settings,
        schedule_state=_schedule_state(step),
        tokens_processed_total=tokens_processed,
    )
    _, payload = read_checkpoint(path, torch.device("cpu"))
    if (payload.get("step") != step or payload.get("tokensProcessedTotal") != tokens_processed
            or payload.get("stageTransitionRecord") != transition_record
            or payload.get("trainingSettings") != settings
            or payload.get("datasetRecord") != dataset_record
            or payload.get("tokenizerRecord") != tokenizer_record):
        raise ValueError("Saved P2-30 task checkpoint failed identity verification")
    return {**saved, "sha256": sha256_file(path)}


def _preflight(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
    require_cuda: bool,
) -> dict[str, Any]:
    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)

    for path, label in (
        (authorization_contract_path, "authorization contract"),
        (preparation_contract_path, "preparation contract"),
        (stage_checkpoint, "stage-zero checkpoint"),
    ):
        if path.is_symlink():
            raise ValueError(f"P2-30 {label} must not be a symlink")

    contract = _json(authorization_contract_path)
    _validate_authorization(contract)
    authorization_path = authorization_contract_path.resolve(strict=True)
    expected_output = path_within_root(root / Path(contract["outputDirectory"]), root)
    if output != expected_output:
        raise ValueError("P2-30 first run must use the single authorized output directory")
    if output.exists():
        raise FileExistsError("P2-30 first-run output already exists; resume and overwrite are forbidden")

    preparation_contract = _json(preparation_contract_path)
    preparation_path = preparation_contract_path.resolve(strict=True)
    if (preparation_contract.get("milestone") != "P2-30"
            or preparation_contract.get("status") != "preparation-gate-passed"):
        raise ValueError("P2-30 preparation gate is not passed")

    bundle = inspect_task_bundle(bundle_dir, preparation_contract)
    data = contract.get("data")
    if not isinstance(data, dict):
        raise ValueError("P2-30 task-data authorization is missing")
    expected_data = {
        "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "vocabularySize": bundle["tokenizer"]["actualVocabularySize"],
        "sourceDatasetManifestSha256": bundle["dataset"]["sourceDatasetManifestSha256"],
        "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "trainRecords": bundle["dataset"]["trainRecords"],
        "validationRecords": bundle["dataset"]["validationRecords"],
    }
    for key, actual in expected_data.items():
        _require_exact(data.get(key), actual, f"data.{key}")

    sampler = contract["training"]["sampler"]
    _require_exact(sampler.get("trainJsonlSha256"), bundle["dataset"]["trainJsonlSha256"],
                   "training.sampler.trainJsonlSha256")
    _require_exact(sampler.get("indexSha256"), sha256_file(bundle["root"] / "train.index.json"),
                   "training.sampler.indexSha256")

    model, payload = _verify_stage(
        checkpoint_path=stage_checkpoint.resolve(strict=True),
        bundle=bundle,
        contract=contract,
    )
    if require_cuda:
        select_device("cuda")

    baseline = contract["evaluation"]["taskValidation"]
    if (type(baseline.get("baselineLoss")) not in (int, float)
            or baseline.get("baselineTokens") != 8192
            or baseline.get("baselineBatches") != 16
            or baseline.get("tailTargetPositionsExcluded") != 468):
        raise ValueError("P2-30 stage-zero validation baseline contract changed")

    return {
        "authorization": contract,
        "authorizationSha256": sha256_file(authorization_path),
        "preparationContractSha256": sha256_file(preparation_path),
        "bundle": bundle,
        "model": model,
        "payload": payload,
        "output": output,
        "stageCheckpoint": stage_checkpoint.resolve(strict=True),
        "stageCheckpointSha256": sha256_file(stage_checkpoint.resolve(strict=True)),
    }


def preflight_first_finetune(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Verify every first-run gate without creating outputs or updating weights."""
    checked = _preflight(
        bundle_dir=bundle_dir,
        stage_checkpoint=stage_checkpoint,
        authorization_contract_path=authorization_contract_path,
        preparation_contract_path=preparation_contract_path,
        output_dir=output_dir,
        artifact_root=artifact_root,
        require_cuda=True,
    )
    contract = checked["authorization"]
    bundle = checked["bundle"]
    return {
        "schemaVersion": 1,
        "milestone": "P2-30",
        "authorized": True,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "authorizationContractSha256": checked["authorizationSha256"],
        "stageCheckpointSha256": checked["stageCheckpointSha256"],
        "taskBundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "trainRecords": bundle["dataset"]["trainRecords"],
        "validationRecords": bundle["dataset"]["validationRecords"],
        "maximumSteps": contract["training"]["maximumSteps"],
        "maximumWallTimeSeconds": contract["training"]["maximumWallTimeSeconds"],
        "device": "cuda",
        "outputWouldBe": str(checked["output"].relative_to(artifact_root.resolve())),
    }


def run_first_finetune(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Execute only the single bounded, owner-authorized P2-30 first run."""
    checked = _preflight(
        bundle_dir=bundle_dir,
        stage_checkpoint=stage_checkpoint,
        authorization_contract_path=authorization_contract_path,
        preparation_contract_path=preparation_contract_path,
        output_dir=output_dir,
        artifact_root=artifact_root,
        require_cuda=True,
    )
    root = artifact_root.resolve()
    output = checked["output"]
    bundle = checked["bundle"]
    contract = checked["authorization"]
    source_hash = checked["stageCheckpointSha256"]
    model = checked["model"]
    payload = checked["payload"]
    device = select_device("cuda")

    # Four trained checkpoints can each include AdamW moments; reserve a conservative 2 GiB.
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
        raise RuntimeError("Fresh P2-30 task optimizer unexpectedly contains state")

    tokenizer = PlexTokenizer.load(bundle["root"])
    with CompleteRecordTokenCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train, TokenCorpus(bundle["validationPath"]) as validation:
        _require_exact(train.sampler_record, contract["training"]["sampler"], "runtime sampler")
        settings = _training_settings(checked["authorizationSha256"], train.sampler_record)
        model.train()
        reset_peak_gpu_memory(device)

        baseline_loss = _validation_loss(
            model,
            validation,
            device,
            maximum_batches=VALIDATION_MAXIMUM_BATCHES,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
        )
        expected_baseline = float(contract["evaluation"]["taskValidation"]["baselineLoss"])
        if not math.isclose(baseline_loss, expected_baseline, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"P2-30 stage-zero baseline changed: expected {expected_baseline}, got {baseline_loss}"
            )

        started = time.perf_counter()
        deadline = started + MAXIMUM_WALL_SECONDS
        validations = [{"step": 0, "meanLoss": baseline_loss, "tokens": 8192, "batches": 16}]
        losses: list[float] = []
        tokens_seen = 0
        padding_seen = 0
        saved_checkpoints: list[dict[str, Any]] = []
        interrupted = False

        _append_jsonl(metrics_path, {
            "event": "run_started",
            "startedAtUtc": datetime.now(timezone.utc).isoformat(),
            "authorizationContractSha256": checked["authorizationSha256"],
            "stageCheckpointSha256": source_hash,
            "device": str(device),
            "environment": environment_report(device),
            "trainingSettings": settings,
            "validation": validations[0],
        })

        try:
            while len(losses) < MAXIMUM_STEPS and time.perf_counter() < deadline:
                loss, real_positions, padding_positions = _training_step(
                    model,
                    optimizer,
                    train,
                    rng,
                    device,
                    micro_batch=MICRO_BATCH,
                    accumulation_steps=GRADIENT_ACCUMULATION,
                    loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                    answer_weighted=False,
                )
                step = len(losses) + 1
                losses.append(loss)
                tokens_seen += real_positions
                padding_seen += padding_positions
                _append_jsonl(metrics_path, {
                    "event": "training_progress",
                    "step": step,
                    "loss": loss,
                    "tokensProcessedTotal": tokens_seen,
                    "elapsedSeconds": time.perf_counter() - started,
                })

                if step in VALIDATION_STEPS:
                    validation_loss = _validation_loss(
                        model,
                        validation,
                        device,
                        maximum_batches=VALIDATION_MAXIMUM_BATCHES,
                        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                    )
                    validation_record = {
                        "step": step, "meanLoss": validation_loss, "tokens": 8192, "batches": 16
                    }
                    validations.append(validation_record)
                    _append_jsonl(metrics_path, {"event": "validation", **validation_record})

                if step in CHECKPOINT_STEPS:
                    checkpoint_path = checkpoints_dir / f"step-{step:04d}.pt"
                    saved = _save_verified_checkpoint(
                        path=checkpoint_path,
                        model=model,
                        optimizer=optimizer,
                        step=step,
                        rng=rng,
                        device=device,
                        artifact_root=root,
                        initialization_record=payload["initializationRecord"],
                        transition_record=payload["stageTransitionRecord"],
                        tokenizer_record=bundle["tokenizer"],
                        dataset_record=bundle["dataset"],
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
            final_path = checkpoints_dir / f"step-{completed_steps:04d}-final.pt"
            final = _save_verified_checkpoint(
                path=final_path,
                model=model,
                optimizer=optimizer,
                step=completed_steps,
                rng=rng,
                device=device,
                artifact_root=root,
                initialization_record=payload["initializationRecord"],
                transition_record=payload["stageTransitionRecord"],
                tokenizer_record=bundle["tokenizer"],
                dataset_record=bundle["dataset"],
                settings=settings,
                tokens_processed=tokens_seen,
            )
            saved_checkpoints.append(final)

        elapsed = time.perf_counter() - started
        if sha256_file(checked["stageCheckpoint"]) != source_hash:
            raise ValueError("P2-30 stage-zero source checkpoint changed during the run")
        if (sha256_file(bundle["root"] / "manifest.json") != contract["data"]["bundleManifestSha256"]
                or sha256_file(bundle["trainPath"]) != bundle["dataset"]["trainTokensSha256"]
                or sha256_file(bundle["validationPath"]) != bundle["dataset"]["validationTokensSha256"]
                or sha256_file(bundle["root"] / "train.index.json") != contract["training"]["sampler"]["indexSha256"]):
            raise ValueError("P2-30 task bundle changed during the run")

        result = {
            "schemaVersion": 1,
            "milestone": "P2-30",
            "kind": "p2-30-first-task-finetune-result-v1",
            "trainingPerformed": completed_steps > 0,
            "researchOptimizerUpdates": completed_steps,
            "authorizedMaximumSteps": MAXIMUM_STEPS,
            "authorizedMaximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
            "automaticContinuation": False,
            "resumeAllowed": False,
            "finalHoldoutOpened": False,
            "interrupted": interrupted,
            "elapsedSeconds": elapsed,
            "stageCheckpointSha256": source_hash,
            "authorizationContractSha256": checked["authorizationSha256"],
            "taskBundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
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
            "developmentEvaluationPending": True,
            "continuationAuthorized": False,
        }

    result_path = output / "run-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")
    enforce_storage_limit(root)
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "result": str(result_path.relative_to(root)),
        "metrics": str(metrics_path.relative_to(root)),
    }
