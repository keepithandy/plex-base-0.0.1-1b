"""Continue the approved P2-22 v1 step-100 checkpoint through the P2-22b learning curve."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import torch

from prepare_p2_22_approved_experiment import ARTIFACT_ROOT, verify_prepared
from run_p2_22_approved_experiment import _development_node, _score_candidate, _score_task_set

from plex_training.checkpoint import read_checkpoint
from plex_training.pilot import inspect_pilot_bundle, resume_pilot
from plex_training.tokenizer import sha256_file

EXPERIMENT = "p2-22b-edit-intent-continuation-v1"
SOURCE_EXPERIMENT = "p2-22-edit-intent-classification-approved-v1"
APPROVAL = Path(__file__).resolve().parent / "approvals" / "p2-22b-edit-intent-continuation-v1.json"

CANDIDATE_SHA256 = "592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0"
TOKENIZER_SHA256 = "8f09812c2165cb928c1908f7a81ef59d5e8b6f3f8acb185e083bf1324ed23e5a"
TRAIN_JSONL_SHA256 = "f8eb980971cec99cd8b1f5ffce0bdec50e3746cb13e876db47c28397ef822789"
VALIDATION_JSONL_SHA256 = "706b93384790f1489dbd422cf98ac36668ef81cabbca9cbcc24e7f65c8aaf9d2"
TRAIN_TOKENS_SHA256 = "0c0263cdd72c4b63a351cdd745107e0f3263289fed3664dc6a00f28b3bea18c4"
VALIDATION_TOKENS_SHA256 = "2701d2a81e7e53309cde8976ffb656fd661ffb0623cef979cacbc5aca1d80324"
SOURCE_DATASET_MANIFEST_SHA256 = "7d8f4a60666efa292418438fcd5ac4a169b1f763c24e118bed6b53609bb85884"
SOURCE_SAMPLER_INDEX_SHA256 = "0132712f8aa7dc8267ffc7ef92c3acf7a3e7eb02a19b63a7ca986e7164c382b7"

PARAMETER_COUNT = 27_566_080
VOCABULARY_SIZE = 1074
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
    return (
        isinstance(left, (int, float))
        and math.isfinite(float(left))
        and abs(float(left) - right) <= tolerance
    )


def _verify_approval() -> dict[str, Any]:
    approval = _json(APPROVAL)
    expected = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training-continuation",
        "sourceExperiment": SOURCE_EXPERIMENT,
        "sourceCandidate": "p2-22-edit-intent-classification-candidate-v1",
        "sourceCandidateJsonlSha256": CANDIDATE_SHA256,
        "sourceStep": SOURCE_STEP,
        "sourceTokenizerSha256": TOKENIZER_SHA256,
        "sourceActualVocabularySize": VOCABULARY_SIZE,
        "sourceTrainJsonlSha256": TRAIN_JSONL_SHA256,
        "sourceValidationJsonlSha256": VALIDATION_JSONL_SHA256,
        "sourceTrainTokensSha256": TRAIN_TOKENS_SHA256,
        "sourceValidationTokensSha256": VALIDATION_TOKENS_SHA256,
        "sourceDatasetManifestSha256": SOURCE_DATASET_MANIFEST_SHA256,
        "sourceSamplerIndexSha256": SOURCE_SAMPLER_INDEX_SHA256,
        "sourceTokensProcessedTotal": 151505,
        "sourceTrainingCompleteTaskPasses": 64,
        "sourceCheckpointIdentity": "verify-at-runtime-against-step-100-trained-candidate-score",
        "parameterCount": PARAMETER_COUNT,
        "seed": SEED,
        "preserveOptimizerState": True,
        "preserveSamplerState": True,
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
        "includePerIntentResults": ["REPLACE", "INSERT", "DELETE", "RENAME", "TOGGLE"],
        "sourceTrainingLevelPasses": {"A": 24, "B": 22, "C": 18},
        "sourceTierPasses": {"A": 6, "B": 2, "C": 7},
        "sourceTrainingIntentPasses": {
            "REPLACE": 1, "INSERT": 8, "DELETE": 20, "RENAME": 21, "TOGGLE": 14
        },
        "maximumCumulativeStep": 500,
        "automaticContinuationBeyond500": False,
        "p214ExcludedFromTraining": True,
        "p201bExcludedFromTraining": True,
        "finalHoldoutOpened": False,
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-22b approval differs from the exact owner-authorized continuation")
    if not _close(approval.get("sourceValidationLossBefore"), 7.0730092866080145):
        raise ValueError("P2-22b source validation-loss baseline changed")
    if not _close(approval.get("sourceValidationLossAfter"), 3.3212734971727644):
        raise ValueError("P2-22b source validation loss changed")
    if not _close(approval.get("sourceMeanRecentLoss"), 0.43861074475571515):
        raise ValueError("P2-22b source recent training loss changed")
    return approval


def _verify_source(
    prepared: Path, source_run: Path
) -> tuple[dict[str, Any], Path, dict[str, Any], str]:
    approval = _verify_approval()
    plan = verify_prepared(prepared)
    if (
        plan.get("candidateJsonlSha256") != CANDIDATE_SHA256
        or plan.get("tokenizerSha256") != TOKENIZER_SHA256
        or plan.get("actualVocabularySize") != VOCABULARY_SIZE
        or plan.get("parameterCount") != PARAMETER_COUNT
        or plan.get("seed") != SEED
        or plan.get("samplingPolicy") != "complete-record-v1"
        or plan.get("microBatch") != 1
        or plan.get("gradientAccumulation") != 16
        or plan.get("trainingRecords") != 150
        or plan.get("evaluationRecords") != 75
        or plan.get("trainingLevelCounts") != {"A": 50, "B": 50, "C": 50}
        or plan.get("evaluationTierCounts") != {"A": 25, "B": 25, "C": 25}
        or plan.get("evaluationUsedForGradientTraining") is not False
        or plan.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("Prepared P2-22 v1 bundle differs from the continuation approval")

    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    dataset = bundle["dataset"]
    sampler_preflight = plan.get("completeRecordSamplerPreflight")
    if (
        bundle["tokenizer"].get("tokenizerSha256") != TOKENIZER_SHA256
        or bundle["tokenizer"].get("actualVocabularySize") != VOCABULARY_SIZE
        or dataset.get("sourceDatasetManifestSha256") != SOURCE_DATASET_MANIFEST_SHA256
        or dataset.get("trainJsonlSha256") != TRAIN_JSONL_SHA256
        or dataset.get("validationJsonlSha256") != VALIDATION_JSONL_SHA256
        or dataset.get("trainTokensSha256") != TRAIN_TOKENS_SHA256
        or dataset.get("validationTokensSha256") != VALIDATION_TOKENS_SHA256
        or dataset.get("trainRecords") != 150
        or dataset.get("validationRecords") != 75
        or not isinstance(sampler_preflight, dict)
        or sampler_preflight.get("indexSha256") != SOURCE_SAMPLER_INDEX_SHA256
    ):
        raise ValueError("Prepared tokenizer/dataset identity differs from the approved P2-22b source")

    source_run = source_run.resolve(strict=True)
    source_run.relative_to(ARTIFACT_ROOT.resolve())
    result = _json(source_run / "result.json")
    candidate_score = _json(source_run / "trained-candidate-score.json")
    checkpoint = source_run / "pilot" / "pilot-checkpoint.pt"
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise ValueError("P2-22b source checkpoint is missing or linked")
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
        or result.get("actualVocabularySize") != VOCABULARY_SIZE
        or result.get("evaluationUsedForGradientTraining") is not False
        or result.get("p214UsedForGradientTraining") is not False
        or result.get("p201bUsedForGradientTraining") is not False
        or result.get("automaticExtension") is not False
        or result.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-22 v1 step-100 result does not match the authorized continuation source")

    training = result.get("training")
    if not isinstance(training, dict) or (
        training.get("step") != SOURCE_STEP
        or training.get("stepsThisRun") != SOURCE_STEP
        or training.get("interrupted") is not False
        or training.get("tokensProcessedTotal") != approval["sourceTokensProcessedTotal"]
        or not _close(training.get("validationLossBefore"), approval["sourceValidationLossBefore"])
        or not _close(training.get("validationLossAfter"), approval["sourceValidationLossAfter"])
        or not _close(training.get("meanRecentLoss"), approval["sourceMeanRecentLoss"])
    ):
        raise ValueError("P2-22 v1 step-100 training metrics differ from the owner-reviewed source")

    expected_tiers = {
        tier: result["candidate"]["tiers"][tier]["trained"]
        for tier in ("A", "B", "C")
    }
    if (
        result.get("candidate", {}).get("trainedTraining", {}).get("completeTaskPasses")
        != approval["sourceTrainingCompleteTaskPasses"]
        or {
            level: result.get("candidate", {}).get("trainedTraining", {})
            .get("levels", {}).get(level, {}).get("completeTaskPasses")
            for level in ("A", "B", "C")
        } != approval["sourceTrainingLevelPasses"]
        or {
            tier: result.get("candidate", {}).get("tiers", {})
            .get(tier, {}).get("trained", {}).get("completeTaskPasses")
            for tier in ("A", "B", "C")
        } != approval["sourceTierPasses"]
        or {
            intent: sum(
                result.get("candidate", {}).get("trainedTraining", {})
                .get("levels", {}).get(level, {}).get("byTargetIntent", {})
                .get(intent, {}).get("exact", 0)
                for level in ("A", "B", "C")
            )
            for intent in ("REPLACE", "INSERT", "DELETE", "RENAME", "TOGGLE")
        } != approval["sourceTrainingIntentPasses"]
        or candidate_score.get("checkpointStep") != SOURCE_STEP
        or candidate_score.get("checkpointSha256") != checkpoint_sha
        or candidate_score.get("training") != result.get("candidate", {}).get("trainedTraining")
        or candidate_score.get("tiers") != expected_tiers
    ):
        raise ValueError("P2-22 v1 step-100 scored checkpoint identity changed")

    model, payload = read_checkpoint(checkpoint, torch.device("cpu"))
    actual_parameters = sum(parameter.numel() for parameter in model.parameters())
    settings = payload.get("trainingSettings")
    sampler = settings.get("samplingPolicy") if isinstance(settings, dict) else None
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
        or not isinstance(settings, dict)
        or not isinstance(sampler, dict)
        or sampler.get("kind") != "complete-record-v1"
        or sampler.get("records") != 150
        or sampler.get("trainJsonlSha256") != TRAIN_JSONL_SHA256
        or sampler.get("indexSha256") != SOURCE_SAMPLER_INDEX_SHA256
    ):
        raise ValueError("P2-22b source checkpoint is not a resumable approved step-100 checkpoint")
    del model, payload
    return plan, checkpoint, result, checkpoint_sha


def _score_step(
    checkpoint: Path, prepared: Path, step: int, stage_dir: Path
) -> dict[str, Any]:
    candidate = _score_candidate(
        checkpoint, prepared, "cuda", stage_dir / "candidate-score.json"
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
        raise ValueError(f"P2-22b scoring did not use cumulative step {step}")
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
            for tier in ("A", "B", "C")
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
        raise FileExistsError("P2-22b output exists; choose a fresh directory")
    if output == prepared or output in prepared.parents or prepared in output.parents:
        raise ValueError("P2-22b output must be separate from prepared inputs")

    plan, source_checkpoint, source_result, source_checkpoint_sha = _verify_source(
        prepared, source_run
    )

    task_set = _json(prepared / "scoring" / "p2-01b-dev-v1.json")
    _development_node(task_set)

    output.mkdir(parents=True, exist_ok=False)
    curve = [_source_curve_row(source_result)]
    stages: dict[str, Any] = {}
    current_checkpoint = source_checkpoint
    current_step = SOURCE_STEP

    for target_step in SCORING_STEPS:
        if target_step != current_step + INCREMENT:
            raise ValueError("P2-22b schedule must remain four isolated +100-step increments")
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
            raise ValueError(
                f"P2-22b continuation failed its cumulative step-{target_step} gate"
            )

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
        raise ValueError(
            "P2-22b ended anywhere other than the owner-approved cumulative step 500"
        )
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-22 v1 inputs changed during P2-22b")
    if sha256_file(source_checkpoint) != source_checkpoint_sha:
        raise ValueError("Original P2-22 v1 step-100 checkpoint changed during P2-22b")

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
        "samplerStatePreserved": True,
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
            "P2-22b changes cumulative optimization only. It preserves the exact "
            "P2-22 v1 edit-intent curriculum, tokenizer, architecture, "
            "optimizer/sampler/RNG trajectory, objective, complete-record sampler "
            "and Level A/B/C scoring. The final holdout remains closed."
        ),
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    training = row["training"]
    levels = training["levels"]
    a = row["tiers"]["A"]
    b = row["tiers"]["B"]
    c = row["tiers"]["C"]
    return {
        "step": row["step"],
        "trainingComplete": training["completeTaskPasses"],
        "trainingLevels": {
            level: levels[level]["completeTaskPasses"]
            for level in ("A", "B", "C")
        },
        "tierA": {
            "complete": a["completeTaskPasses"],
            "intentExact": a["intentExact"],
            "knownIntentOutput": a["knownIntentOutput"],
            "wrongKnownIntent": a["wrongKnownIntent"],
            "unknownOrMalformedIntent": a["unknownOrMalformedIntent"],
            "byTargetIntent": a["byTargetIntent"],
            "eos": a["eos"],
        },
        "tierB": {
            "complete": b["completeTaskPasses"],
            "intentExact": b["intentExact"],
            "knownIntentOutput": b["knownIntentOutput"],
            "wrongKnownIntent": b["wrongKnownIntent"],
            "unknownOrMalformedIntent": b["unknownOrMalformedIntent"],
            "byTargetIntent": b["byTargetIntent"],
            "eos": b["eos"],
        },
        "tierC": {
            "complete": c["completeTaskPasses"],
            "intentExact": c["intentExact"],
            "knownIntentOutput": c["knownIntentOutput"],
            "wrongKnownIntent": c["wrongKnownIntent"],
            "unknownOrMalformedIntent": c["unknownOrMalformedIntent"],
            "byTargetIntent": c["byTargetIntent"],
            "eos": c["eos"],
        },
        "p214Passes": row["p214CssEditDevelopment12"]["passes"],
        "p201bPasses": row["p201bDevelopment30"]["passes"],
        "validationLossAfterIncrement": row["validationLossAfterIncrement"],
        "meanRecentLoss": row["meanRecentLoss"],
    }


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
            "learningCurve": [_compact(row) for row in result["learningCurve"]],
            "automaticContinuationBeyond500": result["automaticContinuationBeyond500"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-22b-continuation: {exc}", file=sys.stderr)
        raise SystemExit(2)
