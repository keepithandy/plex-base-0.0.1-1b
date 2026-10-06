"""Run the owner-approved first P2-16 CSS generalization experiment and matched scoring."""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from prepare_p2_16_approved_experiment import (
    ARTIFACT_ROOT,
    EXPERIMENT,
    p2_16_prompt,
    verify_prepared,
)

from plex_training.benchmark import _check_task, render_task_prompt
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.pilot import inspect_pilot_bundle, run_pilot
from plex_training.telemetry import select_device
from plex_training.tokenizer import PlexTokenizer, sha256_file


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _parse_flat_rule(source: str) -> tuple[str | None, dict[str, str], bool]:
    match = re.fullmatch(r"\s*([^{}]+)\{([^{}]*)\}\s*", source, flags=re.DOTALL)
    if not match:
        return None, {}, False
    selector = " ".join(match.group(1).split())
    declarations: dict[str, str] = {}
    duplicate = False
    for raw in match.group(2).split(";"):
        raw = raw.strip()
        if not raw or ":" not in raw:
            continue
        name, value = raw.split(":", 1)
        name = name.strip().lower()
        value = " ".join(value.strip().split())
        if name in declarations:
            duplicate = True
        declarations[name] = value
    return selector, declarations, duplicate


def _failure_flags(row: dict[str, Any], completion: str, eos: bool, passed: bool) -> dict[str, bool]:
    output_selector, output_map, duplicate = _parse_flat_rule(completion)
    input_selector, input_map, _ = _parse_flat_rule(row["inputCss"])
    expected_selector, expected_map, _ = _parse_flat_rule(row["solution"])
    edited = {item["property"] for item in row["operationPrimitives"]}
    requested_not_applied = any(
        output_map.get(prop) != expected_map.get(prop)
        if prop in expected_map
        else prop in output_map
        for prop in edited
    )
    wrong_value = any(
        primitive["operation"] in {"add", "replace"}
        and primitive["property"] in output_map
        and output_map[primitive["property"]] != primitive.get("targetValue")
        for primitive in row["operationPrimitives"]
    )
    preservation_failure = any(
        prop not in edited and output_map.get(prop) != value
        for prop, value in input_map.items()
    )
    unexpected = (
        output_selector != expected_selector
        or any(prop not in expected_map for prop in output_map)
    )
    incomplete = (
        output_selector is None
        or output_selector != expected_selector
        or any(output_map.get(prop) != value for prop, value in expected_map.items())
    )
    malformed = output_selector is None
    copied = " ".join(completion.split()) == " ".join(row["inputCss"].split())
    repeated = duplicate or completion.count("{") > 1 or completion.count("}") > 1
    return {
        "requestedEditNotApplied": requested_not_applied,
        "correctPropertyWrongValue": wrong_value,
        "preservationFailure": preservation_failure,
        "unexpectedSelectorOrDeclaration": unexpected,
        "incompleteRule": incomplete,
        "malformedCss": malformed,
        "repeatedFragmentOrDeclaration": repeated,
        "copiedInputWithoutApplyingEdit": copied and not passed,
        "prematureEos": bool(eos and incomplete),
        "noEos": not eos,
    }


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    failure_names = sorted({
        key
        for record in records
        for key in record.get("failureFlags", {})
    })
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "syntaxValid": sum(row.get("parseStatus") == "pass" for row in records),
        "exactStringMatches": sum(bool(row.get("exactString")) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
        "failureCounts": {
            name: sum(bool(row.get("failureFlags", {}).get(name)) for row in records)
            for name in failure_names
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
        raise ValueError("P2-16 checkpoint tokenizer differs from prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-16 checkpoint has an invalid step")

    records = []
    max_new = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    for row in rows:
        prompt_ids = tokenizer.encode(p2_16_prompt(row))
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-16 prompt exceeds model context: {row['id']}")
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
        passed = bool(checked["passed"])
        records.append({
            "id": row["id"],
            "candidateSplit": row["candidateSplit"],
            "evaluationTier": row["evaluationTier"],
            "editFamily": row["editFamily"],
            "operationType": row["operationType"],
            "request": row["request"],
            "expected": row["solution"],
            "completion": completion,
            "generatedTokenCount": len(tokens),
            "eos": eos,
            "parseStatus": checked["parseStatus"],
            "passed": passed,
            "checksPassed": checked["checksPassed"],
            "checksTotal": checked["checksTotal"],
            "exactString": completion.strip() == row["solution"].strip(),
            "failureFlags": _failure_flags(row, completion, eos, passed),
        })

    train = [row for row in records if row["candidateSplit"] == "train"]
    tiers = {
        tier: [
            row for row in records
            if row["candidateSplit"] == "evaluation" and row["evaluationTier"] == tier
        ]
        for tier in ("A", "B", "C", "D")
    }
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize(train),
        "tiers": {tier: _summarize(subset) for tier, subset in tiers.items()},
        "records": records,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _development_node(task_set: dict[str, Any]) -> str | None:
    if not any(task.get("language") == "javascript" for task in task_set.get("tasks", [])):
        return None
    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required to score JavaScript development tasks")
    return node


def _score_task_set(
    checkpoint: Path,
    prepared: Path,
    task_set_path: Path,
    device_name: str,
    output_path: Path,
) -> dict[str, Any]:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    task_set = json.loads(task_set_path.read_text(encoding="utf-8"))
    node_executable = _development_node(task_set)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != bundle["tokenizer"]:
        raise ValueError("Development checkpoint tokenizer differs from prepared bundle")

    records = []
    for task in task_set["tasks"]:
        prompt = render_task_prompt(task_set, task)
        prompt_ids = tokenizer.encode(prompt)
        if len(prompt_ids) >= model.config.context_length:
            records.append({
                "id": task["id"],
                "language": task["language"],
                "passed": False,
                "skipped": "prompt-exceeds-context",
                "eos": False,
                "generatedTokenCount": 0,
                "completion": "",
            })
            continue
        max_new = task_set["inferenceDefaults"]["maxNewTokens"][task["language"]]
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
        checked = _check_task(task, completion, node_executable, 5.0)
        records.append({
            "id": task["id"],
            "language": task["language"],
            "passed": bool(checked["passed"]),
            "parseStatus": checked["parseStatus"],
            "checksPassed": checked["checksPassed"],
            "checksTotal": checked["checksTotal"],
            "eos": eos,
            "generatedTokenCount": len(tokens),
            "completion": completion,
        })

    by_language = {}
    for language in sorted({row["language"] for row in records}):
        subset = [row for row in records if row["language"] == language]
        by_language[language] = {
            "count": len(subset),
            "passes": sum(bool(row["passed"]) for row in subset),
            "eos": sum(bool(row["eos"]) for row in subset),
        }
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "byLanguage": by_language,
        "nodeExecutable": node_executable,
        "records": records,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-16 first run is capped at 1-100 updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-16 first run is capped at ten minutes")


def _tier_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    return {
        "completeTaskPasses": after["completeTaskPasses"] - before["completeTaskPasses"],
        "syntaxValid": after["syntaxValid"] - before["syntaxValid"],
        "exactStringMatches": after["exactStringMatches"] - before["exactStringMatches"],
        "eos": after["eos"] - before["eos"],
    }


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
        raise ValueError("P2-16 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-16 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-16 run exceeds owner-approved bounds")
    if device_name != "cuda":
        raise ValueError("The approved first P2-16 run is CUDA-only")

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
        raise ValueError("P2-16 pilot did not produce a checkpoint")

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
        raise ValueError("Prepared P2-16 inputs changed during the run")

    training = pilot_result["training"]
    training_complete = training["stepsThisRun"] == steps and not training["interrupted"]
    training_fit_complete = trained_candidate["training"]["completeTaskPasses"] == 120
    tiers = {}
    for tier in ("A", "B", "C", "D"):
        tiers[tier] = {
            "stepZero": step_zero_candidate["tiers"][tier],
            "trained": trained_candidate["tiers"][tier],
            "delta": _tier_delta(
                step_zero_candidate["tiers"][tier],
                trained_candidate["tiers"][tier],
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
            "trainingDelta": _tier_delta(
                step_zero_candidate["training"],
                trained_candidate["training"],
            ),
            "trainingFitComplete": training_fit_complete,
            "tiers": tiers,
            "evaluationCaution": (
                "training-fit-complete"
                if training_fit_complete
                else "training-fit-incomplete; interpret zero generalization scores cautiously"
            ),
        },
        "p214CssEditDevelopment12": {
            "stepZeroPasses": step_zero_p214["completeTaskPasses"],
            "trainedPasses": trained_p214["completeTaskPasses"],
            "deltaPasses": (
                trained_p214["completeTaskPasses"] - step_zero_p214["completeTaskPasses"]
            ),
        },
        "p201bDevelopment30": {
            "stepZeroPasses": step_zero_p201b["completeTaskPasses"],
            "trainedPasses": trained_p201b["completeTaskPasses"],
            "deltaPasses": (
                trained_p201b["completeTaskPasses"] - step_zero_p201b["completeTaskPasses"]
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
            "P2-16 is a narrow single-rule CSS generalization experiment. "
            "Tier A-D, P2-14 and P2-01b are development measurements, not a final holdout. "
            "Positive results do not establish broad coding or repository-editing ability."
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
        print(f"plex-p2-16-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
