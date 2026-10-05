"""Run the approved two-arm binding diagnostic; capped at 100 updates/ten minutes per arm."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import shutil
import sys

from prepare_binding_experiment import ARTIFACT_ROOT, ROOT, verify_prepared, load_inputs, write_json
from prepare_binding_candidate import sha256_file, prompt_text, source_text
from diagnose_transfer import check_completion, summarize

SOURCE_INITIALIZATION = ARTIFACT_ROOT / "initializations/p2-request-following-step-zero-v3/initialization.pt"
SOURCE_INITIALIZATION_SHA = "d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5"


def validate_bounds(steps, minutes):
    if type(steps) is not int or not 1 <= steps <= 100:
        raise ValueError("Each arm requires 1–100 optimizer updates")
    if not math.isfinite(minutes) or not 0 < minutes <= 10:
        raise ValueError("Each arm is capped at ten minutes")


def require_identical_initial_weights(payloads, equal):
    reference = payloads[0]
    for payload in payloads:
        if (payload.get("step") != 0 or payload.get("seed") != 1337
                or payload.get("modelFamily") != "plex-from-scratch"
                or payload.get("initializationRecord", {}).get("pretrainedCheckpointLoaded") is not False
                or payload.get("initializationRecord", {}).get("pretrainedModelWeightsLoaded") is not False
                or payload.get("modelConfig") != reference.get("modelConfig")
                or payload.get("codec") != reference.get("codec")
                or payload.get("optimizerStateDict", {}).get("state") != {}):
            raise ValueError("Comparison requires fresh matching scratch initializations")
        state = payload["modelStateDict"]
        if state.keys() != reference["modelStateDict"].keys() or any(
                not equal(reference["modelStateDict"][key], tensor) for key, tensor in state.items()):
            raise ValueError("Initial parameter tensors differ; no comparison training may start")


def replay_exposure(rows, steps, tokenizer, contracts):
    rng = random.Random(1337)
    operation_counts = dict.fromkeys((r["sourceId"] for r in rows), 0)
    record_counts = dict.fromkeys((r["id"] for r in rows), 0)
    targets = 0
    lengths = {r["id"]: len(tokenizer.encode(source_text(r, contracts))) for r in rows}
    for _ in range(steps * 16):
        row = rng.choice(rows)
        record_counts[row["id"]] += 1
        operation_counts[row["sourceId"]] += 1
        targets += lengths[row["id"]]  # EOS adds one token, next-token targets subtract one.
    return {"operationSelections": operation_counts, "recordSelections": record_counts, "realTargets": targets}


def score_cases(checkpoint, bundle, cases, settings, output, device_name):
    from plex_training.checkpoint import read_checkpoint
    from plex_training.completion import _completion_tokenizer, _generate_token_ids
    from plex_training.telemetry import select_device
    device = select_device(device_name)
    tokenizer, tokenizer_record = _completion_tokenizer(bundle)
    model, payload = read_checkpoint(checkpoint, device)
    if payload.get("tokenizerRecord") != tokenizer_record:
        raise ValueError("Completion bundle does not match saved checkpoint")
    records = []
    for group, case in cases:
        ids = tokenizer.encode(prompt_text(case, settings["outputContracts"]))
        if len(ids) >= model.config.context_length:
            raise ValueError("Diagnostic prompt exceeds model context")
        tokens, eos = _generate_token_ids(model, ids, actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=settings["inferenceDefaults"]["maxNewTokens"][case["language"]],
            temperature=0.0, seed=1337, device=device)
        text = tokenizer.decode(tokens)
        records.append({"id": case["id"], "kind": group, "language": case["language"],
                        "completion": text, **check_completion(case, text, eos, shutil.which("node"))})
    report = {"checkpointSha256": sha256_file(checkpoint), "groups": summarize(records), "records": records,
              "scoreMeaning": "Exact/static/binding measures only; generated code is never executed."}
    write_json(output, report)
    return report["groups"]


def run(prepared, output, device_name="cuda", steps=100, minutes=10):
    validate_bounds(steps, minutes)
    prepared, output = prepared.resolve(), output.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output == prepared or prepared in output.parents or output in prepared.parents:
        raise ValueError("Run output must be separate from prepared inputs")
    if output.exists():
        raise FileExistsError("Comparison output exists; choose a fresh path")
    plan = verify_prepared(prepared)
    train, evaluation, settings, _ = load_inputs()
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Recorded scratch step-zero source changed")
    # Load the runtime and verify both standard pilot bundles before writing any run output.
    import torch
    from plex_training.initialization import initialize_model
    from plex_training.pilot import inspect_pilot_bundle, run_pilot
    from plex_training.telemetry import select_device
    from plex_training.task_run import generate_development_responses
    from plex_training.benchmark import evaluate_files
    from plex_training.tokenizer import PlexTokenizer
    select_device(device_name)
    for arm in ("original-only", "varied"):
        inspect_pilot_bundle(prepared / arm / "tokenizer")
    output.mkdir(parents=True, exist_ok=False)
    initializations = {}
    for arm in ("original-only", "varied"):
        result = initialize_model(prepared / arm / "tokenizer", output / arm / "initialization",
                                  seed=1337, artifact_root=ARTIFACT_ROOT)
        initializations[arm] = result
    paths = [SOURCE_INITIALIZATION] + [output / arm / "initialization/initialization.pt"
                                      for arm in ("original-only", "varied")]
    payloads = [torch.load(path, map_location="cpu", weights_only=True) for path in paths]
    require_identical_initial_weights(payloads, torch.equal)
    del payloads
    # Arm bundle/checkpoint metadata differs because data differs; parameter tensors are identical.
    arms = {}
    for arm in ("original-only", "varied"):
        print(json.dumps({"event": "arm_starting", "arm": arm, "maximumSteps": steps,
                          "maximumMinutes": minutes}), flush=True)
        pilot = run_pilot(bundle_dir=prepared / arm / "tokenizer",
            dataset_dir=prepared / arm / "dataset",
            initialization=output / arm / "initialization/initialization.pt",
            output_dir=output / arm / "pilot", artifact_root=ARTIFACT_ROOT,
            minutes=minutes, steps=steps, device_name=device_name,
            sampling_policy="complete-record-v1", answer_weight=1)
        rows = [r for r in train if r["kind"] == "original"] if arm == "original-only" else train
        exposure = replay_exposure(rows, pilot["training"]["stepsThisRun"],
                                  PlexTokenizer.load(prepared / arm / "tokenizer"), settings["outputContracts"])
        if exposure["realTargets"] != pilot["training"]["tokensProcessedThisRun"]:
            raise ValueError("Actual training targets differ from sampler replay")
        arms[arm] = {"training": pilot, "exposure": exposure, "initialization": initializations[arm]}
        if pilot["training"]["stepsThisRun"] != steps or pilot["training"]["interrupted"]:
            report = {"comparisonComplete": False, "reason": "An arm stopped before the requested updates",
                      "arms": arms, "noAutomaticExtension": True}
            write_json(output / "comparison.json", report)
            return report
    reserved = json.loads((ARTIFACT_ROOT / "diagnostics/p2-transfer-v1/cases.json").read_text(encoding="utf-8"))["cases"]
    cases = [("candidate-original" if r["kind"] == "original" else "candidate-new", r) for r in train]
    cases += [("reserved-transfer", r) for r in reserved if r["kind"] == "variation"]
    cases += [("new-transfer", r) for r in evaluation]
    for arm in ("original-only", "varied"):
        checkpoint, bundle = output / arm / "pilot/pilot-checkpoint.pt", prepared / arm / "tokenizer"
        arms[arm]["completionGroups"] = score_cases(checkpoint, bundle, cases, settings,
                                                    output / arm / "completion-score.json", device_name)
        dev_output = output / arm / "development"
        generate_development_responses(task_set_path=ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json",
            checkpoint_path=checkpoint, bundle_dir=bundle, output_dir=dev_output,
            artifact_root=ARTIFACT_ROOT, device_name=device_name)
        score = evaluate_files(ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json", dev_output / "responses.jsonl")
        write_json(dev_output / "score.json", score)
        arms[arm]["development"] = {key: score[key] for key in
                                   ("passed", "tasks", "assertionsPassed", "assertionsTotal", "truncatedOutputs")}
    verify_prepared(prepared)
    if sha256_file(SOURCE_INITIALIZATION) != SOURCE_INITIALIZATION_SHA:
        raise ValueError("Original scratch checkpoint changed during comparison")
    report = {"schemaVersion": 1, "comparisonComplete": True, "experiment": plan["experiment"],
              "initialWeightsTensorwiseEqual": True, "sourceInitializationUnchanged": True,
              "preparedManifestSha256": sha256_file(prepared / "experiment.json"),
              "stepsPerArm": steps, "minutesCapPerArm": minutes, "arms": arms,
              "limits": "Selected six-operation diagnostic; same-family transfer; static checks only; no final holdout."}
    write_json(output / "comparison.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=ARTIFACT_ROOT / "experiments/p2-binding-v1")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda", "cpu", "auto"), default="cuda")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--minutes", type=float, default=10)
    args = parser.parse_args()
    try:
        report = run(args.prepared, args.output_dir, args.device, args.steps, args.minutes)
        print(json.dumps({"report": str(args.output_dir / "comparison.json"),
                          "comparisonComplete": report["comparisonComplete"],
                          "arms": {arm: {"step": result["training"]["training"]["step"],
                              "completionGroups": result.get("completionGroups"), "development": result.get("development")}
                                   for arm, result in report["arms"].items()}}, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"plex-binding: {exc}", file=sys.stderr)
        sys.exit(2)
