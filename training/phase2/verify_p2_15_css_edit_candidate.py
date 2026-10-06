"""Verify the complete P2-15 review-only candidate without authorizing training."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from prepare_p2_15_css_edit_candidate import (
    CANDIDATE_JSONL_SHA256,
    INPUT,
    OUT,
    P2_14_TASK_SET_SHA256,
    PENDING,
    PHASE2,
    _encoded_rows,
    _sha,
    rows,
)

EXPERIMENT = "p2-15-css-edit-candidate-v1"


def _split_digest(examples: list[dict], split: str) -> str:
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True)
        for row in examples
        if row["candidateSplit"] == split
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _record_text(row: dict) -> str:
    prefix = (
        f"Write a small CSS coding solution.\nRequest: {row['request']}\n"
        "Output contract: Return CSS rules only. Do not include HTML, Markdown fences, or explanations.\n"
        "Return code only. Do not include Markdown fences or explanations.\n"
    )
    return prefix + row["solution"]


def _expected_record_path(row: dict) -> Path:
    return (
        OUT
        / "records"
        / row["candidateSplit"]
        / row["splitGroupId"]
        / f"{row['id']}.txt"
    )


def verify() -> dict:
    examples = rows()
    if len(examples) != 36:
        raise ValueError("P2-15 deterministic candidate no longer has 36 records")

    counts = Counter(row["candidateSplit"] for row in examples)
    if counts != Counter({"train": 24, "validation": 12}):
        raise ValueError("P2-15 deterministic split is no longer 24/12")

    group_splits: dict[str, set[str]] = {}
    for row in examples:
        group_splits.setdefault(row["splitGroupId"], set()).add(row["candidateSplit"])
        if row.get("approvalStatus") != PENDING:
            raise ValueError(f"P2-15 row is no longer pending owner review: {row['id']}")
    if len(group_splits) != 12 or any(len(splits) != 1 for splits in group_splits.values()):
        raise ValueError("P2-15 semantic groups are no longer split-disjoint")

    expected_jsonl = _encoded_rows(examples)
    if _sha(expected_jsonl) != CANDIDATE_JSONL_SHA256:
        raise ValueError("P2-15 deterministic rows no longer match the pinned candidate SHA-256")
    if not INPUT.is_file() or INPUT.read_bytes() != expected_jsonl:
        raise ValueError("Saved P2-15 candidate JSONL differs from deterministic rows")

    p2_14 = PHASE2 / "drafts/p2-14-css-edit-step200-v1/task-set.json"
    if not p2_14.is_file() or _sha(p2_14.read_bytes()) != P2_14_TASK_SET_SHA256:
        raise ValueError("Pinned P2-14 development task set changed")

    review_json_path = OUT / "review.json"
    review_md_path = OUT / "REVIEW.md"
    if not review_json_path.is_file() or not review_md_path.is_file():
        raise ValueError("P2-15 review artifacts are incomplete")

    review = json.loads(review_json_path.read_text(encoding="utf-8"))
    expected_scalar = {
        "candidate": EXPERIMENT,
        "approvalStatus": PENDING,
        "records": 36,
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "trainingRowsSha256": _split_digest(examples, "train"),
        "validationRowsSha256": _split_digest(examples, "validation"),
        "developmentTaskSetSha256": P2_14_TASK_SET_SHA256,
        "staticAuthoredSolutionsPassed": 36,
        "externalSourceTextIncluded": False,
        "tokenizerFitted": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    for key, value in expected_scalar.items():
        if review.get(key) != value:
            raise ValueError(f"P2-15 review metadata mismatch: {key}")

    if review.get("recordsBySplit") != {"train": 24, "validation": 12}:
        raise ValueError("P2-15 review split counts changed")
    expected_groups = {
        name: sorted(splits) for name, splits in sorted(group_splits.items())
    }
    if review.get("semanticGroups") != expected_groups:
        raise ValueError("P2-15 review semantic-group map changed")

    proposal = review.get("proposedExperiment")
    expected_proposal = {
        "freshInitialization": True,
        "seed": 1337,
        "matchedStepZeroEvaluation": True,
        "maximumDurationMinutes": 10,
        "maximumUpdates": 100,
        "requiresSeparateOwnerApproval": True,
    }
    if proposal != expected_proposal:
        raise ValueError("P2-15 proposed experiment bounds changed")

    expected_files = {"REVIEW.md", "review.json"}
    for row in examples:
        path = _expected_record_path(row)
        relative = path.relative_to(OUT).as_posix()
        expected_files.add(relative)
        if not path.is_file():
            raise ValueError(f"Missing P2-15 generated record: {relative}")
        if path.read_bytes() != _record_text(row).encode("utf-8"):
            raise ValueError(f"P2-15 generated record changed: {relative}")

    actual_files = {
        path.relative_to(OUT).as_posix()
        for path in OUT.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        unexpected = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        raise ValueError(
            f"P2-15 review directory file set changed; unexpected={unexpected}, missing={missing}"
        )

    review_md = review_md_path.read_text(encoding="utf-8")
    required_fragments = (
        "**Status: ready for owner review; not approved for training.**",
        CANDIDATE_JSONL_SHA256,
        review["trainingRowsSha256"],
        review["validationRowsSha256"],
        P2_14_TASK_SET_SHA256,
        "Final holdout opened: **no**",
    )
    if any(fragment not in review_md for fragment in required_fragments):
        raise ValueError("P2-15 review markdown is missing pinned review facts")
    for row in examples:
        if review_md.count(f"#### {row['id']} —") != 1:
            raise ValueError(f"P2-15 review markdown row listing changed: {row['id']}")

    return {
        "verified": True,
        "candidate": EXPERIMENT,
        "approvalStatus": PENDING,
        "records": len(examples),
        "recordsBySplit": dict(counts),
        "semanticGroups": len(group_splits),
        "generatedRecordFilesVerified": len(examples),
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "trainingRowsSha256": review["trainingRowsSha256"],
        "validationRowsSha256": review["validationRowsSha256"],
        "proposedMaximumUpdates": proposal["maximumUpdates"],
        "proposedMaximumDurationMinutes": proposal["maximumDurationMinutes"],
        "trainingAuthorized": False,
        "finalHoldoutOpened": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-15-preapproval-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
