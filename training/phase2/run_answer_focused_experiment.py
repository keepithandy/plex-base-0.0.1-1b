"""Run P2-03 ordinary-vs-answer-focused complete-record training on the approved 24 examples."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import torch

from prepare_binding_candidate import sha256_file
from prepare_binding_experiment import (
    ARTIFACT_ROOT,
    CANDIDATE_SHA,
    EVALUATION_SHA,
    ROOT,
    load_inputs,
    verify_prepared,
    write_json,
)
from run_binding_experiment import (
    SOURCE_INITIALIZATION,
    SOURCE_INITIALIZATION_SHA,
    require_identical_initial_weights,
    replay_exposure,
    score_cases,
)
from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.benchmark import evaluate_files
from plex_training.config import DEFAULT_CONFIG
from plex_training.data import TokenCorpus
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.record_sampling import CompleteRecordTokenCorpus
from plex_training.runner import run_training
from plex_training.task_run import generate_development_responses
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer


EXPERIMENT = "p2-03-answer-focused-complete-record-v1"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("Each objective arm requires 1–100 optimizer updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("Each objective arm is capped at ten minutes")


def _run_arm(
    *,
    bundle_dir: Path,
    dataset_dir: Path,
    initialization: Path,
    output_dir: Path,
    device_name: str,
    steps: int,
    minutes: float,
    answer_focused: bool,
) -> dict:
    bundle = inspect_pilot_bundle(bundle_dir)
    tokenizer = PlexTokenizer.load(bundle_dir)
    source_type = AnswerFocusedCompleteRecordTokenCorpus if answer_focused else CompleteRecordTokenCorpus
    source = source_type(
        bundle["trainPath"],
        dataset_jsonl=dataset_dir / "train.jsonl",
        index_path=bundle_dir / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    )
    with source as train, TokenCorpus(bundle["validationPath"]) as validation:
        result = run_training(
            train_source=train,
            validation=validation,
            device_name=device_name,
            minutes=minutes,
            step_limit=steps,
            output_checkpoint=output_dir / "pilot/pilot-checkpoint.pt",
            metrics_path=output_dir / "pilot/metrics.jsonl",
            artifact_root=ARTIFACT_ROOT,
            seed=1337,
            micro_batch=1,
            accumulation_steps=16,
            checkpoint_interval_minutes=5.0,
            resume_from=initialization,
            config=DEFAULT_CONFIG,
            codec=CODEC,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
            answer_weight=1,
        )
        audit = source.sampling_audit()
        objective = (
            source.objective_record
            if answer_focused
            else {
                "kind": "ordinary-complete-record-next-token-v1",
                "promptTargetWeight": 1,
                "answerAndEosTargetWeight": 1,
                "paddingTargetWeight": 0,
            }
        )

    if not answer_focused:
        audit = {
            **audit,
            "supervisedTargetPositions": audit["realTargetPositions"],
            "excludedPromptTargetPositions": 0,
            "answerObjective": objective,
        }
    expected_nonzero_targets = audit["supervisedTargetPositions"]
    if result["tokensProcessedThisRun"] != expected_nonzero_targets:
        raise ValueError("Runner nonzero-loss target accounting differs from the objective audit")
    expected_zero_weight = audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
    if result["paddingTargetPositionsThisRun"] != expected_zero_weight:
        raise ValueError("Runner zero-weight target accounting differs from the objective audit")

    return {
        "training": result,
        "objective": objective,
        "accounting": {
            "examples": audit["examples"],
            "realContextTargets": audit["realTargetPositions"],
            "supervisedTargets": audit["supervisedTargetPositions"],
            "excludedPromptTargets": audit["excludedPromptTargetPositions"],
            "paddingTargets": audit["paddingTargetPositions"],
            "recordsSelected": audit["recordsSelected"],
            "minimumRecordSelections": audit["minimumRecordSelections"],
            "maximumRecordSelections": audit["maximumRecordSelections"],
        },
        "samplingAudit": audit,
    }


def run(
    prepared: Path,
    output: Path,
    device_name: str = "cuda",
    steps: int = 100,
    minutes: float = 10,
) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("Run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("Answer-focused comparison output exists; choose a fresh path")

    plan = verify_prepared(prepared)
    if (plan.get("candidateJsonlSha256") != CANDIDATE_SHA
            or plan.get("evaluationJsonlSha256") != EVALUATION_SHA
            or plan.get("arms", {}).get("varied", {}).get("trainRecords") != 24):
        raise ValueError("Comparison requires the exact approved 24-example varied arm")

    train, evaluation, settings, _ = load_inputs()
    varied_bundle = prepared / "varied/tokenizer"
    varied_dataset = prepared / "varied/dataset"
    bundle = inspect_pilot_bundle(varied_bundle)
    if bundle["dataset"].get("trainRecords") != 24:
        raise ValueError("Prepared varied bundle no longer contains 24 training records")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch step-zero source changed")
    select_device(device_name)

    output.mkdir(parents=True, exist_ok=False)
    initialization_reports = {}
    for arm in ("ordinary", "answer-focused"):
        initialization_reports[arm] = initialize_model(
            varied_bundle,
            output / arm / "initialization",
            seed=1337,
            artifact_root=ARTIFACT_ROOT,
        )

    initialization_paths = [SOURCE_INITIALIZATION] + [
        output / arm / "initialization/initialization.pt"
        for arm in ("ordinary", "answer-focused")
    ]
    payloads = [torch.load(path, map_location="cpu", weights_only=True) for path in initialization_paths]
    require_identical_initial_weights(payloads, torch.equal)
    del payloads

    arms = {}
    for arm, answer_focused in (("ordinary", False), ("answer-focused", True)):
        print(json.dumps({
            "event": "objective_arm_starting",
            "arm": arm,
            "maximumSteps": steps,
            "maximumMinutes": minutes,
        }), flush=True)
        arms[arm] = _run_arm(
            bundle_dir=varied_bundle,
            dataset_dir=varied_dataset,
            initialization=output / arm / "initialization/initialization.pt",
            output_dir=output / arm,
            device_name=device_name,
            steps=steps,
            minutes=minutes,
            answer_focused=answer_focused,
        )
        arms[arm]["initialization"] = initialization_reports[arm]
        training = arms[arm]["training"]
        if training["stepsThisRun"] != steps or training["interrupted"]:
            report = {
                "schemaVersion": 1,
                "comparisonComplete": False,
                "experiment": EXPERIMENT,
                "reason": "An objective arm stopped before the requested updates",
                "arms": arms,
                "noAutomaticExtension": True,
            }
            write_json(output / "comparison.json", report)
            return report

    replay = replay_exposure(
        train,
        steps,
        PlexTokenizer.load(varied_bundle),
        settings["outputContracts"],
    )
    for arm in ("ordinary", "answer-focused"):
        accounting = arms[arm]["accounting"]
        if accounting["examples"] != steps * 16 or accounting["realContextTargets"] != replay["realTargets"]:
            raise ValueError("Objective arms did not receive the same complete-record exposure")
    if arms["ordinary"]["accounting"]["realContextTargets"] != arms["answer-focused"]["accounting"]["realContextTargets"]:
        raise ValueError("Objective arms processed different real context target counts")

    reserved = json.loads(
        (ARTIFACT_ROOT / "diagnostics/p2-transfer-v1/cases.json").read_text(encoding="utf-8")
    )["cases"]
    cases = [
        ("candidate-original" if row["kind"] == "original" else "candidate-new", row)
        for row in train
    ]
    cases += [("reserved-transfer", row) for row in reserved if row["kind"] == "variation"]
    cases += [("new-transfer", row) for row in evaluation]

    for arm in ("ordinary", "answer-focused"):
        checkpoint = output / arm / "pilot/pilot-checkpoint.pt"
        arms[arm]["completionGroups"] = score_cases(
            checkpoint,
            varied_bundle,
            cases,
            settings,
            output / arm / "completion-score.json",
            device_name,
        )
        dev_output = output / arm / "development"
        generate_development_responses(
            task_set_path=ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json",
            checkpoint_path=checkpoint,
            bundle_dir=varied_bundle,
            output_dir=dev_output,
            artifact_root=ARTIFACT_ROOT,
            device_name=device_name,
        )
        score = evaluate_files(
            ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json",
            dev_output / "responses.jsonl",
        )
        write_json(dev_output / "score.json", score)
        arms[arm]["development"] = {
            key: score[key]
            for key in ("passed", "tasks", "assertionsPassed", "assertionsTotal", "truncatedOutputs")
        }

    verify_prepared(prepared)
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Original scratch checkpoint changed during comparison")

    report = {
        "schemaVersion": 1,
        "comparisonComplete": True,
        "experiment": EXPERIMENT,
        "approvedCandidateJsonlSha256": CANDIDATE_SHA,
        "evaluationOnlyJsonlSha256": EVALUATION_SHA,
        "approvedTrainingExamples": 24,
        "newTrainingExamples": 0,
        "tokenizerRefitted": False,
        "initialWeightsTensorwiseEqual": True,
        "sourceInitializationUnchanged": True,
        "stepsPerArm": steps,
        "minutesCapPerArm": minutes,
        "sharedRecordSelectionReplay": replay,
        "comparisonVariable": (
            "ordinary complete-record next-token loss versus answer/EOS-only loss; "
            "full prompts remain in causal context in both arms"
        ),
        "arms": arms,
        "limits": (
            "Selected 24-example/six-operation diagnostic; static/exact transfer and development checks; "
            "no final holdout and no automatic longer run."
        ),
    }
    write_json(output / "comparison.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepared",
        type=Path,
        default=ARTIFACT_ROOT / "experiments/p2-binding-v1",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda", "cpu", "auto"), default="cuda")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--minutes", type=float, default=10)
    args = parser.parse_args()
    try:
        report = run(args.prepared, args.output_dir, args.device, args.steps, args.minutes)
        print(json.dumps({
            "report": str(args.output_dir / "comparison.json"),
            "comparisonComplete": report["comparisonComplete"],
            "arms": {
                arm: {
                    "step": result["training"]["step"],
                    "objective": result["objective"]["kind"],
                    "accounting": result["accounting"],
                    "completionGroups": result.get("completionGroups"),
                    "development": result.get("development"),
                }
                for arm, result in report["arms"].items()
            },
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"plex-answer-focused: {exc}", file=sys.stderr)
        sys.exit(2)
