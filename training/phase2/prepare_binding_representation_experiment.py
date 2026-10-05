"""Freeze the approved P2-06 representation ladder into three isolated experiment inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_binding_representation_probe import LEVELS, build, validate
from prepare_compositional_experiment import (
    ARTIFACT_ROOT,
    DEV_SHA,
    TOKENIZER_BUNDLE,
    TOKENIZER_SHA,
    pack_train,
    read_rows,
    write_json,
)
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DRAFT = PHASE2 / "drafts/p2-06-binding-representation-v1"
APPROVAL = PHASE2 / "approvals/p2-06-binding-representation-v1.json"
EXPECTED = {
    "single-copy": {
        "candidate": "13452867b30a38b9ffc3e42ef440d3ac560c3103d5d479d014525eae10a12727",
        "evaluation": "9cf9777c431de134f880eb152d84794af9f848e69f25a36420c605bcc6a144c8",
        "train": 6,
        "eval": 6,
    },
    "dual-binding": {
        "candidate": "856f20637a3bd42e0b6838964503a3aaf74a86af3a0d464128194f9ab3c6aabb",
        "evaluation": "e3afa59441365fd2a88089704755f5b9fbb9b27f88804416616272283c5d5399",
        "train": 6,
        "eval": 3,
    },
    "css-composition": {
        "candidate": "a84de00032d543a4b2bc9e9d67ef0bea5ef2cc94b080ea862f37179253b1ec6b",
        "evaluation": "969ca23edf91ff9175e9ac502395a5aa850b541c3392843e20aa82b38eb56dee",
        "train": 6,
        "eval": 3,
    },
}


def load_inputs() -> tuple[dict, dict, dict]:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("scope") != "local-P2-diagnostic-training"
            or approval.get("objective") != "answer-eos-only-complete-record-v1"
            or approval.get("freshModelPerLevel") is not True
            or approval.get("referenceTokenizerRefitted") is not False
            or approval.get("finalHoldoutOpened") is not False):
        raise ValueError("Exact P2-06 owner approval is required")
    approved_levels = approval.get("levels")
    if not isinstance(approved_levels, dict) or set(approved_levels) != set(LEVELS):
        raise ValueError("P2-06 approval level list changed")

    deterministic = build()
    validate(deterministic)
    loaded = {}
    for level in LEVELS:
        expected = EXPECTED[level]
        candidate = DRAFT / level / "candidate.jsonl"
        evaluation = DRAFT / level / "evaluation-only.jsonl"
        approved = approved_levels[level]
        if (approved.get("candidateJsonlSha256") != expected["candidate"]
                or approved.get("evaluationJsonlSha256") != expected["evaluation"]
                or approved.get("trainingRecords") != expected["train"]
                or approved.get("evaluationOnlyRecords") != expected["eval"]
                or approved.get("evaluationApprovedForTraining") is not False):
            raise ValueError(f"{level} approval identity changed")
        if sha256_file(candidate) != expected["candidate"] or sha256_file(evaluation) != expected["evaluation"]:
            raise ValueError(f"{level} draft differs from the approved hashes")
        train_rows, eval_rows = read_rows(candidate), read_rows(evaluation)
        if train_rows != deterministic[level]["train"] or eval_rows != deterministic[level]["evaluation"]:
            raise ValueError(f"{level} rows differ from the deterministic reviewed probe")
        loaded[level] = {"train": train_rows, "evaluation": eval_rows}

    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen reference tokenizer changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    return loaded, settings, approval


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-06 experiment already exists; choose a fresh directory")
    levels, settings, approval = load_inputs()
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(APPROVAL, output / "approval.json")
    prepared_levels = {}
    for level in LEVELS:
        root = output / level
        (root / "approved").mkdir(parents=True)
        (root / "heldout").mkdir()
        shutil.copyfile(DRAFT / level / "candidate.jsonl", root / "approved/candidate.jsonl")
        shutil.copyfile(DRAFT / level / "evaluation-only.jsonl", root / "heldout/evaluation-only.jsonl")
        packed = pack_train(levels[level]["train"], root, tokenizer, settings["outputContracts"])
        prepared_levels[level] = {
            "trainingRecords": len(levels[level]["train"]),
            "evaluationOnlyRecords": len(levels[level]["evaluation"]),
            "candidateJsonlSha256": EXPECTED[level]["candidate"],
            "evaluationJsonlSha256": EXPECTED[level]["evaluation"],
            "packedTrain": packed,
        }
    files = {str(path.relative_to(output)).replace("\\", "/"): sha256_file(path)
             for path in output.rglob("*") if path.is_file()}
    limits = approval["limits"]
    plan = {
        "schemaVersion": 1,
        "experiment": "p2-06-binding-representation-v1",
        "approvalStatus": "approved",
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "samplingPolicy": "complete-record-v1",
        "freshModelPerLevel": True,
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "levels": prepared_levels,
        "maximumStepsPerLevel": limits["maximumStepsPerLevel"],
        "maximumMinutesPerLevel": limits["maximumMinutesPerLevel"],
        "maximumTotalSteps": limits["maximumTotalSteps"],
        "maximumTotalMinutes": limits["maximumTotalMinutes"],
        "seedPerLevel": limits["seedPerLevel"],
        "microBatch": limits["microBatch"],
        "gradientAccumulation": limits["gradientAccumulation"],
        "files": files,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    write_json(output / "experiment.json", plan)
    return plan


def verify_prepared(prepared: Path) -> dict:
    levels, settings, _ = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    if (plan.get("experiment") != "p2-06-binding-representation-v1"
            or plan.get("approvalStatus") != "approved"
            or plan.get("trainingObjective") != "answer-eos-only-complete-record-v1"
            or plan.get("freshModelPerLevel") is not True
            or plan.get("evaluationUsedForTraining") is not False
            or plan.get("evaluationUsedForRuntimeValidationLoss") is not False
            or plan.get("maximumStepsPerLevel") != 100
            or plan.get("maximumMinutesPerLevel") != 10
            or plan.get("maximumTotalSteps") != 300
            or plan.get("maximumTotalMinutes") != 30):
        raise ValueError("Prepared P2-06 plan differs from owner-approved bounds")
    if sha256_file(prepared / "approval.json") != sha256_file(APPROVAL):
        raise ValueError("Prepared P2-06 approval changed")
    for relative, digest in plan["files"].items():
        path = prepared / relative
        path.resolve().relative_to(prepared.resolve())
        if path.is_symlink() or sha256_file(path) != digest:
            raise ValueError("Prepared P2-06 input changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    for level in LEVELS:
        root = prepared / level
        if read_rows(root / "approved/candidate.jsonl") != levels[level]["train"]:
            raise ValueError(f"Prepared {level} training rows changed")
        if read_rows(root / "heldout/evaluation-only.jsonl") != levels[level]["evaluation"]:
            raise ValueError(f"Prepared {level} evaluation rows changed")
        expected_texts = []
        from prepare_binding_candidate import source_text
        for row in levels[level]["train"]:
            expected_texts.append({
                "recordId": row["id"],
                "splitGroupId": row["splitGroupId"],
                "sourceId": row["sourceId"],
                "text": source_text(row, settings["outputContracts"]),
            })
        if read_rows(root / "dataset/train.jsonl") != expected_texts:
            raise ValueError(f"Prepared {level} training text changed")
        # Constructing the verified sampler later rechecks exact token IDs and the index.
        if plan["levels"][level]["packedTrain"]["trainJsonlSha256"] != sha256_file(root / "dataset/train.jsonl"):
            raise ValueError(f"Prepared {level} packed text identity changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-06-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
