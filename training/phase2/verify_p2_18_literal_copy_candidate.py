"""Read-only verification for the unapproved P2-18 literal copy candidate."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "training" / "phase2"
CANDIDATE = PHASE2 / "drafts" / "p2-18-literal-copy-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-18-literal-copy-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"
P2_17 = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1.jsonl"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6"
TRAIN_SHA256 = "cdb1c1cd1be27418e2a06362ba44ed5709e3a6a1ab9deaa497b1ad6f89937fce"
TIER_SHA256 = {
    "A": "be4bbfed980a3f219aec5fe84cb61ea0bcc39b2707ef0264d91a8b703e2aac56",
    "B": "902e08cfadfe9e81a0b37f7682b98ef470a12013afe994ce3a5f77346beb2d54",
    "C": "7c81ca29356ccffb2af569862937146767010a7167701c6bfe4cff636b34c29a",
    "D": "d33aeedd77fb8fda2169d1688b091ea077a7942db21998555380ba3f04fdc125",
}
P2_17_SHA256 = "2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5"
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"
PENDING = "pending-owner-review"
PROVENANCE = "codex-authored-local-p2-18-literal-copy-candidate"
LEVEL_KIND = {
    "A": "direct-copy",
    "B": "labeled-copy",
    "C": "select-literal",
    "D": "assemble-plan",
}


def _canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(_canonical_bytes(path)).hexdigest()


def _encoded(rows: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + "\n"
    ).encode("utf-8")


def _rows(path: Path = CANDIDATE) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank row at line {line_no}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"row {line_no} is not an object")
        result.append(value)
    return result


def _expected(row: dict[str, Any]) -> tuple[str, str]:
    level = row["level"]
    selector = row["selector"]
    old_value = row["oldValue"]
    new_value = row["newValue"]
    if level == "A":
        literal = selector if row["literalType"] == "selector" else new_value
        return (
            f"COPY EXACTLY:\n{literal}\nReturn the copied text only.",
            literal,
        )
    if level == "B":
        label = row["literalType"]
        literal = selector if label == "selector" else new_value
        return (
            f"INPUT:\n{label}={literal}\n\n"
            f"Return exactly one line in the form {label}=<copied literal>.",
            f"{label}={literal}",
        )
    if level == "C":
        field = row["targetField"]
        values = {"selector": selector, "old": old_value, "new": new_value}
        return (
            f"INPUT:\nselector={selector}\nold={old_value}\nnew={new_value}\n\n"
            f"COPY FIELD: {field}\nReturn the exact literal value only.",
            values[field],
        )
    if level == "D":
        return (
            f"INPUT:\nselector={selector}\nold={old_value}\nnew={new_value}\n\n"
            "Return exactly these three fields in this order, copying every literal exactly:\n"
            "selector=...\nold=...\nnew=...",
            f"selector={selector}\nold={old_value}\nnew={new_value}",
        )
    raise ValueError(f"unsupported level: {level!r}")


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(value)))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _other_requests() -> dict[str, list[dict[str, Any]]]:
    return {
        "P2-17": _rows(P2_17),
        "P2-14": json.loads(P2_14.read_text(encoding="utf-8"))["tasks"],
        "P2-01b": json.loads(P2_01B.read_text(encoding="utf-8"))["tasks"],
    }


def _prompt_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for name, tasks in _other_requests().items():
        exact = {_norm(task["request"]) for task in tasks}
        maximum = 0.0
        pair = None
        for row in rows:
            left = _words(row["request"])
            for task in tasks:
                score = _jaccard(left, _words(task["request"]))
                if score > maximum:
                    maximum = score
                    pair = [row["id"], task["id"]]
        report[name] = {
            "exactRequestOverlap": sum(_norm(row["request"]) in exact for row in rows),
            "maxWordJaccard": round(maximum, 6),
            "maxPair": pair,
        }
    return report


def verify() -> dict[str, Any]:
    if _sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-18 candidate SHA-256 changed")
    if _sha(P2_17) != P2_17_SHA256:
        raise ValueError("P2-17 candidate identity changed")
    if _sha(P2_14) != P2_14_SHA256 or _sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("development task-set identity changed")

    rows = _rows()
    if len(rows) != 216 or _encoded(rows) != _canonical_bytes(CANDIDATE):
        raise ValueError("P2-18 count or canonical JSONL encoding changed")
    if len({row.get("id") for row in rows}) != 216:
        raise ValueError("P2-18 IDs must be unique")
    if len({row.get("request") for row in rows}) != 216:
        raise ValueError("P2-18 requests must be unique")

    train = [row for row in rows if row.get("candidateSplit") == "train"]
    evaluation = [row for row in rows if row.get("candidateSplit") == "evaluation"]
    if len(train) != 144 or len(evaluation) != 72:
        raise ValueError("P2-18 must retain the 144/72 partition")
    if Counter(row.get("level") for row in train) != Counter({"A":36,"B":36,"C":36,"D":36}):
        raise ValueError("P2-18 training level balance changed")
    if Counter(row.get("evaluationTier") for row in evaluation) != Counter({"A":18,"B":18,"C":18,"D":18}):
        raise ValueError("P2-18 evaluation tier balance changed")

    required = {
        "schemaVersion","approvalStatus","candidateSplit","evaluationTier","id","level",
        "taskKind","literalType","targetField","selector","oldValue","newValue",
        "request","solution","checks","provenance",
    }
    authored_passes = 0
    for row in rows:
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        if (
            row["schemaVersion"] != 1
            or row["approvalStatus"] != PENDING
            or row["provenance"] != PROVENANCE
            or row["checks"] != []
            or row["taskKind"] != LEVEL_KIND.get(row["level"])
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")
        if row["candidateSplit"] == "train" and row["evaluationTier"] is not None:
            raise ValueError(f"{row['id']} training row has an evaluation tier")
        if row["candidateSplit"] == "evaluation" and row["evaluationTier"] != row["level"]:
            raise ValueError(f"{row['id']} evaluation tier differs from its level")
        if not isinstance(row["selector"], str) or not re.fullmatch(r"(?:\.unit-|#node-)[0-9a-f]{8}", row["selector"]):
            raise ValueError(f"{row['id']} selector grammar changed")
        if not isinstance(row["oldValue"], str) or not isinstance(row["newValue"], str):
            raise ValueError(f"{row['id']} literal values must be strings")
        request, solution = _expected(row)
        if row["request"] != request or row["solution"] != solution:
            raise ValueError(f"{row['id']} request/solution differs from deterministic metadata")
        authored_passes += 1

    train_a = [row for row in train if row["level"] == "A"]
    train_b = [row for row in train if row["level"] == "B"]
    eval_a = [row for row in evaluation if row["level"] == "A"]
    eval_b = [row for row in evaluation if row["level"] == "B"]
    if Counter(row["literalType"] for row in train_a) != Counter({"selector":18,"value":18}):
        raise ValueError("P2-18 Level A training literal balance changed")
    if Counter(row["literalType"] for row in train_b) != Counter({"selector":18,"value":18}):
        raise ValueError("P2-18 Level B training literal balance changed")
    if Counter(row["literalType"] for row in eval_a) != Counter({"selector":9,"value":9}):
        raise ValueError("P2-18 Tier A literal balance changed")
    if Counter(row["literalType"] for row in eval_b) != Counter({"selector":9,"value":9}):
        raise ValueError("P2-18 Tier B literal balance changed")
    if Counter(row["targetField"] for row in train if row["level"] == "C") != Counter({"selector":12,"old":12,"new":12}):
        raise ValueError("P2-18 Level C training target balance changed")
    if Counter(row["targetField"] for row in evaluation if row["level"] == "C") != Counter({"selector":6,"old":6,"new":6}):
        raise ValueError("P2-18 Tier C target balance changed")

    if hashlib.sha256(_encoded(train)).hexdigest() != TRAIN_SHA256:
        raise ValueError("P2-18 training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [row for row in evaluation if row["evaluationTier"] == tier]
        if hashlib.sha256(_encoded(subset)).hexdigest() != digest:
            raise ValueError(f"P2-18 Tier {tier} SHA-256 changed")

    train_selectors = {row["selector"] for row in train}
    eval_selectors = {row["selector"] for row in evaluation}
    train_values = {value for row in train for value in (row["oldValue"], row["newValue"])}
    eval_values = {value for row in evaluation for value in (row["oldValue"], row["newValue"])}
    if train_selectors & eval_selectors:
        raise ValueError("P2-18 evaluation selector leaked from training")
    if train_values & eval_values:
        raise ValueError("P2-18 evaluation literal value leaked from training")
    if any(
        marker in selector.casefold()
        for selector in train_selectors | eval_selectors
        for marker in ("train","eval","tier")
    ):
        raise ValueError("P2-18 selector encodes split/tier identity")

    prompt_audit = _prompt_audit(rows)
    if any(entry["exactRequestOverlap"] for entry in prompt_audit.values()):
        raise ValueError("P2-18 duplicates a prior candidate/development request")
    if any(entry["maxWordJaccard"] >= 0.50 for entry in prompt_audit.values()):
        raise ValueError("P2-18 request is unexpectedly close to a prior task")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    fixed = {
        "candidate":"p2-18-literal-copy-candidate-v1",
        "approvalStatus":PENDING,
        "records":216,
        "trainingRecords":144,
        "evaluationRecords":72,
        "trainingLevelCounts":{"A":36,"B":36,"C":36,"D":36},
        "evaluationTierCounts":{"A":18,"B":18,"C":18,"D":18},
        "candidateJsonlSha256":CANDIDATE_SHA256,
        "trainingRowsSha256":TRAIN_SHA256,
        "tierSha256":TIER_SHA256,
        "trainEvaluationSelectorOverlap":0,
        "trainEvaluationLiteralValueOverlap":0,
        "evaluationLiteralsAreHeldOut":True,
        "tokenizerFitted":False,
        "checkpointInitialized":False,
        "trainingRunCreated":False,
        "modelTrained":False,
        "finalHoldoutOpened":False,
        "developmentPromptAudit":prompt_audit,
    }
    if any(review.get(key) != value for key, value in fixed.items()):
        raise ValueError("P2-18 review metadata differs from the pinned candidate")

    forbidden = {"tokenizer","initialization","checkpoint","run","pilot"}
    for path in REVIEW_DIR.rglob("*"):
        if any(part.casefold() in forbidden for part in path.parts):
            raise ValueError(f"P2-18 review directory contains a forbidden artifact: {path}")

    return {
        "verified":True,
        "approvalStatus":PENDING,
        "records":216,
        "trainingRecords":144,
        "evaluationRecords":72,
        "trainingLevelCounts":{"A":36,"B":36,"C":36,"D":36},
        "evaluationTierCounts":{"A":18,"B":18,"C":18,"D":18},
        "authoredSolutionsPassed":authored_passes,
        "trainEvaluationSelectorOverlap":0,
        "trainEvaluationLiteralValueOverlap":0,
        "developmentPromptAudit":prompt_audit,
        "candidateJsonlSha256":CANDIDATE_SHA256,
        "tokenizerFitted":False,
        "checkpointInitialized":False,
        "trainingRunCreated":False,
        "modelTrained":False,
        "finalHoldoutOpened":False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-p2-18-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
