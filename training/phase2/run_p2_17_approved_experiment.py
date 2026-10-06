"""Run the owner-approved first P2-17 semantic binding experiment and matched scoring."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from prepare_p2_17_approved_experiment import (
    ARTIFACT_ROOT,
    EXPERIMENT,
    p2_17_prompt,
    verify_prepared,
)

from plex_training.benchmark import _check_task
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.pilot import inspect_pilot_bundle, run_pilot
from plex_training.telemetry import select_device
from plex_training.tokenizer import PlexTokenizer, sha256_file

from run_p2_16_approved_experiment import _development_node, _score_task_set

PLAN_FIELDS = ("selector", "operation", "property", "old", "new")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _expected_plan_fields(row: dict[str, Any]) -> dict[str, str]:
    return {
        "selector": row["selector"],
        "operation": row["operation"],
        "property": row["property"],
        "old": row["sourceValue"] if row["sourceValue"] is not None else "<none>",
        "new": row["targetValue"] if row["targetValue"] is not None else "<none>",
    }


def _parse_plan(completion: str) -> tuple[dict[str, str], bool]:
    lines = completion.strip().splitlines()
    if len(lines) != 5:
        return {}, False
    values: dict[str, str] = {}
    for field, line in zip(PLAN_FIELDS, lines):
        prefix = field + "="
        if not line.startswith(prefix):
            return {}, False
        value = line[len(prefix):]
        if not value or field in values:
            return {}, False
        values[field] = value
    return values, True


def _parse_css(source: str) -> tuple[str | None, dict[str, str]]:
    match = re.fullmatch(r"\s*([^{}]+)\{([^{}]*)\}\s*", source, flags=re.DOTALL)
    if not match:
        return None, {}
    selector = " ".join(match.group(1).split())
    declarations: dict[str, str] = {}
    for raw in match.group(2).split(";"):
        raw = raw.strip()
        if not raw or ":" not in raw:
            continue
        name, value = raw.split(":", 1)
        name = name.strip().lower()
        value = " ".join(value.strip().split())
        if not name or not value or name in declarations:
            return None, {}
        declarations[name] = value
    return selector, declarations


def _css_binding_flags(row: dict[str, Any], completion: str) -> dict[str, bool]:
    output_selector, output = _parse_css(completion)
    _, source = _parse_css(row["inputCss"])
    prop = row["property"]
    operation = row["operation"]
    target = row["targetValue"]
    selector_exact = output_selector == row["selector"]
    if operation in {"replace", "add"}:
        edit_applied = output.get(prop) == target
    else:
        edit_applied = prop not in output
    preserved = all(
        output.get(name) == value
        for name, value in source.items()
        if name != prop
    )
    return {
        "selectorExact": selector_exact,
        "requestedEditApplied": edit_applied,
        "unrelatedDeclarationsPreserved": preserved,
    }


def _summarize_plan(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "fullPlanExact": sum(bool(row["fullPlanExact"]) for row in records),
        "formatValid": sum(bool(row["planFormatValid"]) for row in records),
        "selectorExact": sum(bool(row["fieldExact"]["selector"]) for row in records),
        "operationExact": sum(bool(row["fieldExact"]["operation"]) for row in records),
        "propertyExact": sum(bool(row["fieldExact"]["property"]) for row in records),
        "oldValueExact": sum(bool(row["fieldExact"]["old"]) for row in records),
        "newValueExact": sum(bool(row["fieldExact"]["new"]) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
    }


def _summarize_css(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "syntaxValid": sum(row.get("parseStatus") == "pass" for row in records),
        "exactStringMatches": sum(bool(row["exactString"]) for row in records),
        "selectorExact": sum(bool(row["bindingFlags"]["selectorExact"]) for row in records),
        "requestedEditApplied": sum(bool(row["bindingFlags"]["requestedEditApplied"]) for row in records),
        "unrelatedDeclarationsPreserved": sum(
            bool(row["bindingFlags"]["unrelatedDeclarationsPreserved"]) for row in records
        ),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
    }


def _summarize_mixed(records: list[dict[str, Any]]) -> dict[str, Any]:
    extract = [row for row in records if row["taskKind"] == "extract-plan"]
    apply = [row for row in records if row["taskKind"] == "apply-plan"]
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "extractPlan": _summarize_plan(extract),
        "applyPlan": _summarize_css(apply),
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
        raise ValueError("P2-17 checkpoint tokenizer differs from prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-17 checkpoint has an invalid step")

    max_new = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    records: list[dict[str, Any]] = []
    for row in rows:
        prompt_ids = tokenizer.encode(p2_17_prompt(row))
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-17 prompt exceeds model context: {row['id']}")
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
        common = {
            "id": row["id"],
            "scenarioId": row["scenarioId"],
            "candidateSplit": row["candidateSplit"],
            "evaluationTier": row["evaluationTier"],
            "taskKind": row["taskKind"],
            "request": row["request"],
            "expected": row["solution"],
            "completion": completion,
            "generatedTokenCount": len(tokens),
            "eos": eos,
        }
        if row["taskKind"] == "extract-plan":
            parsed, format_valid = _parse_plan(completion)
            expected = _expected_plan_fields(row)
            field_exact = {
                field: format_valid and parsed.get(field) == expected[field]
                for field in PLAN_FIELDS
            }
            full = format_valid and all(field_exact.values())
            records.append({
                **common,
                "passed": full,
                "planFormatValid": format_valid,
                "fullPlanExact": full,
                "exactString": completion.strip() == row["solution"].strip(),
                "fieldExact": field_exact,
                "parsedPlan": parsed,
            })
        else:
            checked = _check_task(
                {
                    "id": row["id"],
                    "language": "css",
                    "difficulty": "basic",
                    "checks": row["checks"],
                },
                completion,
                None,
                5.0,
            )
            records.append({
                **common,
                "passed": bool(checked["passed"]),
                "parseStatus": checked["parseStatus"],
                "checksPassed": checked["checksPassed"],
                "checksTotal": checked["checksTotal"],
                "exactString": completion.strip() == row["solution"].strip(),
                "bindingFlags": _css_binding_flags(row, completion),
            })

    train = [row for row in records if row["candidateSplit"] == "train"]
    tiers = {
        tier: [row for row in records if row["evaluationTier"] == tier]
        for tier in ("A", "B", "C")
    }
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize_mixed(train),
        "tiers": {
            "A": _summarize_plan(tiers["A"]),
            "B": _summarize_css(tiers["B"]),
            "C": _summarize_css(tiers["C"]),
        },
        "records": records,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _delta(before: dict[str, Any], after: dict[str, Any], keys: tuple[str, ...]) -> dict[str, int]:
    return {key: int(after[key]) - int(before[key]) for key in keys}


def _validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-17 first run is capped at 1-100 updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-17 first run is capped at ten minutes")


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
        raise ValueError("P2-17 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-17 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-17 run exceeds owner-approved bounds")
    if device_name != "cuda":
        raise ValueError("The approved first P2-17 run is CUDA-only")

    _development_node(json.loads(
        (prepared / "scoring/p2-01b-dev-v1.json").read_text(encoding="utf-8")
    ))

    output.mkdir(parents=True, exist_ok=False)
    initialization = prepared / "initialization/initialization.pt"

    step_zero_candidate = _score_candidate(
        initialization, prepared, device_name, output / "step-zero-candidate-score.json"
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
        raise ValueError("P2-17 pilot did not produce a checkpoint")

    trained_candidate = _score_candidate(
        checkpoint, prepared, device_name, output / "trained-candidate-score.json"
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
        raise ValueError("Prepared P2-17 inputs changed during the run")

    training = pilot_result["training"]
    training_complete = training["stepsThisRun"] == steps and not training["interrupted"]
    train_fit_complete = trained_candidate["training"]["completeTaskPasses"] == 120

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
                "A": {
                    "stepZero": step_zero_candidate["tiers"]["A"],
                    "trained": trained_candidate["tiers"]["A"],
                    "delta": _delta(
                        step_zero_candidate["tiers"]["A"],
                        trained_candidate["tiers"]["A"],
                        (
                            "completeTaskPasses", "fullPlanExact", "formatValid",
                            "selectorExact", "operationExact", "propertyExact",
                            "oldValueExact", "newValueExact", "eos",
                        ),
                    ),
                },
                "B": {
                    "stepZero": step_zero_candidate["tiers"]["B"],
                    "trained": trained_candidate["tiers"]["B"],
                    "delta": _delta(
                        step_zero_candidate["tiers"]["B"],
                        trained_candidate["tiers"]["B"],
                        (
                            "completeTaskPasses", "syntaxValid", "exactStringMatches",
                            "selectorExact", "requestedEditApplied",
                            "unrelatedDeclarationsPreserved", "eos",
                        ),
                    ),
                },
                "C": {
                    "stepZero": step_zero_candidate["tiers"]["C"],
                    "trained": trained_candidate["tiers"]["C"],
                    "delta": _delta(
                        step_zero_candidate["tiers"]["C"],
                        trained_candidate["tiers"]["C"],
                        (
                            "completeTaskPasses", "syntaxValid", "exactStringMatches",
                            "selectorExact", "requestedEditApplied",
                            "unrelatedDeclarationsPreserved", "eos",
                        ),
                    ),
                },
            },
            "evaluationCaution": (
                "training-fit-complete"
                if train_fit_complete
                else "training-fit-incomplete; interpret zero full-task transfer cautiously"
            ),
        },
        "p214CssEditDevelopment12": {
            "stepZeroPasses": step_zero_p214["completeTaskPasses"],
            "trainedPasses": trained_p214["completeTaskPasses"],
            "deltaPasses": trained_p214["completeTaskPasses"] - step_zero_p214["completeTaskPasses"],
        },
        "p201bDevelopment30": {
            "stepZeroPasses": step_zero_p201b["completeTaskPasses"],
            "trainedPasses": trained_p201b["completeTaskPasses"],
            "deltaPasses": trained_p201b["completeTaskPasses"] - step_zero_p201b["completeTaskPasses"],
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
            "P2-17 is a narrow CSS semantic-binding experiment. Tier A measures literal "
            "edit-plan extraction, Tier B measures application of an explicit plan, and Tier C "
            "measures composition without direct chain training. P2-14 and P2-01b are development "
            "sets, not final holdouts."
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
        print(f"plex-p2-17-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
