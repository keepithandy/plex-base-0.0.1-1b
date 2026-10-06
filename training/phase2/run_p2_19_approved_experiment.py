"""Run the owner-approved first P2-19 reference-binding experiment and matched scoring."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from prepare_p2_19_approved_experiment import (
    ARTIFACT_ROOT,
    EXPERIMENT,
    p2_19_prompt,
    verify_prepared,
)

from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.pilot import inspect_pilot_bundle, run_pilot
from plex_training.telemetry import select_device
from plex_training.tokenizer import PlexTokenizer, sha256_file

from run_p2_17_approved_experiment import _development_node, _score_task_set


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _target_reference(row: dict[str, Any]) -> str:
    if row["level"] == "D":
        raise ValueError("Level D has no single target reference")
    return {
        "selector": row["selectorRef"],
        "old": row["oldRef"],
        "new": row["newRef"],
    }[row["targetField"]]


def _parse_reference_plan(
    completion: str,
) -> tuple[dict[str, str], bool]:
    lines = completion.strip().splitlines()
    fields = ("selector_ref", "old_ref", "new_ref")
    if len(lines) != 3:
        return {}, False
    parsed: dict[str, str] = {}
    for field, line in zip(fields, lines):
        prefix = field + "="
        if not line.startswith(prefix):
            return {}, False
        value = line[len(prefix):]
        if not value:
            return {}, False
        parsed[field] = value
    return parsed, True


def _score_row(
    row: dict[str, Any],
    completion: str,
    eos: bool,
    token_count: int,
) -> dict[str, Any]:
    normalized = completion.strip()
    expected = row["solution"].strip()
    references = set(row["referenceVocabulary"])
    common = {
        "id": row["id"],
        "candidateSplit": row["candidateSplit"],
        "evaluationTier": row["evaluationTier"],
        "level": row["level"],
        "taskKind": row["taskKind"],
        "request": row["request"],
        "expected": row["solution"],
        "completion": completion,
        "generatedTokenCount": token_count,
        "eos": eos,
        "exactString": normalized == expected,
    }

    if row["level"] in {"A", "B", "C"}:
        target = _target_reference(row)
        exact = normalized == target
        known = normalized in references
        return {
            **common,
            "passed": exact,
            "targetField": row["targetField"],
            "expectedReference": target,
            "referenceExact": exact,
            "knownReferenceOutput": known,
            "wrongKnownReference": known and not exact,
            "unknownOrMalformedReference": not known,
        }

    if row["level"] == "D":
        parsed, format_valid = _parse_reference_plan(completion)
        expected_fields = {
            "selector_ref": row["selectorRef"],
            "old_ref": row["oldRef"],
            "new_ref": row["newRef"],
        }
        field_exact = {
            field: format_valid and parsed.get(field) == value
            for field, value in expected_fields.items()
        }
        known_field = {
            field: format_valid and parsed.get(field) in references
            for field in expected_fields
        }
        full = format_valid and all(field_exact.values())
        return {
            **common,
            "passed": full,
            "formatValid": format_valid,
            "fullPlanExact": full,
            "fieldExact": field_exact,
            "knownReferenceField": known_field,
            "parsedPlan": parsed,
        }

    raise ValueError(f"Unsupported P2-19 level: {row['level']}")


def _base_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "exactStringMatches": sum(bool(row["exactString"]) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
    }


def _summary_reference(records: list[dict[str, Any]]) -> dict[str, Any]:
    base = _base_summary(records)
    summary: dict[str, Any] = {
        **base,
        "referenceExact": sum(bool(row["referenceExact"]) for row in records),
        "knownReferenceOutput": sum(
            bool(row["knownReferenceOutput"]) for row in records
        ),
        "wrongKnownReference": sum(
            bool(row["wrongKnownReference"]) for row in records
        ),
        "unknownOrMalformedReference": sum(
            bool(row["unknownOrMalformedReference"]) for row in records
        ),
        "byTargetField": {},
    }
    for field in ("selector", "old", "new"):
        subset = [row for row in records if row["targetField"] == field]
        summary["byTargetField"][field] = {
            "count": len(subset),
            "exact": sum(bool(row["referenceExact"]) for row in subset),
            "wrongKnownReference": sum(
                bool(row["wrongKnownReference"]) for row in subset
            ),
            "unknownOrMalformedReference": sum(
                bool(row["unknownOrMalformedReference"]) for row in subset
            ),
        }
    return summary


def _summary_d(records: list[dict[str, Any]]) -> dict[str, Any]:
    base = _base_summary(records)
    return {
        **base,
        "formatValid": sum(bool(row["formatValid"]) for row in records),
        "fullPlanExact": sum(bool(row["fullPlanExact"]) for row in records),
        "selectorReferenceExact": sum(
            bool(row["fieldExact"]["selector_ref"]) for row in records
        ),
        "oldReferenceExact": sum(
            bool(row["fieldExact"]["old_ref"]) for row in records
        ),
        "newReferenceExact": sum(
            bool(row["fieldExact"]["new_ref"]) for row in records
        ),
        "selectorKnownReference": sum(
            bool(row["knownReferenceField"]["selector_ref"]) for row in records
        ),
        "oldKnownReference": sum(
            bool(row["knownReferenceField"]["old_ref"]) for row in records
        ),
        "newKnownReference": sum(
            bool(row["knownReferenceField"]["new_ref"]) for row in records
        ),
    }


def _summarize(level: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    if level in {"A", "B", "C"}:
        return _summary_reference(records)
    if level == "D":
        return _summary_d(records)
    raise ValueError(f"Unsupported P2-19 summary level: {level}")


def _summarize_training(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "levels": {
            level: _summarize(
                level, [row for row in records if row["level"] == level]
            )
            for level in ("A", "B", "C", "D")
        },
    }


def _score_candidate(
    checkpoint: Path,
    prepared: Path,
    device_name: str,
    output_path: Path,
) -> dict[str, Any]:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    settings = json.loads(
        (prepared / "scoring/p2-14-task-set.json").read_text(encoding="utf-8")
    )
    rows = _load_rows(prepared / "approved/candidate.jsonl")
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != bundle["tokenizer"]:
        raise ValueError("P2-19 checkpoint tokenizer differs from prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-19 checkpoint has an invalid step")

    max_new = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    records: list[dict[str, Any]] = []
    for row in rows:
        prompt_ids = tokenizer.encode(p2_19_prompt(row))
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-19 prompt exceeds model context: {row['id']}")
        tokens, eos = _generate_token_ids(
            model,
            prompt_ids,
            actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=max_new,
            temperature=0.0,
            seed=1337,
            device=device,
        )
        completion = tokenizer.decode(tokens)
        records.append(_score_row(row, completion, eos, len(tokens)))

    train = [row for row in records if row["candidateSplit"] == "train"]
    tiers = {
        tier: [row for row in records if row["evaluationTier"] == tier]
        for tier in ("A", "B", "C", "D")
    }
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize_training(train),
        "tiers": {
            tier: _summarize(tier, tiers[tier])
            for tier in ("A", "B", "C", "D")
        },
        "records": records,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _delta(
    before: dict[str, Any],
    after: dict[str, Any],
    keys: tuple[str, ...],
) -> dict[str, int]:
    return {
        key: int(after[key]) - int(before[key])
        for key in keys
    }


def _validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-19 first run is capped at 1-100 updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-19 first run is capped at ten minutes")


def run(
    prepared: Path,
    output: Path,
    *,
    device_name: str = "cuda",
    steps: int = 100,
    minutes: float = 10.0,
) -> dict[str, Any]:
    _validate_bounds(steps, minutes)
    prepared = prepared.resolve()
    output = output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or output in prepared.parents or prepared in output.parents:
        raise ValueError("P2-19 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-19 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-19 run exceeds owner-approved bounds")
    if device_name != "cuda":
        raise ValueError("The approved first P2-19 run is CUDA-only")

    _development_node(json.loads(
        (prepared / "scoring/p2-01b-dev-v1.json").read_text(encoding="utf-8")
    ))

    output.mkdir(parents=True, exist_ok=False)
    initialization = prepared / "initialization/initialization.pt"

    step_zero_candidate = _score_candidate(
        initialization,
        prepared,
        device_name,
        output / "step-zero-candidate-score.json",
    )
    step_zero_p214 = _score_task_set(
        initialization,
        prepared,
        prepared / "scoring/p2-14-task-set.json",
        device_name,
        output / "step-zero-p2-14-score.json",
    )
    step_zero_p201b = _score_task_set(
        initialization,
        prepared,
        prepared / "scoring/p2-01b-dev-v1.json",
        device_name,
        output / "step-zero-p2-01b-score.json",
    )

    pilot_result = run_pilot(
        bundle_dir=prepared / "tokenizer",
        initialization=initialization,
        output_dir=output / "pilot",
        artifact_root=ARTIFACT_ROOT,
        minutes=minutes,
        steps=steps,
        device_name=device_name,
        micro_batch=plan["microBatch"],
        gradient_accumulation=plan["gradientAccumulation"],
        checkpoint_every_minutes=5.0,
        dataset_dir=prepared / "dataset",
        answer_weight=1,
        sampling_policy="complete-record-v1",
    )
    checkpoint = output / "pilot/pilot-checkpoint.pt"
    if not checkpoint.is_file():
        raise ValueError("P2-19 pilot did not produce a checkpoint")

    trained_candidate = _score_candidate(
        checkpoint,
        prepared,
        device_name,
        output / "trained-candidate-score.json",
    )
    trained_p214 = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring/p2-14-task-set.json",
        device_name,
        output / "trained-p2-14-score.json",
    )
    trained_p201b = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring/p2-01b-dev-v1.json",
        device_name,
        output / "trained-p2-01b-score.json",
    )

    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-19 inputs changed during the run")

    training = pilot_result["training"]
    training_complete = (
        training["stepsThisRun"] == steps and not training["interrupted"]
    )
    train_fit_complete = (
        trained_candidate["training"]["completeTaskPasses"] == 144
    )

    reference_delta = (
        "completeTaskPasses",
        "referenceExact",
        "knownReferenceOutput",
        "wrongKnownReference",
        "unknownOrMalformedReference",
        "eos",
    )
    tier_delta_keys = {
        "A": reference_delta,
        "B": reference_delta,
        "C": reference_delta,
        "D": (
            "completeTaskPasses",
            "formatValid",
            "fullPlanExact",
            "selectorReferenceExact",
            "oldReferenceExact",
            "newReferenceExact",
            "eos",
        ),
    }

    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training_complete,
        "trainingInterrupted": training["interrupted"],
        "freshScratchInitialization": True,
        "seed": plan["seed"],
        "device": device_name,
        "parameterCount": plan["parameterCount"],
        "samplingPolicy": plan["samplingPolicy"],
        "lossObjective": plan["lossObjective"],
        "approvedMaximumSteps": plan["maximumSteps"],
        "actualStepCap": steps,
        "approvedMaximumMinutes": plan["maximumMinutes"],
        "actualMinuteCap": minutes,
        "training": training,
        "candidate": {
            "stepZeroTraining": step_zero_candidate["training"],
            "trainedTraining": trained_candidate["training"],
            "trainingFitComplete": train_fit_complete,
            "tiers": {
                tier: {
                    "stepZero": step_zero_candidate["tiers"][tier],
                    "trained": trained_candidate["tiers"][tier],
                    "delta": _delta(
                        step_zero_candidate["tiers"][tier],
                        trained_candidate["tiers"][tier],
                        tier_delta_keys[tier],
                    ),
                }
                for tier in ("A", "B", "C", "D")
            },
            "evaluationCaution": (
                "training-fit-complete"
                if train_fit_complete
                else (
                    "training-fit-incomplete; interpret weak reference-binding "
                    "transfer cautiously"
                )
            ),
        },
        "p214CssEditDevelopment12": {
            "stepZeroPasses": step_zero_p214["completeTaskPasses"],
            "trainedPasses": trained_p214["completeTaskPasses"],
            "deltaPasses": (
                trained_p214["completeTaskPasses"]
                - step_zero_p214["completeTaskPasses"]
            ),
        },
        "p201bDevelopment30": {
            "stepZeroPasses": step_zero_p201b["completeTaskPasses"],
            "trainedPasses": trained_p201b["completeTaskPasses"],
            "deltaPasses": (
                trained_p201b["completeTaskPasses"]
                - step_zero_p201b["completeTaskPasses"]
            ),
            "stepZeroByLanguage": step_zero_p201b["byLanguage"],
            "trainedByLanguage": trained_p201b["byLanguage"],
        },
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "actualVocabularySize": plan["actualVocabularySize"],
        "tokenizerFitSplit": "train",
        "evaluationUsedForTokenizerFit": False,
        "evaluationUsedForGradientTraining": False,
        "p214UsedForGradientTraining": False,
        "p201bUsedForGradientTraining": False,
        "automaticExtension": False,
        "finalHoldoutOpened": False,
        "limitations": (
            "P2-19 is a narrow reference-mediated binding experiment. "
            "Level A tests raw-literal-to-reference lookup, Level B explicit "
            "reference selection, Level C semantic reference selection, and "
            "Level D three-reference plan assembly. It does not by itself "
            "establish coding ability."
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--minutes", type=float, default=10.0)
    args = parser.parse_args()
    try:
        result = run(
            args.prepared,
            args.output_dir,
            device_name=args.device,
            steps=args.steps,
            minutes=args.minutes,
        )
        print(json.dumps({
            "report": str(args.output_dir / "result.json"),
            "trainingReachedStepLimit": result["trainingReachedStepLimit"],
            "candidate": result["candidate"],
            "p214CssEditDevelopment12": result["p214CssEditDevelopment12"],
            "p201bDevelopment30": result["p201bDevelopment30"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-19-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
