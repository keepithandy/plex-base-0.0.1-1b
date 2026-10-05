"""Run the approved one-arm P2-11 diagnostic; current sampler ceiling is 100 updates."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys

import torch

from diagnose_saved_checkpoints import ROOT
from prepare_binding_candidate import sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import ARTIFACT_ROOT, TOKENIZER_BUNDLE, read_rows, write_json
from prepare_p2_11_experiment import PHASE2, verify_prepared
from prepare_selector_format_probe import SELECTORS
from run_binding_experiment import SOURCE_INITIALIZATION, SOURCE_INITIALIZATION_SHA, require_identical_initial_weights
from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.config import DEFAULT_CONFIG
from plex_training.data import TokenCorpus
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.runner import run_training
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer

EXPERIMENT = "p2-11-balanced-wording-transfer-v1"
DEV_PATH = PHASE2 / "evaluation/p2-01b-dev-v1.json"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-11 runner is capped at 1-100 by the complete-record training framework")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-11 is capped at ten minutes")


def _classify(row: dict, completion: str, eos: bool) -> str:
    value = row["value"]
    stripped = completion.strip()
    if stripped == value and eos:
        return "exact_selector"
    if stripped in SELECTORS and eos:
        return "wrong_known_selector"
    if value in stripped and eos:
        return "expected_selector_with_extra_text"
    return "other_or_no_eos"


def _summarize(records: list[dict], group: str) -> dict:
    selected = [record for record in records if record["group"] == group]
    return {
        "count": len(selected),
        "exact": sum(record["category"] == "exact_selector" for record in selected),
        "wrongKnownSelector": sum(record["category"] == "wrong_known_selector" for record in selected),
        "expectedSelectorWithExtraText": sum(
            record["category"] == "expected_selector_with_extra_text" for record in selected
        ),
        "otherOrNoEos": sum(record["category"] == "other_or_no_eos" for record in selected),
        "eos": sum(record["eos"] for record in selected),
        "generatedTokenCount": sum(record["generatedTokenCount"] for record in selected),
        "beginsWithNewline": sum(record["beginsWithNewline"] for record in selected),
    }


def _score(checkpoint: Path, train_rows: list[dict], evaluation_rows: list[dict],
           settings: dict, device_name: str, output_path: Path) -> dict:
    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != tokenizer_record or payload.get("step", 0) < 1:
        raise ValueError("P2-11 checkpoint tokenizer or training identity is invalid")
    records = []
    for group, rows in (("training", train_rows), ("evaluation", evaluation_rows)):
        for row in rows:
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            if len(prompt_ids) >= model.config.context_length:
                raise ValueError(f"P2-11 request exceeds model context: {row['id']}")
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
            records.append({
                "id": row["id"],
                "group": group,
                "phrasingId": row["phrasingId"],
                "layoutId": row["layoutId"],
                "value": row["value"],
                "request": row["request"],
                "completion": completion,
                "beginsWithNewline": completion.startswith("\n"),
                "generatedTokenIds": tokens,
                "generatedTokenPieces": [tokenizer.decode([token_id]) for token_id in tokens],
                "generatedTokenCount": len(tokens),
                "eos": eos,
                "category": _classify(row, completion, eos),
            })
    cells = {}
    for group in ("training", "evaluation"):
        group_records = [record for record in records if record["group"] == group]
        cells[group] = {}
        for phrase_id in sorted({record["phrasingId"] for record in group_records}):
            cells[group][phrase_id] = {}
            for layout_id in ("colon-space", "colon-newline"):
                rows = [record for record in group_records
                        if record["phrasingId"] == phrase_id and record["layoutId"] == layout_id]
                cells[group][phrase_id][layout_id] = {
                    "count": len(rows),
                    "exact": sum(row["category"] == "exact_selector" for row in rows),
                    "wrongKnownSelector": sum(row["category"] == "wrong_known_selector" for row in rows),
                    "expectedSelectorWithExtraText": sum(
                        row["category"] == "expected_selector_with_extra_text" for row in rows
                    ),
                    "otherOrNoEos": sum(row["category"] == "other_or_no_eos" for row in rows),
                }
    result = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize(records, "training"),
        "evaluation": _summarize(records, "evaluation"),
        "conditionCells": cells,
        "records": records,
        "evaluationSemantics": "Known selector values under four fresh held-out phrasings and crossed input layouts.",
        "finalHoldoutOpened": False,
    }
    write_json(output_path, result)
    return result


def _replay_sampling_audit(prepared: Path, plan: dict, steps: int) -> dict:
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    source = AnswerFocusedCompleteRecordTokenCorpus(
        prepared / "dataset/train.tokens.u16le",
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "dataset/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=plan["packedTrain"]["trainJsonlSha256"],
    )
    rng = random.Random(plan["seed"])
    with source:
        for _ in range(steps * plan["microBatch"] * plan["gradientAccumulation"]):
            source.sample_masked_batch(rng, plan["microBatch"], DEFAULT_CONFIG.context_length)
        return source.sampling_audit()


def run(prepared: Path, output: Path, device_name: str = "cuda",
        steps: int = 100, minutes: float = 10.0) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-11 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-11 run output exists; choose a fresh directory")
    plan = verify_prepared(prepared)
    if (steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]
            or steps > plan["maximumTotalSteps"] or minutes > plan["maximumTotalMinutes"]):
        raise ValueError("Requested P2-11 run exceeds approved bounds")
    if device_name != plan["device"]:
        raise ValueError("P2-11 owner approval specifies CUDA")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded seed-1337 scratch initialization changed")

    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    train_rows = read_rows(prepared / "approved/candidate.jsonl")
    evaluation_rows = read_rows(prepared / "evaluation-only/evaluation-only.jsonl")
    output.mkdir(parents=True, exist_ok=False)
    initialization = initialize_model(TOKENIZER_BUNDLE, output / "initialization",
                                      seed=plan["seed"], artifact_root=ARTIFACT_ROOT)
    source_payload = torch.load(SOURCE_INITIALIZATION, map_location="cpu", weights_only=True)
    initial_payload = torch.load(output / "initialization/initialization.pt",
                                 map_location="cpu", weights_only=True)
    require_identical_initial_weights([source_payload, initial_payload], torch.equal)
    del source_payload, initial_payload

    dataset_record = {
        "kind": EXPERIMENT,
        "trainJsonlSha256": plan["packedTrain"]["trainJsonlSha256"],
        "trainTokensSha256": plan["packedTrain"]["trainTokensSha256"],
        "trainTokenCount": plan["packedTrain"]["tokenCount"],
        "trainRecords": len(train_rows),
        "validationSource": "p2-request-following-v3-validation",
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "validationTokensSha256": bundle["dataset"]["validationTokensSha256"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "validationRecords": bundle["dataset"]["validationRecords"],
        "p211EvaluationUsedForValidation": False,
    }
    source = AnswerFocusedCompleteRecordTokenCorpus(
        prepared / "dataset/train.tokens.u16le",
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "dataset/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=plan["packedTrain"]["trainJsonlSha256"],
    )
    print(json.dumps({"event": "p2_11_training_starting", "trainingRecords": len(train_rows),
                      "evaluationOnlyRecords": len(evaluation_rows), "maximumSteps": steps,
                      "maximumMinutes": minutes, "device": device_name}), flush=True)
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
            resume_from=output / "initialization/initialization.pt",
            codec=CODEC,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=dataset_record,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
            validation_maximum_batches=100,
            answer_weight=1,
        )
        audit = source.sampling_audit()
    if training["tokensProcessedThisRun"] != audit["supervisedTargetPositions"]:
        raise ValueError("P2-11 supervised-target accounting differs from sampler audit")
    if training["paddingTargetPositionsThisRun"] != (
            audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]):
        raise ValueError("P2-11 zero-weight target accounting differs from sampler audit")
    checkpoint = output / "pilot/pilot-checkpoint.pt"
    if not checkpoint.is_file():
        raise ValueError("P2-11 training did not produce a scoreable checkpoint")
    scores = _score(checkpoint, train_rows, evaluation_rows, settings, device_name,
                    output / "completion-score.json")
    audit_replay = _replay_sampling_audit(prepared, plan, training["stepsThisRun"])
    if (audit_replay["supervisedTargetPositions"] != training["tokensProcessedThisRun"]
            or audit_replay["paddingTargetPositions"] + audit_replay["excludedPromptTargetPositions"]
            != training["paddingTargetPositionsThisRun"]):
        raise ValueError("P2-11 replayed sampler accounting differs from training telemetry")
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-11 inputs changed during training")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch initialization changed during P2-11")
    training_complete = training["stepsThisRun"] == steps and not training["interrupted"]
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training_complete,
        "trainingInterrupted": training["interrupted"],
        "freshScratchInitialization": True,
        "initialWeightsTensorwiseEqualToRecordedSeed1337": True,
        "initialization": initialization,
        "training": training,
        "approvedMaximumSteps": plan["maximumSteps"],
        "actualStepCap": steps,
        "device": device_name,
        "accounting": {
            "examples": audit_replay["examples"],
            "recordsSelected": audit_replay["recordsSelected"],
            "minimumRecordSelections": audit_replay["minimumRecordSelections"],
            "maximumRecordSelections": audit_replay["maximumRecordSelections"],
            "realContextTargets": audit_replay["realTargetPositions"],
            "supervisedTargets": audit_replay["supervisedTargetPositions"],
            "excludedPromptTargets": audit_replay["excludedPromptTargetPositions"],
            "paddingTargets": audit_replay["paddingTargetPositions"],
        },
        "scoring": {"training": scores["training"], "evaluation": scores["evaluation"],
                    "conditionCells": scores["conditionCells"]},
        "trainingConverged": scores["training"]["exact"] == len(train_rows),
        "evaluationInterpretation": (
            "interpretable-after-96-of-96-training-convergence"
            if scores["training"]["exact"] == len(train_rows)
            else "inconclusive-p2-11-supplied-set-did-not-reach-96-of-96"
        ),
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "evaluationJsonlSha256": plan["evaluationJsonlSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "trainingObjective": plan["trainingObjective"],
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Narrow selector-copy diagnostic over eight known values, two input layouts, four fresh held-out phrasings, and one fresh initialization. Thirty-two P2-10 evaluation requests were promoted to P2-11 training. This is not evidence of broad instruction understanding or coding ability.",
    }
    write_json(output / "result.json", report)
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
        result = run(args.prepared, args.output_dir, args.device, args.steps, args.minutes)
        print(json.dumps({"report": str(args.output_dir / "result.json"),
                          "trainingReachedStepLimit": result["trainingReachedStepLimit"],
                          "trainingConverged": result["trainingConverged"],
                          "training": result["scoring"]["training"],
                          "evaluation": result["scoring"]["evaluation"],
                          "finalHoldoutOpened": result["finalHoldoutOpened"]}, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-11-run: {exc}", file=sys.stderr)
        raise SystemExit(2)
