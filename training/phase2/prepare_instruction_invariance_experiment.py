"""Freeze the explicitly approved P2-07 candidate into immutable run inputs."""
from __future__ import annotations

import argparse
import array
import hashlib
import json
from pathlib import Path
import shutil
import sys

from prepare_binding_candidate import ROOT, sha256_file, source_text
from prepare_compositional_experiment import ARTIFACT_ROOT, DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA, pack_train, read_rows, write_json
from prepare_instruction_invariance_probe import build, validate
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DRAFT = PHASE2 / "drafts/p2-07-instruction-invariance-v1"
APPROVAL = PHASE2 / "approvals/p2-07-instruction-invariance-v1.json"
EXPECTED = {
    "candidate": "ed0bee7c2c7f99ffaa7c349ba4e644d8c26d33266976fbe3fb8e96af1095245f",
    "evaluation": "01a861a3343c58f68f269fc9dc4fbf1f7bf77ce7e6ba0764e85d752b7f706414",
    "reviewMarkdown": "38123e30add9938c6fb45e54b6daf249216f2ef1d5d870dce64f1d07a0a1bef5",
    "trainingRecords": 24,
    "evaluationOnlyRecords": 6,
}


def canonical_text_sha256(path: Path) -> str:
    """Hash UTF-8 text with Git-independent LF endings for reviewed identities."""
    normalized = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def load_inputs() -> tuple[list[dict], list[dict], dict, dict]:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("approvedBy") != "repository-owner"
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
            or approval.get("finalHoldoutOpened") is not False):
        raise ValueError("Exact owner-approved P2-07 candidate and scope are required")
    limits = approval.get("limits", {})
    if limits != {
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "maximumTotalSteps": 100,
        "maximumTotalMinutes": 10,
        "seed": 1337,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "automaticExtension": False,
    }:
        raise ValueError("P2-07 approval bounds changed")
    candidate_path, evaluation_path = DRAFT / "candidate.jsonl", DRAFT / "evaluation-only.jsonl"
    review_path = DRAFT / "REVIEW.md"
    if (canonical_text_sha256(candidate_path) != EXPECTED["candidate"]
            or canonical_text_sha256(evaluation_path) != EXPECTED["evaluation"]
            or canonical_text_sha256(review_path) != EXPECTED["reviewMarkdown"]):
        raise ValueError("P2-07 review candidate differs from its approved hashes")
    train, evaluation = read_rows(candidate_path), read_rows(evaluation_path)
    expected_train, expected_evaluation = build()
    validate(train, evaluation)
    if train != expected_train or evaluation != expected_evaluation:
        raise ValueError("P2-07 reviewed rows differ from deterministic candidate generation")
    if len(train) != EXPECTED["trainingRecords"] or len(evaluation) != EXPECTED["evaluationOnlyRecords"]:
        raise ValueError("P2-07 row counts differ from owner-approved counts")

    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Runtime validation output-contract settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen P2 tokenizer changed; refusing experiment preparation")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    return train, evaluation, settings, approval


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-07 experiment exists; choose a fresh directory")
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
    limits = approval["limits"]
    plan = {
        "schemaVersion": 1,
        "experiment": "p2-07-instruction-invariance-v1",
        "approvalStatus": "approved",
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "samplingPolicy": "complete-record-v1",
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "approvalSha256": canonical_text_sha256(APPROVAL),
        "trainingRecords": 24,
        "evaluationOnlyRecords": 6,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "freshModelFromScratch": True,
        "seed": limits["seed"],
        "microBatch": limits["microBatch"],
        "gradientAccumulation": limits["gradientAccumulation"],
        "device": limits["device"],
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "maximumSteps": limits["maximumSteps"],
        "maximumMinutes": limits["maximumMinutes"],
        "maximumTotalSteps": limits["maximumTotalSteps"],
        "maximumTotalMinutes": limits["maximumTotalMinutes"],
        "automaticExtension": False,
        "packedTrain": packed,
        "files": files,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    write_json(output / "experiment.json", plan)
    return plan


def verify_prepared(prepared: Path) -> dict:
    prepared = prepared.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    train, evaluation, settings, _ = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    expected_plan = {
        "experiment": "p2-07-instruction-invariance-v1",
        "approvalStatus": "approved",
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "candidateJsonlSha256": EXPECTED["candidate"],
        "evaluationJsonlSha256": EXPECTED["evaluation"],
        "reviewMarkdownSha256": EXPECTED["reviewMarkdown"],
        "trainingRecords": 24,
        "evaluationOnlyRecords": 6,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "freshModelFromScratch": True,
        "seed": 1337,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "maximumTotalSteps": 100,
        "maximumTotalMinutes": 10,
        "automaticExtension": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(plan.get(key) != value for key, value in expected_plan.items()):
        raise ValueError("Prepared P2-07 plan differs from exact owner approval")
    if canonical_text_sha256(prepared / "approval.json") != canonical_text_sha256(APPROVAL):
        raise ValueError("Prepared P2-07 approval artifact changed")
    if plan.get("approvalSha256") != canonical_text_sha256(APPROVAL):
        raise ValueError("Prepared P2-07 approval identity changed")
    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-07 file changed: {relative}")
    required_files = {
        "approval.json", "approved/candidate.jsonl", "evaluation-only/evaluation-only.jsonl",
        "dataset/train.jsonl", "dataset/train.index.json", "dataset/train.tokens.u16le",
    }
    if set(plan.get("files", {})) != required_files:
        raise ValueError("Prepared P2-07 input file list changed")
    if read_rows(prepared / "approved/candidate.jsonl") != train:
        raise ValueError("Prepared P2-07 training rows changed")
    if read_rows(prepared / "evaluation-only/evaluation-only.jsonl") != evaluation:
        raise ValueError("Prepared P2-07 evaluation-only rows changed")
    expected_texts = [{
        "recordId": row["id"],
        "splitGroupId": row["splitGroupId"],
        "sourceId": row["sourceId"],
        "text": source_text(row, settings["outputContracts"]),
    } for row in train]
    if read_rows(prepared / "dataset/train.jsonl") != expected_texts:
        raise ValueError("Prepared P2-07 training text differs from approved rows")
    if plan["packedTrain"].get("trainJsonlSha256") != sha256_file(prepared / "dataset/train.jsonl"):
        raise ValueError("Prepared P2-07 packed text identity changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    packed = array.array("H")
    packed.frombytes((prepared / "dataset/train.tokens.u16le").read_bytes())
    if sys.byteorder != "little":
        packed.byteswap()
    expected_tokens = [token for row in train
                       for token in tokenizer.encode(source_text(row, settings["outputContracts"])) + [3]]
    if packed.tolist() != expected_tokens:
        raise ValueError("Prepared P2-07 packed training token IDs changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-07-experiment-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
