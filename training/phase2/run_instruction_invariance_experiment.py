"""Run the owner-approved single-arm P2-07 diagnostic; capped at 100 steps/ten minutes."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys

import torch

from diagnose_saved_checkpoints import ROOT
from prepare_binding_candidate import prompt_text, sha256_file
from prepare_compositional_experiment import ARTIFACT_ROOT, TOKENIZER_BUNDLE, read_rows, write_json
from prepare_instruction_invariance_experiment import PHASE2, verify_prepared
from run_binding_experiment import SOURCE_INITIALIZATION, SOURCE_INITIALIZATION_SHA, require_identical_initial_weights
from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.data import TokenCorpus
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.config import DEFAULT_CONFIG
from plex_training.runner import run_training
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, PlexTokenizer

EXPERIMENT = "p2-07-instruction-invariance-v1"
DEV_PATH = PHASE2 / "evaluation/p2-01b-dev-v1.json"


def validate_bounds(steps: int, minutes: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("P2-07 is capped at 1-100 optimizer updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("P2-07 is capped at ten minutes")


def _score_record(row: dict, completion: str, eos: bool, training_answers: set[str]) -> dict:
    expected = "\n" + row["solution"]
    exact = completion == expected and eos
    selector_pass = (row["operationFamily"] == "selector-copy"
                     and completion.strip() == row["value"] and eos)
    gap_pass = (row["operationFamily"] == "gap-copy"
                and completion.strip() == row["value"] and eos)
    return {
        "exact": exact,
        "representationPass": exact,
        "bindingPass": (completion.strip() == row["value"] and eos),
        "eos": eos,
        "selectorCopyPass": selector_pass,
        "gapCopyPass": gap_pass,
        "replayedTrainingSolution": completion in training_answers,
    }


def _summarize(records: list[dict], group: str) -> dict:
    rows = [row for row in records if row["group"] == group]
    measures = ("exact", "representationPass", "bindingPass", "eos",
                "selectorCopyPass", "gapCopyPass", "replayedTrainingSolution")
    return {
        "count": len(rows),
        **{key: sum(bool(row[key]) for row in rows) for key in measures},
        "generatedTokenCount": sum(row["generatedTokenCount"] for row in rows),
    }


def _interpret(training: dict, evaluation: dict) -> str:
    if training["representationPass"] != 24:
        return "inconclusive-instruction-invariance: supplied paraphrase matrix did not fully converge"
    passed = evaluation["representationPass"]
    if passed == 6:
        return "instruction-invariance-demonstrated-within-single-copy-probe"
    if passed >= 4:
        return "partial-instruction-invariance-within-single-copy-probe"
    if passed >= 1:
        return "limited-instruction-invariance-within-single-copy-probe"
    return "no-heldout-paraphrase-transfer-after-supplied-convergence"


def score(checkpoint: Path, train_rows: list[dict], evaluation_rows: list[dict],
          settings: dict, device_name: str, output_path: Path) -> dict:
    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != tokenizer_record:
        raise ValueError("P2-07 checkpoint tokenizer identity changed")
    training_answers = {"\n" + row["solution"] for row in train_rows}
    records = []
    for group, rows in (("training", train_rows), ("evaluation", evaluation_rows)):
        for row in rows:
            ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            if len(ids) >= model.config.context_length:
                raise ValueError("P2-07 request exceeds model context")
            tokens, eos = _generate_token_ids(
                model,
                ids,
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
                "operationFamily": row["operationFamily"],
                "value": row["value"],
                "phrasingId": row["phrasingId"],
                "request": row["request"],
                "expected": row["solution"],
                "completion": completion,
                "generatedTokenCount": len(tokens),
                **_score_record(row, completion, eos, training_answers),
            })
    result = {
        "schemaVersion": 1,
        "checkpointSha256": sha256_file(checkpoint),
        "training": _summarize(records, "training"),
        "evaluation": _summarize(records, "evaluation"),
        "records": records,
        "evaluationSemantics": "Known-value copying under a held-out instruction phrase; evaluation answers are also present in training by design.",
    }
    write_json(output_path, result)
    return result


def replay_sampling_audit(prepared: Path, plan: dict, steps: int) -> dict:
    """Replay the pinned Python sampler without training to recover exact accounting."""
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    source = AnswerFocusedCompleteRecordTokenCorpus(
        prepared / "dataset/train.tokens.u16le",
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "dataset/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=plan["packedTrain"]["trainJsonlSha256"],
    )
    rng = random.Random(plan["seed"])
    draws = steps * plan["microBatch"] * plan["gradientAccumulation"]
    with source:
        for _ in range(draws):
            source.sample_masked_batch(rng, plan["microBatch"], DEFAULT_CONFIG.context_length)
        return source.sampling_audit()


def run(prepared: Path, output: Path, device_name: str = "cuda",
        steps: int = 100, minutes: float = 10.0) -> dict:
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("P2-07 run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("P2-07 run output exists; choose a fresh directory")
    plan = verify_prepared(prepared)
    if (steps > plan["maximumSteps"] or minutes > plan["maximumMinutes"]
            or steps > plan["maximumTotalSteps"] or minutes > plan["maximumTotalMinutes"]):
        raise ValueError("Requested P2-07 run exceeds the exact approved bounds")
    if device_name != plan["device"]:
        raise ValueError("P2-07 owner approval specifies CUDA")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded seed-1337 scratch initialization changed")

    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    device = select_device(device_name)
    train_rows = read_rows(prepared / "approved/candidate.jsonl")
    evaluation_rows = read_rows(prepared / "evaluation-only/evaluation-only.jsonl")
    output.mkdir(parents=True, exist_ok=False)

    initialization = initialize_model(
        TOKENIZER_BUNDLE,
        output / "initialization",
        seed=plan["seed"],
        artifact_root=ARTIFACT_ROOT,
    )
    source_payload = torch.load(SOURCE_INITIALIZATION, map_location="cpu", weights_only=True)
    initial_payload = torch.load(output / "initialization/initialization.pt", map_location="cpu", weights_only=True)
    require_identical_initial_weights([source_payload, initial_payload], torch.equal)
    del source_payload, initial_payload

    dataset_record = {
        "kind": EXPERIMENT,
        "trainJsonlSha256": plan["packedTrain"]["trainJsonlSha256"],
        "trainTokensSha256": plan["packedTrain"]["trainTokensSha256"],
        "trainTokenCount": plan["packedTrain"]["tokenCount"],
        "trainRecords": 24,
        "validationSource": "p2-request-following-v3-validation",
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "validationTokensSha256": bundle["dataset"]["validationTokensSha256"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "validationRecords": bundle["dataset"]["validationRecords"],
        "p207EvaluationUsedForValidation": False,
    }
    source = AnswerFocusedCompleteRecordTokenCorpus(
        prepared / "dataset/train.tokens.u16le",
        dataset_jsonl=prepared / "dataset/train.jsonl",
        index_path=prepared / "dataset/train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=plan["packedTrain"]["trainJsonlSha256"],
    )
    print(json.dumps({
        "event": "p2_07_training_starting",
        "trainingRecords": len(train_rows),
        "evaluationOnlyRecords": len(evaluation_rows),
        "maximumSteps": steps,
        "maximumMinutes": minutes,
        "device": device_name,
    }), flush=True)
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
        raise ValueError("P2-07 supervised-target accounting differs from the sampler audit")
    if training["paddingTargetPositionsThisRun"] != (
            audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]):
        raise ValueError("P2-07 zero-weight target accounting differs from the sampler audit")
    checkpoint = output / "pilot/pilot-checkpoint.pt"
    if not checkpoint.is_file():
        raise ValueError("P2-07 training did not produce a scoreable checkpoint")
    scores = score(checkpoint, train_rows, evaluation_rows, settings, device_name,
                   output / "completion-score.json")
    diagnosis = _interpret(scores["training"], scores["evaluation"])
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-07 inputs changed during the run")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch initialization changed during P2-07")
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training["stepsThisRun"] == steps and not training["interrupted"],
        "trainingInterrupted": training["interrupted"],
        "freshScratchInitialization": True,
        "initialWeightsTensorwiseEqualToRecordedSeed1337": True,
        "initialization": initialization,
        "training": training,
        "device": device_name,
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
        "scoring": {"training": scores["training"], "evaluation": scores["evaluation"]},
        "suppliedConverged": scores["training"]["representationPass"] == 24,
        "diagnosis": diagnosis,
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "evaluationJsonlSha256": plan["evaluationJsonlSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "trainingObjective": plan["trainingObjective"],
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Narrow single-value selector/gap copy probe. Evaluation uses known values with one held-out wording per family and is not evidence of broad natural-language understanding.",
    }
    write_json(output / "result.json", report)
    return report


def score_completed_run(prepared: Path, output: Path, device_name: str = "cuda") -> dict:
    """Score a completed approved checkpoint after a post-training reporting failure."""
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if not output.is_dir() or not (output / "pilot/pilot-checkpoint.pt").is_file():
        raise ValueError("No completed P2-07 checkpoint exists at the requested run directory")
    if (output / "result.json").exists() or (output / "completion-score.json").exists():
        raise FileExistsError("P2-07 scoring output already exists")
    plan = verify_prepared(prepared)
    if device_name != plan["device"]:
        raise ValueError("P2-07 owner approval specifies CUDA")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded seed-1337 scratch initialization changed")

    metrics_path = output / "pilot/metrics.jsonl"
    metrics = [json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines()]
    finished = [record for record in metrics if record.get("event") == "run_finished"]
    if len(finished) != 1:
        raise ValueError("P2-07 telemetry does not contain exactly one completed training run")
    training = finished[0]
    if (training.get("stepsThisRun", 0) < 1
            or training["stepsThisRun"] > plan["maximumSteps"]
            or training.get("elapsedSeconds", float("inf")) > plan["maximumMinutes"] * 60
            or training.get("interrupted") is not False):
        raise ValueError("P2-07 checkpoint did not complete within its approved bounds")
    checkpoint_path = output / "pilot/pilot-checkpoint.pt"
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    dataset = payload.get("datasetRecord", {})
    training_settings = payload.get("trainingSettings", {})
    if (payload.get("step") != training["step"] or payload.get("seed") != plan["seed"]
            or payload.get("modelFamily") != "plex-from-scratch"
            or payload.get("tokenizerRecord", {}).get("tokenizerSha256") != plan["tokenizerSha256"]
            or dataset.get("kind") != EXPERIMENT
            or dataset.get("trainJsonlSha256") != plan["packedTrain"]["trainJsonlSha256"]
            or dataset.get("p207EvaluationUsedForValidation") is not False
            or training_settings.get("samplingPolicy", {}).get("answerObjective", {}).get("kind")
            != "answer-eos-only-complete-record-v1"
            or training_settings.get("microBatch") != plan["microBatch"]
            or training_settings.get("gradientAccumulation") != plan["gradientAccumulation"]):
        raise ValueError("P2-07 checkpoint metadata differs from approved training inputs")
    init_path = output / "initialization/initialization.pt"
    init_payload = torch.load(init_path, map_location="cpu", weights_only=True)
    source_payload = torch.load(SOURCE_INITIALIZATION, map_location="cpu", weights_only=True)
    require_identical_initial_weights([source_payload, init_payload], torch.equal)
    del source_payload, init_payload, payload

    settings = json.loads(DEV_PATH.read_text(encoding="utf-8"))
    train_rows = read_rows(prepared / "approved/candidate.jsonl")
    evaluation_rows = read_rows(prepared / "evaluation-only/evaluation-only.jsonl")
    scores = score(checkpoint_path, train_rows, evaluation_rows, settings, device_name,
                   output / "completion-score.json")
    audit = replay_sampling_audit(prepared, plan, training["stepsThisRun"])
    if (audit["supervisedTargetPositions"] != training["tokensProcessedThisRun"]
            or audit["paddingTargetPositions"] + audit["excludedPromptTargetPositions"]
            != training["paddingTargetPositionsThisRun"]):
        raise ValueError("Replayed P2-07 sampler audit differs from completed run telemetry")
    report = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "scoringComplete": True,
        "trainingReachedStepLimit": training["stepsThisRun"] == plan["maximumSteps"],
        "trainingInterrupted": False,
        "freshScratchInitialization": True,
        "initialWeightsTensorwiseEqualToRecordedSeed1337": True,
        "initialization": {
            "checkpointSha256": sha256_file(init_path),
            "referenceCheckpointSha256": SOURCE_INITIALIZATION_SHA,
            "seed": plan["seed"],
        },
        "training": training,
        "device": device_name,
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
        "scoring": {"training": scores["training"], "evaluation": scores["evaluation"]},
        "suppliedConverged": scores["training"]["representationPass"] == 24,
        "diagnosis": _interpret(scores["training"], scores["evaluation"]),
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "evaluationJsonlSha256": plan["evaluationJsonlSha256"],
        "tokenizerSha256": plan["tokenizerSha256"],
        "trainingObjective": plan["trainingObjective"],
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "noAutomaticExtension": True,
        "finalHoldoutOpened": False,
        "limitations": "Narrow single-value selector/gap copy probe. Evaluation uses known values with one held-out wording per family and is not evidence of broad natural-language understanding.",
    }
    if verify_prepared(prepared) != plan:
        raise ValueError("Prepared P2-07 inputs changed during scoring")
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch initialization changed during scoring")
    write_json(output / "result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--minutes", type=float, default=10.0)
    parser.add_argument("--score-existing-run", action="store_true",
                        help="score an already completed checkpoint without running training again")
    args = parser.parse_args()
    try:
        result = (score_completed_run(args.prepared, args.output_dir, args.device)
                  if args.score_existing_run
                  else run(args.prepared, args.output_dir, args.device, args.steps, args.minutes))
        print(json.dumps({
            "report": str(args.output_dir / "result.json"),
            "scoringComplete": result["scoringComplete"],
            "trainingReachedStepLimit": result["trainingReachedStepLimit"],
            "suppliedConverged": result["suppliedConverged"],
            "diagnosis": result["diagnosis"],
            "training": result["scoring"]["training"],
            "evaluation": result["scoring"]["evaluation"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-07-run: {exc}", file=sys.stderr)
        sys.exit(2)
