"""Run the approved six-record P2-04 answer-focused compositional-binding diagnostic."""
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
from prepare_compositional_experiment import (
    ARTIFACT_ROOT,
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

EXPERIMENT = "p2-04-compositional-binding-answer-focused-v1"
DEV_PATH = ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-04 requires 1-100 optimizer updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-04 is capped at ten minutes")


def summarize(records: list[dict], group: str) -> dict:
    rows = [row for row in records if row["group"] == group]
    measures = ("exact", "staticPass", "bindingPass", "compositionPass",
                "syntaxPass", "selectorPass", "gapPass", "replayedTrainingSolution")
    return {"count": len(rows), **{key: sum(bool(row[key]) for row in rows) for key in measures}}


def score_records(checkpoint: Path, train_rows: list[dict], heldout_rows: list[dict],
                  settings: dict, device_name: str, output: Path) -> dict:
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for P2-04 CSS scoring")
    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != tokenizer_record:
        raise ValueError("P2-04 checkpoint tokenizer identity changed")
    training_solutions = {"\n" + row["solution"] for row in train_rows}
    records = []
    for group, rows in (("training", train_rows), ("heldout", heldout_rows)):
        for row in rows:
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            if len(prompt_ids) >= model.config.context_length:
                raise ValueError("P2-04 prompt exceeds model context")
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
            static = _check_task(
                {"id": row["id"], "language": "css", "difficulty": "basic", "checks": row["checks"]},
                completion,
                node,
                5.0,
            )
            selector = row["bindings"]["selector"]
            gap = row["bindings"]["gap"]
            selector_pass = selector in completion
            gap_pass = gap in completion
            binding_pass = selector_pass and gap_pass and eos
            static_pass = bool(static["passed"]) and eos
            records.append({
                "id": row["id"],
                "group": group,
                "bindings": row["bindings"],
                "completion": completion,
                "expected": row["solution"],
                "generatedTokens": len(tokens),
                "eos": eos,
                "exact": completion == "\n" + row["solution"] and eos,
                "staticPass": static_pass,
                "bindingPass": binding_pass,
                "compositionPass": static_pass and binding_pass,
                "syntaxPass": static["parseStatus"] == "pass",
                "selectorPass": selector_pass,
                "gapPass": gap_pass,
                "replayedTrainingSolution": group == "heldout" and completion in training_solutions,
            })
    report = {
        "schemaVersion": 1,
        "checkpointSha256": sha256_file(checkpoint),
        "training": summarize(records, "training"),
        "heldout": summarize(records, "heldout"),
        "records": records,
        "scoreMeaning": "Static CSS plus exact selector/gap binding; generated code is never executed.",
    }
    write_json(output, report)
    return report


def run(prepared: Path, output: Path, device_name: str = "cuda",
        steps: int = 100, minutes: float = 10.0) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-04 output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-04 run output already exists; choose a fresh directory")
    plan = verify_prepared(prepared)
    if steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]:
        raise ValueError("Requested P2-04 run exceeds owner-approved bounds")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch step-zero source changed")
    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    base_bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    select_device(device_name)

    output.mkdir(parents=True, exist_ok=False)
    initialization = initialize_model(
        TOKENIZER_BUNDLE,
        output / "initialization",
        seed=plan["seed"],
        artifact_root=ARTIFACT_ROOT,
    )
    initial_paths = [SOURCE_INITIALIZATION, output / "initialization/initialization.pt"]
    payloads = [torch.load(path, map_location="cpu", weights_only=True) for path in initial_paths]
    require_identical_initial_weights(payloads, torch.equal)
    del payloads

    dataset_record = {
        "kind": "p2-04-compositional-binding-v1",
        "preparedExperimentSha256": sha256_file(prepared / "experiment.json"),
        "trainJsonlSha256": plan["packedTrain"]["trainJsonlSha256"],
        "trainTokensSha256": plan["packedTrain"]["trainTokensSha256"],
        "trainTokenCount": plan["packedTrain"]["tokenCount"],
        "trainRecords": 6,
        "validationSource": "p2-request-following-v3-validation",
        "validationJsonlSha256": base_bundle["dataset"]["validationJsonlSha256"],
        "validationTokensSha256": base_bundle["dataset"]["validationTokensSha256"],
        "validationTokenCount": base_bundle["dataset"]["validationTokenCount"],
        "validationRecords": base_bundle["dataset"]["validationRecords"],
        "p204HeldoutUsedForValidation": False,
    }
    source = AnswerFocusedCompleteRecordTokenCorpus(
        prepared / "dataset/train.tokens.u16le",
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "dataset/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=plan["packedTrain"]["trainJsonlSha256"],
    )
    with source as train, TokenCorpus(base_bundle["validationPath"]) as validation:
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
            resume_from=output / "initialization/initialization.pt",
            codec=CODEC,
            tokenizer_record=base_bundle["tokenizer"],
            dataset_record=dataset_record,
            loss_vocabulary_size=base_bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
            answer_weight=1,
        )
        audit = source.sampling_audit()

    if training["tokensProcessedThisRun"] != audit["supervisedTargetPositions"]:
        raise ValueError("P2-04 supervised-target accounting differs from the answer-focused audit")
    expected_zero = audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
    if training["paddingTargetPositionsThisRun"] != expected_zero:
        raise ValueError("P2-04 zero-weight target accounting differs from the answer-focused audit")
    accounting = {
        "examples": audit["examples"],
        "recordsSelected": audit["recordsSelected"],
        "minimumRecordSelections": audit["minimumRecordSelections"],
        "maximumRecordSelections": audit["maximumRecordSelections"],
        "realContextTargets": audit["realTargetPositions"],
        "supervisedTargets": audit["supervisedTargetPositions"],
        "excludedPromptTargets": audit["excludedPromptTargetPositions"],
        "paddingTargets": audit["paddingTargetPositions"],
    }
    if training["stepsThisRun"] != steps or training["interrupted"]:
        report = {
            "schemaVersion": 1,
            "experiment": EXPERIMENT,
            "runComplete": False,
            "reason": "Training stopped before the approved update target",
            "training": training,
            "accounting": accounting,
            "noAutomaticExtension": True,
            "finalHoldoutOpened": False,
        }
        write_json(output / "result.json", report)
        return report

    train_rows = read_rows(prepared / "approved/candidate.jsonl")
    heldout_rows = read_rows(prepared / "heldout/evaluation-only.jsonl")
    scoring = score_records(
        output / "pilot/pilot-checkpoint.pt",
        train_rows,
        heldout_rows,
        settings,
        device_name,
        output / "completion-score.json",
    )
    supplied_converged = scoring["training"]["compositionPass"] == 6
    heldout_passes = scoring["heldout"]["compositionPass"]
    if not supplied_converged:
        interpretation = "inconclusive-transfer: fit all six approved training combinations before interpreting held-out failures"
    elif heldout_passes == 3:
        interpretation = "full-compositional-transfer-within-this-one-css-operation"
    elif heldout_passes > 0:
        interpretation = "partial-compositional-transfer-within-this-one-css-operation"
    else:
        interpretation = "no-compositional-transfer-demonstrated-after-supplied-fit"

    verify_prepared(prepared)
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Original scratch checkpoint changed during P2-04")
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "runComplete": True,
        "objective": source.objective_record,
        "steps": steps,
        "minutesCap": minutes,
        "initialWeightsMatchRecordedScratch": True,
        "training": training,
        "accounting": accounting,
        "scoring": {"training": scoring["training"], "heldout": scoring["heldout"]},
        "suppliedConverged": supplied_converged,
        "heldOutCompositionPasses": heldout_passes,
        "interpretation": interpretation,
        "p204HeldoutUsedForTraining": False,
        "p204HeldoutUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Six supplied and three held-out combinations inside one CSS operation; diagnostic evidence only.",
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
            "runComplete": result["runComplete"],
            "suppliedConverged": result.get("suppliedConverged"),
            "heldOutCompositionPasses": result.get("heldOutCompositionPasses"),
            "interpretation": result.get("interpretation"),
            "scoring": result.get("scoring"),
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-04-run: {exc}", file=sys.stderr)
        sys.exit(2)
