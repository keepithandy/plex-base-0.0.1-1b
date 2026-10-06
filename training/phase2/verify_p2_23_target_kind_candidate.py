"""Read-only verification for the unapproved P2-23 target-kind candidate."""
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
CANDIDATE = PHASE2 / "drafts" / "p2-23-target-kind-classification-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-23-target-kind-classification-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"

P2_22C = PHASE2 / "evaluation" / "p2-22c-presence-transition-diagnostic-v1.jsonl"
P2_22 = PHASE2 / "drafts" / "p2-22-edit-intent-classification-candidate-v1.jsonl"
P2_21 = PHASE2 / "drafts" / "p2-21-semantic-role-generalization-candidate-v1.jsonl"
P2_20 = PHASE2 / "drafts" / "p2-20-role-decomposition-candidate-v1.jsonl"
P2_19 = PHASE2 / "drafts" / "p2-19-reference-binding-candidate-v1.jsonl"
P2_18 = PHASE2 / "drafts" / "p2-18-literal-copy-candidate-v1.jsonl"
P2_17 = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1.jsonl"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08"
TRAIN_SHA256 = "f51cf7808a8b37a9fe60513401117efd81d0c28c10fe1a0ab154dc5724af45e7"
TIER_SHA256 = {
    "A": "6157b1e41f98a9e2b30a660deae8ae712a7a910fe1d991f0653c8918e00ce3d6",
    "B": "1d194209d6813a4ff58876ee2103194985fa973eb925992ae1b45599d67678f8",
    "C": "bf1a195e2bbbd0b0325cc1de31fdb7a1d817045abdbda07d107082500129a01a",
}

P2_22C_SHA256 = "4d445110d7688e2c9e3d1ba83eb9597eb3320550b71ac9324bf970f6bc1fa479"
P2_22_SHA256 = "592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0"
P2_21_SHA256 = "8206798467f74bda9867c0179495b535eade3849ca1d8a5d3147de00f27e5584"
P2_20_SHA256 = "8d7c54ceed8a0c90a437626e504e2ba39582f0ca5c57c243db5c564e2c02985d"
P2_19_SHA256 = "e96d6b8edd2a756a03d285f1081491232df7f79886a47d6ab02efcdb29211fa1"
P2_18_SHA256 = "9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6"
P2_17_SHA256 = "2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5"
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"

PENDING = "pending-owner-review"
PROVENANCE = "codex-authored-local-p2-23-target-kind-classification-candidate"
TARGET_KINDS = (
    "CSS_SELECTOR",
    "CSS_PROPERTY",
    "HTML_ELEMENT",
    "HTML_ATTRIBUTE",
    "JS_IDENTIFIER",
    "JS_PROPERTY",
)
LEVEL_KIND = {
    "A": "direct-target-kind-paraphrase",
    "B": "minimal-contrast-target-kind",
    "C": "repository-style-target-kind",
}
SEMANTIC_FAMILY = {
    "A": "direct-target-kind-paraphrase",
    "B": "minimal-target-kind-contrast",
    "C": "repository-style-target-kind",
}
TARGET_KIND_DEFINITIONS = {
    "CSS_SELECTOR": "stylesheet rule matcher",
    "CSS_PROPERTY": "stylesheet declaration field name",
    "HTML_ELEMENT": "markup tag or node type",
    "HTML_ATTRIBUTE": "named field attached to a markup element",
    "JS_IDENTIFIER": "declaration-level JavaScript symbol name",
    "JS_PROPERTY": "JavaScript object/member key",
}
PROMPT_AUDIT = {
    "P2-22c": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.264151,
        "maxPair": ["p2-23-e-b-007", "p2-22c-e-c-001"],
    },
    "P2-22": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.375,
        "maxPair": ["p2-23-t-a-036", "p2-22-t-a-048"],
    },
    "P2-21": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.433333,
        "maxPair": ["p2-23-t-a-007", "p2-21-t-a-035"],
    },
    "P2-20": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.222222,
        "maxPair": ["p2-23-e-a-008", "p2-20-t-a-048"],
    },
    "P2-19": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.156863,
        "maxPair": ["p2-23-e-c-023", "p2-19-t-c-001"],
    },
    "P2-18": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.151515,
        "maxPair": ["p2-23-e-a-008", "p2-18-copy-038"],
    },
    "P2-17": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.131148,
        "maxPair": ["p2-23-t-b-011", "p2-17-bind-123"],
    },
    "P2-14": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.118644,
        "maxPair": ["p2-23-t-c-026", "p2-14-css-edit-gap"],
    },
    "P2-01b": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.128205,
        "maxPair": ["p2-23-t-a-004", "p2dev-css-08-sticky-header"],
    },
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


def _rows(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank row at line {line_no}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"row {line_no} is not an object")
        result.append(value)
    return result


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(value)))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _prior_requests() -> dict[str, list[dict[str, Any]]]:
    return {
        "P2-22c": _rows(P2_22C),
        "P2-22": _rows(P2_22),
        "P2-21": _rows(P2_21),
        "P2-20": _rows(P2_20),
        "P2-19": _rows(P2_19),
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
            "exactRequestOverlap": sum(
                _norm(row["request"]) in exact for row in rows
            ),
            "maxWordJaccard": round(maximum, 6),
            "maxPair": pair,
        }
    return report


def _context(row: dict[str, Any]) -> str | None:
    if row["level"] == "A":
        return None
    marker = "\nQUESTION:" if row["level"] == "B" else "\nREQUEST:"
    if marker not in row["request"]:
        raise ValueError(f"{row['id']} has no context/query boundary")
    return row["request"].split(marker, 1)[0]


def _same_target_near_duplicates(
    train: list[dict[str, Any]], evaluation: list[dict[str, Any]]
) -> list[tuple[str, str, float]]:
    matches: list[tuple[str, str, float]] = []
    for eval_row in evaluation:
        left = _words(eval_row["request"])
        for train_row in train:
            if (
                train_row["level"] != eval_row["level"]
                or train_row["targetKind"] != eval_row["targetKind"]
            ):
                continue
            score = _jaccard(left, _words(train_row["request"]))
            if score >= 0.65:
                matches.append((eval_row["id"], train_row["id"], round(score, 6)))
    return matches


def verify() -> dict[str, Any]:
    identities = {
        CANDIDATE: CANDIDATE_SHA256,
        P2_22C: P2_22C_SHA256,
        P2_22: P2_22_SHA256,
        P2_21: P2_21_SHA256,
        P2_20: P2_20_SHA256,
        P2_19: P2_19_SHA256,
        P2_18: P2_18_SHA256,
        P2_17: P2_17_SHA256,
        P2_14: P2_14_SHA256,
        P2_01B: P2_01B_SHA256,
    }
    for path, expected in identities.items():
        if _sha(path) != expected:
            raise ValueError(f"Phase-2 source identity changed: {path}")

    rows = _rows(CANDIDATE)
    if len(rows) != 216 or _encoded(rows) != _canonical_bytes(CANDIDATE):
        raise ValueError("P2-23 count or canonical JSONL encoding changed")
    if len({row.get("id") for row in rows}) != 216:
        raise ValueError("P2-23 IDs must be unique")
    if len({row.get("request") for row in rows}) != 216:
        raise ValueError("P2-23 requests must be unique")

    train = [row for row in rows if row.get("candidateSplit") == "train"]
    evaluation = [
        row for row in rows if row.get("candidateSplit") == "evaluation"
    ]
    if len(train) != 144 or len(evaluation) != 72:
        raise ValueError("P2-23 must retain the 144/72 partition")
    if Counter(row.get("level") for row in train) != Counter(
        {"A": 48, "B": 48, "C": 48}
    ):
        raise ValueError("P2-23 training level balance changed")
    if Counter(row.get("evaluationTier") for row in evaluation) != Counter(
        {"A": 24, "B": 24, "C": 24}
    ):
        raise ValueError("P2-23 evaluation tier balance changed")
    if Counter(row.get("targetKind") for row in train) != Counter(
        {kind: 24 for kind in TARGET_KINDS}
    ):
        raise ValueError("P2-23 training target-kind balance changed")
    if Counter(row.get("targetKind") for row in evaluation) != Counter(
        {kind: 12 for kind in TARGET_KINDS}
    ):
        raise ValueError("P2-23 evaluation target-kind balance changed")

    required = {
        "schemaVersion", "approvalStatus", "candidateSplit", "evaluationTier",
        "id", "level", "taskKind", "targetKind", "targetKindVocabulary",
        "semanticFamily", "request", "solution", "checks", "provenance",
    }
    valid_line = (
        "VALID LABELS: CSS_SELECTOR | CSS_PROPERTY | HTML_ELEMENT | "
        "HTML_ATTRIBUTE | JS_IDENTIFIER | JS_PROPERTY"
    )
    for row in rows:
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        level = row["level"]
        if (
            row["schemaVersion"] != 1
            or row["approvalStatus"] != PENDING
            or row["provenance"] != PROVENANCE
            or row["checks"] != []
            or row["taskKind"] != LEVEL_KIND.get(level)
            or row["semanticFamily"] != SEMANTIC_FAMILY.get(level)
            or row["targetKindVocabulary"] != list(TARGET_KINDS)
            or row["targetKind"] not in TARGET_KINDS
            or row["solution"] != row["targetKind"]
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")
        if row["candidateSplit"] == "train" and row["evaluationTier"] is not None:
            raise ValueError(f"{row['id']} training row has an evaluation tier")
        if (
            row["candidateSplit"] == "evaluation"
            and row["evaluationTier"] != level
        ):
            raise ValueError(f"{row['id']} evaluation tier differs from level")

        visible = row["request"]
        folded = visible.casefold()
        if any(
            marker in folded
            for marker in ("candidatesplit", "evaluationtier", "p2-23-")
        ):
            raise ValueError(f"{row['id']} exposes metadata to the model")
        if re.search(r"\bR[0-5]\b", visible):
            raise ValueError(f"{row['id']} unexpectedly contains reference vocabulary")
        if valid_line not in visible:
            raise ValueError(f"{row['id']} target-kind output vocabulary changed")
        if re.search(
            r"(?:\.[a-z][a-z0-9_-]*|#[a-z][a-z0-9_-]*|"
            r"\d+(?:\.\d+)?(?:px|rem|%|ms|vh|ch))",
            visible,
            re.I,
        ):
            raise ValueError(f"{row['id']} unexpectedly contains a raw repo literal")

        if level == "A":
            if "contrastGroup" in row:
                raise ValueError(f"{row['id']} Level A should not have a group")
            if not visible.startswith("SEMANTIC QUESTION: "):
                raise ValueError(f"{row['id']} Level A prompt format changed")
            if not visible.endswith("Answer with exactly one label."):
                raise ValueError(f"{row['id']} Level A output contract changed")
        elif level == "B":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Level B lacks a contrast group")
            if not visible.startswith("EDIT MODEL: ") or "\nQUESTION:" not in visible:
                raise ValueError(f"{row['id']} Level B prompt format changed")
            if not visible.endswith("Return the target-kind label only."):
                raise ValueError(f"{row['id']} Level B output contract changed")
        elif level == "C":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Level C lacks a contrast group")
            if "\nREQUEST:" not in visible:
                raise ValueError(f"{row['id']} Level C prompt format changed")
            if not visible.endswith("Return the target-kind label only."):
                raise ValueError(f"{row['id']} Level C output contract changed")
        else:
            raise ValueError(f"{row['id']} has an unsupported level")

    for level in ("A", "B", "C"):
        train_subset = [row for row in train if row["level"] == level]
        eval_subset = [row for row in evaluation if row["level"] == level]
        if Counter(row["targetKind"] for row in train_subset) != Counter(
            {kind: 8 for kind in TARGET_KINDS}
        ):
            raise ValueError(f"P2-23 Level {level} target-kind balance changed")
        if Counter(row["targetKind"] for row in eval_subset) != Counter(
            {kind: 4 for kind in TARGET_KINDS}
        ):
            raise ValueError(f"P2-23 Tier {level} target-kind balance changed")

    for level in ("B", "C"):
        train_groups = Counter(
            row["contrastGroup"] for row in train if row["level"] == level
        )
        eval_groups = Counter(
            row["contrastGroup"] for row in evaluation if row["level"] == level
        )
        if len(train_groups) != 8 or set(train_groups.values()) != {6}:
            raise ValueError(f"P2-23 Level {level} training groups changed")
        if len(eval_groups) != 4 or set(eval_groups.values()) != {6}:
            raise ValueError(f"P2-23 Tier {level} evaluation groups changed")
        if set(train_groups) & set(eval_groups):
            raise ValueError(f"P2-23 Level {level} group IDs cross splits")
        for group in list(train_groups) + list(eval_groups):
            members = [row for row in rows if row.get("contrastGroup") == group]
            if {row["targetKind"] for row in members} != set(TARGET_KINDS):
                raise ValueError(f"P2-23 contrast group {group} is incomplete")

    train_requests = {_norm(row["request"]) for row in train}
    if any(_norm(row["request"]) in train_requests for row in evaluation):
        raise ValueError("P2-23 train/evaluation exact request overlap is nonzero")

    train_context = {_context(row) for row in train if row["level"] != "A"}
    eval_context = {
        _context(row) for row in evaluation if row["level"] != "A"
    }
    if train_context & eval_context:
        raise ValueError("P2-23 B/C train/evaluation context overlap is nonzero")

    near = _same_target_near_duplicates(train, evaluation)
    if near:
        raise ValueError(
            "P2-23 same-target train/evaluation near-duplicates remain: "
            + json.dumps(near)
        )

    if hashlib.sha256(_encoded(train)).hexdigest() != TRAIN_SHA256:
        raise ValueError("P2-23 training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [
            row for row in evaluation if row["evaluationTier"] == tier
        ]
        if hashlib.sha256(_encoded(subset)).hexdigest() != digest:
            raise ValueError(f"P2-23 Tier {tier} SHA-256 changed")

    prompt_audit = _prompt_audit(rows)
    if prompt_audit != PROMPT_AUDIT:
        raise ValueError("P2-23 prior-task prompt audit changed")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    expected_review = {
        "schemaVersion": 1,
        "candidate": "p2-23-target-kind-classification-candidate-v1",
        "approvalStatus": PENDING,
        "records": 216,
        "trainingRecords": 144,
        "evaluationRecords": 72,
        "trainingLevelCounts": {"A": 48, "B": 48, "C": 48},
        "evaluationTierCounts": {"A": 24, "B": 24, "C": 24},
        "targetKindVocabulary": list(TARGET_KINDS),
        "trainingPerTargetKind": 24,
        "evaluationPerTargetKind": 12,
        "perLevelTrainingPerTargetKind": 8,
        "perTierEvaluationPerTargetKind": 4,
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "chanceBaselinePerTier": 1 / 6,
        "trainEvaluationExactRequestOverlap": 0,
        "trainEvaluationContextOverlap": 0,
        "sameTargetKindTrainEvaluationNearDuplicatesAtOrAbove065": 0,
        "levelBContrastGroups": {"train": 8, "evaluation": 4},
        "levelCContrastGroups": {"train": 8, "evaluation": 4},
        "priorPromptAudit": PROMPT_AUDIT,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(review.get(key) != value for key, value in expected_review.items()):
        raise ValueError("P2-23 review metadata differs from the pinned candidate")

    return {
        "verified": True,
        "approvalStatus": PENDING,
        "records": 216,
        "authoredSolutionsPassed": 216,
        "trainingRecords": 144,
        "evaluationRecords": 72,
        "trainingLevelCounts": {"A": 48, "B": 48, "C": 48},
        "evaluationTierCounts": {"A": 24, "B": 24, "C": 24},
        "targetKindVocabulary": list(TARGET_KINDS),
        "targetKindDefinitions": TARGET_KIND_DEFINITIONS,
        "trainingPerTargetKind": 24,
        "evaluationPerTargetKind": 12,
        "chanceBaselinePerTier": 1 / 6,
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "trainEvaluationExactRequestOverlap": 0,
        "trainEvaluationContextOverlap": 0,
        "sameTargetKindTrainEvaluationNearDuplicatesAtOrAbove065": 0,
        "levelBContrastGroups": {"train": 8, "evaluation": 4},
        "levelCContrastGroups": {"train": 8, "evaluation": 4},
        "priorPromptAudit": prompt_audit,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-p2-23-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
