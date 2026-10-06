"""Continue the approved P2-16 step-100 checkpoint through the P2-16b learning curve."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import torch

from prepare_p2_16_approved_experiment import ARTIFACT_ROOT, verify_prepared
from run_p2_16_approved_experiment import _score_candidate, _score_task_set

from plex_training.checkpoint import read_checkpoint
from plex_training.pilot import inspect_pilot_bundle, resume_pilot
from plex_training.tokenizer import sha256_file


EXPERIMENT = "p2-16b-optimization-continuation-v1"
SOURCE_EXPERIMENT = "p2-16-css-generalization-approved-v1"
APPROVAL = (
    Path(__file__).resolve().parent
    / "approvals"
    / "p2-16b-optimization-continuation-v1.json"
)
CANDIDATE_SHA256 = "639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc"
TOKENIZER_SHA256 = "1b0494e0e56bc904dfc94c1d9a571eefca82e20f78276632191514b69421b7a0"
TRAIN_JSONL_SHA256 = "ac48d07ab0b39edd1e810fa551be571e6f0d1d653cccce9120fc6121d4ee7ea1"
VALIDATION_JSONL_SHA256 = "c92d6248fc954e23fb7c22e364864656ea73185b91296245fa888420e7a5e540"
TRAIN_TOKENS_SHA256 = "5b15eecd538adbfca25b21f5ae1ef61a68c0cfb4544e4983244b68a2e7d5388f"
VALIDATION_TOKENS_SHA256 = "f3eca3c737cee9109ce1a9912ff5e0eb1a9b138b1a8e53b10480ffae3a123dd6"
SOURCE_DATASET_MANIFEST_SHA256 = (
    "1782168fc6a753e2c26b9e5d5f15015c99a5dcaea3f96fdb98781f73bbcec28e"
)
PARAMETER_COUNT = 27_566_080
SEED = 1337
SOURCE_STEP = 100
INCREMENT = 100
SCORING_STEPS = (200, 300, 400, 500)
MINUTES_PER_INCREMENT = 10.0


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _close(left: Any, right: float, *, tolerance: float = 1e-12) -> bool:
    return isinstance(left, (int, float)) and math.isfinite(float(left)) and abs(float(left) - right) <= tolerance


def _verify_approval() -> dict[str, Any]:
    approval = _json(APPROVAL)
    expected = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training-continuation",
        "sourceExperiment": SOURCE_EXPERIMENT,
        "sourceCandidate": "p2-16-css-generalization-candidate-v1",
        "sourceCandidateJsonlSha256": CANDIDATE_SHA256,
        "sourceStep": SOURCE_STEP,
        "sourceTokenizerSha256": TOKENIZER_SHA256,
        "sourceActualVocabularySize": 717,
        "sourceTrainJsonlSha256": TRAIN_JSONL_SHA256,
        "sourceValidationJsonlSha256": VALIDATION_JSONL_SHA256,
        "sourceTrainTokensSha256": TRAIN_TOKENS_SHA256,
        "sourceValidationTokensSha256": VALIDATION_TOKENS_SHA256,
        "sourceDatasetManifestSha256": SOURCE_DATASET_MANIFEST_SHA256,
        "sourceTokensProcessedTotal": 225_764,
        "sourceCheckpointIdentity": "verify-at-runtime-against-step-100-trained-candidate-score",
        "parameterCount": PARAMETER_COUNT,
        "seed": SEED,
        "preserveOptimizerState": True,
        "preserveRngState": True,
        "preserveTokenizer": True,
        "preserveDataset": True,
        "lossObjective": "ordinary-next-token-over-complete-records",
        "samplingPolicy": "complete-record-v1",
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "continuationIncrements": [100, 100, 100, 100],
        "cumulativeScoringSteps": list(SCORING_STEPS),
        "maximumCumulativeStep": 500,
        "automaticContinuationBeyond500": False,
        "p214ExcludedFromTraining": True,
        "p201bExcludedFromTraining": True,
        "finalHoldoutOpened": False,
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-16b approval differs from the exact owner-authorized continuation")
    if not _close(approval.get("sourceValidationLossBefore"), 6.716460253063001):
        raise ValueError("P2-16b approval source validation-loss baseline changed")
    if not _close(approval.get("sourceValidationLossAfter"), 3.3871124669125208):
        raise ValueError("P2-16b approval source validation loss changed")
    if not _close(approval.get("sourceMeanRecentLoss"), 0.32886304398998617):
        raise ValueError("P2-16b approval source recent training loss changed")
    message = approval.get("ownerMessage")
    if not isinstance(message, str) or "through cumulative step 500" not in message:
        raise ValueError("P2-16b approval does not retain the owner authorization")
    return approval


def _verify_source(
    prepared: Path,
    source_run: Path,
) -> tuple[dict[str, Any], Path, dict[str, Any], str]:
    approval = _verify_approval()
    plan = verify_prepared(prepared)
    if (
        plan.get("candidateJsonlSha256") != CANDIDATE_SHA256
        or plan.get("tokenizerSha256") != TOKENIZER_SHA256
        or plan.get("actualVocabularySize") != 717
        or plan.get("parameterCount") != PARAMETER_COUNT
        or plan.get("seed") != SEED
        or plan.get("samplingPolicy") != "complete-record-v1"
        or plan.get("microBatch") != 1
        or plan.get("gradientAccumulation") != 16
        or plan.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("Prepared P2-16 bundle differs from the continuation approval")

    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    dataset = bundle["dataset"]
    if (
        bundle["tokenizer"].get("tokenizerSha256") != TOKENIZER_SHA256
        or dataset.get("sourceDatasetManifestSha256") != SOURCE_DATASET_MANIFEST_SHA256
        or dataset.get("trainJsonlSha256") != TRAIN_JSONL_SHA256
        or dataset.get("validationJsonlSha256") != VALIDATION_JSONL_SHA256
        or dataset.get("trainTokensSha256") != TRAIN_TOKENS_SHA256
        or dataset.get("validationTokensSha256") != VALIDATION_TOKENS_SHA256
        or dataset.get("trainRecords") != 120
        or dataset.get("validationRecords") != 60
    ):
        raise ValueError("Prepared tokenizer/dataset identity differs from the approved P2-16b source")

    source_run = source_run.resolve(strict=True)
    source_run.relative_to(ARTIFACT_ROOT.resolve())
    result = _json(source_run / "result.json")
    candidate_score = _json(source_run / "trained-candidate-score.json")
    checkpoint = source_run / "pilot" / "pilot-checkpoint.pt"
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise ValueError("P2-16b source checkpoint is missing or linked")

    checkpoint_sha = sha256_file(checkpoint)
    if (
        result.get("experiment") != SOURCE_EXPERIMENT
        or result.get("trainingReachedStepLimit") is not True
        or result.get("trainingInterrupted") is not False
        or result.get("freshScratchInitialization") is not True
        or result.get("seed") != SEED
        or result.get("device") != "cuda"
        or result.get("parameterCount") != PARAMETER_COUNT
        or result.get("samplingPolicy") != "complete-record-v1"
        or result.get("lossObjective") != "ordinary-next-token-over-complete-records"
        or result.get("actualStepCap") != SOURCE_STEP
        or result.get("candidateJsonlSha256") != CANDIDATE_SHA256
        or result.get("tokenizerSha256") != TOKENIZER_SHA256
        or result.get("actualVocabularySize") != 717
        or result.get("evaluationUsedForGradientTraining") is not False
        or result.get("p214UsedForGradientTraining") is not False
        or result.get("p201bUsedForGradientTraining") is not False
        or result.get("automaticExtension") is not False
        or result.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-16 step-100 result does not match the authorized continuation source")

    training = result.get("training")
    if not isinstance(training, dict):
        raise ValueError("P2-16 step-100 training summary is missing")
    if (
        training.get("step") != SOURCE_STEP
        or training.get("stepsThisRun") != SOURCE_STEP
        or training.get("interrupted") is not False
        or training.get("tokensProcessedTotal") != approval["sourceTokensProcessedTotal"]
        or not _close(training.get("validationLossBefore"), approval["sourceValidationLossBefore"])
        or not _close(training.get("validationLossAfter"), approval["sourceValidationLossAfter"])
        or not _close(training.get("meanRecentLoss"), approval["sourceMeanRecentLoss"])
    ):
        raise ValueError("P2-16 step-100 training metrics differ from the owner-reviewed source")

    if (
        candidate_score.get("checkpointStep") != SOURCE_STEP
        or candidate_score.get("checkpointSha256") != checkpoint_sha
        or candidate_score.get("training") != result.get("candidate", {}).get("trainedTraining")
        or candidate_score.get("tiers")
        != {
            tier: result["candidate"]["tiers"][tier]["trained"]
            for tier in ("A", "B", "C", "D")
        }
    ):
        raise ValueError("P2-16 step-100 scored checkpoint identity changed")

    model, payload = read_checkpoint(checkpoint, torch.device("cpu"))
    actual_parameters = sum(parameter.numel() for parameter in model.parameters())
    if (
        actual_parameters != PARAMETER_COUNT
        or payload.get("step") != SOURCE_STEP
        or payload.get("seed") != SEED
        or payload.get("codec") != "plex-byte-bpe-v1"
        or payload.get("tokenizerRecord") != bundle["tokenizer"]
        or payload.get("datasetRecord") != bundle["dataset"]
        or not isinstance(payload.get("optimizerStateDict"), dict)
        or not isinstance(payload.get("samplingRngState"), tuple)
        or not isinstance(payload.get("torchCpuRngState"), torch.Tensor)
        or not isinstance(payload.get("torchCudaRngStates"), list)
        or not payload.get("torchCudaRngStates")
        or not isinstance(payload.get("trainingSettings"), dict)
        or payload["trainingSettings"].get("samplingPolicy", {}).get("kind")
        != "complete-record-v1"
    ):
        raise ValueError("P2-16 source checkpoint is not a resumable approved step-100 checkpoint")
    del model, payload
    return plan, checkpoint, result, checkpoint_sha


def _score_step(
    checkpoint: Path,
    prepared: Path,
    step: int,
    stage_dir: Path,
) -> dict[str, Any]:
    candidate = _score_candidate(
        checkpoint,
        prepared,
        "cuda",
        stage_dir / "candidate-score.json",
    )
    p214 = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring" / "p2-14-task-set.json",
        "cuda",
        stage_dir / "p2-14-score.json",
    )
    p201b = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring" / "p2-01b-dev-v1.json",
        "cuda",
        stage_dir / "p2-01b-score.json",
    )
    if (
        candidate.get("checkpointStep") != step
        or p214.get("checkpointStep") != step
        or p201b.get("checkpointStep") != step
    ):
        raise ValueError(f"P2-16b scoring did not use cumulative step {step}")
    return {
        "training": candidate["training"],
        "tiers": candidate["tiers"],
        "p214CssEditDevelopment12": {
            "passes": p214["completeTaskPasses"],
            "eos": p214["eos"],
        },
        "p201bDevelopment30": {
            "passes": p201b["completeTaskPasses"],
            "eos": p201b["eos"],
            "byLanguage": p201b["byLanguage"],
        },
    }


def _source_curve_row(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": SOURCE_STEP,
        "stepsThisIncrement": SOURCE_STEP,
        "training": result["candidate"]["trainedTraining"],
        "tiers": {
            tier: result["candidate"]["tiers"][tier]["trained"]
            for tier in ("A", "B", "C", "D")
        },
        "p214CssEditDevelopment12": {
            "passes": result["p214CssEditDevelopment12"]["trainedPasses"],
        },
        "p201bDevelopment30": {
            "passes": result["p201bDevelopment30"]["trainedPasses"],
            "byLanguage": result["p201bDevelopment30"]["trainedByLanguage"],
        },
        "validationLossBeforeIncrement": result["training"]["validationLossBefore"],
        "validationLossAfterIncrement": result["training"]["validationLossAfter"],
        "meanRecentLoss": result["training"]["meanRecentLoss"],
        "tokensProcessedTotal": result["training"]["tokensProcessedTotal"],
    }


def run(prepared: Path, source_run: Path, output: Path) -> dict[str, Any]:
    prepared = prepared.resolve(strict=True)
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("P2-16b output exists; choose a fresh directory")
    if output == prepared or output in prepared.parents or prepared in output.parents:
        raise ValueError("P2-16b output must be separate from prepared inputs")

    plan, source_checkpoint, source_result, source_checkpoint_sha = _verify_source(
        prepared,
        source_run,
    )
    output.mkdir(parents=True, exist_ok=False)

    curve = [_source_curve_row(source_result)]
    stages: dict[str, Any] = {}
    current_checkpoint = source_checkpoint
    current_step = SOURCE_STEP

    for target_step in SCORING_STEPS:
        if target_step != current_step + INCREMENT:
            raise ValueError("P2-16b continuation schedule is not four isolated +100-step increments")
        stage_dir = output / f"step-{target_step}"
        resume = resume_pilot(
            bundle_dir=prepared / "tokenizer",
            checkpoint_path=current_checkpoint,
            output_dir=stage_dir,
            artifact_root=ARTIFACT_ROOT,
            minutes=MINUTES_PER_INCREMENT,
            steps=INCREMENT,
            device_name="cuda",
            micro_batch=1,
            gradient_accumulation=16,
            checkpoint_every_minutes=5.0,
            dataset_dir=prepared / "dataset",
        )
        checkpoint = stage_dir / "resumed-checkpoint.pt"
        if (
            resume.get("resumeCheckPassed") is not True
            or resume.get("sourceStep") != current_step
            or resume.get("resumedExpectedSteps") != INCREMENT
            or resume.get("resumedStepsCompleted") != INCREMENT
            or resume.get("samplingPolicy") != "complete-record-v1"
            or resume.get("training", {}).get("step") != target_step
            or resume.get("training", {}).get("stepsThisRun") != INCREMENT
            or resume.get("training", {}).get("interrupted") is not False
            or resume.get("resumedCheckpointSha256") != sha256_file(checkpoint)
        ):
            raise ValueError(f"P2-16b continuation failed its cumulative step-{target_step} gate")

        scores = _score_step(checkpoint, prepared, target_step, stage_dir)
        training = resume["training"]
        row = {
            "step": target_step,
            "sourceStep": current_step,
            "stepsThisIncrement": INCREMENT,
            **scores,
            "validationLossBeforeIncrement": training["validationLossBefore"],
            "validationLossAfterIncrement": training["validationLossAfter"],
            "meanRecentLoss": training["meanRecentLoss"],
            "tokensProcessedThisIncrement": training["tokensProcessedThisRun"],
            "tokensProcessedTotal": training["tokensProcessedTotal"],
            "elapsedSeconds": training["elapsedSeconds"],
            "checkpointSha256": resume["resumedCheckpointSha256"],
        }
        curve.append(row)
        stages[str(target_step)] = {
            "sourceCheckpointSha256": resume["sourceCheckpointSha256"],
            "checkpointSha256": resume["resumedCheckpointSha256"],
            "resumeCheckPassed": True,
            "validationLossBefore": training["validationLossBefore"],
            "validationLossAfter": training["validationLossAfter"],
            "meanRecentLoss": training["meanRecentLoss"],
        }
        current_checkpoint = checkpoint
        current_step = target_step

    if current_step != 500:
        raise ValueError("P2-16b ended anywhere other than the owner-approved cumulative step 500")
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-16 inputs changed during P2-16b continuation")
    if sha256_file(source_checkpoint) != source_checkpoint_sha:
        raise ValueError("Original P2-16 step-100 checkpoint changed during P2-16b")

    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "sourceExperiment": SOURCE_EXPERIMENT,
        "sourceStep": SOURCE_STEP,
        "sourceCheckpointSha256": source_checkpoint_sha,
        "finalStep": current_step,
        "scoringSteps": list(SCORING_STEPS),
        "continuationIncrements": [100, 100, 100, 100],
        "device": "cuda",
        "parameterCount": PARAMETER_COUNT,
        "seed": SEED,
        "optimizerStatePreserved": True,
        "rngStatePreserved": True,
        "tokenizerPreserved": True,
        "datasetPreserved": True,
        "tokenizerSha256": TOKENIZER_SHA256,
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "samplingPolicy": "complete-record-v1",
        "lossObjective": "ordinary-next-token-over-complete-records",
        "microBatch": 1,
        "gradientAccumulation": 16,
        "learningCurve": curve,
        "stages": stages,
        "p214UsedForGradientTraining": False,
        "p201bUsedForGradientTraining": False,
        "automaticContinuationBeyond500": False,
        "finalHoldoutOpened": False,
        "limitations": (
            "P2-16b changes cumulative optimization only. It reuses the approved P2-16 "
            "curriculum, tokenizer, architecture, optimizer trajectory, RNG trajectory, "
            "objective, sampler and development scoring. The final holdout remains closed."
        ),
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.prepared, args.source_run, args.output_dir)
        print(json.dumps({
            "report": str(args.output_dir / "result.json"),
            "sourceStep": result["sourceStep"],
            "finalStep": result["finalStep"],
            "learningCurve": [
                {
                    "step": row["step"],
                    "trainingPasses": row["training"]["completeTaskPasses"],
                    "trainingSyntaxValid": row["training"]["syntaxValid"],
                    "tierPasses": {
                        tier: row["tiers"][tier]["completeTaskPasses"]
                        for tier in ("A", "B", "C", "D")
                    },
                    "tierSyntaxValid": {
                        tier: row["tiers"][tier]["syntaxValid"]
                        for tier in ("A", "B", "C", "D")
                    },
                    "p214Passes": row["p214CssEditDevelopment12"]["passes"],
                    "p201bPasses": row["p201bDevelopment30"]["passes"],
                    "validationLossAfterIncrement": row["validationLossAfterIncrement"],
                    "meanRecentLoss": row["meanRecentLoss"],
                }
                for row in result["learningCurve"]
            ],
            "automaticContinuationBeyond500": result["automaticContinuationBeyond500"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-16b-continuation: {exc}", file=sys.stderr)
        raise SystemExit(2)
