"""Evaluation-only request variations on six learned families; never train or execute code."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from diagnose_saved_checkpoints import (
    ROOT, load_approved, prompt_text, _check_task,
)

CANDIDATE_SHA = "555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016"
# Frozen before generation. Two independent, single-detail changes per original.
VARIATIONS = (
    ("gap-html-bidi-02", (("Kyoto", "Osaka"), ("Kyoto", "Harbor"))),
    ("gap-html-progress-01", (("35", "62"), ("100", "200"))),
    ("gap-css-logical-border-03", ((".top-edge", ".panel-edge"), ("2px", "5px"))),
    ("gap-css-layout-01", ((".toolbar", ".command-bar"), ("12px", "20px"))),
    ("gap-javascript-division-01", (("quotientTowardZero", "truncateQuotient"),
                                    ("quotientTowardZero", "divideIntegers"))),
    ("gap-javascript-array-copy-01", (("copyItems", "cloneItems"), ("copyItems", "duplicateItems"))),
)


def sha256_file(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def replace_strings(value, before, after):
    if isinstance(value, str):
        return value.replace(before, after)
    if isinstance(value, list):
        return [replace_strings(item, before, after) for item in value]
    if isinstance(value, dict):
        return {key: replace_strings(item, before, after) for key, item in value.items()}
    return value


def build_cases(rows):
    by_id = {row["id"]: row for row in rows}
    cases = []
    known_requests = {row["request"] for row in rows}
    known_solutions = {row["solution"] for row in rows}
    for source_id, changes in VARIATIONS:
        source = by_id[source_id]
        if source["candidateSplit"] != "train":
            raise ValueError("Transfer controls must come from training only")
        original = {key: copy.deepcopy(source[key]) for key in ("language", "request", "solution", "checks")}
        original.update(id=source_id + "-original", sourceId=source_id, kind="original",
                        originalSolution=source["solution"], before=None, after=None)
        cases.append(original)
        for index, (before, after) in enumerate(changes, 1):
            if before not in source["request"] or before not in source["solution"]:
                raise ValueError("Variation must change both prompt and reference")
            variant = replace_strings({key: copy.deepcopy(source[key]) for key in
                                       ("language", "request", "solution", "checks")}, before, after)
            if variant["request"] in known_requests or variant["solution"] in known_solutions:
                raise ValueError("Variation duplicates an approved corpus prompt or solution")
            variant.update(id=source_id + f"-variation-{index}", sourceId=source_id, kind="variation",
                           originalSolution=source["solution"], before=before, after=after)
            cases.append(variant)
    if len({row["request"] for row in cases}) != len(cases):
        raise ValueError("Duplicate transfer prompts")
    return cases


def check_completion(case, completion, eos, node):
    static = _check_task({"id": case["id"], "language": case["language"],
                          "difficulty": "basic", "checks": case["checks"]}, completion, node, 5.0)
    # Presence/absence is a narrow textual binding check, not semantic equivalence.
    binding = case["kind"] == "original" or (
        case["after"] in completion and case["before"] not in completion)
    return {
        "exact": completion == "\n" + case["solution"] and eos,
        "staticPass": static["passed"] and binding and eos,
        "bindingPass": binding and eos,
        "syntaxPass": static["parseStatus"] == "pass",
        "repeatedOriginalReference": case["kind"] == "variation" and
            completion == "\n" + case["originalSolution"] and eos,
        "oldBindingPresent": case["kind"] == "variation" and case["before"] in completion,
        "empty": not completion.strip(), "truncated": not eos,
    }


def summarize(records):
    groups = defaultdict(list)
    for row in records:
        groups[row["kind"]].append(row)
        groups[row["kind"] + "/" + row["language"]].append(row)
    measures = ("exact", "staticPass", "bindingPass", "syntaxPass", "repeatedOriginalReference",
                "oldBindingPresent", "empty", "truncated")
    return {key: {"count": len(rows), **{m: sum(r[m] for r in rows) for m in measures}}
            for key, rows in sorted(groups.items())}


def run(output: Path, device_name: str, prepare_only: bool = False):
    if output.exists():
        raise FileExistsError("Transfer output already exists; choose a fresh directory")
    phase2 = ROOT / "training/phase2"
    artifacts = ROOT / "training/artifacts"
    candidate = phase2 / "drafts/p2-02-request-following-v3/candidate.jsonl"
    rows, digest = load_approved(candidate, phase2 / "approvals/p2-02-request-following-v3.json")
    if digest != CANDIDATE_SHA:
        raise ValueError("Transfer plan requires the pinned approved v3 candidate")
    cases = build_cases(rows)
    settings_path = phase2 / "evaluation/p2-01b-dev-v1.json"
    settings = json.loads(settings_path.read_text())
    if sha256_file(settings_path) != "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4":
        raise ValueError("Development decoding settings changed")
    checkpoints = (
        (100, artifacts / "pilot/p2-complete-record-100step-v1/pilot-checkpoint.pt",
         "0737e617facc7ae9d8e3f1c9c6888cdcc066183d40a711f231933161de7e4e2e"),
        (200, artifacts / "pilot/p2-complete-record-200step-v2/resumed-checkpoint.pt",
         "348423a1dcb58639c1384216b67318144658d33e4e37ae48f76a121c851a692b"),
    )
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for syntax-only reference checks")
    for case in cases:
        if not check_completion(case, "\n" + case["solution"], True, node)["staticPass"]:
            raise ValueError("Transfer reference failed its checks")
        if case["kind"] == "variation" and check_completion(
                case, "\n" + case["originalSolution"], True, node)["staticPass"]:
            raise ValueError("Unchanged answer incorrectly passes a variation")
    # Freeze the reviewed cases before loading either model or generating outputs.
    output.mkdir(parents=True, exist_ok=False)
    plan = {"schemaVersion": 1, "use": "evaluation-only-never-train", "candidateSha256": digest,
            "selection": "six controls known exact at step 200; diagnostic selection bias",
            "developmentSettingsSha256": sha256_file(settings_path), "cases": cases}
    plan_path = output / "cases.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if prepare_only:
        return {"cases": str(plan_path), "casesSha256": sha256_file(plan_path),
                "referencesPassed": len(cases), "staleAnswersRejected": 12,
                "checkpointEvaluationRun": False}
    from plex_training.checkpoint import read_checkpoint
    from plex_training.completion import _completion_tokenizer, _generate_token_ids
    from plex_training.telemetry import select_device
    from plex_training.tokenizer import CODEC

    tokenizer, tokenizer_record = _completion_tokenizer(artifacts / "tokenizers/p2-request-following-v3")
    device = select_device(device_name)
    results = []
    for step, path, expected_sha in checkpoints:
        if sha256_file(path) != expected_sha:
            raise ValueError("Saved checkpoint differs from the frozen comparison")
        model, payload = read_checkpoint(path, device)
        if (payload["step"] != step or payload.get("codec") != CODEC
                or payload.get("tokenizerRecord") != tokenizer_record
                or payload.get("initializationRecord", {}).get("pretrainedCheckpointLoaded") is not False
                or payload.get("initializationRecord", {}).get("pretrainedModelWeightsLoaded") is not False):
            raise ValueError("Checkpoint does not match the scratch-trained comparison")
        records = []
        for case in cases:
            prompt = prompt_text(case, settings["outputContracts"])
            ids = tokenizer.encode(prompt)
            cap = settings["inferenceDefaults"]["maxNewTokens"][case["language"]]
            if len(ids) >= model.config.context_length:
                raise ValueError("Transfer prompt exceeds context")
            tokens, eos = _generate_token_ids(model, ids, actual_vocab=tokenizer.vocabulary_size,
                max_new_tokens=cap, temperature=0.0, seed=1337, device=device)
            completion = tokenizer.decode(tokens)
            records.append({"id": case["id"], "kind": case["kind"], "language": case["language"],
                            "completion": completion, "generatedTokens": len(tokens),
                            **check_completion(case, completion, eos, node)})
        if sha256_file(path) != expected_sha:
            raise ValueError("Checkpoint changed during evaluation")
        results.append({"step": step, "checkpointSha256": expected_sha,
                        "groups": summarize(records), "records": records})
        del model, payload
    report = {"schemaVersion": 1, "kind": "evaluation-only-transfer-diagnostic",
              "casesSha256": sha256_file(plan_path), "scriptSha256": sha256_file(Path(__file__)),
              "tokenizer": tokenizer_record, "device": str(device),
              "decoding": settings["inferenceDefaults"], "checkpoints": results,
              "limitations": "Selected learned controls; 12 variations; static checks only; no code execution, training, or final holdout."}
    encoded = json.dumps(report, indent=2) + "\n"
    if len(encoded.encode()) > 4 * 1024**2:
        raise ValueError("Transfer report exceeds size bound")
    (output / "report.json").write_text(encoded, encoding="utf-8")
    return {"report": str(output / "report.json"), "checkpoints":
            [{"step": r["step"], "groups": r["groups"]} for r in results]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    parser.add_argument("--prepare-only", action="store_true",
                        help="Validate and save evaluation cases without importing PyTorch")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output, args.device, args.prepare_only), indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"plex-transfer: {exc}", file=sys.stderr)
        sys.exit(2)
