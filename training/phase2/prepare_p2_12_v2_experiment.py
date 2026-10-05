"""Freeze the exact owner-approved P2-12 v2 inputs; this module never trains."""
from __future__ import annotations

import argparse
import array
import hashlib
import json
from pathlib import Path
import shutil
import sys

from prepare_binding_candidate import ROOT, sha256_file, source_text
from prepare_compositional_experiment import (
    ARTIFACT_ROOT, DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA, pack_train,
    read_rows, write_json,
)
from prepare_p2_12_answer_start_candidate_v2 import (
    DEFAULT_OUTPUT as DRAFT, EXPERIMENT, build as build_candidate,
)
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
APPROVAL = PHASE2 / "approvals/p2-12-answer-start-transfer-v2.json"
EXPECTED = {
    "candidate": "bdffb5cf4cdca89238c4651ce9c77ed260332ef47a10e7e137a309ab865e0d03",
    "evaluation": "a81b05aa3452d9b04d9f9b4d6b1a0d0e8ebf2614c3de24c0c4083eb975629fb7",
    "reviewMarkdown": "9040f6513a7d0fd2a722813d1bf8fa9c2bc50b9c07e37c3bf0419cec2f113a77",
    "trainingRecords": 96,
    "evaluationOnlyRecords": 64,
    "promotedHistoricalEvaluationRequests": 32,
}
OBJECTIVE = "answer-eos-only-complete-record-v1"


def canonical_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def limits() -> dict:
    return {
        "maximumSteps": 100, "maximumMinutes": 10,
        "maximumTotalSteps": 100, "maximumTotalMinutes": 10,
        "seed": 1337, "microBatch": 1, "gradientAccumulation": 16,
        "device": "cuda", "automaticExtension": False,
    }


def load_inputs() -> tuple[list[dict], list[dict], dict, dict]:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8-sig"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("candidate") != EXPERIMENT
            or approval.get("scope") != "local-P2-diagnostic-training"
            or approval.get("objective") != OBJECTIVE
            or approval.get("candidateJsonlSha256") != EXPECTED["candidate"]
            or approval.get("evaluationJsonlSha256") != EXPECTED["evaluation"]
            or approval.get("reviewMarkdownSha256") != EXPECTED["reviewMarkdown"]
            or approval.get("trainingRecords") != EXPECTED["trainingRecords"]
            or approval.get("evaluationOnlyRecords") != EXPECTED["evaluationOnlyRecords"]
            or approval.get("promotedHistoricalEvaluationRequests") != EXPECTED["promotedHistoricalEvaluationRequests"]
            or approval.get("evaluationApprovedForTraining") is not False
            or approval.get("evaluationApprovedForRuntimeValidationLoss") is not False
            or approval.get("tokenizerSha256") != TOKENIZER_SHA
            or approval.get("tokenizerRefitted") is not False
            or approval.get("freshModelFromScratch") is not True
            or approval.get("finalHoldoutOpened") is not False
            or approval.get("limits") != limits()):
        raise ValueError("Exact owner-approved P2-12 v2 candidate hashes and bounds are required")

    candidate_path = DRAFT / "candidate.jsonl"
    evaluation_path = DRAFT / "evaluation-only.jsonl"
    review_path = DRAFT / "REVIEW.md"
    review_json_path = DRAFT / "review.json"
    if (canonical_sha256(candidate_path) != EXPECTED["candidate"]
            or canonical_sha256(evaluation_path) != EXPECTED["evaluation"]
            or canonical_sha256(review_path) != EXPECTED["reviewMarkdown"]):
        raise ValueError("P2-12 v2 review inputs differ from the approved hashes")
    summary = json.loads(review_json_path.read_text(encoding="utf-8"))
    if (summary.get("candidateJsonlSha256") != EXPECTED["candidate"]
            or summary.get("evaluationJsonlSha256") != EXPECTED["evaluation"]
            or summary.get("reviewMarkdownSha256") != EXPECTED["reviewMarkdown"]
            or summary.get("p211EvaluationRequestsPromotedToTraining") != 32
            or summary.get("explicitNewlineEvaluationPhrases") != 2
            or summary.get("neutralCopyEvaluationPhrases") != 2
            or summary.get("freshEvaluationRequestsDisjointFromAllP210AndP211Requests") is not True
            or summary.get("finalHoldoutOpened") is not False):
        raise ValueError("P2-12 v2 review metadata differs from the approved candidate")
    train, evaluation = read_rows(candidate_path), read_rows(evaluation_path)
    expected_train, expected_evaluation = build_candidate()
    if train != expected_train or evaluation != expected_evaluation:
        raise ValueError("P2-12 v2 rows differ from deterministic candidate generation")
    if len(train) != 96 or len(evaluation) != 64:
        raise ValueError("P2-12 v2 approved matrix counts changed")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Runtime validation settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen P2 tokenizer changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    return train, evaluation, settings, approval


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-12 v2 experiment exists; choose a fresh directory")
    train, evaluation, settings, approval = load_inputs()
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    output.mkdir(parents=True, exist_ok=False)
    (output / "approved").mkdir()
    (output / "evaluation-only").mkdir()
    shutil.copyfile(DRAFT / "candidate.jsonl", output / "approved/candidate.jsonl")
    shutil.copyfile(DRAFT / "evaluation-only.jsonl", output / "evaluation-only/evaluation-only.jsonl")
    shutil.copyfile(APPROVAL, output / "approval.json")
    packed = pack_train(train, output, tokenizer, settings["outputContracts"])
    files = {str(path.relative_to(output)).replace("\\", "/"): sha256_file(path)
             for path in output.rglob("*") if path.is_file()}
    plan = {
        "schemaVersion": 1, "experiment": EXPERIMENT, "approvalStatus": "approved",
        "trainingObjective": OBJECTIVE, "samplingPolicy": "complete-record-v1",
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "approvalSha256": canonical_sha256(APPROVAL),
        "trainingRecords": len(train), "evaluationOnlyRecords": len(evaluation),
        "promotedHistoricalEvaluationRequests": 32,
        "tokenizerSha256": TOKENIZER_SHA, "tokenizerRefitted": False,
        "freshModelFromScratch": True, "seed": approval["limits"]["seed"],
        "microBatch": approval["limits"]["microBatch"],
        "gradientAccumulation": approval["limits"]["gradientAccumulation"],
        "device": approval["limits"]["device"],
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "maximumSteps": 100, "maximumMinutes": 10,
        "maximumTotalSteps": 100, "maximumTotalMinutes": 10,
        "automaticExtension": False, "packedTrain": packed, "files": files,
        "modelTrained": False, "finalHoldoutOpened": False,
    }
    write_json(output / "experiment.json", plan)
    return plan


def verify_prepared(prepared: Path) -> dict:
    prepared = prepared.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    train, evaluation, settings, _approval = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    expected = {
        "experiment": EXPERIMENT, "approvalStatus": "approved",
        "trainingObjective": OBJECTIVE,
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "trainingRecords": 96, "evaluationOnlyRecords": 64,
        "promotedHistoricalEvaluationRequests": 32,
        "tokenizerSha256": TOKENIZER_SHA, "tokenizerRefitted": False,
        "freshModelFromScratch": True, "seed": 1337, "microBatch": 1,
        "gradientAccumulation": 16, "device": "cuda",
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "maximumSteps": 100, "maximumMinutes": 10,
        "maximumTotalSteps": 100, "maximumTotalMinutes": 10,
        "automaticExtension": False, "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(plan.get(key) != value for key, value in expected.items()):
        raise ValueError("Prepared P2-12 v2 plan differs from exact owner approval")
    if canonical_sha256(prepared / "approval.json") != canonical_sha256(APPROVAL):
        raise ValueError("Prepared P2-12 v2 approval artifact changed")
    if plan.get("approvalSha256") != canonical_sha256(APPROVAL):
        raise ValueError("Prepared P2-12 v2 approval identity changed")
    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-12 v2 file changed: {relative}")
    required = {"approval.json", "approved/candidate.jsonl",
                "evaluation-only/evaluation-only.jsonl", "dataset/train.jsonl",
                "dataset/train.index.json", "dataset/train.tokens.u16le"}
    if set(plan.get("files", {})) != required:
        raise ValueError("Prepared P2-12 v2 input file list changed")
    if read_rows(prepared / "approved/candidate.jsonl") != train:
        raise ValueError("Prepared P2-12 v2 training rows changed")
    if read_rows(prepared / "evaluation-only/evaluation-only.jsonl") != evaluation:
        raise ValueError("Prepared P2-12 v2 evaluation-only rows changed")
    expected_texts = [{"recordId": r["id"], "splitGroupId": r["splitGroupId"],
                       "sourceId": r["sourceId"],
                       "text": source_text(r, settings["outputContracts"])} for r in train]
    if read_rows(prepared / "dataset/train.jsonl") != expected_texts:
        raise ValueError("Packed P2-12 v2 text differs from approved rows")
    if plan["packedTrain"].get("trainJsonlSha256") != sha256_file(prepared / "dataset/train.jsonl"):
        raise ValueError("Packed P2-12 v2 text identity changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    packed = array.array("H")
    packed.frombytes((prepared / "dataset/train.tokens.u16le").read_bytes())
    if sys.byteorder != "little":
        packed.byteswap()
    expected_tokens = [token for row in train
                       for token in tokenizer.encode(source_text(row, settings["outputContracts"])) + [3]]
    if packed.tolist() != expected_tokens:
        raise ValueError("Packed P2-12 v2 token IDs differ from approved rows")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-12-v2-experiment-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
