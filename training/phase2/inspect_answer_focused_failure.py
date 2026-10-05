"""Identify failed supplied bindings from a completed P2-03 answer-focused run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from prepare_binding_experiment import ROOT

DEFAULT_CANDIDATE = ROOT / "training/phase2/drafts/p2-03-binding-diversity-v1/candidate.jsonl"


def load_rows(path: Path) -> dict[str, dict]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        rows[row["id"]] = row
    return rows


def inspect(score_path: Path, candidate_path: Path = DEFAULT_CANDIDATE) -> dict:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    records = score.get("records")
    if not isinstance(records, list):
        raise ValueError("Completion score has no record-level results")
    candidate = load_rows(candidate_path)
    failures = []
    for record in records:
        if record.get("kind") != "candidate-new":
            continue
        if record.get("exact") and record.get("bindingPass"):
            continue
        row = candidate.get(record.get("id"))
        if row is None:
            raise ValueError(f"Scored candidate id is missing from approved candidate: {record.get('id')}")
        failures.append({
            "id": row["id"],
            "sourceId": row["sourceId"],
            "language": row["language"],
            "request": row["request"],
            "expected": row["solution"],
            "completion": record.get("completion", ""),
            "exact": bool(record.get("exact")),
            "bindingPass": bool(record.get("bindingPass")),
            "staticPass": bool(record.get("staticPass")),
            "syntaxPass": bool(record.get("syntaxPass")),
            "oldBindingPresent": record.get("oldBindingPresent", 0),
            "repeatedOriginalReference": record.get("repeatedOriginalReference", 0),
        })
    return {
        "score": str(score_path),
        "candidateFailures": len(failures),
        "singleFailure": len(failures) == 1,
        "recommendedSourceId": failures[0]["sourceId"] if len(failures) == 1 else None,
        "failures": failures,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, required=True,
                        help="answer-focused/completion-score.json from the completed comparison")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.score, args.candidate), indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-answer-failure: {exc}", file=sys.stderr)
        sys.exit(2)
