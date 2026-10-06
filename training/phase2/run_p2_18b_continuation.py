"""Continue the approved P2-18 v3 step-100 checkpoint through the P2-18b learning curve."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import torch

from prepare_p2_18_approved_experiment import ARTIFACT_ROOT, verify_prepared
from run_p2_18_approved_experiment import _development_node, _score_candidate, _score_task_set

from plex_training.checkpoint import read_checkpoint
from plex_training.pilot import inspect_pilot_bundle, resume_pilot
from plex_training.tokenizer import sha256_file

EXPERIMENT = "p2-18b-literal-copy-continuation-v1"
SOURCE_EXPERIMENT = "p2-18-literal-copy-approved-v1"
APPROVAL = Path(__file__).resolve().parent / "approvals" / "p2-18b-literal-copy-continuation-v1.json"

CANDIDATE_SHA256 = "9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6"
TOKENIZER_SHA256 = "44756dc5700e4ac4d258403429358c0d4783b55fccb0271d695e29ed0bd54533"
TRAIN_JSONL_SHA256 = "9f06700c7b3ddd965614307ba18d5e83b6df8e67c403f4c06855401feb108de1"
VALIDATION_JSONL_SHA256 = "347a17d49ac322c30d61c423139074027610ddc5583bacd07804d788baae84cd"
TRAIN_TOKENS_SHA256 = "80bc255f1d07d5583ef8e0ee187459ee72e5bbbb86ae2c6975c0af0334d38894"
VALIDATION_TOKENS_SHA256 = "718bc305a2554b15eac3383db56316ac6867cb6d813bd349d6bcbbbfb1dd3e92"
SOURCE_DATASET_MANIFEST_SHA256 = "43f828c38b936f98e9bb140cc7bfd5f7e86f12d56029655274b8fb4656270d81"

PARAMETER_COUNT = 27_566_080
VOCABULARY_SIZE = 820
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
        "sourceCandidate": "p2-18-literal-copy-candidate-v1",
        "sourceCandidateJsonlSha256": CANDIDATE_SHA256,
        "sourceStep": SOURCE_STEP,
        "sourceTokenizerSha256": TOKENIZER_SHA256,
        "sourceActualVocabularySize": VOCABULARY_SIZE,
        "sourceTrainJsonlSha256": TRAIN_JSONL_SHA256,
        "sourceValidationJsonlSha256": VALIDATION_JSONL_SHA256,
        "sourceTrainTokensSha256": TRAIN_TOKENS_SHA256,
        "sourceValidationTokensSha256": VALIDATION_TOKENS_SHA256,
        "sourceDatasetManifestSha256": SOURCE_DATASET_MANIFEST_SHA256,
        "sourceTokensProcessedTotal": 132286,
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
        "maximumCumulativeStep": 500,
        "automaticContinuationBeyond500": False,
        "p214ExcludedFromTraining": True,
        "p201bExcludedFromTraining": True,
        "finalHoldoutOpened": False,
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-18b approval differs from the exact owner-authorized continuation")
    if not _close(approval.get("sourceValidationLossBefore"), 6.828160087267558):
        raise ValueError("P2-18b source validation-loss baseline changed")
    if not _close(approval.get("sourceValidationLossAfter"), 2.876676877339681):
        raise ValueError("P2-18b source validation loss changed")
    if not _close(approval.get("sourceMeanRecentLoss"), 0.5493557507172226):
        raise ValueError("P2-18b source recent training loss changed")
    message = approval.get("ownerMessage")
    if not isinstance(message, str) or "through cumulative step 500" not in message:
        raise ValueError("P2-18b approval does not retain the owner authorization")
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
        or plan.get("trainingRecords") != 144
        or plan.get("evaluationRecords") != 72
        or plan.get("evaluationUsedForGradientTraining") is not False
        or plan.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("Prepared P2-18 v3 bundle differs from the continuation approval")

    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    dataset = bundle["dataset"]
    if (
        bundle["tokenizer"].get("tokenizerSha256") != TOKENIZER_SHA256
        or bundle["tokenizer"].get("actualVocabularySize") != VOCABULARY_SIZE
        or dataset.get("sourceDatasetManifestSha256") != SOURCE_DATASET_MANIFEST_SHA256
        or dataset.get("trainJsonlSha256") != TRAIN_JSONL_SHA256
        or dataset.get("validationJsonlSha256") != VALIDATION_JSONL_SHA256
        or dataset.get("trainTokensSha256") != TRAIN_TOKENS_SHA256
        or dataset.get("validationTokensSha256") != VALIDATION_TOKENS_SHA256
        or dataset.get("trainRecords") != 144
        or dataset.get("validationRecords") != 72
    ):
        raise ValueError("Prepared tokenizer/dataset identity differs from the approved P2-18b source")

    source_run = source_run.resolve(strict=True)
    source_run.relative_to(ARTIFACT_ROOT.resolve())
    result = _json(source_run / "result.json")
    candidate_score = _json(source_run / "trained-candidate-score.json")
    checkpoint = source_run / "pilot" / "pilot-checkpoint.pt"
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise ValueError("P2-18b source checkpoint is missing or linked")
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
        raise ValueError("P2-18 v3 step-100 result does not match the authorized continuation source")

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
        raise ValueError("P2-18 v3 step-100 training metrics differ from the owner-reviewed source")

    expected_tiers = {
        tier: result["candidate"]["tiers"][tier]["trained"]
        for tier in ("A", "B", "C", "D")
    }
    if (
        candidate_score.get("checkpointStep") != SOURCE_STEP
        or candidate_score.get("checkpointSha256") != checkpoint_sha
        or candidate_score.get("training") != result.get("candidate", {}).get("trainedTraining")
        or candidate_score.get("tiers") != expected_tiers
    ):
        raise ValueError("P2-18 v3 step-100 scored checkpoint identity changed")

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
        or sampler.get("records") != 144
        or sampler.get("trainJsonlSha256") != TRAIN_JSONL_SHA256
    ):
        raise ValueError("P2-18b source checkpoint is not a resumable approved step-100 checkpoint")
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
        raise ValueError(f"P2-18b scoring did not use cumulative step {step}")
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
        raise FileExistsError("P2-18b output exists; choose a fresh directory")
    if output == prepared or output in prepared.parents or prepared in output.parents:
        raise ValueError("P2-18b output must be separate from prepared inputs")

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
            raise ValueError("P2-18b schedule must remain four isolated +100-step increments")
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
                f"P2-18b continuation failed its cumulative step-{target_step} gate"
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
        raise ValueError("P2-18b ended anywhere other than the owner-approved cumulative step 500")
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-18 v3 inputs changed during P2-18b")
    if sha256_file(source_checkpoint) != source_checkpoint_sha:
        raise ValueError("Original P2-18 v3 step-100 checkpoint changed during P2-18b")

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
            "P2-18b changes cumulative optimization only. It preserves the exact P2-18 v3 "
            "literal-copy curriculum, tokenizer, architecture, optimizer/sampler/RNG trajectory, "
            "objective, complete-record sampler and Level A/B/C/D scoring. The final holdout "
            "remains closed."
        ),
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    train = row["training"]
    levels = train["levels"]
    a = row["tiers"]["A"]
    b = row["tiers"]["B"]
    c = row["tiers"]["C"]
    d = row["tiers"]["D"]
    return {
        "step": row["step"],
        "trainingComplete": train["completeTaskPasses"],
        "trainingLevels": {
            level: levels[level]["completeTaskPasses"]
            for level in ("A", "B", "C", "D")
        },
        "tierA": {
            "complete": a["completeTaskPasses"],
            "literalExact": a["literalExact"],
            "selectorExact": a["selectorLiteralExact"],
            "valueExact": a["valueLiteralExact"],
            "eos": a["eos"],
        },
        "tierB": {
            "complete": b["completeTaskPasses"],
            "format": b["formatValid"],
            "label": b["labelExact"],
            "literalExact": b["literalExact"],
            "selectorExact": b["selectorLiteralExact"],
            "valueExact": b["valueLiteralExact"],
            "eos": b["eos"],
        },
        "tierC": {
            "complete": c["completeTaskPasses"],
            "selectedFieldExact": c["selectedFieldExact"],
            "wrongFieldRetrieval": c["wrongFieldRetrieval"],
            "byTargetField": c["byTargetField"],
            "eos": c["eos"],
        },
        "tierD": {
            "complete": d["completeTaskPasses"],
            "format": d["formatValid"],
            "fullPlan": d["fullPlanExact"],
            "selector": d["selectorExact"],
            "old": d["oldValueExact"],
            "new": d["newValueExact"],
            "eos": d["eos"],
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
        print(f"plex-p2-18b-continuation: {exc}", file=sys.stderr)
        raise SystemExit(2)
