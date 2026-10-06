"""Run the owner-approved first P2-20 role-decomposition experiment and matched scoring."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from prepare_p2_20_approved_experiment import (
    ARTIFACT_ROOT,
    EXPERIMENT,
    p2_20_prompt,
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
    return {
        "SELECTOR": row["selectorRef"],
        "OLD": row["oldRef"],
        "NEW": row["newRef"],
    }[row["targetRole"]]


def _common(
    row: dict[str, Any],
    completion: str,
    eos: bool,
    token_count: int,
) -> dict[str, Any]:
    normalized = completion.strip()
    expected = row["solution"].strip()
    return {
        "id": row["id"],
        "candidateSplit": row["candidateSplit"],
        "evaluationTier": row["evaluationTier"],
        "level": row["level"],
        "taskKind": row["taskKind"],
        "targetRole": row["targetRole"],
        "request": row["request"],
        "expected": row["solution"],
        "completion": completion,
        "generatedTokenCount": token_count,
        "eos": eos,
        "exactString": normalized == expected,
    }


def _score_row(
    row: dict[str, Any],
    completion: str,
    eos: bool,
    token_count: int,
) -> dict[str, Any]:
    normalized = completion.strip()
    common = _common(row, completion, eos, token_count)

    if row["level"] == "A":
        roles = set(row["roleVocabulary"])
        exact = normalized == row["targetRole"]
        known = normalized in roles
        return {
            **common,
            "passed": exact,
            "roleExact": exact,
            "knownRoleOutput": known,
            "wrongKnownRole": known and not exact,
            "unknownOrMalformedRole": not known,
        }

    if row["level"] in {"B", "C"}:
        references = set(row["referenceVocabulary"])
        expected_reference = _target_reference(row)
        exact = normalized == expected_reference
        known = normalized in references
        return {
            **common,
            "passed": exact,
            "expectedReference": expected_reference,
            "referenceExact": exact,
            "knownReferenceOutput": known,
            "wrongKnownReference": known and not exact,
            "unknownOrMalformedReference": not known,
        }

    raise ValueError(f"Unsupported P2-20 level: {row['level']}")


def _base_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "exactStringMatches": sum(bool(row["exactString"]) for row in records),
        "eos": sum(bool(row["eos"]) for row in records),
        "noEos": sum(not bool(row["eos"]) for row in records),
        "generatedTokenCount": sum(int(row["generatedTokenCount"]) for row in records),
    }


def _summary_a(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        **_base_summary(records),
        "roleExact": sum(bool(row["roleExact"]) for row in records),
        "knownRoleOutput": sum(bool(row["knownRoleOutput"]) for row in records),
        "wrongKnownRole": sum(bool(row["wrongKnownRole"]) for row in records),
        "unknownOrMalformedRole": sum(
            bool(row["unknownOrMalformedRole"]) for row in records
        ),
        "byTargetRole": {},
    }
    for role in ("SELECTOR", "OLD", "NEW"):
        subset = [row for row in records if row["targetRole"] == role]
        summary["byTargetRole"][role] = {
            "count": len(subset),
            "exact": sum(bool(row["roleExact"]) for row in subset),
            "wrongKnownRole": sum(bool(row["wrongKnownRole"]) for row in subset),
            "unknownOrMalformedRole": sum(
                bool(row["unknownOrMalformedRole"]) for row in subset
            ),
        }
    return summary


def _summary_reference(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        **_base_summary(records),
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
        "byTargetRole": {},
    }
    for role in ("SELECTOR", "OLD", "NEW"):
        subset = [row for row in records if row["targetRole"] == role]
        summary["byTargetRole"][role] = {
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


def _summarize(level: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    if level == "A":
        return _summary_a(records)
    if level in {"B", "C"}:
        return _summary_reference(records)
    raise ValueError(f"Unsupported P2-20 summary level: {level}")


def _summarize_training(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(records),
        "completeTaskPasses": sum(bool(row["passed"]) for row in records),
        "levels": {
            level: _summarize(
                level, [row for row in records if row["level"] == level]
            )
            for level in ("A", "B", "C")
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
        raise ValueError("P2-20 checkpoint tokenizer differs from prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-20 checkpoint has an invalid step")

    max_new = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    records: list[dict[str, Any]] = []
    for row in rows:
        prompt_ids = tokenizer.encode(p2_20_prompt(row))
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-20 prompt exceeds model context: {row['id']}")
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
        for tier in ("A", "B", "C")
    }
    result = {
        "checkpointStep": payload["step"],
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize_training(train),
        "tiers": {
            tier: _summarize(tier, tiers[tier])
            for tier in ("A", "B", "C")
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
    return {key: int(after[key]) - int(before[key]) for key in keys}


def _validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-20 first run is capped at 1-100 updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-20 first run is capped at ten minutes")


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
        raise ValueError("P2-20 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-20 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-20 run exceeds owner-approved bounds")
    if device_name != "cuda":
        raise ValueError("The approved first P2-20 run is CUDA-only")

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
        raise ValueError("P2-20 pilot did not produce a checkpoint")

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
        raise ValueError("Prepared P2-20 inputs changed during the run")

    training = pilot_result["training"]
    training_complete = (
        training["stepsThisRun"] == steps and not training["interrupted"]
    )
    train_fit_complete = (
        trained_candidate["training"]["completeTaskPasses"] == 144
    )

    tier_delta_keys = {
        "A": (
            "completeTaskPasses",
            "roleExact",
            "knownRoleOutput",
            "wrongKnownRole",
            "unknownOrMalformedRole",
            "eos",
        ),
        "B": (
            "completeTaskPasses",
            "referenceExact",
            "knownReferenceOutput",
            "wrongKnownReference",
            "unknownOrMalformedReference",
            "eos",
        ),
        "C": (
            "completeTaskPasses",
            "referenceExact",
            "knownReferenceOutput",
            "wrongKnownReference",
            "unknownOrMalformedReference",
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
                for tier in ("A", "B", "C")
            },
            "evaluationCaution": (
                "training-fit-complete"
                if train_fit_complete
                else (
                    "training-fit-incomplete; interpret weak P2-20 primitive "
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
            "P2-20 is a narrow decomposition experiment. Level A tests semantic "
            "role classification, Level B explicit symbolic lookup, and Level C "
            "their composition. It does not by itself establish coding ability."
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
        print(f"plex-p2-20-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
