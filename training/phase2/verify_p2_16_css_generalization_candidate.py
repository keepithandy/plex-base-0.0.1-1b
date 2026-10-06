"""Read-only verification for the unapproved P2-16 CSS generalization candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.benchmark import _check_task

PHASE2 = ROOT / "training" / "phase2"
CANDIDATE = PHASE2 / "drafts" / "p2-16-css-generalization-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-16-css-generalization-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc"
TRAIN_SHA256 = "50b3ccd2e7fad9e2b67d8886adb04dc15e76e5de06952b1df9870ae639ae6e59"
TIER_SHA256 = {
    "A": "1e1baa18bbe5ae0415ad3b57dccef40cdee56845469135d468048671f3f2c024",
    "B": "a096e1c0f837e7473355cb921ba8fbfd2c281ae10b95fa87f6fa0eace2f984b0",
    "C": "3c01756e11244cf68c3b1c6c765b4480daf248689c3e4181308e6f863a3cc515",
    "D": "f8f696f1213d83d0b45aea9a6cddd19a822363e6c8ef4b680b11aacf1d8ea460",
}
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"
PENDING = "pending-owner-review"

TRAIN_FAMILIES = {
    "border-radius",
    "opacity",
    "width",
    "max-width",
    "padding",
    "margin-block-start",
    "font-size",
    "line-height",
    "letter-spacing",
    "outline-offset",
    "background-color",
    "box-shadow",
}
TIER_D_FAMILIES = {"white-space", "aspect-ratio", "list-style-type", "text-transform"}
EXPECTED_TIERS = Counter({"A": 24, "B": 12, "C": 12, "D": 12})
EXPECTED_TRAIN_OPERATIONS = Counter({"replace": 72, "add": 24, "remove": 24})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_text_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _file_sha(path: Path) -> str:
    return _sha(_canonical_text_bytes(path))


def _encoded(rows: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + "\n"
    ).encode("utf-8")


def _load_rows() -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(CANDIDATE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank candidate line at {line_no}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"candidate line {line_no} is not an object")
        rows.append(row)
    return rows


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _word_set(value: str) -> set[str]:
    normalized = value.casefold()
    normalized = re.sub(
        r"#[0-9a-f]+|rgb\([^)]*\)|hsl\([^)]*\)|\b-?\d+(?:\.\d+)?(?:px|rem|em|%|vh|vw)?\b",
        "<value>",
        normalized,
    )
    return set(re.findall(r"[a-z][a-z-]*|<value>", normalized))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _parse_rule(source: str) -> tuple[str, list[tuple[str, str]]]:
    match = re.fullmatch(r"\s*([^{}]+)\{([^{}]*)\}\s*", source, flags=re.DOTALL)
    if not match:
        raise ValueError(f"not one flat CSS rule: {source!r}")
    selector = " ".join(match.group(1).split())
    declarations: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in match.group(2).split(";"):
        raw = raw.strip()
        if not raw:
            continue
        if ":" not in raw:
            raise ValueError(f"malformed declaration: {raw!r}")
        name, value = raw.split(":", 1)
        name = name.strip().lower()
        value = " ".join(value.strip().split())
        if not name or not value or name in seen:
            raise ValueError(f"invalid or duplicate declaration: {raw!r}")
        seen.add(name)
        declarations.append((name, value))
    return selector, declarations


def _apply_primitives(
    declarations: list[tuple[str, str]],
    primitives: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    result = list(declarations)
    for primitive in primitives:
        prop = primitive["property"]
        operation = primitive["operation"]
        source = primitive.get("sourceValue")
        target = primitive.get("targetValue")
        positions = [index for index, (name, _) in enumerate(result) if name == prop]
        if operation == "replace":
            if len(positions) != 1 or result[positions[0]][1] != source or target is None:
                raise ValueError(f"invalid replace primitive for {prop}")
            result[positions[0]] = (prop, target)
        elif operation == "add":
            if positions or source is not None or target is None:
                raise ValueError(f"invalid add primitive for {prop}")
            result.append((prop, target))
        elif operation == "remove":
            if len(positions) != 1 or result[positions[0]][1] != source or target is not None:
                raise ValueError(f"invalid remove primitive for {prop}")
            del result[positions[0]]
        else:
            raise ValueError(f"unsupported primitive operation {operation!r}")
    return result


def _literal_key(row: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            primitive["property"],
            primitive["operation"],
            primitive.get("sourceValue"),
            primitive.get("targetValue"),
        )
        for primitive in row["operationPrimitives"]
    )


def _dev_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    task_sets = {
        "P2-14": json.loads(P2_14.read_text(encoding="utf-8"))["tasks"],
        "P2-01b": json.loads(P2_01B.read_text(encoding="utf-8"))["tasks"],
    }
    result: dict[str, Any] = {}
    for name, tasks in task_sets.items():
        exact = {_norm(task["request"]) for task in tasks}
        max_jaccard = 0.0
        max_pair: list[str] | None = None
        for row in rows:
            words = set(re.findall(r"[a-z0-9#.%_-]+", _norm(row["request"])))
            for task in tasks:
                other = set(re.findall(r"[a-z0-9#.%_-]+", _norm(task["request"])))
                score = _jaccard(words, other)
                if score > max_jaccard:
                    max_jaccard = score
                    max_pair = [row["id"], task["id"]]
        result[name] = {
            "exactRequestOverlap": sum(_norm(row["request"]) in exact for row in rows),
            "maxWordJaccard": round(max_jaccard, 6),
            "maxPair": max_pair,
        }
    return result


def verify() -> dict[str, Any]:
    if not CANDIDATE.is_file() or not REVIEW_JSON.is_file():
        raise ValueError("P2-16 candidate or review metadata is missing")
    if _file_sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-16 candidate SHA-256 changed")
    if _file_sha(P2_14) != P2_14_SHA256:
        raise ValueError("P2-14 development set SHA-256 changed")
    if _file_sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("P2-01b development set SHA-256 changed")

    rows = _load_rows()
    if len(rows) != 180:
        raise ValueError("P2-16 candidate must contain 180 records")
    if _encoded(rows) != _canonical_text_bytes(CANDIDATE):
        raise ValueError("candidate JSONL is not canonical deterministic JSON")

    ids = [row.get("id") for row in rows]
    selectors = [row.get("selector") for row in rows]
    requests = [row.get("request") for row in rows]
    source_target_pairs = [(row.get("inputCss"), row.get("solution")) for row in rows]
    if len(set(ids)) != len(ids) or len(set(selectors)) != len(selectors):
        raise ValueError("candidate IDs and selectors must be globally unique")
    if len(set(requests)) != len(requests):
        raise ValueError("candidate has exact duplicate requests")
    if len(set(source_target_pairs)) != len(source_target_pairs):
        raise ValueError("candidate has duplicate source/target pairs")

    split_counts = Counter(row.get("candidateSplit") for row in rows)
    if split_counts != Counter({"train": 120, "evaluation": 60}):
        raise ValueError(f"unexpected candidate split counts: {split_counts}")
    tier_counts = Counter(
        row.get("evaluationTier")
        for row in rows
        if row.get("candidateSplit") == "evaluation"
    )
    if tier_counts != EXPECTED_TIERS:
        raise ValueError(f"unexpected evaluation tier counts: {tier_counts}")
    if any(row.get("evaluationTier") is not None for row in rows if row.get("candidateSplit") == "train"):
        raise ValueError("training rows must not have evaluation tiers")

    for row in rows:
        required = {
            "id", "language", "request", "instruction", "inputCss", "solution", "checks",
            "editFamily", "editFamilies", "operationType", "operationPrimitives",
            "semanticGroupId", "instructionTemplateId", "selector", "candidateSplit",
            "evaluationTier", "provenance", "approvalStatus", "deterministicChecks",
        }
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        if row["language"] != "css" or row["approvalStatus"] != PENDING:
            raise ValueError(f"{row['id']} has invalid language or approval status")
        if row["provenance"] != "codex-authored-local-training-candidate":
            raise ValueError(f"{row['id']} has unexpected provenance")
        if row["deterministicChecks"] != {
            "staticChecker": "css_stylesheet_exact",
            "preserveUnrelatedDeclarations": True,
        }:
            raise ValueError(f"{row['id']} has unexpected deterministic-check metadata")

        input_selector, before = _parse_rule(row["inputCss"])
        output_selector, after = _parse_rule(row["solution"])
        if input_selector != row["selector"] or output_selector != row["selector"]:
            raise ValueError(f"{row['id']} selector drifted")
        expected_after = _apply_primitives(before, row["operationPrimitives"])
        if after != expected_after:
            raise ValueError(f"{row['id']} does not preserve/apply declarations deterministically")

        expected_map = {name: value for name, value in after}
        if row["checks"] != [{
            "kind": "css_stylesheet_exact",
            "rules": {row["selector"]: expected_map},
        }]:
            raise ValueError(f"{row['id']} check map differs from its expected output")

        checked = _check_task(
            {"id": row["id"], "language": "css", "difficulty": "basic", "checks": row["checks"]},
            row["solution"],
            None,
            5.0,
        )
        if not checked["passed"]:
            raise ValueError(f"{row['id']} authored output fails the repository CSS checker: {checked}")

    train = [row for row in rows if row["candidateSplit"] == "train"]
    eval_rows = [row for row in rows if row["candidateSplit"] == "evaluation"]
    if _sha(_encoded(train)) != TRAIN_SHA256:
        raise ValueError("training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [row for row in eval_rows if row["evaluationTier"] == tier]
        if _sha(_encoded(subset)) != digest:
            raise ValueError(f"Tier {tier} SHA-256 changed")

    train_family_counts = Counter(row["editFamily"] for row in train)
    if set(train_family_counts) != TRAIN_FAMILIES or set(train_family_counts.values()) != {10}:
        raise ValueError(f"training family balance changed: {train_family_counts}")
    train_ops = Counter(row["operationType"] for row in train)
    if train_ops != EXPECTED_TRAIN_OPERATIONS:
        raise ValueError(f"training operation balance changed: {train_ops}")

    train_templates = {row["instructionTemplateId"] for row in train}
    train_literal = {_literal_key(row) for row in train}
    train_values: dict[str, set[Any]] = defaultdict(set)
    for row in train:
        primitive = row["operationPrimitives"][0]
        train_values[primitive["property"]].add(
            primitive["targetValue"] if primitive["targetValue"] is not None else primitive["sourceValue"]
        )

    for tier in ("A", "B", "C", "D"):
        subset = [row for row in eval_rows if row["evaluationTier"] == tier]
        if any(_literal_key(row) in train_literal for row in subset):
            raise ValueError(f"Tier {tier} repeats a literal transformation from training")

    tier_a = [row for row in eval_rows if row["evaluationTier"] == "A"]
    if any(set(row["editFamilies"]) - TRAIN_FAMILIES for row in tier_a):
        raise ValueError("Tier A must use seen property families")
    if any(row["instructionTemplateId"] not in train_templates for row in tier_a):
        raise ValueError("Tier A must intentionally reuse seen instruction templates")
    for row in tier_a:
        primitive = row["operationPrimitives"][0]
        held_value = primitive["targetValue"] if primitive["targetValue"] is not None else primitive["sourceValue"]
        if held_value in train_values[primitive["property"]]:
            raise ValueError(f"Tier A value leaked from training: {row['id']}")

    tier_b = [row for row in eval_rows if row["evaluationTier"] == "B"]
    if any(set(row["editFamilies"]) - TRAIN_FAMILIES for row in tier_b):
        raise ValueError("Tier B must use seen property families")
    if any(row["instructionTemplateId"] in train_templates for row in tier_b):
        raise ValueError("Tier B wording templates must be held out")
    for row in tier_b:
        primitive = row["operationPrimitives"][0]
        held_value = primitive["targetValue"] if primitive["targetValue"] is not None else primitive["sourceValue"]
        if held_value in train_values[primitive["property"]]:
            raise ValueError(f"Tier B literal value leaked from training: {row['id']}")

    tier_c = [row for row in eval_rows if row["evaluationTier"] == "C"]
    if any(
        row["operationType"] != "compose"
        or len(row["operationPrimitives"]) != 2
        or len(row["editFamilies"]) != 2
        or set(row["editFamilies"]) - TRAIN_FAMILIES
        for row in tier_c
    ):
        raise ValueError("Tier C must compose two seen property families")
    if any(row["instructionTemplateId"] in train_templates for row in tier_c):
        raise ValueError("Tier C composition wording must be held out")

    tier_d = [row for row in eval_rows if row["evaluationTier"] == "D"]
    tier_d_families = {family for row in tier_d for family in row["editFamilies"]}
    if tier_d_families != TIER_D_FAMILIES or tier_d_families & TRAIN_FAMILIES:
        raise ValueError("Tier D property-family holdout changed")
    if any(row["instructionTemplateId"] in train_templates for row in tier_d):
        raise ValueError("Tier D wording templates must not reuse training templates")

    near_duplicate = {}
    for tier in ("A", "B", "C", "D"):
        max_score = 0.0
        max_pair = None
        for row in [item for item in eval_rows if item["evaluationTier"] == tier]:
            left = _word_set(row["instruction"])
            for other in train:
                score = _jaccard(left, _word_set(other["instruction"]))
                if score > max_score:
                    max_score = score
                    max_pair = [row["id"], other["id"]]
        near_duplicate[tier] = {"maxInstructionJaccard": round(max_score, 6), "maxPair": max_pair}
    if any(near_duplicate[tier]["maxInstructionJaccard"] >= 0.70 for tier in ("B", "C", "D")):
        raise ValueError("unexpected near-duplicate instruction leakage into Tier B/C/D")

    dev_stats = _dev_stats(rows)
    if any(value["exactRequestOverlap"] for value in dev_stats.values()):
        raise ValueError("candidate duplicates an existing development request")
    if any(value["maxWordJaccard"] >= 0.70 for value in dev_stats.values()):
        raise ValueError("candidate is unexpectedly close to an existing development request")

    report = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    fixed = {
        "candidate": "p2-16-css-generalization-candidate-v1",
        "approvalStatus": PENDING,
        "records": 180,
        "trainingRecords": 120,
        "evaluationRecords": 60,
        "evaluationTierCounts": dict(EXPECTED_TIERS),
        "trainingOperationCounts": dict(EXPECTED_TRAIN_OPERATIONS),
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "p214DevelopmentTaskSetSha256": P2_14_SHA256,
        "p201bDevelopmentTaskSetSha256": P2_01B_SHA256,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(report.get(key) != value for key, value in fixed.items()):
        raise ValueError("review metadata differs from the pinned P2-16 candidate")
    if report.get("nearDuplicateInstructionAudit") != near_duplicate:
        raise ValueError("review near-duplicate audit changed")
    if report.get("developmentPromptAudit") != dev_stats:
        raise ValueError("review development-prompt audit changed")

    forbidden_names = {"tokenizer", "initialization", "checkpoint", "run", "pilot"}
    for path in REVIEW_DIR.rglob("*"):
        if any(part.casefold() in forbidden_names for part in path.parts):
            raise ValueError(f"candidate review directory contains forbidden training artifact: {path}")

    return {
        "verified": True,
        "records": len(rows),
        "trainingRecords": len(train),
        "evaluationTierCounts": dict(tier_counts),
        "staticAuthoredSolutionsPassed": len(rows),
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "nearDuplicateInstructionAudit": near_duplicate,
        "developmentPromptAudit": dev_stats,
        "approvalStatus": PENDING,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-p2-16-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
