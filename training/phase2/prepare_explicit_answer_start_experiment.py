"""Freeze exact-owner-approved P2-10 inputs for one bounded diagnostic run."""
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
from prepare_explicit_answer_start_candidate import (
    DEFAULT_OUTPUT as DRAFT, EXPERIMENT, build as build_candidate,
    validate as validate_candidate,
)
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
APPROVAL = PHASE2 / "approvals/p2-10-explicit-answer-start-v1.json"
EXPECTED = {
    "candidate": "ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8",
    "evaluation": "632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9",
    "reviewMarkdown": "9f2e8f16c31861e5ddd8ad1ab1214c77a7a0e67c0020f34b0bdcf0f947026999",
    "trainingRecords": 64,
    "evaluationOnlyRecords": 16,
}


def canonical_text_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _limits() -> dict:
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
            or approval.get("objective") != "answer-eos-only-complete-record-v1"
            or approval.get("candidateJsonlSha256") != EXPECTED["candidate"]
            or approval.get("evaluationJsonlSha256") != EXPECTED["evaluation"]
            or approval.get("reviewMarkdownSha256") != EXPECTED["reviewMarkdown"]
            or approval.get("trainingRecords") != EXPECTED["trainingRecords"]
            or approval.get("evaluationOnlyRecords") != EXPECTED["evaluationOnlyRecords"]
            or approval.get("evaluationApprovedForTraining") is not False
            or approval.get("evaluationApprovedForRuntimeValidationLoss") is not False
            or approval.get("tokenizerSha256") != TOKENIZER_SHA
            or approval.get("tokenizerRefitted") is not False
            or approval.get("freshModelFromScratch") is not True
            or approval.get("finalHoldoutOpened") is not False
            or approval.get("limits") != _limits()):
        raise ValueError("Exact owner-approved P2-10 candidate and bounds are required")
    candidate_path, evaluation_path = DRAFT / "candidate.jsonl", DRAFT / "evaluation-only.jsonl"
    review_path = DRAFT / "REVIEW.md"
    if (canonical_text_sha256(candidate_path) != EXPECTED["candidate"]
            or canonical_text_sha256(evaluation_path) != EXPECTED["evaluation"]
            or canonical_text_sha256(review_path) != EXPECTED["reviewMarkdown"]):
        raise ValueError("P2-10 reviewed inputs differ from approved hashes")
    train, evaluation = read_rows(candidate_path), read_rows(evaluation_path)
    expected_train, expected_eval, _ = build_candidate()
    validate_candidate(train, evaluation)
    if train != expected_train or evaluation != expected_eval:
        raise ValueError("P2-10 rows differ from deterministic candidate generation")
    if len(train) != EXPECTED["trainingRecords"] or len(evaluation) != EXPECTED["evaluationOnlyRecords"]:
        raise ValueError("P2-10 counts differ from owner-approved counts")
    if sha256_file(PHASE2 / "evaluation/p2-01b-dev-v1.json") != DEV_SHA:
        raise ValueError("Runtime validation settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen P2 tokenizer changed")
    settings = json.loads((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    return train, evaluation, settings, approval


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-10 experiment exists; choose a fresh directory")
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
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "samplingPolicy": "complete-record-v1",
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "approvalSha256": canonical_text_sha256(APPROVAL),
        "trainingRecords": len(train), "evaluationOnlyRecords": len(evaluation),
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
    train, evaluation, settings, _ = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    expected = {
        "experiment": EXPERIMENT, "approvalStatus": "approved",
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "trainingRecords": 64, "evaluationOnlyRecords": 16,
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
        raise ValueError("Prepared P2-10 plan differs from exact owner approval")
    if canonical_text_sha256(prepared / "approval.json") != canonical_text_sha256(APPROVAL):
        raise ValueError("Prepared P2-10 approval artifact changed")
    if plan.get("approvalSha256") != canonical_text_sha256(APPROVAL):
        raise ValueError("Prepared P2-10 approval identity changed")
    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-10 file changed: {relative}")
    required = {"approval.json", "approved/candidate.jsonl",
                "evaluation-only/evaluation-only.jsonl", "dataset/train.jsonl",
                "dataset/train.index.json", "dataset/train.tokens.u16le"}
    if set(plan.get("files", {})) != required:
        raise ValueError("Prepared P2-10 input file list changed")
    if read_rows(prepared / "approved/candidate.jsonl") != train:
        raise ValueError("Prepared P2-10 training rows changed")
    if read_rows(prepared / "evaluation-only/evaluation-only.jsonl") != evaluation:
        raise ValueError("Prepared P2-10 evaluation-only rows changed")
    expected_texts = [{"recordId": r["id"], "splitGroupId": r["splitGroupId"],
                       "sourceId": r["sourceId"],
                       "text": source_text(r, settings["outputContracts"])} for r in train]
    if read_rows(prepared / "dataset/train.jsonl") != expected_texts:
        raise ValueError("Packed P2-10 text differs from approved rows")
    if plan["packedTrain"].get("trainJsonlSha256") != sha256_file(prepared / "dataset/train.jsonl"):
        raise ValueError("Packed P2-10 text identity changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    packed = array.array("H")
    packed.frombytes((prepared / "dataset/train.tokens.u16le").read_bytes())
    if sys.byteorder != "little":
        packed.byteswap()
    expected_tokens = [t for row in train
                       for t in tokenizer.encode(source_text(row, settings["outputContracts"])) + [3]]
    if packed.tolist() != expected_tokens:
        raise ValueError("Packed P2-10 tokens differ from approved text")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-10-experiment-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
