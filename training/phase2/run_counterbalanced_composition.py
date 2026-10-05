"""Run the approved three-fold P2-05 counterbalanced composition diagnostic."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys

import torch

from prepare_binding_candidate import ROOT, sha256_file
from prepare_compositional_experiment import read_rows
from prepare_counterbalanced_composition import (
    ARTIFACT_ROOT,
    FOLD_HELDOUT,
    TOKENIZER_BUNDLE,
    verify_prepared,
    write_json,
)
from run_binding_experiment import (
    SOURCE_INITIALIZATION,
    SOURCE_INITIALIZATION_SHA,
    require_identical_initial_weights,
)
from run_compositional_experiment import score_records
from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.data import TokenCorpus
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.runner import run_training
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer

EXPERIMENT = "p2-05-counterbalanced-composition-v1"
DEV_PATH = ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-05 requires 1-100 optimizer updates per fold")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-05 is capped at ten minutes per fold")


def replay_exposure(rows: list[dict], steps: int, seed: int = 1337) -> dict:
    rng = random.Random(seed)
    counts = {row["id"]: 0 for row in rows}
    pair_by_id = {row["id"]: row["bindings"] for row in rows}
    for _ in range(steps * 16):
        row = rng.choice(rows)
        counts[row["id"]] += 1
    return {
        "examples": steps * 16,
        "recordSelections": counts,
        "pairSelections": [
            {"bindings": pair_by_id[record_id], "selections": count}
            for record_id, count in counts.items()
        ],
        "minimumRecordSelections": min(counts.values()),
        "maximumRecordSelections": max(counts.values()),
    }


def summarize_records(records: list[dict]) -> dict:
    measures = ("exact", "staticPass", "bindingPass", "compositionPass",
                "syntaxPass", "selectorPass", "gapPass", "replayedTrainingSolution")
    return {"count": len(records), **{key: sum(bool(row[key]) for row in records) for key in measures}}


def interpretation(converged_folds: int, passes: int) -> str:
    if converged_folds != 3:
        return "inconclusive-counterbalanced-transfer: all three folds must fit their six supplied combinations"
    if passes == 9:
        return "full-counterbalanced-compositional-transfer-within-this-css-operation"
    if passes >= 7:
        return "strong-counterbalanced-composition-signal-within-this-css-operation"
    if passes >= 4:
        return "partial-counterbalanced-compositional-transfer-within-this-css-operation"
    if passes > 0:
        return "limited-counterbalanced-compositional-transfer-within-this-css-operation"
    return "no-counterbalanced-compositional-transfer-demonstrated-after-supplied-fit"


def run(prepared: Path, output: Path, device_name: str = "cuda",
        steps: int = 100, minutes: float = 10.0) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-05 output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-05 run output already exists; choose a fresh directory")
    plan = verify_prepared(prepared)
    if (steps > plan["maximumStepsPerFold"] or minutes > plan["maximumMinutesPerFold"]
            or steps * len(FOLD_HELDOUT) > plan["maximumTotalSteps"]
            or minutes * len(FOLD_HELDOUT) > plan["maximumTotalMinutes"]):
        raise ValueError("Requested P2-05 run exceeds owner-approved bounds")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch step-zero source changed")
    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    base_bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    select_device(device_name)

    output.mkdir(parents=True, exist_ok=False)
    initialization_reports = {}
    initialization_paths = [SOURCE_INITIALIZATION]
    for fold_name in FOLD_HELDOUT:
        result = initialize_model(
            TOKENIZER_BUNDLE,
            output / fold_name / "initialization",
            seed=plan["seedPerFold"],
            artifact_root=ARTIFACT_ROOT,
        )
        initialization_reports[fold_name] = result
        initialization_paths.append(output / fold_name / "initialization/initialization.pt")
    payloads = [torch.load(path, map_location="cpu", weights_only=True) for path in initialization_paths]
    require_identical_initial_weights(payloads, torch.equal)
    del payloads

    folds = {}
    all_heldout_records = []
    for fold_name in FOLD_HELDOUT:
        fold_input = prepared / fold_name
        fold_plan = plan["folds"][fold_name]
        train_rows = read_rows(fold_input / "approved/candidate.jsonl")
        heldout_rows = read_rows(fold_input / "heldout/evaluation-only.jsonl")
        heldout_pairs = {tuple(row["bindings"][key] for key in ("selector", "gap")) for row in heldout_rows}
        if heldout_pairs != set(FOLD_HELDOUT[fold_name]):
            raise ValueError(f"{fold_name} held-out rows differ from the approved split")
        dataset_record = {
            "kind": "p2-05-counterbalanced-composition-v1",
            "fold": fold_name,
            "preparedExperimentSha256": sha256_file(prepared / "experiment.json"),
            "trainJsonlSha256": fold_plan["packedTrain"]["trainJsonlSha256"],
            "trainTokensSha256": fold_plan["packedTrain"]["trainTokensSha256"],
            "trainTokenCount": fold_plan["packedTrain"]["tokenCount"],
            "trainRecords": 6,
            "validationSource": "p2-request-following-v3-validation",
            "validationJsonlSha256": base_bundle["dataset"]["validationJsonlSha256"],
            "validationTokensSha256": base_bundle["dataset"]["validationTokensSha256"],
            "validationTokenCount": base_bundle["dataset"]["validationTokenCount"],
            "validationRecords": base_bundle["dataset"]["validationRecords"],
            "foldHeldoutUsedForValidation": False,
        }
        source = AnswerFocusedCompleteRecordTokenCorpus(
            fold_input / "dataset/train.tokens.u16le",
            dataset_jsonl=fold_input / "dataset/train.jsonl",
            index_path=fold_input / "dataset/train.index.json",
            tokenizer=tokenizer,
            expected_jsonl_sha256=fold_plan["packedTrain"]["trainJsonlSha256"],
        )
        print(json.dumps({
            "event": "p2_05_fold_starting",
            "fold": fold_name,
            "maximumSteps": steps,
            "maximumMinutes": minutes,
            "heldOutPairs": [list(item) for item in FOLD_HELDOUT[fold_name]],
        }), flush=True)
        with source as train, TokenCorpus(base_bundle["validationPath"]) as validation:
            training = run_training(
                train_source=train,
                validation=validation,
                device_name=device_name,
                minutes=minutes,
                step_limit=steps,
                output_checkpoint=output / fold_name / "pilot/pilot-checkpoint.pt",
                metrics_path=output / fold_name / "pilot/metrics.jsonl",
                artifact_root=ARTIFACT_ROOT,
                seed=plan["seedPerFold"],
                micro_batch=plan["microBatch"],
                accumulation_steps=plan["gradientAccumulation"],
                checkpoint_interval_minutes=5.0,
                resume_from=output / fold_name / "initialization/initialization.pt",
                codec=CODEC,
                tokenizer_record=base_bundle["tokenizer"],
                dataset_record=dataset_record,
                loss_vocabulary_size=base_bundle["tokenizer"]["actualVocabularySize"],
                validation_maximum_batches=100,
                answer_weight=1,
            )
            audit = source.sampling_audit()
        if training["tokensProcessedThisRun"] != audit["supervisedTargetPositions"]:
            raise ValueError(f"{fold_name} supervised-target accounting differs from its answer-focused audit")
        expected_zero = audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
        if training["paddingTargetPositionsThisRun"] != expected_zero:
            raise ValueError(f"{fold_name} zero-weight accounting differs from its answer-focused audit")
        accounting = {
            "examples": audit["examples"],
            "recordsSelected": audit["recordsSelected"],
            "minimumRecordSelections": audit["minimumRecordSelections"],
            "maximumRecordSelections": audit["maximumRecordSelections"],
            "realContextTargets": audit["realTargetPositions"],
            "supervisedTargets": audit["supervisedTargetPositions"],
            "excludedPromptTargets": audit["excludedPromptTargetPositions"],
            "paddingTargets": audit["paddingTargetPositions"],
            "selectionReplay": replay_exposure(train_rows, training["stepsThisRun"], plan["seedPerFold"]),
        }
        folds[fold_name] = {
            "initialization": initialization_reports[fold_name],
            "training": training,
            "accounting": accounting,
        }
        if training["stepsThisRun"] != steps or training["interrupted"]:
            report = {
                "schemaVersion": 1,
                "experiment": EXPERIMENT,
                "allFoldsComplete": False,
                "reason": f"{fold_name} stopped before the approved update target",
                "folds": folds,
                "noAutomaticExtension": True,
                "finalHoldoutOpened": False,
            }
            write_json(output / "result.json", report)
            return report
        scoring = score_records(
            output / fold_name / "pilot/pilot-checkpoint.pt",
            train_rows,
            heldout_rows,
            settings,
            device_name,
            output / fold_name / "completion-score.json",
        )
        supplied_converged = scoring["training"]["compositionPass"] == 6
        heldout_records = [row for row in scoring["records"] if row["group"] == "heldout"]
        for row in heldout_records:
            row["fold"] = fold_name
        all_heldout_records.extend(heldout_records)
        folds[fold_name]["scoring"] = {
            "training": scoring["training"],
            "heldout": scoring["heldout"],
        }
        folds[fold_name]["suppliedConverged"] = supplied_converged

    heldout_keys = [(row["bindings"]["selector"], row["bindings"]["gap"]) for row in all_heldout_records]
    if len(heldout_keys) != 9 or len(set(heldout_keys)) != 9:
        raise ValueError("P2-05 did not evaluate each matrix cell exactly once as fold-local heldout")
    aggregate = summarize_records(all_heldout_records)
    converged_folds = sum(bool(result["suppliedConverged"]) for result in folds.values())
    decision = interpretation(converged_folds, aggregate["compositionPass"])
    verify_prepared(prepared)
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Original scratch checkpoint changed during P2-05")
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "allFoldsComplete": True,
        "freshScratchInitializationPerFold": True,
        "initialWeightsTensorwiseEqualAcrossFolds": True,
        "seedPerFold": plan["seedPerFold"],
        "stepsPerFold": steps,
        "minutesCapPerFold": minutes,
        "foldsSuppliedConverged": converged_folds,
        "aggregateHeldout": aggregate,
        "heldOutCompositionPasses": aggregate["compositionPass"],
        "heldOutCompositionTotal": 9,
        "interpretation": decision,
        "folds": folds,
        "heldoutRecords": all_heldout_records,
        "foldLocalHeldoutOnly": True,
        "globalPristineHoldoutClaim": False,
        "foldHeldoutsUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Three counterbalanced folds over one 3x3 CSS selector-gap matrix; each cell is held out once but trained in the other two folds; diagnostic evidence only.",
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
            "allFoldsComplete": result["allFoldsComplete"],
            "foldsSuppliedConverged": result.get("foldsSuppliedConverged"),
            "heldOutCompositionPasses": result.get("heldOutCompositionPasses"),
            "heldOutCompositionTotal": result.get("heldOutCompositionTotal"),
            "interpretation": result.get("interpretation"),
            "aggregateHeldout": result.get("aggregateHeldout"),
            "folds": {
                name: {
                    "suppliedConverged": fold.get("suppliedConverged"),
                    "training": fold.get("scoring", {}).get("training"),
                    "heldout": fold.get("scoring", {}).get("heldout"),
                }
                for name, fold in result.get("folds", {}).items()
            },
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-05-run: {exc}", file=sys.stderr)
        sys.exit(2)
