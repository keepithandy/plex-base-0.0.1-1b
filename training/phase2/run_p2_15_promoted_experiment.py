"""Run the owner-approved P2-15 promoted CSS edit diagnostic and score matched checkpoints."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

from prepare_p2_15_css_edit_candidate import rows as candidate_rows
from prepare_p2_15_promoted_experiment import ARTIFACT_ROOT, EXPERIMENT, p2_15_prompt, verify_prepared

from plex_training.benchmark import _check_task, render_task_prompt
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.pilot import inspect_pilot_bundle, run_pilot
from plex_training.telemetry import select_device
from plex_training.tokenizer import PlexTokenizer, sha256_file


def _summarize(records: list[dict]) -> dict:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "exactStringMatches": sum(bool(row.get("exactString")) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
    }


def _score_candidate(
    checkpoint: Path,
    prepared: Path,
    device_name: str,
    output_path: Path,
) -> dict:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    settings = json.loads(
        (prepared / "scoring/p2-14-task-set.json").read_text(encoding="utf-8")
    )
    device = select_device(device_name)
    node_executable = _development_node(task_set)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != bundle["tokenizer"]:
        raise ValueError("P2-15 checkpoint tokenizer differs from prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-15 checkpoint has an invalid step")

    records = []
    for row in candidate_rows():
        prompt = p2_15_prompt(row)
        prompt_ids = tokenizer.encode(prompt)
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-15 prompt exceeds model context: {row['id']}")
        tokens, eos = _generate_token_ids(
            model,
            prompt_ids,
            actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=settings["inferenceDefaults"]["maxNewTokens"]["css"],
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
        records.append({
            "id": row["id"],
            "split": row["candidateSplit"],
            "splitGroupId": row["splitGroupId"],
            "request": row["request"],
            "expected": row["solution"],
            "completion": completion,
            "generatedTokenCount": len(tokens),
            "eos": eos,
            "passed": bool(checked["passed"]),
            "checksPassed": checked["checksPassed"],
            "checksTotal": checked["checksTotal"],
            "exactString": completion.strip() == row["solution"],
        })

    train = [row for row in records if row["split"] == "train"]
    validation = [row for row in records if row["split"] == "validation"]
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize(train),
        "validation": _summarize(validation),
        "nodeExecutable": node_executable,
        "records": records,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _development_node(task_set: dict) -> str | None:
    if not any(task.get("language") == "javascript" for task in task_set.get("tasks", [])):
        return None
    node = shutil.which("node")
    if node is None:
        raise ValueError(
            "Node.js is required to score JavaScript tasks in the P2-01b development set"
        )
    return node


def _score_task_set(
    checkpoint: Path,
    prepared: Path,
    task_set_path: Path,
    device_name: str,
    output_path: Path,
) -> dict:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    task_set = json.loads(task_set_path.read_text(encoding="utf-8"))
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
        raise ValueError("P2-15 is capped at 1-100 updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-15 is capped at ten minutes")


def run(
    prepared: Path,
    output: Path,
    *,
    device_name: str = "cuda",
    steps: int = 100,
    minutes: float = 10.0,
) -> dict:
    _validate_bounds(steps, minutes)
    prepared = prepared.resolve()
    output = output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or output in prepared.parents or prepared in output.parents:
        raise ValueError("P2-15 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-15 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-15 run exceeds owner-approved bounds")
    if device_name != "cuda":
        raise ValueError("The approved P2-15 diagnostic is a CUDA run")

    output.mkdir(parents=True, exist_ok=False)
    initialization = prepared / "initialization/initialization.pt"

    step_zero_candidate = _score_candidate(
        initialization,
        prepared,
        device_name,
        output / "step-zero-candidate-score.json",
    )
    step_zero_p201b = _score_task_set(
        initialization,
        prepared,
        prepared / "scoring/p2-01b-dev-v1.json",
        device_name,
        output / "step-zero-p2-01b-score.json",
    )
    step_zero_p214 = _score_task_set(
        initialization,
        prepared,
        prepared / "scoring/p2-14-task-set.json",
        device_name,
        output / "step-zero-p2-14-score.json",
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
        raise ValueError("P2-15 pilot did not produce a checkpoint")

    trained_candidate = _score_candidate(
        checkpoint,
        prepared,
        device_name,
        output / "trained-candidate-score.json",
    )
    trained_p201b = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring/p2-01b-dev-v1.json",
        device_name,
        output / "trained-p2-01b-score.json",
    )
    trained_p214 = _score_task_set(
        checkpoint,
        prepared,
        prepared / "scoring/p2-14-task-set.json",
        device_name,
        output / "trained-p2-14-score.json",
    )

    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-15 inputs changed during the run")

    training = pilot_result["training"]
    training_complete = (
        training["stepsThisRun"] == steps
        and not training["interrupted"]
    )
    train_converged = trained_candidate["training"]["completeTaskPasses"] == 24
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training_complete,
        "trainingInterrupted": training["interrupted"],
        "freshScratchInitialization": True,
        "seed": plan["seed"],
        "device": device_name,
        "samplingPolicy": plan["samplingPolicy"],
        "lossObjective": plan["lossObjective"],
        "approvedMaximumSteps": plan["maximumSteps"],
        "actualStepCap": steps,
        "approvedMaximumMinutes": plan["maximumMinutes"],
        "actualMinuteCap": minutes,
        "training": training,
        "candidate": {
            "stepZero": {
                "training": step_zero_candidate["training"],
                "validation": step_zero_candidate["validation"],
            },
            "trained": {
                "training": trained_candidate["training"],
                "validation": trained_candidate["validation"],
            },
            "delta": {
                "trainingCompleteTaskPasses": (
                    trained_candidate["training"]["completeTaskPasses"]
                    - step_zero_candidate["training"]["completeTaskPasses"]
                ),
                "validationCompleteTaskPasses": (
                    trained_candidate["validation"]["completeTaskPasses"]
                    - step_zero_candidate["validation"]["completeTaskPasses"]
                ),
            },
            "trainingConverged": train_converged,
            "validationInterpretation": (
                "interpretable-after-24-of-24-training-convergence"
                if train_converged
                else "inconclusive-supplied-training-set-did-not-reach-24-of-24"
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
        "p214CssEditDevelopment12": {
            "stepZeroPasses": step_zero_p214["completeTaskPasses"],
            "trainedPasses": trained_p214["completeTaskPasses"],
            "deltaPasses": (
                trained_p214["completeTaskPasses"] - step_zero_p214["completeTaskPasses"]
            ),
        },
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "actualVocabularySize": plan["actualVocabularySize"],
        "tokenizerFitSplit": "train",
        "validationUsedForGradientTraining": False,
        "automaticExtension": False,
        "finalHoldoutOpened": False,
        "limitations": (
            "P2-15 is a narrow CSS request-to-code diagnostic over eight training edit families "
            "and four withheld validation edit families. P2-01b and P2-14 are development sets, "
            "not final holdouts. Positive results do not establish broad coding ability."
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
            "p201bDevelopment30": result["p201bDevelopment30"],
            "p214CssEditDevelopment12": result["p214CssEditDevelopment12"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-15-promoted-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
