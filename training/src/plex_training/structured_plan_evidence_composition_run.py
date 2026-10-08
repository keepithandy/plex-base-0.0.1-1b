"""Bounded P2-44 first-run implementation.

The runner exists before owner approval so its guardrails can be reviewed and
tested. It refuses to execute unless the frozen authorization contract is
explicitly changed to the owner-approved state.
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
from .runner import (
    ADAMW_BETAS,
    ADAMW_EPSILON,
    ADAMW_LEARNING_RATE,
    ADAMW_WEIGHT_DECAY,
    SCHEDULE_KIND,
    _validation_loss,
    seed_everything,
)
from .structured_plan_evidence_composition_bundle import (
    inspect_evidence_composition_bundle,
)
from .structured_plan_evidence_composition_curriculum import (
    EXPECTED_BUNDLE_MANIFEST_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    EXPECTED_TRAIN_INDEX_SHA256,
    EXPECTED_TRAIN_JSONL_SHA256,
    EXPECTED_VALIDATION_INDEX_SHA256,
    EXPECTED_VALIDATION_JSONL_SHA256,
)
from .structured_plan_evidence_composition_stage import (
    EXPECTED_BASE_CHECKPOINT_SHA256,
)
from .structured_plan_evidence_composition_training import (
    CHECKPOINT_STEPS,
    EXPECTED_EXAMPLES,
    EXPECTED_REAL_TARGET_POSITIONS,
    EXPECTED_STAGE_CHECKPOINT_SHA256,
    GRADIENT_ACCUMULATION,
    MAXIMUM_STEPS,
    MAXIMUM_WALL_SECONDS,
    MICRO_BATCH,
    SEED,
    VALIDATION_MAXIMUM_BATCHES,
    VALIDATION_STEPS,
    _verify_stage,
    preflight_evidence_composition_training,
)
from .structured_plan_semantic_binding_training import (
    StructuredPlanCompleteRecordCorpus,
    _structured_plan_training_step,
)
from .telemetry import (
    environment_report,
    peak_gpu_memory,
    reset_peak_gpu_memory,
    select_device,
)
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-44"
AUTHORIZATION_KIND = "plex-p2-44-first-evidence-composition-run-contract-v1"
AUTHORIZED_STATUS = "owner-approved-first-run"
AUTHORIZED_APPROVER = "keepithandy"
AUTHORIZED_DATE = "2026-10-08"
AUTHORIZED_OUTPUT_DIRECTORY = "structured-plan/p2-44-first-run"
TRAINING_SETTINGS_KIND = "p2-44-authorized-evidence-composition-training-v1"
RESULT_KIND = "p2-44-first-evidence-composition-run-result-v1"

DEFAULT_AUTHORIZATION_CONTRACT = Path(
    "training/pretraining/p2-44-first-run-contract.json"
)
DEFAULT_PREFLIGHT_CONTRACT = Path(
    "training/pretraining/p2-44-training-preflight-contract.json"
)
DEFAULT_BUNDLE = Path("training/artifacts/structured-plan/p2-44-training-bundle")
DEFAULT_STAGE_CHECKPOINT = Path(
    "training/artifacts/structured-plan/p2-44-stage0/stage-checkpoint.pt"
)
DEFAULT_OUTPUT = Path("training/artifacts/structured-plan/p2-44-first-run")
FROZEN_BASELINE_LOSS = 3.3981438778542183
FROZEN_BASELINE_BATCHES = 37


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"P2-44 contract mismatch: {label}")


def _validate_authorization(contract: dict[str, Any]) -> None:
    """Require explicit owner approval and the exact frozen scientific packet."""
    _require_exact(contract.get("schemaVersion"), 1, "schemaVersion")
    _require_exact(contract.get("milestone"), MILESTONE, "milestone")
    _require_exact(contract.get("kind"), AUTHORIZATION_KIND, "kind")
    _require_exact(contract.get("status"), AUTHORIZED_STATUS, "status")
    _require_exact(contract.get("approvalPacketComplete"), True, "approvalPacketComplete")
    _require_exact(contract.get("modelTrainingAuthorized"), True, "modelTrainingAuthorized")
    _require_exact(contract.get("approvedBy"), AUTHORIZED_APPROVER, "approvedBy")
    _require_exact(contract.get("approvedDate"), AUTHORIZED_DATE, "approvedDate")
    _require_exact(
        contract.get("outputDirectory"),
        AUTHORIZED_OUTPUT_DIRECTORY,
        "outputDirectory",
    )

    execution = contract.get("executionState")
    if not isinstance(execution, dict):
        raise ValueError("P2-44 execution state is missing")
    for key, expected in {
        "trainingExecuted": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }.items():
        _require_exact(execution.get(key), expected, f"executionState.{key}")

    stage = contract.get("baseStage")
    if not isinstance(stage, dict):
        raise ValueError("P2-44 base stage is missing")
    expected_stage = {
        "checkpointSha256": EXPECTED_STAGE_CHECKPOINT_SHA256,
        "p244Step": 0,
        "p244TokensProcessed": 0,
        "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
        "parameterCount": DEFAULT_CONFIG.parameter_count(),
        "modelWeightsPreserved": True,
        "optimizerStateEmpty": True,
        "samplerStateReset": True,
    }
    for key, expected in expected_stage.items():
        _require_exact(stage.get(key), expected, f"baseStage.{key}")

    data = contract.get("data")
    if not isinstance(data, dict):
        raise ValueError("P2-44 data authorization is missing")
    expected_data = {
        "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
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
    for key, expected in expected_data.items():
        _require_exact(data.get(key), expected, f"data.{key}")

    training = contract.get("training")
    if not isinstance(training, dict):
        raise ValueError("P2-44 training authorization is missing")
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
        "expectedExamplesAt100Steps": EXPECTED_EXAMPLES,
        "expectedRealTargetPositionsAt100Steps": EXPECTED_REAL_TARGET_POSITIONS,
        "resumeAllowed": False,
        "automaticContinuation": False,
    }
    for key, expected in expected_training.items():
        _require_exact(training.get(key), expected, f"training.{key}")

    expected_sampler = {
        "endPolicy": "stop-at-record-eos-v1",
        "indexSha256": EXPECTED_TRAIN_INDEX_SHA256,
        "kind": "complete-record-v1",
        "lossReduction": "mean-real-targets-per-microbatch-then-mean-accumulation-v1",
        "paddingPolicy": "right-pad-to-batch-longest-zero-target-weight-v1",
        "records": 108,
        "selection": "uniform-record-with-replacement",
        "tokenAccounting": "nonpadding-next-token-targets-v1",
        "trainJsonlSha256": EXPECTED_TRAIN_JSONL_SHA256,
    }
    _require_exact(training.get("sampler"), expected_sampler, "training.sampler")

    evaluation = contract.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("P2-44 evaluation authorization is missing")
    _require_exact(
        evaluation.get("method"),
        "sequential-packed-next-token-loss",
        "evaluation.method",
    )
    _require_exact(evaluation.get("steps"), list(VALIDATION_STEPS), "evaluation.steps")
    _require_exact(
        evaluation.get("maximumBatches"),
        VALIDATION_MAXIMUM_BATCHES,
        "evaluation.maximumBatches",
    )
    _require_exact(
        evaluation.get("checkpointSteps"),
        list(CHECKPOINT_STEPS),
        "evaluation.checkpointSteps",
    )
    _require_exact(
        evaluation.get("baselineBatches"),
        FROZEN_BASELINE_BATCHES,
        "evaluation.baselineBatches",
    )
    if not math.isclose(
        float(evaluation.get("baselineLoss")),
        FROZEN_BASELINE_LOSS,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("P2-44 contract mismatch: evaluation.baselineLoss")

    protected = contract.get("protectedEvaluation")
    if protected != {
        "validationExcludedFromGradients": True,
        "p231DevelopmentExcludedFromGradients": True,
        "p242ResponsesExcludedFromGradients": True,
        "p243DiagnosticExcludedFromGradients": True,
        "finalProjectHoldoutMustRemainClosed": True,
    }:
        raise ValueError("P2-44 protected evaluation authorization changed")

    _require_exact(
        contract.get("continuationRule"),
        "Stop after the bounded first run. Any continuation is a separate reviewed decision.",
        "continuationRule",
    )


def _training_settings(contract_sha: str, sampler: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "kind": TRAINING_SETTINGS_KIND,
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
        schedule_state={
            "kind": SCHEDULE_KIND,
            "step": step,
            "learningRate": ADAMW_LEARNING_RATE,
        },
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
        raise ValueError("Saved P2-44 checkpoint failed identity verification")
    return {**saved, "sha256": sha256_file(path)}


def run_evidence_composition_training(
    *,
    bundle_dir: Path = DEFAULT_BUNDLE,
    stage_checkpoint: Path = DEFAULT_STAGE_CHECKPOINT,
    authorization_contract_path: Path = DEFAULT_AUTHORIZATION_CONTRACT,
    preflight_contract_path: Path = DEFAULT_PREFLIGHT_CONTRACT,
    output_dir: Path = DEFAULT_OUTPUT,
    artifact_root: Path = Path("training/artifacts"),
) -> dict[str, Any]:
    """Execute one bounded owner-authorized P2-44 run."""
    auth = _json(authorization_contract_path)
    _validate_authorization(auth)

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / AUTHORIZED_OUTPUT_DIRECTORY, root)
    if output != expected_output:
        raise ValueError("P2-44 first run must use the approved output directory")
    if output.exists():
        raise FileExistsError(
            "P2-44 first-run output already exists; resume/overwrite are not supported"
        )

    preflight = preflight_evidence_composition_training(
        bundle_dir=bundle_dir,
        stage_checkpoint=stage_checkpoint,
        contract_path=preflight_contract_path,
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
        "expectedRealTargetPositionsAt100Steps":
            auth["training"]["expectedRealTargetPositionsAt100Steps"],
    }.items():
        _require_exact(preflight.get(key), expected, f"preflight.{key}")
    if not math.isclose(
        float(preflight["baselineValidationLoss"]),
        float(auth["evaluation"]["baselineLoss"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("P2-44 baseline validation loss changed before training")

    bundle = inspect_evidence_composition_bundle(bundle_dir)
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
        raise RuntimeError("Fresh P2-44 optimizer unexpectedly contains state")

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
            raise ValueError("P2-44 stage-zero baseline changed before training")

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
        final = next(
            (item for item in saved_checkpoints if item["step"] == completed_steps),
            None,
        )
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
            raise ValueError("P2-44 stage source changed during training")

        result = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "kind": RESULT_KIND,
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
            "meanRecentLoss": (
                sum(losses[-20:]) / len(losses[-20:]) if losses else None
            ),
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
