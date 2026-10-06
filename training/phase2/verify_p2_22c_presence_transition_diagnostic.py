"""Read-only verification for the P2-22c presence-transition diagnostic."""
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
DIAGNOSTIC = PHASE2 / "evaluation" / "p2-22c-presence-transition-diagnostic-v1.jsonl"
REVIEW = PHASE2 / "evaluation" / "p2-22c-presence-transition-diagnostic-v1.review.json"
P2_22 = PHASE2 / "drafts" / "p2-22-edit-intent-classification-candidate-v1.jsonl"

DIAGNOSTIC_SHA256 = "4d445110d7688e2c9e3d1ba83eb9597eb3320550b71ac9324bf970f6bc1fa479"
TIER_SHA256 = {
    "A": "f94aa202d263128044e64ec1eb8cc9e4c724df5218e4ccba4577368cdfc41f5b",
    "B": "a2a1f014ca0bfbcd589a9a95cb226299f2393f1ccee89d9ae17d29dbbbc6a638",
    "C": "42c61d12689fa337d691949c0217675fbc90a93a080edc7b2633853f6d352a27",
}
P2_22_SHA256 = "592cac0e1c18ad9139057352b132cb39621279c7ec331aad9963610869b25bc0"
INTENTS = ("INSERT", "DELETE", "REPLACE")
STATE_BY_INTENT = {
    "INSERT": ("ABSENT", "PRESENT", "NEWLY_PRESENT"),
    "DELETE": ("PRESENT", "ABSENT", "REMOVED"),
    "REPLACE": ("PRESENT", "PRESENT", "CHANGED"),
}
TASK_KIND = {
    "A": "explicit-state-transition",
    "B": "minimal-state-transition-contrast",
    "C": "repository-state-transition",
}


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(_canonical_bytes(path)).hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank row at line {line_no}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"row {line_no} is not an object")
        result.append(row)
    return result


def _encoded(rows: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + "\n"
    ).encode("utf-8")


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(value)))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _p222_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    p222 = _rows(P2_22)
    exact = {_norm(row["request"]) for row in p222}
    overlap = 0
    maximum = 0.0
    pair: list[str] | None = None
    for row in rows:
        if _norm(row["request"]) in exact:
            overlap += 1
        left = _words(row["request"])
        for prior in p222:
            score = _jaccard(left, _words(prior["request"]))
            if score > maximum:
                maximum = score
                pair = [row["id"], prior["id"]]
    return {
        "exactRequestOverlap": overlap,
        "maxWordJaccard": round(maximum, 6),
        "maxPair": pair,
    }


def verify() -> dict[str, Any]:
    if _sha(DIAGNOSTIC) != DIAGNOSTIC_SHA256:
        raise ValueError("P2-22c diagnostic SHA-256 changed")
    if _sha(P2_22) != P2_22_SHA256:
        raise ValueError("P2-22 candidate identity changed")

    rows = _rows(DIAGNOSTIC)
    if len(rows) != 45:
        raise ValueError("P2-22c must contain exactly 45 evaluation-only rows")
    if _encoded(rows) != _canonical_bytes(DIAGNOSTIC):
        raise ValueError("P2-22c JSONL is not canonically encoded")
    if len({row.get("id") for row in rows}) != 45:
        raise ValueError("P2-22c IDs must be unique")
    if len({row.get("request") for row in rows}) != 45:
        raise ValueError("P2-22c requests must be unique")

    if Counter(row.get("tier") for row in rows) != Counter({"A": 15, "B": 15, "C": 15}):
        raise ValueError("P2-22c tier balance changed")
    if Counter(row.get("targetIntent") for row in rows) != Counter(
        {"INSERT": 15, "DELETE": 15, "REPLACE": 15}
    ):
        raise ValueError("P2-22c intent balance changed")

    required = {
        "schemaVersion", "approvalStatus", "diagnostic", "diagnosticSplit", "id",
        "tier", "taskKind", "targetIntent", "intentVocabulary", "beforePresence",
        "afterPresence", "contentRelation", "request", "solution", "provenance",
    }
    for row in rows:
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        tier = row["tier"]
        intent = row["targetIntent"]
        expected_state = STATE_BY_INTENT.get(intent)
        if (
            row["schemaVersion"] != 1
            or row["approvalStatus"] != "approved-evaluation-only"
            or row["diagnostic"] != "p2-22c-presence-transition-diagnostic-v1"
            or row["diagnosticSplit"] != "evaluation-only"
            or row["taskKind"] != TASK_KIND.get(tier)
            or row["intentVocabulary"] != list(INTENTS)
            or row["solution"] != intent
            or row["provenance"]
            != "codex-authored-local-p2-22c-presence-transition-diagnostic"
            or expected_state is None
            or (
                row["beforePresence"],
                row["afterPresence"],
                row["contentRelation"],
            ) != expected_state
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")

        visible = row["request"]
        folded = visible.casefold()
        if any(marker in folded for marker in ("p2-22c-", "diagnosticsplit", "targetintent")):
            raise ValueError(f"{row['id']} exposes metadata to the model")
        if re.search(r"\bR[0-5]\b", visible):
            raise ValueError(f"{row['id']} unexpectedly contains reference vocabulary")
        if not all(label in visible for label in INTENTS):
            raise ValueError(f"{row['id']} does not expose the three diagnostic labels")

        if tier == "A":
            if "contrastGroup" in row or "repositoryDomain" in row:
                raise ValueError(f"{row['id']} Tier A contains grouped/repository metadata")
        elif tier == "B":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Tier B lacks a contrast group")
            if "repositoryDomain" in row:
                raise ValueError(f"{row['id']} Tier B contains repository metadata")
        elif tier == "C":
            if not isinstance(row.get("contrastGroup"), str):
                raise ValueError(f"{row['id']} Tier C lacks a contrast group")
            if row.get("repositoryDomain") not in {
                "css", "html", "javascript", "component", "generic"
            }:
                raise ValueError(f"{row['id']} Tier C repository domain changed")
        else:
            raise ValueError(f"{row['id']} has an unsupported tier")

    for tier, digest in TIER_SHA256.items():
        subset = [row for row in rows if row["tier"] == tier]
        if len(subset) != 15:
            raise ValueError(f"P2-22c Tier {tier} count changed")
        if Counter(row["targetIntent"] for row in subset) != Counter(
            {"INSERT": 5, "DELETE": 5, "REPLACE": 5}
        ):
            raise ValueError(f"P2-22c Tier {tier} intent balance changed")
        if hashlib.sha256(_encoded(subset)).hexdigest() != digest:
            raise ValueError(f"P2-22c Tier {tier} SHA-256 changed")

    for tier in ("B", "C"):
        subset = [row for row in rows if row["tier"] == tier]
        groups = Counter(row["contrastGroup"] for row in subset)
        if len(groups) != 5 or set(groups.values()) != {3}:
            raise ValueError(f"P2-22c Tier {tier} contrast groups changed")
        for group in groups:
            members = [row for row in subset if row["contrastGroup"] == group]
            if {row["targetIntent"] for row in members} != set(INTENTS):
                raise ValueError(f"P2-22c contrast group {group} is incomplete")

    audit = _p222_audit(rows)
    if audit != {
        "exactRequestOverlap": 0,
        "maxWordJaccard": 0.432432,
        "maxPair": ["p2-22c-e-a-007", "p2-22-e-a-006"],
    }:
        raise ValueError("P2-22c overlap audit changed")

    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    expected_review = {
        "schemaVersion": 1,
        "diagnostic": "p2-22c-presence-transition-diagnostic-v1",
        "authorizationStatus": "owner-authorized-evaluation-only",
        "sourceExperiment": "p2-22b-edit-intent-continuation-v1",
        "sourceStep": 500,
        "records": 45,
        "tierCounts": {"A": 15, "B": 15, "C": 15},
        "intentCounts": {"INSERT": 15, "DELETE": 15, "REPLACE": 15},
        "intentCountsPerTier": {"INSERT": 5, "DELETE": 5, "REPLACE": 5},
        "diagnosticJsonlSha256": DIAGNOSTIC_SHA256,
        "tierSha256": TIER_SHA256,
        "legalDiagnosticOutputs": list(INTENTS),
        "transitionDefinitions": {
            "INSERT": "ABSENT -> PRESENT",
            "DELETE": "PRESENT -> ABSENT",
            "REPLACE": "PRESENT -> PRESENT with changed content",
        },
        "chanceBaselinePerTier": 1 / 3,
        "p222ExactRequestOverlap": 0,
        "p222MaxWordJaccard": 0.432432,
        "p222MaxPair": ["p2-22c-e-a-007", "p2-22-e-a-006"],
        "matchedContrastSimilarityIntentional": True,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "gradientTrainingPerformed": False,
        "modelWeightsModified": False,
        "finalHoldoutOpened": False,
    }
    if any(review.get(key) != value for key, value in expected_review.items()):
        raise ValueError("P2-22c review metadata differs from the pinned diagnostic")

    return {
        "verified": True,
        "authorizationStatus": "owner-authorized-evaluation-only",
        "records": 45,
        "tierCounts": {"A": 15, "B": 15, "C": 15},
        "intentCounts": {"INSERT": 15, "DELETE": 15, "REPLACE": 15},
        "intentCountsPerTier": {"INSERT": 5, "DELETE": 5, "REPLACE": 5},
        "diagnosticJsonlSha256": DIAGNOSTIC_SHA256,
        "tierSha256": TIER_SHA256,
        "p222PromptAudit": audit,
        "chanceBaselinePerTier": 1 / 3,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "gradientTrainingPerformed": False,
        "modelWeightsModified": False,
        "finalHoldoutOpened": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-p2-22c-diagnostic-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
