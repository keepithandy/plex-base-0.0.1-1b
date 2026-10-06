"""Score the evaluation-only P2-22c presence-transition diagnostic at P2-22b step 500."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import torch

from prepare_p2_22_approved_experiment import ARTIFACT_ROOT, verify_prepared
from verify_p2_22c_presence_transition_diagnostic import (
    DIAGNOSTIC,
    DIAGNOSTIC_SHA256,
    INTENTS,
    verify as verify_diagnostic,
)

from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.pilot import inspect_pilot_bundle
from plex_training.telemetry import select_device
from plex_training.tokenizer import PlexTokenizer, sha256_file

EXPERIMENT = "p2-22c-presence-transition-diagnostic-v1"
SOURCE_EXPERIMENT = "p2-22b-edit-intent-continuation-v1"
SOURCE_CANDIDATE_SHA256 = "592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0"
TOKENIZER_SHA256 = "8f09812c2165cb928c1908f7a81ef59d5e8b6f3f8acb185e083bf1324ed23e5a"
PARAMETER_COUNT = 27_566_080
VOCABULARY_SIZE = 1074
SEED = 1337
SOURCE_STEP = 500
BASE_INTENTS = ("REPLACE", "INSERT", "DELETE", "RENAME", "TOGGLE")
TIERS = ("A", "B", "C")

FINAL_TIER_EXACT = {"A": 16, "B": 16, "C": 18}
FINAL_TIER_INTENT_EXACT = {
    "A": {"REPLACE": 3, "INSERT": 0, "DELETE": 3, "RENAME": 5, "TOGGLE": 5},
    "B": {"REPLACE": 5, "INSERT": 0, "DELETE": 3, "RENAME": 5, "TOGGLE": 3},
    "C": {"REPLACE": 4, "INSERT": 2, "DELETE": 4, "RENAME": 5, "TOGGLE": 3},
}
SOURCE_INSERT_CONFUSION = {
    "DELETE": 6,
    "REPLACE": 3,
    "RENAME": 2,
    "TOGGLE": 2,
    "INSERT": 2,
}


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _rows(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("P2-22c row is not an object")
            result.append(row)
    return result


def _prompt(row: dict[str, Any]) -> str:
    return (
        "Write a small edit-intent classification solution.\n"
        f"Request: {row['request']}\n"
        "Output contract: Return only the requested output in the exact requested format.\n"
        "Return code only. Do not include Markdown fences or explanations."
    )


def _close(left: Any, right: float, *, tolerance: float = 1e-12) -> bool:
    return (
        isinstance(left, (int, float))
        and math.isfinite(float(left))
        and abs(float(left) - right) <= tolerance
    )


def _source_insert_confusion(candidate_score: dict[str, Any]) -> dict[str, int]:
    counts = Counter()
    for row in candidate_score.get("records", []):
        if (
            row.get("candidateSplit") == "evaluation"
            and row.get("targetIntent") == "INSERT"
        ):
            completion = str(row.get("completion", "")).strip()
            counts[completion if completion in BASE_INTENTS else "OTHER"] += 1
    return {key: counts.get(key, 0) for key in (*BASE_INTENTS, "OTHER") if counts.get(key, 0)}


def _verify_source(
    prepared: Path, source_run: Path
) -> tuple[dict[str, Any], Path, dict[str, Any], str]:
    plan = verify_prepared(prepared)
    if (
        plan.get("candidateJsonlSha256") != SOURCE_CANDIDATE_SHA256
        or plan.get("tokenizerSha256") != TOKENIZER_SHA256
        or plan.get("actualVocabularySize") != VOCABULARY_SIZE
        or plan.get("parameterCount") != PARAMETER_COUNT
        or plan.get("seed") != SEED
        or plan.get("trainingRecords") != 150
        or plan.get("evaluationRecords") != 75
        or plan.get("trainingLevelCounts") != {"A": 50, "B": 50, "C": 50}
        or plan.get("evaluationTierCounts") != {"A": 25, "B": 25, "C": 25}
        or plan.get("evaluationUsedForGradientTraining") is not False
        or plan.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("Prepared P2-22 bundle differs from the P2-22c source policy")

    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    if (
        bundle["tokenizer"].get("tokenizerSha256") != TOKENIZER_SHA256
        or bundle["tokenizer"].get("actualVocabularySize") != VOCABULARY_SIZE
        or bundle["dataset"].get("trainRecords") != 150
        or bundle["dataset"].get("validationRecords") != 75
    ):
        raise ValueError("Prepared P2-22 tokenizer/dataset identity changed")

    source_run = source_run.resolve(strict=True)
    source_run.relative_to(ARTIFACT_ROOT.resolve())
    result = _json(source_run / "result.json")
    if (
        result.get("experiment") != SOURCE_EXPERIMENT
        or result.get("finalStep") != SOURCE_STEP
        or result.get("candidateJsonlSha256") != SOURCE_CANDIDATE_SHA256
        or result.get("tokenizerSha256") != TOKENIZER_SHA256
        or result.get("parameterCount") != PARAMETER_COUNT
        or result.get("seed") != SEED
        or result.get("optimizerStatePreserved") is not True
        or result.get("samplerStatePreserved") is not True
        or result.get("rngStatePreserved") is not True
        or result.get("automaticContinuationBeyond500") is not False
        or result.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-22b result does not match the reviewed diagnostic source")

    curve = result.get("learningCurve")
    if not isinstance(curve, list) or [row.get("step") for row in curve] != [
        100, 200, 300, 400, 500
    ]:
        raise ValueError("P2-22b learning curve identity changed")
    final = curve[-1]
    training = final.get("training")
    tiers = final.get("tiers")
    if not isinstance(training, dict) or not isinstance(tiers, dict):
        raise ValueError("P2-22b final scoring block is missing")
    if (
        training.get("completeTaskPasses") != 150
        or {
            level: training.get("levels", {}).get(level, {}).get("completeTaskPasses")
            for level in TIERS
        } != {"A": 50, "B": 50, "C": 50}
        or {
            tier: tiers.get(tier, {}).get("completeTaskPasses")
            for tier in TIERS
        } != FINAL_TIER_EXACT
        or not _close(final.get("validationLossAfterIncrement"), 3.9322557279041837)
        or not _close(final.get("meanRecentLoss"), 0.07278045556158759)
        or final.get("p214CssEditDevelopment12", {}).get("passes") != 0
        or final.get("p201bDevelopment30", {}).get("passes") != 0
    ):
        raise ValueError("P2-22b final step metrics differ from the reviewed source")

    for tier in TIERS:
        actual = {
            intent: tiers[tier]
            .get("byTargetIntent", {})
            .get(intent, {})
            .get("exact")
            for intent in BASE_INTENTS
        }
        if actual != FINAL_TIER_INTENT_EXACT[tier]:
            raise ValueError(f"P2-22b Tier {tier} intent breakdown changed")

    stage = source_run / "step-500"
    checkpoint = stage / "resumed-checkpoint.pt"
    candidate_score = _json(stage / "candidate-score.json")
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise ValueError("P2-22b step-500 checkpoint is missing")
    checkpoint_sha = sha256_file(checkpoint)
    if (
        candidate_score.get("checkpointStep") != SOURCE_STEP
        or candidate_score.get("checkpointSha256") != checkpoint_sha
        or result.get("stages", {}).get("500", {}).get("checkpointSha256")
        != checkpoint_sha
        or _source_insert_confusion(candidate_score) != SOURCE_INSERT_CONFUSION
    ):
        raise ValueError("P2-22b step-500 checkpoint/scoring identity changed")

    model, payload = read_checkpoint(checkpoint, torch.device("cpu"))
    actual_parameters = sum(parameter.numel() for parameter in model.parameters())
    if (
        actual_parameters != PARAMETER_COUNT
        or payload.get("step") != SOURCE_STEP
        or payload.get("seed") != SEED
        or payload.get("tokenizerRecord") != bundle["tokenizer"]
        or payload.get("datasetRecord") != bundle["dataset"]
    ):
        raise ValueError("P2-22b step-500 checkpoint payload changed")
    del model, payload
    return plan, checkpoint, candidate_score, checkpoint_sha


def _score_row(
    row: dict[str, Any], completion: str, eos: bool, token_count: int
) -> dict[str, Any]:
    normalized = completion.strip()
    expected = row["solution"]
    known_base = normalized in BASE_INTENTS
    in_diagnostic = normalized in INTENTS
    exact = normalized == expected
    return {
        "id": row["id"],
        "tier": row["tier"],
        "taskKind": row["taskKind"],
        "targetIntent": row["targetIntent"],
        "beforePresence": row["beforePresence"],
        "afterPresence": row["afterPresence"],
        "contentRelation": row["contentRelation"],
        "request": row["request"],
        "expected": expected,
        "completion": completion,
        "normalizedCompletion": normalized,
        "generatedTokenCount": token_count,
        "eos": eos,
        "passed": exact,
        "intentExact": exact,
        "knownP222IntentOutput": known_base,
        "diagnosticVocabularyOutput": in_diagnostic,
        "outOfDiagnosticVocabulary": known_base and not in_diagnostic,
        "unknownOrMalformedIntent": not known_base,
    }


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {
        expected: {predicted: 0 for predicted in (*BASE_INTENTS, "OTHER")}
        for expected in INTENTS
    }
    for row in records:
        predicted = (
            row["normalizedCompletion"]
            if row["normalizedCompletion"] in BASE_INTENTS
            else "OTHER"
        )
        confusion[row["targetIntent"]][predicted] += 1

    by_intent: dict[str, Any] = {}
    for intent in INTENTS:
        subset = [row for row in records if row["targetIntent"] == intent]
        by_intent[intent] = {
            "count": len(subset),
            "exact": sum(bool(row["intentExact"]) for row in subset),
            "knownP222IntentOutput": sum(
                bool(row["knownP222IntentOutput"]) for row in subset
            ),
            "diagnosticVocabularyOutput": sum(
                bool(row["diagnosticVocabularyOutput"]) for row in subset
            ),
            "outOfDiagnosticVocabulary": sum(
                bool(row["outOfDiagnosticVocabulary"]) for row in subset
            ),
            "unknownOrMalformedIntent": sum(
                bool(row["unknownOrMalformedIntent"]) for row in subset
            ),
        }

    reverse_polarity = (
        confusion["INSERT"]["DELETE"] + confusion["DELETE"]["INSERT"]
    )
    presence_exact = by_intent["INSERT"]["exact"] + by_intent["DELETE"]["exact"]
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "intentExact": sum(bool(row["intentExact"]) for row in records),
        "knownP222IntentOutput": sum(
            bool(row["knownP222IntentOutput"]) for row in records
        ),
        "diagnosticVocabularyOutput": sum(
            bool(row["diagnosticVocabularyOutput"]) for row in records
        ),
        "outOfDiagnosticVocabulary": sum(
            bool(row["outOfDiagnosticVocabulary"]) for row in records
        ),
        "unknownOrMalformedIntent": sum(
            bool(row["unknownOrMalformedIntent"]) for row in records
        ),
        "eos": sum(bool(row["eos"]) for row in records),
        "byTargetIntent": by_intent,
        "confusionMatrix": confusion,
        "presencePolarityExact": presence_exact,
        "presencePolarityCount": (
            by_intent["INSERT"]["count"] + by_intent["DELETE"]["count"]
        ),
        "reversePolarityConfusions": reverse_polarity,
    }


def run(
    prepared: Path,
    source_run: Path,
    output: Path,
    *,
    device_name: str = "cuda",
) -> dict[str, Any]:
    verify_diagnostic()
    prepared = prepared.resolve(strict=True)
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("P2-22c output exists; choose a fresh directory")
    if device_name != "cuda":
        raise ValueError("P2-22c is pinned to CUDA scoring for checkpoint comparability")

    plan, checkpoint, source_score, checkpoint_sha = _verify_source(
        prepared, source_run
    )
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    settings = _json(prepared / "scoring" / "p2-14-task-set.json")
    max_new = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("step") != SOURCE_STEP:
        raise ValueError("P2-22c did not load cumulative step 500")

    rows = _rows(DIAGNOSTIC)
    records: list[dict[str, Any]] = []
    for row in rows:
        prompt_ids = tokenizer.encode(_prompt(row))
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-22c prompt exceeds model context: {row['id']}")
        generated, eos = _generate_token_ids(
            model,
            prompt_ids,
            actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=max_new,
            temperature=0.0,
            seed=SEED,
            device=device,
        )
        records.append(
            _score_row(row, tokenizer.decode(generated), eos, len(generated))
        )

    del model, payload
    output.mkdir(parents=True, exist_ok=False)
    tiers = {
        tier: _summary([row for row in records if row["tier"] == tier])
        for tier in TIERS
    }
    overall = _summary(records)
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "authorizationStatus": "owner-authorized-evaluation-only",
        "evaluationOnly": True,
        "sourceExperiment": SOURCE_EXPERIMENT,
        "sourceStep": SOURCE_STEP,
        "sourceCheckpointSha256": checkpoint_sha,
        "sourceP222InsertConfusion": SOURCE_INSERT_CONFUSION,
        "diagnosticJsonlSha256": DIAGNOSTIC_SHA256,
        "tokenizerSha256": TOKENIZER_SHA256,
        "parameterCount": PARAMETER_COUNT,
        "actualVocabularySize": VOCABULARY_SIZE,
        "device": device_name,
        "seed": SEED,
        "chanceBaselinePerTier": 1 / 3,
        "overall": overall,
        "tiers": tiers,
        "records": records,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "gradientTrainingPerformed": False,
        "modelWeightsModified": False,
        "preparedInputsChanged": verify_prepared(prepared) != plan,
        "sourceCandidateScoreCheckpointSha256": source_score["checkpointSha256"],
        "finalHoldoutOpened": False,
        "limitations": (
            "P2-22c is an evaluation-only state-transition diagnostic. It tests "
            "whether explicit before/after presence structure resolves the INSERT/"
            "DELETE polarity defect observed at P2-22b step 500. It does not train "
            "the model and is not the final project holdout."
        ),
    }
    if report["preparedInputsChanged"]:
        raise ValueError("Prepared P2-22 inputs changed during P2-22c scoring")

    (output / "result.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _compact(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "complete": summary["completeTaskPasses"],
        "count": summary["count"],
        "byTargetIntent": summary["byTargetIntent"],
        "presencePolarityExact": summary["presencePolarityExact"],
        "presencePolarityCount": summary["presencePolarityCount"],
        "reversePolarityConfusions": summary["reversePolarityConfusions"],
        "confusionMatrix": summary["confusionMatrix"],
        "eos": summary["eos"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    args = parser.parse_args()
    try:
        result = run(
            args.prepared,
            args.source_run,
            args.output_dir,
            device_name=args.device,
        )
        print(json.dumps({
            "report": str(args.output_dir / "result.json"),
            "sourceStep": result["sourceStep"],
            "overall": _compact(result["overall"]),
            "tiers": {
                tier: _compact(result["tiers"][tier])
                for tier in TIERS
            },
            "gradientTrainingPerformed": result["gradientTrainingPerformed"],
            "modelWeightsModified": result["modelWeightsModified"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-22c-diagnostic: {exc}", file=sys.stderr)
        raise SystemExit(2)
