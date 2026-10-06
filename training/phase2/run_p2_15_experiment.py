"""Run the exact approved P2-15 CSS request-to-code diagnostic."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import torch

from prepare_code_pair_candidate import prompt_text
from prepare_p2_15_experiment import ARTIFACT_ROOT, EXPERIMENT, verify_prepared

from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.benchmark import _check_task
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _generate_token_ids
from plex_training.config import DEFAULT_CONFIG
from plex_training.data import TokenCorpus
from plex_training.pilot import inspect_pilot_bundle
from plex_training.runner import run_training
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer, sha256_file


def _candidate_rows(prepared: Path) -> tuple[list[dict], list[dict]]:
    rows = [
        json.loads(line)
        for line in (prepared / "approved/candidate.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    train = [row for row in rows if row["candidateSplit"] == "train"]
    validation = [row for row in rows if row["candidateSplit"] == "validation"]
    if len(train) != 24 or len(validation) != 12:
        raise ValueError("Prepared P2-15 candidate split changed")
    return train, validation


def _summarize(records: list[dict], group: str) -> dict:
    selected = [record for record in records if record["group"] == group]
    return {
        "count": len(selected),
        "completeRulePasses": sum(record["passed"] for record in selected),
        "exactStringMatches": sum(record["exactString"] for record in selected),
        "eos": sum(record["eos"] for record in selected),
        "noEos": sum(not record["eos"] for record in selected),
        "generatedTokenCount": sum(record["generatedTokenCount"] for record in selected),
    }


def _score(
    checkpoint: Path,
    prepared: Path,
    train_rows: list[dict],
    validation_rows: list[dict],
    device_name: str,
    output_path: Path,
) -> dict:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    settings = json.loads(
        (prepared / "scoring/p2-14-task-set.json").read_text(encoding="utf-8")
    )
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != bundle["tokenizer"]:
        raise ValueError("P2-15 checkpoint tokenizer identity does not match prepared bundle")
    if type(payload.get("step")) is not int or payload["step"] < 0:
        raise ValueError("P2-15 checkpoint has an invalid training step")

    records = []
    for group, rows in (("training", train_rows), ("validation", validation_rows)):
        for row in rows:
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
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
            records.append(
                {
                    "id": row["id"],
                    "group": group,
                    "splitGroupId": row["splitGroupId"],
                    "request": row["request"],
                    "expected": row["solution"],
                    "completion": completion,
                    "generatedTokenIds": tokens,
                    "generatedTokenPieces": [tokenizer.decode([token_id]) for token_id in tokens],
                    "generatedTokenCount": len(tokens),
                    "eos": eos,
                    "passed": bool(checked["passed"]),
                    "checksPassed": checked["checksPassed"],
                    "checksTotal": checked["checksTotal"],
                    "exactString": completion.strip() == row["solution"],
                }
            )

    result = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "checkpoint": str(checkpoint),
        "checkpointSha256": sha256_file(checkpoint),
        "checkpointStep": payload["step"],
        "training": _summarize(records, "training"),
        "validation": _summarize(records, "validation"),
        "records": records,
        "scoringRule": "css_stylesheet_exact from the approved P2-15 candidate",
        "temperature": 0.0,
        "seed": 1337,
        "finalHoldoutOpened": False,
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def _replay_sampling_audit(prepared: Path, plan: dict, steps: int) -> dict:
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    source = AnswerFocusedCompleteRecordTokenCorpus(
        bundle["trainPath"],
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "tokenizer/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    )
    rng = random.Random(plan["seed"])
    with source:
        for _ in range(steps * plan["microBatch"] * plan["gradientAccumulation"]):
            source.sample_masked_batch(rng, plan["microBatch"], DEFAULT_CONFIG.context_length)
        return source.sampling_audit()


def validate_bounds(steps: int, minutes: float) -> None:
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
    validate_bounds(steps, minutes)
    prepared = prepared.resolve()
    output = output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-15 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-15 run output exists; choose a fresh directory")

    plan = verify_prepared(prepared)
    if (
        steps > plan["maximumSteps"]
        or minutes > plan["maximumMinutes"]
        or steps > plan["maximumTotalSteps"]
        or minutes > plan["maximumTotalMinutes"]
    ):
        raise ValueError("Requested P2-15 run exceeds owner-approved bounds")
    if device_name != plan["device"]:
        raise ValueError("P2-15 owner approval specifies CUDA")

    train_rows, validation_rows = _candidate_rows(prepared)
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    tokenizer = PlexTokenizer.load(prepared / "tokenizer")
    device = select_device(device_name)

    output.mkdir(parents=True, exist_ok=False)
    step_zero = _score(
        prepared / "initialization/initialization.pt",
        prepared,
        train_rows,
        validation_rows,
        device_name,
        output / "step-zero-score.json",
    )

    source = AnswerFocusedCompleteRecordTokenCorpus(
        bundle["trainPath"],
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "tokenizer/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    )
    print(
        json.dumps(
            {
                "event": "p2_15_training_starting",
                "trainingRecords": len(train_rows),
                "validationRecords": len(validation_rows),
                "maximumSteps": steps,
                "maximumMinutes": minutes,
                "device": device_name,
                "tokenizerSha256": plan["tokenizerSha256"],
                "actualVocabularySize": plan["actualVocabularySize"],
            }
        ),
        flush=True,
    )

    with source as train, TokenCorpus(bundle["validationPath"]) as validation:
        training = run_training(
            train_source=train,
            validation=validation,
            device_name=device_name,
            minutes=minutes,
            step_limit=steps,
            output_checkpoint=output / "pilot/pilot-checkpoint.pt",
            metrics_path=output / "pilot/metrics.jsonl",
            artifact_root=ARTIFACT_ROOT,
            seed=plan["seed"],
            micro_batch=plan["microBatch"],
            accumulation_steps=plan["gradientAccumulation"],
            checkpoint_interval_minutes=5.0,
            resume_from=prepared / "initialization/initialization.pt",
            config=DEFAULT_CONFIG,
            codec=CODEC,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
            answer_weight=1,
        )
        audit = source.sampling_audit()

    if training["tokensProcessedThisRun"] != audit["supervisedTargetPositions"]:
        raise ValueError("P2-15 supervised-target accounting differs from sampler audit")
    if training["paddingTargetPositionsThisRun"] != (
        audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
    ):
        raise ValueError("P2-15 zero-weight target accounting differs from sampler audit")

    checkpoint = output / "pilot/pilot-checkpoint.pt"
    if not checkpoint.is_file():
        raise ValueError("P2-15 training did not produce a scoreable checkpoint")

    trained = _score(
        checkpoint,
        prepared,
        train_rows,
        validation_rows,
        device_name,
        output / "trained-score.json",
    )
    replay = _replay_sampling_audit(prepared, plan, training["stepsThisRun"])
    if (
        replay["supervisedTargetPositions"] != training["tokensProcessedThisRun"]
        or replay["paddingTargetPositions"] + replay["excludedPromptTargetPositions"]
        != training["paddingTargetPositionsThisRun"]
    ):
        raise ValueError("P2-15 replayed sampler accounting differs from training telemetry")
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-15 inputs changed during training")

    training_complete = training["stepsThisRun"] == steps and not training["interrupted"]
    supplied_converged = trained["training"]["completeRulePasses"] == 24
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training_complete,
        "trainingInterrupted": training["interrupted"],
        "freshScratchInitialization": True,
        "seed": plan["seed"],
        "device": device_name,
        "approvedMaximumSteps": plan["maximumSteps"],
        "actualStepCap": steps,
        "approvedMaximumMinutes": plan["maximumMinutes"],
        "actualMinuteCap": minutes,
        "training": training,
        "samplingAudit": replay,
        "stepZero": {
            "training": step_zero["training"],
            "validation": step_zero["validation"],
            "checkpointSha256": step_zero["checkpointSha256"],
        },
        "trained": {
            "training": trained["training"],
            "validation": trained["validation"],
            "checkpointSha256": trained["checkpointSha256"],
        },
        "delta": {
            "trainingCompleteRulePasses": (
                trained["training"]["completeRulePasses"]
                - step_zero["training"]["completeRulePasses"]
            ),
            "validationCompleteRulePasses": (
                trained["validation"]["completeRulePasses"]
                - step_zero["validation"]["completeRulePasses"]
            ),
        },
        "trainingConverged": supplied_converged,
        "validationInterpretation": (
            "interpretable-after-24-of-24-training-convergence"
            if supplied_converged
            else "inconclusive-supplied-training-set-did-not-reach-24-of-24"
        ),
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "trainingRowsSha256": plan["trainingRowsSha256"],
        "validationRowsSha256": plan["validationRowsSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "actualVocabularySize": plan["actualVocabularySize"],
        "tokenizerFitSplit": "train",
        "validationUsedForTraining": False,
        "validationUsedForRuntimeValidationLoss": True,
        "trainingObjective": plan["trainingObjective"],
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": (
            "Narrow 36-example single-rule CSS edit diagnostic with eight training families "
            "and four family-disjoint validation families. This is not evidence of broad CSS "
            "editing, repository editing, or general coding ability."
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
        print(
            json.dumps(
                {
                    "report": str(args.output_dir / "result.json"),
                    "trainingReachedStepLimit": result["trainingReachedStepLimit"],
                    "trainingConverged": result["trainingConverged"],
                    "stepZero": result["stepZero"],
                    "trained": result["trained"],
                    "validationInterpretation": result["validationInterpretation"],
                    "finalHoldoutOpened": result["finalHoldoutOpened"],
                },
                indent=2,
            )
        )
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-15-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
