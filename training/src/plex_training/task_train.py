"""Owner-authorized, contract-bound P2-30 task-format fine-tuning."""

from __future__ import annotations

import json
import math
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
    evaluate_checkpoint,
    seed_everything,
)
from .task_finetune import _json, inspect_task_bundle
from .telemetry import environment_report, peak_gpu_memory, reset_peak_gpu_memory, select_device
from .tokenizer import CODEC, PlexTokenizer, sha256_file

POLICY = {
    "learningRate": ADAMW_LEARNING_RATE,
    "betas": list(ADAMW_BETAS),
    "epsilon": ADAMW_EPSILON,
    "weightDecay": ADAMW_WEIGHT_DECAY,
    "gradientClippingNorm": 1.0,
    "schedule": SCHEDULE_KIND,
    "microBatch": 1,
    "gradientAccumulation": 16,
    "maximumSteps": 100,
    "maximumWallTimeSeconds": 600,
    "device": "cuda",
    "seed": 1337,
    "contextLength": 512,
    "dropout": 0.1,
    "objective": "ordinary-next-token-v1",
    "answerWeight": 1,
}
EVALUATION_STEPS = (0, 25, 50, 75, 100)
CHECKPOINT_STEPS = (25, 50, 75, 100)
ARTIFACT_LIMIT_BYTES = 200 * 1024**3


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()


def _load_authorization(contract_path: Path) -> dict[str, Any]:
    contract = _json(contract_path.resolve(strict=True), maximum_bytes=1024 * 1024)
    training = contract.get("training")
    evaluation = contract.get("evaluation")
    protected = contract.get("protectedEvaluation")
    if (
        contract.get("schemaVersion") != 1
        or contract.get("milestone") != "P2-30"
        or contract.get("kind") != "plex-p2-30-first-task-finetune-contract-v1"
        or contract.get("status") != "owner-approved"
        or contract.get("modelTrainingAuthorized") is not True
        or contract.get("approvedBy") != "keepithandy"
        or contract.get("approvedDate") != "2026-10-07"
        or not isinstance(training, dict)
        or not isinstance(evaluation, dict)
        or not isinstance(protected, dict)
    ):
        raise ValueError("P2-30 first-run contract is not explicitly owner-authorized")

    for key, expected in POLICY.items():
        if training.get(key) != expected:
            raise ValueError(f"P2-30 first-run contract changes fixed training policy: {key}")
    if (
        training.get("optimizer") != "AdamW"
        or training.get("optimizerStatePolicy") != "fresh-empty-task-stage-optimizer; never P2-29 moments"
        or training.get("tokenAccounting") != "nonpadding-next-token-targets-v1"
        or training.get("resumeAllowed") is not False
        or training.get("automaticContinuation") is not False
        or training.get("sampler", {}).get("kind") != "complete-record-v1"
        or training.get("sampler", {}).get("selection") != "uniform-record-with-replacement"
        or training.get("sampler", {}).get("endPolicy") != "stop-at-record-eos-v1"
        or training.get("sampler", {}).get("paddingPolicy") != "right-pad-to-batch-longest-zero-target-weight-v1"
    ):
        raise ValueError("P2-30 first-run contract changes the fixed optimizer/sampler policy")

    task_validation = evaluation.get("taskValidation", {})
    if (
        task_validation.get("method") != "sequential-packed-next-token-loss"
        or task_validation.get("maximumBatches") != 100
        or task_validation.get("steps") != list(EVALUATION_STEPS)
        or evaluation.get("checkpointSteps") != list(CHECKPOINT_STEPS)
        or evaluation.get("alwaysSaveFinalCompletedStep") is not True
        or protected.get("validationExcludedFromGradients") is not True
        or protected.get("p2_01bExcludedFromGradients") is not True
        or protected.get("finalProjectHoldoutMustRemainClosed") is not True
        or protected.get("developmentBaselineMustNotBeUsedForOptimization") is not True
    ):
        raise ValueError("P2-30 first-run contract weakens protected evaluation or cadence")
    return contract


def _verify_inputs(
    *,
    contract: dict[str, Any],
    preparation_contract: dict[str, Any],
    contract_path: Path,
    checkpoint_path: Path,
    bundle_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if (
        preparation_contract.get("milestone") != "P2-30"
        or preparation_contract.get("status") != "preparation-gate-passed"
        or preparation_contract.get("authorization", {}).get("modelTrainingAuthorized") is not False
        or preparation_contract.get("firstTrainingContract") != "training/pretraining/p2-30-first-finetune-contract.json"
    ):
        raise ValueError("P2-30 preparation contract does not point at the approved first-run contract")

    data = contract.get("data", {})
    base = contract.get("baseStage", {})
    bundle = inspect_task_bundle(bundle_dir, preparation_contract)
    root = bundle["root"]
    manifest_sha = sha256_file(root / "manifest.json")
    if (
        manifest_sha != data.get("bundleManifestSha256")
        or bundle["tokenizer"].get("tokenizerSha256") != data.get("tokenizerSha256")
        or bundle["tokenizer"].get("actualVocabularySize") != data.get("vocabularySize")
        or bundle["dataset"].get("sourceDatasetManifestSha256") != data.get("sourceDatasetManifestSha256")
        or bundle["dataset"].get("trainJsonlSha256") != data.get("trainJsonlSha256")
        or bundle["dataset"].get("validationJsonlSha256") != data.get("validationJsonlSha256")
        or bundle["dataset"].get("trainRecords") != data.get("trainRecords")
        or bundle["dataset"].get("validationRecords") != data.get("validationRecords")
    ):
        raise ValueError("P2-30 task bundle does not match the owner-approved first-run contract")

    checkpoint_path = checkpoint_path.resolve(strict=True)
    if checkpoint_path.is_symlink() or sha256_file(checkpoint_path) != base.get("checkpointSha256"):
        raise ValueError("P2-30 starting checkpoint is not the authorized stage-zero checkpoint")

    model, payload = read_checkpoint(checkpoint_path, torch.device("cpu"))
    stage = payload.get("stageTransitionRecord")
    initialization = payload.get("initializationRecord")
    optimizer_state = payload.get("optimizerStateDict")
    if (
        model.config != DEFAULT_CONFIG
        or parameter_count(model) != base.get("parameterCount")
        or payload.get("codec") != CODEC
        or payload.get("step") != 0
        or payload.get("tokensProcessedTotal") != 0
        or payload.get("seed") != POLICY["seed"]
        or payload.get("tokenizerRecord") != bundle["tokenizer"]
        or payload.get("datasetRecord") != bundle["dataset"]
        or not isinstance(initialization, dict)
        or initialization.get("pretrainedCheckpointLoaded") is not False
        or initialization.get("pretrainedModelWeightsLoaded") is not False
        or not isinstance(stage, dict)
        or stage.get("kind") != "plex-task-finetune-stage-transition-v1"
        or stage.get("milestone") != "P2-30"
        or stage.get("baseCheckpointSha256") != base.get("baseWebCheckpointSha256")
        or stage.get("taskStageStep") != 0
        or stage.get("modelWeightsLoadedFromBase") is not True
        or stage.get("pretrainingOptimizerStateReused") is not False
        or stage.get("pretrainingSamplerStateReused") is not False
        or stage.get("pretrainingStepReusedAsTaskStep") is not False
        or stage.get("modelTrainingPerformed") is not False
        or not isinstance(optimizer_state, dict)
        or optimizer_state.get("state") != {}
        or payload.get("samplingRngState") != random.Random(POLICY["seed"]).getstate()
    ):
        raise ValueError("P2-30 stage-zero checkpoint provenance/state does not satisfy authorization")

    sampler = contract["training"]["sampler"]
    if (
        sampler.get("records") != data.get("trainRecords")
        or sampler.get("trainJsonlSha256") != data.get("trainJsonlSha256")
        or sampler.get("indexSha256") != sha256_file(root / "train.index.json")
    ):
        raise ValueError("P2-30 complete-record sampler identity differs from authorization")
    return bundle, payload, stage


def run_authorized_task_finetune(
    *,
    checkpoint_path: Path,
    bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    contract_path: Path,
    preparation_contract_path: Path,
) -> dict[str, Any]:
    """Run exactly one owner-authorized P2-30 bounded task fine-tune."""
    contract = _load_authorization(contract_path)
    preparation_contract = _json(preparation_contract_path.resolve(strict=True))
    bundle, stage_payload, stage_record = _verify_inputs(
        contract=contract,
        preparation_contract=preparation_contract,
        contract_path=contract_path,
        checkpoint_path=checkpoint_path,
        bundle_dir=bundle_dir,
    )

    root = artifact_root.resolve()
    output_dir = path_within_root(output_dir, root)
    if output_dir.exists():
        raise FileExistsError("P2-30 first-run output already exists; resume/overwrite is not authorized")

    data_root = bundle["root"]
    baseline = evaluate_checkpoint(
        checkpoint_path,
        data_root / "validation.tokens.u16le",
        device_name="cuda",
        maximum_batches=100,
        codec=CODEC,
        tokenizer_record=bundle["tokenizer"],
        dataset_record=bundle["dataset"],
        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
    )
    expected_baseline = contract["evaluation"]["taskValidation"]
    if (
        baseline["checkpointStep"] != 0
        or baseline["tokens"] != expected_baseline["baselineTokens"]
        or baseline["batches"] != expected_baseline["baselineBatches"]
        or not math.isclose(
            baseline["meanLoss"], expected_baseline["baselineLoss"], rel_tol=0.0, abs_tol=1e-12
        )
    ):
        raise ValueError("P2-30 stage-zero baseline no longer reproduces the authorized evidence")

    device = select_device("cuda")
    seed_everything(POLICY["seed"])
    rng = random.Random(POLICY["seed"])
    model, payload = read_checkpoint(checkpoint_path, device)
    if payload.get("stageTransitionRecord") != stage_record:
        raise ValueError("P2-30 stage-transition record changed between verification and CUDA load")
    torch.set_rng_state(stage_payload["torchCpuRngState"].cpu())
    torch.cuda.manual_seed_all(POLICY["seed"])
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-30 optimizer unexpectedly contains state")

    tokenizer = PlexTokenizer.load(data_root)
    train = CompleteRecordTokenCorpus(
        data_root / "train.tokens.u16le",
        dataset_jsonl=data_root / "train.jsonl",
        index_path=data_root / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=contract["data"]["trainJsonlSha256"],
    )
    validation = TokenCorpus(data_root / "validation.tokens.u16le")
    training_settings = {
        "schemaVersion": 1,
        "kind": "p2-30-authorized-task-finetune-v1",
        "authorizationContract": str(contract_path),
        "authorizationContractSha256": sha256_file(contract_path),
        "microBatch": POLICY["microBatch"],
        "gradientAccumulation": POLICY["gradientAccumulation"],
        "optimizer": {
            "kind": "AdamW",
            "learningRate": ADAMW_LEARNING_RATE,
            "betas": list(ADAMW_BETAS),
            "weightDecay": ADAMW_WEIGHT_DECAY,
            "epsilon": ADAMW_EPSILON,
        },
        "learningRateSchedule": SCHEDULE_KIND,
        "samplingPolicy": train.sampler_record,
        "objective": POLICY["objective"],
        "answerWeight": POLICY["answerWeight"],
        "lossVocabularySize": bundle["tokenizer"]["actualVocabularySize"],
        "validationMaximumBatches": 100,
        "resumeAllowed": False,
        "automaticContinuation": False,
    }

    output_dir.mkdir(parents=True, exist_ok=False)
    metrics_path = output_dir / "metrics.jsonl"
    contract_copy = output_dir / "authorization-contract.json"
    contract_copy.write_bytes(contract_path.read_bytes())
    _append_jsonl(metrics_path, {
        "event": "run_authorized",
        "startedAtUtc": datetime.now(timezone.utc).isoformat(),
        "authorizationContractSha256": sha256_file(contract_path),
        "stageCheckpointSha256": sha256_file(checkpoint_path),
        "taskBundleManifestSha256": sha256_file(data_root / "manifest.json"),
        "baseline": baseline,
        "trainingSettings": training_settings,
        "stageTransitionRecord": stage_record,
        "environment": environment_report(device),
    })
    enforce_storage_limit(root, limit_bytes=ARTIFACT_LIMIT_BYTES)

    model.train()
    reset_peak_gpu_memory(device)
    started = time.perf_counter()
    deadline = started + POLICY["maximumWallTimeSeconds"]
    step = 0
    real_targets = 0
    padding_targets = 0
    losses: list[float] = []
    validations: list[dict[str, Any]] = [baseline]
    checkpoints: list[dict[str, Any]] = []
    interrupted = False

    try:
        while step < POLICY["maximumSteps"]:
            if time.perf_counter() >= deadline:
                break
            loss, real, padding = _training_step(
                model,
                optimizer,
                train,
                rng,
                device,
                micro_batch=POLICY["microBatch"],
                accumulation_steps=POLICY["gradientAccumulation"],
                loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                answer_weighted=False,
            )
            step += 1
            real_targets += real
            padding_targets += padding
            losses.append(loss)
            if step == 1 or step % 10 == 0:
                _append_jsonl(metrics_path, {
                    "event": "training_progress",
                    "step": step,
                    "loss": loss,
                    "realTargetPositions": real_targets,
                    "paddingTargetPositions": padding_targets,
                    "elapsedSeconds": time.perf_counter() - started,
                    "peakGpuMemory": peak_gpu_memory(device),
                })

            if step in CHECKPOINT_STEPS:
                checkpoint = output_dir / f"checkpoint-step-{step}.pt"
                saved = save_checkpoint(
                    model,
                    optimizer,
                    step=step,
                    seed=POLICY["seed"],
                    codec=CODEC,
                    sampling_rng=rng,
                    device=device,
                    destination=checkpoint,
                    artifact_root=root,
                    initialization_record=payload["initializationRecord"],
                    stage_transition_record=stage_record,
                    tokenizer_record=bundle["tokenizer"],
                    dataset_record=bundle["dataset"],
                    training_settings=training_settings,
                    schedule_state={
                        "kind": SCHEDULE_KIND,
                        "step": step,
                        "learningRate": ADAMW_LEARNING_RATE,
                    },
                    tokens_processed_total=real_targets,
                )
                saved["sha256"] = sha256_file(checkpoint)
                checkpoints.append(saved)
                if step in EVALUATION_STEPS:
                    result = evaluate_checkpoint(
                        checkpoint,
                        data_root / "validation.tokens.u16le",
                        device_name="cuda",
                        maximum_batches=100,
                        codec=CODEC,
                        tokenizer_record=bundle["tokenizer"],
                        dataset_record=bundle["dataset"],
                        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                    )
                    validations.append(result)
                    _append_jsonl(metrics_path, {"event": "validation", **result})
                enforce_storage_limit(root, limit_bytes=ARTIFACT_LIMIT_BYTES)
    except KeyboardInterrupt:
        interrupted = True

    elapsed = time.perf_counter() - started
    final_path = output_dir / f"checkpoint-step-{step}.pt"
    if not final_path.exists():
        saved = save_checkpoint(
            model,
            optimizer,
            step=step,
            seed=POLICY["seed"],
            codec=CODEC,
            sampling_rng=rng,
            device=device,
            destination=final_path,
            artifact_root=root,
            initialization_record=payload["initializationRecord"],
            stage_transition_record=stage_record,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            training_settings=training_settings,
            schedule_state={
                "kind": SCHEDULE_KIND,
                "step": step,
                "learningRate": ADAMW_LEARNING_RATE,
            },
            tokens_processed_total=real_targets,
        )
        saved["sha256"] = sha256_file(final_path)
        checkpoints.append(saved)

    final_model, final_payload = read_checkpoint(final_path, torch.device("cpu"))
    if (
        final_model.config != DEFAULT_CONFIG
        or final_payload.get("stageTransitionRecord") != stage_record
        or final_payload.get("tokenizerRecord") != bundle["tokenizer"]
        or final_payload.get("datasetRecord") != bundle["dataset"]
        or final_payload.get("step") != step
        or final_payload.get("tokensProcessedTotal") != real_targets
        or final_payload.get("trainingSettings") != training_settings
    ):
        raise RuntimeError("Saved P2-30 checkpoint failed final identity verification")

    if step == POLICY["maximumSteps"]:
        expected_targets, expected_rng = train.replay_progress(
            POLICY["seed"], POLICY["maximumSteps"] * POLICY["gradientAccumulation"]
        )
        if (
            real_targets != contract["training"]["expectedRealTargetPositionsAt100Steps"]
            or real_targets != expected_targets
            or rng.getstate() != expected_rng
        ):
            raise RuntimeError("P2-30 complete-record progress differs from the authorized deterministic replay")

    result = {
        "schemaVersion": 1,
        "milestone": "P2-30",
        "kind": "plex-p2-30-first-task-finetune-result-v1",
        "authorizationContractSha256": sha256_file(contract_path),
        "startingCheckpointSha256": contract["baseStage"]["checkpointSha256"],
        "taskBundleManifestSha256": contract["data"]["bundleManifestSha256"],
        "completedUpdates": step,
        "maximumAuthorizedUpdates": POLICY["maximumSteps"],
        "elapsedSeconds": elapsed,
        "stoppedByWallTime": step < POLICY["maximumSteps"] and not interrupted,
        "interrupted": interrupted,
        "realTargetPositions": real_targets,
        "paddingTargetPositions": padding_targets,
        "samplerAudit": train.sampling_audit(),
        "meanRecentLoss": sum(losses[-20:]) / len(losses[-20:]) if losses else None,
        "validations": validations,
        "checkpoints": checkpoints,
        "finalCheckpoint": str(final_path.relative_to(root)),
        "finalCheckpointSha256": sha256_file(final_path),
        "peakGpuMemory": peak_gpu_memory(device),
        "finalHoldoutOpened": False,
        "p2_01bUsedForGradients": False,
        "automaticContinuationAuthorized": False,
        "resumeAuthorized": False,
    }
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    _append_jsonl(metrics_path, {"event": "run_finished", **result})
    enforce_storage_limit(root, limit_bytes=ARTIFACT_LIMIT_BYTES)
    train.close()
    validation.close()
    return result
