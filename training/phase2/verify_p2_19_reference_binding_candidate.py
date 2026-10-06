"""Read-only verification for the unapproved P2-19 reference-binding candidate."""
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
CANDIDATE = PHASE2 / "drafts" / "p2-19-reference-binding-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-19-reference-binding-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"
P2_18 = PHASE2 / "drafts" / "p2-18-literal-copy-candidate-v1.jsonl"
P2_17 = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1.jsonl"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "e96d6b8edd2a756a03d285f1081491232df7f79886a47d6ab02efcdb29211fa1"
TRAIN_SHA256 = "dac085cc16c2e9e0bdaa653f3ec0494e2a7954a2cb18c1454af50a80f35dc9a0"
TIER_SHA256 = {
    "A": "2779755050d81d14742e2f73f1976564c5bcd9b49e11e0f5520d3f89c93fbbbd",
    "B": "7d21a52304179e82969d3156704c24e738fcfb74c4b99422ae23e2beaa15be52",
    "C": "b73c569942d68246065e9dbb21e96eb57450b074ad88e009096ffe0c692312eb",
    "D": "e61b677fbaff95f93a8362067f521577382a50820d62bfae9c7921508c29acb6",
}
P2_18_SHA256 = "9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6"
P2_17_SHA256 = "2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5"
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"

PENDING = "pending-owner-review"
PROVENANCE = "codex-authored-local-p2-19-reference-binding-candidate"
REFERENCES = ("R0", "R1", "R2", "R3", "R4", "R5")
FIELDS = ("selector", "old", "new")
LEVEL_KIND = {
    "A": "literal-reference-lookup",
    "B": "explicit-reference-binding",
    "C": "semantic-reference-binding",
    "D": "assemble-reference-plan",
}
SEMANTIC_PHRASES = {
    "selector": (
        "Return the reference for the target selector.",
        "Return the reference for the selector being edited.",
        "Return the reference for the element selector.",
    ),
    "old": (
        "Return the reference for the current value.",
        "Return the reference for the value being replaced.",
        "Return the reference for the existing value.",
    ),
    "new": (
        "Return the reference for the replacement value.",
        "Return the reference for the requested new value.",
        "Return the reference for the value to write.",
    ),
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


def _reference_table(row: dict[str, Any]) -> str:
    mapping = {
        row["selectorRef"]: row["selector"],
        row["oldRef"]: row["oldValue"],
        row["newRef"]: row["newValue"],
    }
    return "\n".join(f"{reference}={mapping[reference]}" for reference in sorted(mapping))


def _bindings(row: dict[str, Any]) -> str:
    return (
        f"selector_ref={row['selectorRef']}\n"
        f"old_ref={row['oldRef']}\n"
        f"new_ref={row['newRef']}"
    )


def _target_reference(row: dict[str, Any]) -> str:
    return {
        "selector": row["selectorRef"],
        "old": row["oldRef"],
        "new": row["newRef"],
    }[row["targetField"]]


def _target_literal(row: dict[str, Any]) -> str:
    return {
        "selector": row["selector"],
        "old": row["oldValue"],
        "new": row["newValue"],
    }[row["targetField"]]


def _row_index(row: dict[str, Any]) -> int:
    match = re.fullmatch(r"p2-19-[te]-[abcd]-(\d{3})", row["id"])
    if match is None:
        raise ValueError(f"{row.get('id')} has an invalid ID")
    return int(match.group(1)) - 1


def _expected(row: dict[str, Any]) -> tuple[str, str]:
    level = row["level"]
    table = _reference_table(row)
    if level == "A":
        return (
            f"REFERENCE TABLE:\n{table}\n\n"
            f"TARGET LITERAL:\n{_target_literal(row)}\n\n"
            "Return only the reference name whose literal matches the target.",
            _target_reference(row),
        )
    if level == "B":
        return (
            f"REFERENCE TABLE:\n{table}\n\n"
            f"BINDINGS:\n{_bindings(row)}\n\n"
            f"COPY FIELD: {row['targetField']}_ref\n"
            "Return the exact reference name only.",
            _target_reference(row),
        )
    if level == "C":
        phrase = SEMANTIC_PHRASES[row["targetField"]][_row_index(row) % 3]
        return (
            f"REFERENCE TABLE:\n{table}\n\n"
            f"BINDINGS:\n{_bindings(row)}\n\n"
            f"REQUEST: {phrase}\n"
            "Return the exact reference name only.",
            _target_reference(row),
        )
    if level == "D":
        return (
            f"REFERENCE TABLE:\n{table}\n\n"
            f"BINDINGS:\n{_bindings(row)}\n\n"
            "Return exactly these three reference fields in this order:\n"
            "selector_ref=...\nold_ref=...\nnew_ref=...",
            _bindings(row),
        )
    raise ValueError(f"unsupported P2-19 level: {level!r}")


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(value)))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _prior_requests() -> dict[str, list[dict[str, Any]]]:
    return {
        "P2-18": _rows(P2_18),
        "P2-17": _rows(P2_17),
        "P2-14": json.loads(P2_14.read_text(encoding="utf-8"))["tasks"],
        "P2-01b": json.loads(P2_01B.read_text(encoding="utf-8"))["tasks"],
    }


def _prompt_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for name, tasks in _prior_requests().items():
        exact = {_norm(task["request"]) for task in tasks}
        maximum = 0.0
        pair: list[str] | None = None
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


def _role_reference_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        role: dict(Counter(row[f"{role}Ref"] for row in rows))
        for role in FIELDS
    }


def _target_reference_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(_target_reference(row) for row in rows))


def verify() -> dict[str, Any]:
    if _sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-19 candidate SHA-256 changed")
    if _sha(P2_18) != P2_18_SHA256 or _sha(P2_17) != P2_17_SHA256:
        raise ValueError("prior Phase-2 candidate identity changed")
    if _sha(P2_14) != P2_14_SHA256 or _sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("development task-set identity changed")

    rows = _rows()
    if len(rows) != 216 or _encoded(rows) != _canonical_bytes(CANDIDATE):
        raise ValueError("P2-19 count or canonical JSONL encoding changed")
    if len({row.get("id") for row in rows}) != 216:
        raise ValueError("P2-19 IDs must be unique")
    if len({row.get("request") for row in rows}) != 216:
        raise ValueError("P2-19 requests must be unique")

    train = [row for row in rows if row.get("candidateSplit") == "train"]
    evaluation = [row for row in rows if row.get("candidateSplit") == "evaluation"]
    if len(train) != 144 or len(evaluation) != 72:
        raise ValueError("P2-19 must retain the 144/72 partition")
    if Counter(row.get("level") for row in train) != Counter({"A":36,"B":36,"C":36,"D":36}):
        raise ValueError("P2-19 training level balance changed")
    if Counter(row.get("evaluationTier") for row in evaluation) != Counter({"A":18,"B":18,"C":18,"D":18}):
        raise ValueError("P2-19 evaluation tier balance changed")

    required = {
        "schemaVersion","approvalStatus","candidateSplit","evaluationTier","id","level",
        "taskKind","targetField","selector","oldValue","newValue","selectorRef","oldRef",
        "newRef","referenceVocabulary","request","solution","checks","provenance",
    }
    for row in rows:
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        if (
            row["schemaVersion"] != 1
            or row["approvalStatus"] != PENDING
            or row["provenance"] != PROVENANCE
            or row["checks"] != []
            or row["taskKind"] != LEVEL_KIND.get(row["level"])
            or row["referenceVocabulary"] != list(REFERENCES)
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")
        if row["candidateSplit"] == "train" and row["evaluationTier"] is not None:
            raise ValueError(f"{row['id']} training row has an evaluation tier")
        if row["candidateSplit"] == "evaluation" and row["evaluationTier"] != row["level"]:
            raise ValueError(f"{row['id']} evaluation tier differs from its level")
        if row["level"] == "D":
            if row["targetField"] is not None:
                raise ValueError(f"{row['id']} Level D unexpectedly has a target field")
        elif row["targetField"] not in FIELDS:
            raise ValueError(f"{row['id']} has an invalid target field")
        if not re.fullmatch(r"(?:\.unit-|#node-)[0-9a-f]{8}", row["selector"]):
            raise ValueError(f"{row['id']} selector grammar changed")
        value_pattern = r"\d+\.\d{3}(?:px|rem|%|ms|vh|ch)"
        if not re.fullmatch(value_pattern, row["oldValue"]) or not re.fullmatch(value_pattern, row["newValue"]):
            raise ValueError(f"{row['id']} value grammar changed")
        refs = (row["selectorRef"], row["oldRef"], row["newRef"])
        if len(set(refs)) != 3 or any(ref not in REFERENCES for ref in refs):
            raise ValueError(f"{row['id']} must use three distinct known references")
        request, solution = _expected(row)
        if row["request"] != request or row["solution"] != solution:
            raise ValueError(f"{row['id']} request/solution differs from deterministic metadata")

    if hashlib.sha256(_encoded(train)).hexdigest() != TRAIN_SHA256:
        raise ValueError("P2-19 training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [row for row in evaluation if row["evaluationTier"] == tier]
        if hashlib.sha256(_encoded(subset)).hexdigest() != digest:
            raise ValueError(f"P2-19 Tier {tier} SHA-256 changed")

    train_selectors = {row["selector"] for row in train}
    eval_selectors = {row["selector"] for row in evaluation}
    train_values = {value for row in train for value in (row["oldValue"], row["newValue"])}
    eval_values = {value for row in evaluation for value in (row["oldValue"], row["newValue"])}
    if train_selectors & eval_selectors:
        raise ValueError("P2-19 evaluation selector leaked from training")
    if train_values & eval_values:
        raise ValueError("P2-19 evaluation literal value leaked from training")
    if len(train_values | eval_values) != 432:
        raise ValueError("P2-19 raw values are not globally unique")
    if any(
        marker in selector.casefold()
        for selector in train_selectors | eval_selectors
        for marker in ("train","eval","tier")
    ):
        raise ValueError("P2-19 selector encodes split/tier identity")

    expected_train_roles = {reference: 6 for reference in REFERENCES}
    expected_eval_roles = {reference: 3 for reference in REFERENCES}
    expected_train_targets = Counter({"selector":12,"old":12,"new":12})
    expected_eval_targets = Counter({"selector":6,"old":6,"new":6})
    expected_train_target_refs = {reference: 6 for reference in REFERENCES}
    expected_eval_target_refs = {reference: 3 for reference in REFERENCES}

    for level in ("A", "B", "C", "D"):
        train_level = [row for row in train if row["level"] == level]
        eval_level = [row for row in evaluation if row["level"] == level]
        if _role_reference_counts(train_level) != {
            role: expected_train_roles for role in FIELDS
        }:
            raise ValueError(f"P2-19 Level {level} training role/reference balance changed")
        if _role_reference_counts(eval_level) != {
            role: expected_eval_roles for role in FIELDS
        }:
            raise ValueError(f"P2-19 Tier {level} evaluation role/reference balance changed")
        if level != "D":
            if Counter(row["targetField"] for row in train_level) != expected_train_targets:
                raise ValueError(f"P2-19 Level {level} training target-field balance changed")
            if Counter(row["targetField"] for row in eval_level) != expected_eval_targets:
                raise ValueError(f"P2-19 Tier {level} evaluation target-field balance changed")
            if _target_reference_counts(train_level) != expected_train_target_refs:
                raise ValueError(f"P2-19 Level {level} training target-reference balance changed")
            if _target_reference_counts(eval_level) != expected_eval_target_refs:
                raise ValueError(f"P2-19 Tier {level} evaluation target-reference balance changed")

    c_train = [row for row in train if row["level"] == "C"]
    c_eval = [row for row in evaluation if row["level"] == "C"]
    for field in FIELDS:
        train_phrases = Counter(
            SEMANTIC_PHRASES[field][_row_index(row) % 3]
            for row in c_train
            if row["targetField"] == field
        )
        eval_phrases = Counter(
            SEMANTIC_PHRASES[field][_row_index(row) % 3]
            for row in c_eval
            if row["targetField"] == field
        )
        if set(train_phrases) != set(SEMANTIC_PHRASES[field]) or set(eval_phrases) != set(SEMANTIC_PHRASES[field]):
            raise ValueError(f"P2-19 Level C semantic phrase coverage changed for {field}")

    prompt_audit = _prompt_audit(rows)
    if any(entry["exactRequestOverlap"] for entry in prompt_audit.values()):
        raise ValueError("P2-19 duplicates a prior candidate/development request")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    fixed = {
        "schemaVersion":1,
        "candidate":"p2-19-reference-binding-candidate-v1",
        "approvalStatus":PENDING,
        "records":216,
        "trainingRecords":144,
        "evaluationRecords":72,
        "trainingLevelCounts":{"A":36,"B":36,"C":36,"D":36},
        "evaluationTierCounts":{"A":18,"B":18,"C":18,"D":18},
        "candidateJsonlSha256":CANDIDATE_SHA256,
        "trainingRowsSha256":TRAIN_SHA256,
        "tierSha256":TIER_SHA256,
        "referenceVocabulary":list(REFERENCES),
        "referenceVocabularySharedAcrossSplits":True,
        "trainEvaluationSelectorOverlap":0,
        "trainEvaluationLiteralValueOverlap":0,
        "evaluationRawLiteralsAreHeldOut":True,
        "roleReferenceAssignmentsBalanced":True,
        "targetReferenceAssignmentsBalanced":True,
        "levelA":"raw-literal-to-reference lookup",
        "levelB":"explicit field-to-reference selection after deterministic prebinding",
        "levelC":"semantic role-to-reference selection after deterministic prebinding",
        "levelD":"three-field reference-plan assembly",
        "tokenizerFitted":False,
        "checkpointInitialized":False,
        "trainingRunCreated":False,
        "modelTrained":False,
        "finalHoldoutOpened":False,
    }
    if any(review.get(key) != value for key, value in fixed.items()):
        raise ValueError("P2-19 review metadata differs from the pinned candidate")

    forbidden = {"tokenizer","initialization","checkpoint","run","pilot"}
    for path in REVIEW_DIR.rglob("*"):
        if any(part.casefold() in forbidden for part in path.parts):
            raise ValueError(f"P2-19 review directory contains a forbidden artifact: {path}")

    return {
        "verified":True,
        "approvalStatus":PENDING,
        "records":216,
        "trainingRecords":144,
        "evaluationRecords":72,
        "trainingLevelCounts":{"A":36,"B":36,"C":36,"D":36},
        "evaluationTierCounts":{"A":18,"B":18,"C":18,"D":18},
        "referenceVocabulary":list(REFERENCES),
        "authoredSolutionsPassed":216,
        "trainEvaluationSelectorOverlap":0,
        "trainEvaluationLiteralValueOverlap":0,
        "roleReferenceAssignmentsBalanced":True,
        "targetReferenceAssignmentsBalanced":True,
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
        print(f"plex-p2-19-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
