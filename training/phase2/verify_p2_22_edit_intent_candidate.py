"""Read-only verification for the unapproved P2-22 edit-intent candidate."""
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
CANDIDATE = PHASE2 / "drafts" / "p2-22-edit-intent-classification-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-22-edit-intent-classification-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"

P2_21 = PHASE2 / "drafts" / "p2-21-semantic-role-generalization-candidate-v1.jsonl"
P2_20 = PHASE2 / "drafts" / "p2-20-role-decomposition-candidate-v1.jsonl"
P2_19 = PHASE2 / "drafts" / "p2-19-reference-binding-candidate-v1.jsonl"
P2_18 = PHASE2 / "drafts" / "p2-18-literal-copy-candidate-v1.jsonl"
P2_17 = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1.jsonl"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0"
TRAIN_SHA256 = "23684d8d25dcfffeb1d680207887d043d188fbbc883fc185ed86d11c024b7d22"
TIER_SHA256 = {
    "A": "adcc58c89d147f2c4dcd53f5403cd4d245fcb67af6797d6b2e6ad8211b13a5d4",
    "B": "254658f09854e92a5d754856bed7feb974fc99b3deecb63b2486089265e1b2e1",
    "C": "86de85089017a2a24945b0fa89aac39ab66ec646184d5218e2cc4cedfb4d47b7",
}

P2_21_SHA256 = "8206798467f74bda9867c0179495b535eade3849ca1d8a5d3147de00f27e5584"
P2_20_SHA256 = "8d7c54ceed8a0c90a437626e504e2ba39582f0ca5c57c243db5c564e2c02985d"
P2_19_SHA256 = "e96d6b8edd2a756a03d285f1081491232df7f79886a47d6ab02efcdb29211fa1"
P2_18_SHA256 = "9329d4704fdf061d45900f20c67bb7fc049896e4f464fff83faac431567447c6"
P2_17_SHA256 = "2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5"
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"

PENDING = "pending-owner-review"
PROVENANCE = "codex-authored-local-p2-22-edit-intent-classification-candidate"
INTENTS = ("REPLACE", "INSERT", "DELETE", "RENAME", "TOGGLE")
LEVEL_KIND = {
    "A": "direct-edit-intent-paraphrase",
    "B": "minimal-contrast-edit-intent",
    "C": "repository-style-edit-intent",
}
SEMANTIC_FAMILY = {
    "A": "direct-intent-paraphrase",
    "B": "minimal-contrast",
    "C": "repository-style",
}
INTENT_DEFINITIONS = {
    "REPLACE": "change an existing value/state while preserving the target's presence and identity",
    "INSERT": "add a new construct or entry that was not previously present",
    "DELETE": "remove an existing construct or entry entirely",
    "RENAME": "change an identifier/name while preserving the underlying logical entity",
    "TOGGLE": "flip a binary/two-state setting to its opposite",
}
PROMPT_AUDIT = {
    "P2-21": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.46875,
        "maxPair": ["p2-22-t-a-010", "p2-21-e-a-018"],
    },
    "P2-20": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.289474,
        "maxPair": ["p2-22-t-c-036", "p2-20-t-a-024"],
    },
    "P2-19": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.12766,
        "maxPair": ["p2-22-t-c-016", "p2-19-t-c-027"],
    },
    "P2-18": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.162162,
        "maxPair": ["p2-22-e-c-016", "p2-18-copy-038"],
    },
    "P2-17": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.157143,
        "maxPair": ["p2-22-t-c-001", "p2-17-bind-001"],
    },
    "P2-14": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.153846,
        "maxPair": ["p2-22-t-c-001", "p2-14-css-edit-gap"],
    },
    "P2-01b": {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.142857,
        "maxPair": ["p2-22-t-a-038", "p2dev-css-08-sticky-header"],
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
    level = row["level"]
    if level == "A":
        return None
    marker = "\nQUESTION:" if level == "B" else "\nREQUEST:"
    if marker not in row["request"]:
        raise ValueError(f"{row['id']} has no context/query boundary")
    return row["request"].split(marker, 1)[0]


def _same_intent_near_duplicates(
    train: list[dict[str, Any]], evaluation: list[dict[str, Any]]
) -> list[tuple[str, str, float]]:
    matches: list[tuple[str, str, float]] = []
    for eval_row in evaluation:
        left = _words(eval_row["request"])
        for train_row in train:
            if (
                train_row["level"] != eval_row["level"]
                or train_row["targetIntent"] != eval_row["targetIntent"]
            ):
                continue
            score = _jaccard(left, _words(train_row["request"]))
            if score >= 0.65:
                matches.append((eval_row["id"], train_row["id"], round(score, 6)))
    return matches


def verify() -> dict[str, Any]:
    if _sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-22 candidate SHA-256 changed")
    if _sha(P2_21) != P2_21_SHA256 or _sha(P2_20) != P2_20_SHA256:
        raise ValueError("recent Phase-2 candidate identity changed")
    if _sha(P2_19) != P2_19_SHA256:
        raise ValueError("P2-19 candidate identity changed")
    if _sha(P2_18) != P2_18_SHA256 or _sha(P2_17) != P2_17_SHA256:
        raise ValueError("prior Phase-2 candidate identity changed")
    if _sha(P2_14) != P2_14_SHA256 or _sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("development task-set identity changed")

    rows = _rows(CANDIDATE)
    if len(rows) != 225 or _encoded(rows) != _canonical_bytes(CANDIDATE):
        raise ValueError("P2-22 count or canonical JSONL encoding changed")
    if len({row.get("id") for row in rows}) != 225:
        raise ValueError("P2-22 IDs must be unique")
    if len({row.get("request") for row in rows}) != 225:
        raise ValueError("P2-22 requests must be unique")

    train = [row for row in rows if row.get("candidateSplit") == "train"]
    evaluation = [row for row in rows if row.get("candidateSplit") == "evaluation"]
    if len(train) != 150 or len(evaluation) != 75:
        raise ValueError("P2-22 must retain the 150/75 partition")
    if Counter(row.get("level") for row in train) != Counter({"A":50,"B":50,"C":50}):
        raise ValueError("P2-22 training level balance changed")
    if Counter(row.get("evaluationTier") for row in evaluation) != Counter({"A":25,"B":25,"C":25}):
        raise ValueError("P2-22 evaluation tier balance changed")

    required = {
        "schemaVersion","approvalStatus","candidateSplit","evaluationTier","id",
        "level","taskKind","targetIntent","intentVocabulary","semanticFamily",
        "request","solution","checks","provenance",
    }
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
            or row["intentVocabulary"] != list(INTENTS)
            or row["targetIntent"] not in INTENTS
            or row["solution"] != row["targetIntent"]
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")
        if row["candidateSplit"] == "train" and row["evaluationTier"] is not None:
            raise ValueError(f"{row['id']} training row has an evaluation tier")
        if row["candidateSplit"] == "evaluation" and row["evaluationTier"] != level:
            raise ValueError(f"{row['id']} evaluation tier differs from its level")

        visible = row["request"]
        visible_folded = visible.casefold()
        if any(marker in visible_folded for marker in ("candidatesplit", "evaluationtier", "p2-22-")):
            raise ValueError(f"{row['id']} exposes metadata to the model")
        if re.search(r"\bR[0-5]\b", visible):
            raise ValueError(f"{row['id']} unexpectedly contains reference vocabulary")
        if re.search(
            r"(?:\.[a-z][a-z0-9_-]*|#[a-z][a-z0-9_-]*|"
            r"\d+(?:\.\d+)?(?:px|rem|%|ms|vh|ch))",
            visible,
            re.I,
        ):
            raise ValueError(f"{row['id']} unexpectedly contains a raw repository literal")

        if level == "A":
            if "contrastGroup" in row:
                raise ValueError(f"{row['id']} Level A should not have a contrast group")
            if re.fullmatch(
                r"SEMANTIC QUESTION: .+\n"
                r"VALID LABELS: REPLACE \| INSERT \| DELETE \| RENAME \| TOGGLE\n"
                r"Answer with exactly one label\.",
                visible,
            ) is None:
                raise ValueError(f"{row['id']} Level A prompt format changed")
        elif level == "B":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Level B lacks a contrast group")
            if not visible.startswith("EDIT MODEL: "):
                raise ValueError(f"{row['id']} Level B prompt format changed")
            if (
                "\nChoose exactly one: REPLACE, INSERT, DELETE, RENAME, or TOGGLE.\n"
                "Return the intent label only."
            ) not in visible:
                raise ValueError(f"{row['id']} Level B output contract changed")
        elif level == "C":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Level C lacks a repository group")
            if (
                "\nREQUEST: " not in visible
                or "\nVALID LABELS: REPLACE | INSERT | DELETE | RENAME | TOGGLE\n"
                "Return exactly one intent label."
                not in visible
            ):
                raise ValueError(f"{row['id']} Level C prompt format changed")
        else:
            raise ValueError(f"{row['id']} has an unsupported level")

    if hashlib.sha256(_encoded(train)).hexdigest() != TRAIN_SHA256:
        raise ValueError("P2-22 training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [row for row in evaluation if row["evaluationTier"] == tier]
        if hashlib.sha256(_encoded(subset)).hexdigest() != digest:
            raise ValueError(f"P2-22 Tier {tier} SHA-256 changed")

    expected_train = Counter({intent:10 for intent in INTENTS})
    expected_eval = Counter({intent:5 for intent in INTENTS})
    for level in ("A","B","C"):
        train_level = [row for row in train if row["level"] == level]
        eval_level = [row for row in evaluation if row["level"] == level]
        if Counter(row["targetIntent"] for row in train_level) != expected_train:
            raise ValueError(f"P2-22 Level {level} training intent balance changed")
        if Counter(row["targetIntent"] for row in eval_level) != expected_eval:
            raise ValueError(f"P2-22 Tier {level} evaluation intent balance changed")

    for level, train_groups, eval_groups in (("B",10,5),("C",10,5)):
        train_level = [row for row in train if row["level"] == level]
        eval_level = [row for row in evaluation if row["level"] == level]
        train_counter = Counter(row["contrastGroup"] for row in train_level)
        eval_counter = Counter(row["contrastGroup"] for row in eval_level)
        if len(train_counter) != train_groups or set(train_counter.values()) != {5}:
            raise ValueError(f"P2-22 Level {level} training five-way groups changed")
        if len(eval_counter) != eval_groups or set(eval_counter.values()) != {5}:
            raise ValueError(f"P2-22 Tier {level} evaluation five-way groups changed")
        for group, records in (
            (group, [row for row in train_level if row["contrastGroup"] == group])
            for group in train_counter
        ):
            if {row["targetIntent"] for row in records} != set(INTENTS):
                raise ValueError(f"P2-22 Level {level} training group {group} is incomplete")
        for group, records in (
            (group, [row for row in eval_level if row["contrastGroup"] == group])
            for group in eval_counter
        ):
            if {row["targetIntent"] for row in records} != set(INTENTS):
                raise ValueError(f"P2-22 Tier {level} evaluation group {group} is incomplete")

    train_requests = {_norm(row["request"]) for row in train}
    if any(_norm(row["request"]) in train_requests for row in evaluation):
        raise ValueError("P2-22 evaluation request leaked from training")

    train_contexts = {
        _context(row)
        for row in train
        if row["level"] in {"B", "C"}
    }
    eval_contexts = {
        _context(row)
        for row in evaluation
        if row["level"] in {"B", "C"}
    }
    if None in train_contexts or None in eval_contexts:
        raise ValueError("P2-22 context extraction failed")
    if train_contexts & eval_contexts:
        raise ValueError("P2-22 evaluation context leaked from training")

    near_duplicates = _same_intent_near_duplicates(train, evaluation)
    if near_duplicates:
        raise ValueError(
            "P2-22 has same-intent train/evaluation wording overlap >= 0.65: "
            + repr(near_duplicates[:5])
        )

    prompt_audit = _prompt_audit(rows)
    if prompt_audit != PROMPT_AUDIT:
        raise ValueError("P2-22 prior-task prompt audit changed")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    fixed = {
        "schemaVersion":1,
        "candidate":"p2-22-edit-intent-classification-candidate-v1",
        "approvalStatus":PENDING,
        "records":225,
        "trainingRecords":150,
        "evaluationRecords":75,
        "trainingLevelCounts":{"A":50,"B":50,"C":50},
        "evaluationTierCounts":{"A":25,"B":25,"C":25},
        "candidateJsonlSha256":CANDIDATE_SHA256,
        "trainingRowsSha256":TRAIN_SHA256,
        "tierSha256":TIER_SHA256,
        "intentVocabulary":list(INTENTS),
        "trainIntentCountsPerLevel":{intent:10 for intent in INTENTS},
        "evaluationIntentCountsPerTier":{intent:5 for intent in INTENTS},
        "canonicalIntentDefinitions":INTENT_DEFINITIONS,
        "levelA":"clean unseen edit-intent paraphrases -> canonical intent label",
        "levelB":"minimal-contrast edit-intent classification -> canonical intent label",
        "levelC":"repository-style edit language -> canonical intent label",
        "levelBContrastGroups":{"train":10,"evaluation":5,"recordsPerGroup":5},
        "levelCRepositoryGroups":{"train":10,"evaluation":5,"recordsPerGroup":5},
        "trainEvaluationExactRequestOverlap":0,
        "trainEvaluationContextOverlap":0,
        "duplicateRequests":0,
        "sameIntentTrainEvaluationNearDuplicatesAtOrAbove065":0,
        "referenceVocabularyRequired":False,
        "rawRepositoryLiteralsRequired":False,
        "codeGenerationRequired":False,
        "simpleChanceBaseline":0.2,
        "developmentPromptAudit":PROMPT_AUDIT,
        "tokenizerFitted":False,
        "checkpointInitialized":False,
        "trainingRunCreated":False,
        "modelTrained":False,
        "finalHoldoutOpened":False,
    }
    if any(review.get(key) != value for key, value in fixed.items()):
        raise ValueError("P2-22 review metadata differs from the pinned candidate")

    forbidden = {"tokenizer","initialization","checkpoint","run","pilot"}
    for path in REVIEW_DIR.rglob("*"):
        if any(part.casefold() in forbidden for part in path.parts):
            raise ValueError(f"P2-22 review directory contains a forbidden artifact: {path}")

    return {
        "verified":True,
        "approvalStatus":PENDING,
        "records":225,
        "trainingRecords":150,
        "evaluationRecords":75,
        "trainingLevelCounts":{"A":50,"B":50,"C":50},
        "evaluationTierCounts":{"A":25,"B":25,"C":25},
        "authoredSolutionsPassed":225,
        "intentVocabulary":list(INTENTS),
        "trainEvaluationExactRequestOverlap":0,
        "trainEvaluationContextOverlap":0,
        "sameIntentTrainEvaluationNearDuplicatesAtOrAbove065":0,
        "levelBContrastGroups":{"train":10,"evaluation":5},
        "levelCRepositoryGroups":{"train":10,"evaluation":5},
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
        print(f"plex-p2-22-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
