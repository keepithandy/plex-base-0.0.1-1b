"""Freeze the approved six-record P2-04 corpus; never train or open the final holdout."""
from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import shutil
import sys

from prepare_binding_candidate import ROOT, sha256_file, source_text
from prepare_compositional_binding_candidate import build, validate
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
ARTIFACT_ROOT = ROOT / "training/artifacts"
DRAFT = PHASE2 / "drafts/p2-04-compositional-layout-v1"
APPROVAL = PHASE2 / "approvals/p2-04-compositional-binding-probe-v1.json"
TOKENIZER_BUNDLE = ARTIFACT_ROOT / "tokenizers/p2-request-following-v3"
SOURCE_ID = "gap-css-layout-01"
CANDIDATE_SHA = "df7a6b6f8592006c37612b2b179fb9aee278d966914136284d52a63991c8c754"
EVALUATION_SHA = "578c7e376301751e61112b02feb2a9651f9858efc2276b0bf5067de2e5acccff"
TOKENIZER_SHA = "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573"
DEV_SHA = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def load_inputs() -> tuple[list[dict], list[dict], dict, dict]:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("scope") != "local-P2-diagnostic-training"
            or approval.get("sourceId") != SOURCE_ID
            or approval.get("candidateJsonlSha256") != CANDIDATE_SHA
            or approval.get("evaluationJsonlSha256") != EVALUATION_SHA
            or approval.get("records") != 6
            or approval.get("evaluationOnlyRecords") != 3
            or approval.get("evaluationApprovedForTraining") is not False
            or approval.get("objective") != "answer-eos-only-complete-record-v1"):
        raise ValueError("Exact P2-04 owner approval is required")
    candidate = DRAFT / "candidate.jsonl"
    heldout = DRAFT / "evaluation-only.jsonl"
    if sha256_file(candidate) != CANDIDATE_SHA or sha256_file(heldout) != EVALUATION_SHA:
        raise ValueError("Approved P2-04 candidate or held-out set changed")
    train, evaluation = read_rows(candidate), read_rows(heldout)
    expected_train, expected_evaluation, design = build(SOURCE_ID)
    if train != expected_train or evaluation != expected_evaluation:
        raise ValueError("P2-04 rows differ from the approved deterministic matrix")
    validate(train, evaluation, design)
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed")
    return train, evaluation, settings, approval


def pack_train(rows: list[dict], output: Path, tokenizer: PlexTokenizer, contracts: dict) -> dict:
    dataset = output / "dataset"
    dataset.mkdir(parents=True)
    packed = array("H")
    index, texts = [], []
    for row in rows:
        text = source_text(row, contracts)
        ids = tokenizer.encode(text)
        if tokenizer.decode(ids) != text or len(ids) + 1 > 512:
            raise ValueError("Approved P2-04 record failed roundtrip/context validation")
        ids.append(3)
        index.append({"recordId": row["id"], "startToken": len(packed), "tokenCount": len(ids)})
        packed.extend(ids)
        texts.append({"recordId": row["id"], "splitGroupId": row["splitGroupId"],
                      "sourceId": row["sourceId"], "text": text})
    text_path = dataset / "train.jsonl"
    text_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in texts), encoding="utf-8")
    write_json(dataset / "train.index.json", index)
    if sys.byteorder != "little":
        packed.byteswap()
    token_path = dataset / "train.tokens.u16le"
    token_path.write_bytes(packed.tobytes())
    return {
        "records": len(rows),
        "tokenCount": len(packed),
        "trainJsonlSha256": sha256_file(text_path),
        "trainIndexSha256": sha256_file(dataset / "train.index.json"),
        "trainTokensSha256": sha256_file(token_path),
    }


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-04 experiment already exists; choose a fresh directory")
    train, evaluation, settings, approval = load_inputs()
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    output.mkdir(parents=True, exist_ok=False)
    (output / "approved").mkdir()
    (output / "heldout").mkdir()
    shutil.copyfile(DRAFT / "candidate.jsonl", output / "approved/candidate.jsonl")
    shutil.copyfile(DRAFT / "evaluation-only.jsonl", output / "heldout/evaluation-only.jsonl")
    shutil.copyfile(APPROVAL, output / "approval.json")
    packed = pack_train(train, output, tokenizer, settings["outputContracts"])
    files = {str(path.relative_to(output)).replace("\\", "/"): sha256_file(path)
             for path in output.rglob("*") if path.is_file()}
    plan = {
        "schemaVersion": 1,
        "experiment": "p2-04-compositional-binding-answer-focused-v1",
        "approvalStatus": "approved",
        "sourceId": SOURCE_ID,
        "candidateJsonlSha256": CANDIDATE_SHA,
        "evaluationJsonlSha256": EVALUATION_SHA,
        "approvalSha256": sha256_file(APPROVAL),
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "trainingRecords": 6,
        "heldOutRecords": 3,
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "samplingPolicy": "complete-record-v1",
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "heldOutUsedForTraining": False,
        "heldOutUsedForRuntimeValidationLoss": False,
        "maximumSteps": approval["limits"]["maximumSteps"],
        "maximumMinutes": approval["limits"]["maximumMinutes"],
        "seed": approval["limits"]["seed"],
        "microBatch": approval["limits"]["microBatch"],
        "gradientAccumulation": approval["limits"]["gradientAccumulation"],
        "packedTrain": packed,
        "files": files,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    write_json(output / "experiment.json", plan)
    return plan


def verify_prepared(prepared: Path) -> dict:
    train, evaluation, settings, _ = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    if (plan.get("candidateJsonlSha256") != CANDIDATE_SHA
            or plan.get("evaluationJsonlSha256") != EVALUATION_SHA
            or plan.get("trainingRecords") != 6 or plan.get("heldOutRecords") != 3
            or plan.get("trainingObjective") != "answer-eos-only-complete-record-v1"
            or plan.get("heldOutUsedForTraining") is not False
            or plan.get("heldOutUsedForRuntimeValidationLoss") is not False
            or plan.get("maximumSteps") != 100 or plan.get("maximumMinutes") != 10):
        raise ValueError("Prepared P2-04 plan differs from the approved bounds")
    for relative, digest in plan["files"].items():
        path = prepared / relative
        path.resolve().relative_to(prepared.resolve())
        if path.is_symlink() or sha256_file(path) != digest:
            raise ValueError("Prepared P2-04 input changed")
    if (sha256_file(prepared / "approved/candidate.jsonl") != CANDIDATE_SHA
            or sha256_file(prepared / "heldout/evaluation-only.jsonl") != EVALUATION_SHA):
        raise ValueError("Frozen P2-04 rows changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    actual_texts = read_rows(prepared / "dataset/train.jsonl")
    expected_texts = [{"recordId": row["id"], "splitGroupId": row["splitGroupId"],
                       "sourceId": row["sourceId"], "text": source_text(row, settings["outputContracts"])}
                      for row in train]
    if actual_texts != expected_texts:
        raise ValueError("Prepared P2-04 training text differs from approved rows")
    packed = array("H")
    packed.frombytes((prepared / "dataset/train.tokens.u16le").read_bytes())
    if sys.byteorder != "little":
        packed.byteswap()
    expected_ids = [token for row in train
                    for token in tokenizer.encode(source_text(row, settings["outputContracts"])) + [3]]
    if packed.tolist() != expected_ids:
        raise ValueError("Prepared P2-04 token IDs differ from approved text")
    frozen_eval = read_rows(prepared / "heldout/evaluation-only.jsonl")
    if frozen_eval != evaluation:
        raise ValueError("Prepared held-out recombinations differ from the frozen evaluation set")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-04-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
