"""Run three fresh-model P2-06 representation levels and locate the first failing capability."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys

import torch

from diagnose_saved_checkpoints import _check_task
from prepare_binding_candidate import ROOT, prompt_text, sha256_file
from prepare_binding_representation_experiment import (
    ARTIFACT_ROOT,
    LEVELS,
    TOKENIZER_BUNDLE,
    read_rows,
    verify_prepared,
    write_json,
)
from run_binding_experiment import (
    SOURCE_INITIALIZATION,
    SOURCE_INITIALIZATION_SHA,
    require_identical_initial_weights,
)
from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.data import TokenCorpus
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.runner import run_training
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer

EXPERIMENT = "p2-06-binding-representation-v1"
DEV_PATH = ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-06 requires 1-100 optimizer updates per level")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-06 is capped at ten minutes per level")


def _score_one(level: str, row: dict, completion: str, eos: bool, node: str) -> dict:
    expected = "\n" + row["solution"]
    exact = completion == expected and eos
    bindings = row["bindings"]
    selector_pass = True
    gap_pass = True
    syntax_pass = True
    static_pass = exact
    if "selector" in bindings:
        selector = bindings["selector"]
        selector_pass = (completion.strip() == selector if level == "single-copy"
                         else (f"selector={selector}" in completion if level == "dual-binding"
                               else selector in completion))
    if "gap" in bindings:
        gap = bindings["gap"]
        gap_pass = (completion.strip() == gap if level == "single-copy"
                    else (f"gap={gap}" in completion if level == "dual-binding"
                          else gap in completion))
    if level == "css-composition":
        static = _check_task(
            {"id": row["id"], "language": "css", "difficulty": "basic", "checks": row["checks"]},
            completion,
            node,
            5.0,
        )
        syntax_pass = static["parseStatus"] == "pass"
        static_pass = bool(static["passed"]) and eos
    binding_pass = selector_pass and gap_pass and eos
    representation_pass = exact if level in ("single-copy", "dual-binding") else static_pass and binding_pass
    return {
        "exact": exact,
        "representationPass": representation_pass,
        "bindingPass": binding_pass,
        "selectorPass": selector_pass,
        "gapPass": gap_pass,
        "staticPass": static_pass,
        "syntaxPass": syntax_pass,
    }


def _summarize(records: list[dict], group: str) -> dict:
    rows = [row for row in records if row["group"] == group]
    measures = ("exact", "representationPass", "bindingPass", "selectorPass", "gapPass",
                "staticPass", "syntaxPass", "replayedTrainingSolution")
    return {"count": len(rows), **{key: sum(bool(row[key]) for row in rows) for key in measures}}


def score_level(checkpoint: Path, level: str, train_rows: list[dict], eval_rows: list[dict],
                settings: dict, device_name: str, output: Path) -> dict:
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for P2-06 CSS syntax scoring")
    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != tokenizer_record:
        raise ValueError("P2-06 checkpoint tokenizer identity changed")
    training_solutions = {"\n" + row["solution"] for row in train_rows}
    records = []
    for group, rows in (("training", train_rows), ("evaluation", eval_rows)):
        for row in rows:
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            if len(prompt_ids) >= model.config.context_length:
                raise ValueError("P2-06 prompt exceeds model context")
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
            scored = _score_one(level, row, completion, eos, node)
            records.append({
                "id": row["id"],
                "level": level,
                "group": group,
                "bindings": row["bindings"],
                "request": row["request"],
                "expected": row["solution"],
                "completion": completion,
                "generatedTokens": len(tokens),
                "eos": eos,
                "replayedTrainingSolution": group == "evaluation" and completion in training_solutions,
                **scored,
            })
    report = {
        "schemaVersion": 1,
        "level": level,
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize(records, "training"),
        "evaluation": _summarize(records, "evaluation"),
        "records": records,
    }
    write_json(output, report)
    return report


def diagnose(levels: dict[str, dict]) -> str:
    if any(not levels[level]["suppliedConverged"] for level in LEVELS):
        return "inconclusive-representation-ladder: every level must first fit all six supplied examples"
    if levels["single-copy"]["scoring"]["evaluation"]["representationPass"] < 6:
        return "single-binding-copy-or-wording-transfer-bottleneck"
    if levels["dual-binding"]["scoring"]["evaluation"]["representationPass"] < 3:
        return "simultaneous-independent-binding-bottleneck"
    if levels["css-composition"]["scoring"]["evaluation"]["representationPass"] < 3:
        return "code-composition-bottleneck-after-binding-preservation"
    return "representation-ladder-passed: investigate-broader-distribution-or-capacity-effects-next"


def run(prepared: Path, output: Path, device_name: str = "cuda",
        steps: int = 100, minutes: float = 10.0) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-06 output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-06 run output already exists; choose a fresh directory")
    plan = verify_prepared(prepared)
    if (steps > plan["maximumStepsPerLevel"] or minutes > plan["maximumMinutesPerLevel"]
            or steps * len(LEVELS) > plan["maximumTotalSteps"]
            or minutes * len(LEVELS) > plan["maximumTotalMinutes"]):
        raise ValueError("Requested P2-06 run exceeds owner-approved bounds")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch step-zero source changed")

    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    base_bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    select_device(device_name)
    output.mkdir(parents=True, exist_ok=False)

    initialization_reports = {}
    initialization_paths = [SOURCE_INITIALIZATION]
    for level in LEVELS:
        result = initialize_model(
            TOKENIZER_BUNDLE,
            output / level / "initialization",
            seed=plan["seedPerLevel"],
            artifact_root=ARTIFACT_ROOT,
        )
        initialization_reports[level] = result
        initialization_paths.append(output / level / "initialization/initialization.pt")
    payloads = [torch.load(path, map_location="cpu", weights_only=True) for path in initialization_paths]
    require_identical_initial_weights(payloads, torch.equal)
    del payloads

    results = {}
    for level in LEVELS:
        level_input = prepared / level
        level_plan = plan["levels"][level]
        train_rows = read_rows(level_input / "approved/candidate.jsonl")
        eval_rows = read_rows(level_input / "heldout/evaluation-only.jsonl")
        dataset_record = {
            "kind": "p2-06-binding-representation-v1",
            "level": level,
            "preparedExperimentSha256": sha256_file(prepared / "experiment.json"),
            "trainJsonlSha256": level_plan["packedTrain"]["trainJsonlSha256"],
            "trainTokensSha256": level_plan["packedTrain"]["trainTokensSha256"],
            "trainTokenCount": level_plan["packedTrain"]["tokenCount"],
            "trainRecords": 6,
            "validationSource": "p2-request-following-v3-validation",
            "validationJsonlSha256": base_bundle["dataset"]["validationJsonlSha256"],
            "validationTokensSha256": base_bundle["dataset"]["validationTokensSha256"],
            "validationTokenCount": base_bundle["dataset"]["validationTokenCount"],
            "validationRecords": base_bundle["dataset"]["validationRecords"],
            "p206EvaluationUsedForValidation": False,
        }
        source = AnswerFocusedCompleteRecordTokenCorpus(
            level_input / "dataset/train.tokens.u16le",
            dataset_jsonl=level_input / "dataset/train.jsonl",
            index_path=level_input / "dataset/train.index.json",
            tokenizer=tokenizer,
            expected_jsonl_sha256=level_plan["packedTrain"]["trainJsonlSha256"],
        )
        print(json.dumps({
            "event": "p2_06_level_starting",
            "level": level,
            "maximumSteps": steps,
            "maximumMinutes": minutes,
        }), flush=True)
        with source as train, TokenCorpus(base_bundle["validationPath"]) as validation:
            training = run_training(
                train_source=train,
                validation=validation,
                device_name=device_name,
                minutes=minutes,
                step_limit=steps,
                output_checkpoint=output / level / "pilot/pilot-checkpoint.pt",
                metrics_path=output / level / "pilot/metrics.jsonl",
                artifact_root=ARTIFACT_ROOT,
                seed=plan["seedPerLevel"],
                micro_batch=plan["microBatch"],
                accumulation_steps=plan["gradientAccumulation"],
                checkpoint_interval_minutes=5.0,
                resume_from=output / level / "initialization/initialization.pt",
                codec=CODEC,
                tokenizer_record=base_bundle["tokenizer"],
                dataset_record=dataset_record,
                loss_vocabulary_size=base_bundle["tokenizer"]["actualVocabularySize"],
                validation_maximum_batches=100,
                answer_weight=1,
            )
            audit = source.sampling_audit()
        if training["tokensProcessedThisRun"] != audit["supervisedTargetPositions"]:
            raise ValueError(f"{level} supervised-target accounting differs from audit")
        expected_zero = audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
        if training["paddingTargetPositionsThisRun"] != expected_zero:
            raise ValueError(f"{level} zero-weight accounting differs from audit")
        if training["stepsThisRun"] != steps or training["interrupted"]:
            report = {
                "schemaVersion": 1,
                "experiment": EXPERIMENT,
                "allLevelsComplete": False,
                "reason": f"{level} stopped before the approved update target",
                "levels": results,
                "noAutomaticExtension": True,
                "finalHoldoutOpened": False,
            }
            write_json(output / "result.json", report)
            return report
        scoring = score_level(
            output / level / "pilot/pilot-checkpoint.pt",
            level,
            train_rows,
            eval_rows,
            settings,
            device_name,
            output / level / "completion-score.json",
        )
        results[level] = {
            "initialization": initialization_reports[level],
            "training": training,
            "accounting": {
                "examples": audit["examples"],
                "recordsSelected": audit["recordsSelected"],
                "minimumRecordSelections": audit["minimumRecordSelections"],
                "maximumRecordSelections": audit["maximumRecordSelections"],
                "realContextTargets": audit["realTargetPositions"],
                "supervisedTargets": audit["supervisedTargetPositions"],
                "excludedPromptTargets": audit["excludedPromptTargetPositions"],
                "paddingTargets": audit["paddingTargetPositions"],
            },
            "scoring": {"training": scoring["training"], "evaluation": scoring["evaluation"]},
            "suppliedConverged": scoring["training"]["representationPass"] == 6,
        }

    decision = diagnose(results)
    verify_prepared(prepared)
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Original scratch checkpoint changed during P2-06")
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "allLevelsComplete": True,
        "freshScratchInitializationPerLevel": True,
        "initialWeightsTensorwiseEqualAcrossLevels": True,
        "seedPerLevel": plan["seedPerLevel"],
        "stepsPerLevel": steps,
        "minutesCapPerLevel": minutes,
        "diagnosis": decision,
        "levels": results,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Tiny CSS-domain representation diagnostic; Level 1 tests alternate wording on seen values, while Levels 2 and 3 test three held-out pairings. Not broad coding generalization evidence.",
    }
    write_json(output / "result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda", "cpu", "auto"), default="cuda")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--minutes", type=float, default=10.0)
    args = parser.parse_args()
    try:
        result = run(args.prepared, args.output_dir, args.device, args.steps, args.minutes)
        print(json.dumps({
            "report": str(args.output_dir / "result.json"),
            "allLevelsComplete": result["allLevelsComplete"],
            "diagnosis": result.get("diagnosis"),
            "levels": {
                level: {
                    "suppliedConverged": value.get("suppliedConverged"),
                    "training": value.get("scoring", {}).get("training"),
                    "evaluation": value.get("scoring", {}).get("evaluation"),
                }
                for level, value in result.get("levels", {}).items()
            },
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-06-run: {exc}", file=sys.stderr)
        sys.exit(2)
