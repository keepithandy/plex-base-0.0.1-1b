"""Prepare the approved three-fold P2-05 selector-gap composition diagnostic; never train."""
from __future__ import annotations

import argparse
from array import array
import copy
import json
from pathlib import Path
import shutil
import sys

from prepare_binding_candidate import ROOT, sha256_file, source_text
from prepare_compositional_binding_candidate import layout_case
from prepare_compositional_experiment import pack_train, read_rows, TOKENIZER_BUNDLE, TOKENIZER_SHA, DEV_SHA
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
ARTIFACT_ROOT = ROOT / "training/artifacts"
SOURCE_DRAFT = PHASE2 / "drafts/p2-04-compositional-layout-v1"
APPROVAL = PHASE2 / "approvals/p2-05-counterbalanced-composition-v1.json"
SOURCE_CANDIDATE_SHA = "df7a6b6f8592006c37612b2b179fb9aee278d966914136284d52a63991c8c754"
SOURCE_EVALUATION_SHA = "578c7e376301751e61112b02feb2a9651f9858efc2276b0bf5067de2e5acccff"
SELECTORS = (".actions", ".filters", ".controls")
GAPS = ("6px", "14px", "28px")
FOLD_HELDOUT = {
    "fold-a": ((".actions", "28px"), (".filters", "6px"), (".controls", "14px")),
    "fold-b": ((".actions", "6px"), (".filters", "14px"), (".controls", "28px")),
    "fold-c": ((".actions", "14px"), (".filters", "28px"), (".controls", "6px")),
}


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def pair(row: dict) -> tuple[str, str]:
    bindings = row.get("bindings")
    if not isinstance(bindings, dict):
        raise ValueError("P2-05 matrix row has no bindings")
    return bindings.get("selector"), bindings.get("gap")


def canonical_row(selector: str, gap: str, source: dict) -> dict:
    request, solution, checks = layout_case(selector, gap)
    if (source.get("language") != "css" or source.get("sourceId") != "gap-css-layout-01"
            or source.get("request") != request or source.get("solution") != solution
            or source.get("checks") != checks):
        raise ValueError(f"P2-04 source row changed for {selector} + {gap}")
    row = copy.deepcopy(source)
    row.pop("approvalStatus", None)
    row.pop("use", None)
    row["id"] = f"p2-05-layout-{SELECTORS.index(selector)}-{GAPS.index(gap)}"
    row["splitGroupId"] = "p2-05-counterbalanced-css-layout"
    row["provenance"] = "approved-p2-05-counterbalanced-matrix-from-p2-04"
    row["p205MatrixCell"] = True
    return row


def load_inputs() -> tuple[list[dict], dict, dict]:
    candidate_path = SOURCE_DRAFT / "candidate.jsonl"
    evaluation_path = SOURCE_DRAFT / "evaluation-only.jsonl"
    if (sha256_file(candidate_path) != SOURCE_CANDIDATE_SHA
            or sha256_file(evaluation_path) != SOURCE_EVALUATION_SHA):
        raise ValueError("Pinned P2-04 matrix source changed")
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("scope") != "local-P2-diagnostic-training"
            or approval.get("sourceCandidateJsonlSha256") != SOURCE_CANDIDATE_SHA
            or approval.get("sourceEvaluationJsonlSha256") != SOURCE_EVALUATION_SHA
            or approval.get("objective") != "answer-eos-only-complete-record-v1"
            or approval.get("matrixRecords") != 9
            or approval.get("trainingRecordsPerFold") != 6
            or approval.get("heldOutRecordsPerFold") != 3
            or approval.get("eachPairHeldOutExactlyOnce") is not True
            or approval.get("globalPristineHoldoutClaim") is not False):
        raise ValueError("Exact P2-05 owner approval is required")
    source_rows = read_rows(candidate_path) + read_rows(evaluation_path)
    by_pair = {}
    for row in source_rows:
        key = pair(row)
        if key in by_pair:
            raise ValueError("P2-04 matrix contains a duplicate binding pair")
        by_pair[key] = row
    expected_pairs = {(selector, gap) for selector in SELECTORS for gap in GAPS}
    if set(by_pair) != expected_pairs:
        raise ValueError("P2-04 source does not contain the complete 3x3 matrix")
    matrix = [canonical_row(selector, gap, by_pair[(selector, gap)])
              for selector in SELECTORS for gap in GAPS]
    approved_folds = approval.get("folds")
    if not isinstance(approved_folds, dict) or set(approved_folds) != set(FOLD_HELDOUT):
        raise ValueError("P2-05 approval fold list changed")
    all_heldout = []
    for name, expected in FOLD_HELDOUT.items():
        actual = tuple(tuple(item) for item in approved_folds[name].get("heldOutPairs", []))
        if actual != expected:
            raise ValueError(f"Approved {name} held-out pairs changed")
        if {selector for selector, _ in expected} != set(SELECTORS) or {gap for _, gap in expected} != set(GAPS):
            raise ValueError(f"{name} must hold out every selector and gap exactly once")
        all_heldout.extend(expected)
    if len(all_heldout) != 9 or set(all_heldout) != expected_pairs:
        raise ValueError("Every matrix pair must be held out exactly once across P2-05")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed")
    return matrix, settings, approval


def fold_rows(matrix: list[dict], fold_name: str) -> tuple[list[dict], list[dict]]:
    held_pairs = set(FOLD_HELDOUT[fold_name])
    train, heldout = [], []
    for row in matrix:
        destination = heldout if pair(row) in held_pairs else train
        copy_row = copy.deepcopy(row)
        copy_row["p205Fold"] = fold_name
        copy_row["p205FoldRole"] = "heldout" if destination is heldout else "training"
        destination.append(copy_row)
    if len(train) != 6 or len(heldout) != 3:
        raise ValueError(f"{fold_name} must contain six training and three held-out rows")
    for values, key in ((SELECTORS, "selector"), (GAPS, "gap")):
        counts = {value: sum(row["bindings"][key] == value for row in train) for value in values}
        if set(counts.values()) != {2}:
            raise ValueError(f"{fold_name} training is not balanced for {key}")
    return train, heldout


def write_rows(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return sha256_file(path)


def prepare(output: Path) -> dict:
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-05 experiment already exists; choose a fresh directory")
    matrix, settings, approval = load_inputs()
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(APPROVAL, output / "approval.json")
    matrix_sha = write_rows(output / "matrix.jsonl", matrix)
    folds = {}
    for fold_name in FOLD_HELDOUT:
        train, heldout = fold_rows(matrix, fold_name)
        fold_dir = output / fold_name
        (fold_dir / "approved").mkdir(parents=True)
        (fold_dir / "heldout").mkdir()
        train_sha = write_rows(fold_dir / "approved/candidate.jsonl", train)
        heldout_sha = write_rows(fold_dir / "heldout/evaluation-only.jsonl", heldout)
        packed = pack_train(train, fold_dir, tokenizer, settings["outputContracts"])
        folds[fold_name] = {
            "trainingRecords": 6,
            "heldOutRecords": 3,
            "trainingRowsSha256": train_sha,
            "heldOutRowsSha256": heldout_sha,
            "heldOutPairs": [list(item) for item in FOLD_HELDOUT[fold_name]],
            "packedTrain": packed,
        }
    files = {str(path.relative_to(output)).replace("\\", "/"): sha256_file(path)
             for path in output.rglob("*") if path.is_file()}
    plan = {
        "schemaVersion": 1,
        "experiment": "p2-05-counterbalanced-composition-v1",
        "approvalStatus": "approved",
        "sourceId": "gap-css-layout-01",
        "sourceCandidateJsonlSha256": SOURCE_CANDIDATE_SHA,
        "sourceEvaluationJsonlSha256": SOURCE_EVALUATION_SHA,
        "approvalSha256": sha256_file(APPROVAL),
        "matrixSha256": matrix_sha,
        "matrixRecords": 9,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "trainingObjective": "answer-eos-only-complete-record-v1",
        "samplingPolicy": "complete-record-v1",
        "runtimeValidationSource": "existing p2-request-following-v3 validation split",
        "foldLocalHeldoutOnly": True,
        "globalPristineHoldoutClaim": False,
        "folds": folds,
        "maximumStepsPerFold": approval["limits"]["maximumStepsPerFold"],
        "maximumMinutesPerFold": approval["limits"]["maximumMinutesPerFold"],
        "maximumTotalSteps": approval["limits"]["maximumTotalSteps"],
        "maximumTotalMinutes": approval["limits"]["maximumTotalMinutes"],
        "seedPerFold": approval["limits"]["seedPerFold"],
        "microBatch": approval["limits"]["microBatch"],
        "gradientAccumulation": approval["limits"]["gradientAccumulation"],
        "files": files,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    write_json(output / "experiment.json", plan)
    return plan


def verify_prepared(prepared: Path) -> dict:
    matrix, settings, approval = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    if (plan.get("experiment") != "p2-05-counterbalanced-composition-v1"
            or plan.get("approvalStatus") != "approved"
            or plan.get("matrixRecords") != 9
            or plan.get("trainingObjective") != "answer-eos-only-complete-record-v1"
            or plan.get("foldLocalHeldoutOnly") is not True
            or plan.get("globalPristineHoldoutClaim") is not False
            or plan.get("maximumStepsPerFold") != 100
            or plan.get("maximumMinutesPerFold") != 10
            or plan.get("maximumTotalSteps") != 300
            or plan.get("maximumTotalMinutes") != 30):
        raise ValueError("Prepared P2-05 plan differs from owner-approved bounds")
    if sha256_file(prepared / "approval.json") != sha256_file(APPROVAL):
        raise ValueError("Prepared P2-05 approval changed")
    for relative, digest in plan["files"].items():
        path = prepared / relative
        path.resolve().relative_to(prepared.resolve())
        if path.is_symlink() or sha256_file(path) != digest:
            raise ValueError("Prepared P2-05 input changed")
    if read_rows(prepared / "matrix.jsonl") != matrix:
        raise ValueError("Prepared P2-05 matrix changed")
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    for fold_name in FOLD_HELDOUT:
        train, heldout = fold_rows(matrix, fold_name)
        fold_dir = prepared / fold_name
        if (read_rows(fold_dir / "approved/candidate.jsonl") != train
                or read_rows(fold_dir / "heldout/evaluation-only.jsonl") != heldout):
            raise ValueError(f"Prepared {fold_name} rows changed")
        actual_texts = read_rows(fold_dir / "dataset/train.jsonl")
        expected_texts = [{"recordId": row["id"], "splitGroupId": row["splitGroupId"],
                           "sourceId": row["sourceId"], "text": source_text(row, settings["outputContracts"])}
                          for row in train]
        if actual_texts != expected_texts:
            raise ValueError(f"Prepared {fold_name} training text changed")
        packed = array("H")
        packed.frombytes((fold_dir / "dataset/train.tokens.u16le").read_bytes())
        if sys.byteorder != "little":
            packed.byteswap()
        expected_ids = [token for row in train
                        for token in tokenizer.encode(source_text(row, settings["outputContracts"])) + [3]]
        if packed.tolist() != expected_ids:
            raise ValueError(f"Prepared {fold_name} token IDs changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-05-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
