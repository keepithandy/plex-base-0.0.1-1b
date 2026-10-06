"""Read-only verification for the unapproved P2-17 semantic binding candidate."""
from __future__ import annotations

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
CANDIDATE = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1.jsonl"
REVIEW_DIR = PHASE2 / "drafts" / "p2-17-semantic-binding-candidate-v1"
REVIEW_JSON = REVIEW_DIR / "review.json"
P2_14 = PHASE2 / "drafts" / "p2-14-css-edit-step200-v1" / "task-set.json"
P2_01B = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"

CANDIDATE_SHA256 = "2cf3285fb2548519f1733bae2da7f3260a473c7de76bc2bcf538d300753dbca5"
TRAIN_SHA256 = "6a27b5fc1ab84ffe389215d0f19ce2a25257ec689e063dd4de21b0b9369c3da2"
TIER_SHA256 = {
    "A": "63f6097826d838165b4d45631c9001c5cbe865e2e7c10b85cd144a88c0c840eb",
    "B": "6abbbb86c5ec644092327b123ffce56ef187a5297d50f049e36236e3b82151a8",
    "C": "a016e6cf47a8c74e48b706d916902081328a3a227ab5ab9aaee218dc207b9688",
}
P2_14_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
P2_01B_SHA256 = "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4"
PENDING = "pending-owner-review"
PROVENANCE = "codex-authored-local-p2-17-binding-candidate"

EXPECTED_TRAIN_KINDS = Counter({"extract-plan": 60, "apply-plan": 60})
EXPECTED_TIERS = Counter({"A": 20, "B": 20, "C": 20})
EXPECTED_TIER_KINDS = {"A": "extract-plan", "B": "apply-plan", "C": "chain-edit"}
EXPECTED_OPERATIONS = Counter({"replace": 20, "add": 20, "remove": 20})
EXPECTED_PROPERTIES = Counter({
    "border-radius": 10,
    "opacity": 10,
    "width": 10,
    "padding": 10,
    "font-size": 10,
    "line-height": 10,
})
PLAN_FIELDS = ("selector", "operation", "property", "old", "new")


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


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(CANDIDATE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank candidate line at {line_no}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"candidate line {line_no} is not an object")
        rows.append(value)
    return rows


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
    if not declarations:
        raise ValueError("CSS rule has no declarations")
    return selector, declarations


def _render_rule(selector: str, declarations: list[tuple[str, str]]) -> str:
    return selector + " { " + " ".join(f"{name}: {value};" for name, value in declarations) + " }"


def _apply(
    declarations: list[tuple[str, str]],
    operation: str,
    property_name: str,
    source_value: str | None,
    target_value: str | None,
) -> list[tuple[str, str]]:
    positions = [index for index, (name, _) in enumerate(declarations) if name == property_name]
    result = list(declarations)
    if operation == "replace":
        if len(positions) != 1 or result[positions[0]][1] != source_value or target_value is None:
            raise ValueError("invalid replace metadata")
        result[positions[0]] = (property_name, target_value)
    elif operation == "add":
        if positions or source_value is not None or target_value is None:
            raise ValueError("invalid add metadata")
        result.append((property_name, target_value))
    elif operation == "remove":
        if len(positions) != 1 or result[positions[0]][1] != source_value or target_value is not None:
            raise ValueError("invalid remove metadata")
        del result[positions[0]]
    else:
        raise ValueError(f"unsupported operation: {operation!r}")
    return result


def _plan(row: dict[str, Any]) -> str:
    return "\n".join([
        f"selector={row['selector']}",
        f"operation={row['operation']}",
        f"property={row['property']}",
        f"old={row['sourceValue'] if row['sourceValue'] is not None else '<none>'}",
        f"new={row['targetValue'] if row['targetValue'] is not None else '<none>'}",
    ])


def _instruction(row: dict[str, Any]) -> str:
    operation = row["operation"]
    prop = row["property"]
    old = row["sourceValue"]
    new = row["targetValue"]
    if operation == "replace":
        return f"Change {prop} from {old} to {new}. Preserve every other declaration."
    if operation == "add":
        return f"Add {prop} with value {new}. Preserve every existing declaration."
    return f"Remove {prop}. Preserve every other declaration."


def _request(row: dict[str, Any]) -> str:
    if row["taskKind"] == "extract-plan":
        return (
            f"Starting CSS:\n{row['inputCss']}\n\n"
            f"Requested edit: {row['instruction']}\n"
            "Return exactly five lines in this order: selector=..., operation=..., property=..., old=..., new=.... "
            "Use <none> when the old or new value does not exist. Return no explanation."
        )
    if row["taskKind"] == "apply-plan":
        return (
            f"Starting CSS:\n{row['inputCss']}\n\n"
            f"Edit plan:\n{row['editPlan']}\n\n"
            "Apply the edit plan exactly. Return the complete updated CSS rule only, with no explanation."
        )
    if row["taskKind"] == "chain-edit":
        return (
            f"Starting CSS:\n{row['inputCss']}\n\n"
            f"Requested edit: {row['instruction']}\n"
            "Apply the requested edit exactly. Return the complete updated CSS rule only, with no explanation."
        )
    raise ValueError(f"unexpected task kind: {row['taskKind']!r}")


def _plan_fields(plan: str) -> dict[str, str]:
    lines = plan.splitlines()
    if len(lines) != 5:
        raise ValueError("edit plan must contain exactly five lines")
    result: dict[str, str] = {}
    for field, line in zip(PLAN_FIELDS, lines):
        prefix = field + "="
        if not line.startswith(prefix) or field in result:
            raise ValueError("edit plan fields are missing, duplicated, or out of order")
        value = line[len(prefix):]
        if not value:
            raise ValueError("edit plan fields must not be empty")
        result[field] = value
    return result


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _dev_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    task_sets = {
        "P2-14": json.loads(P2_14.read_text(encoding="utf-8"))["tasks"],
        "P2-01b": json.loads(P2_01B.read_text(encoding="utf-8"))["tasks"],
    }
    report: dict[str, Any] = {}
    for label, tasks in task_sets.items():
        exact = {_norm(task["request"]) for task in tasks}
        maximum = 0.0
        pair = None
        for row in rows:
            left = set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(row["request"])))
            for task in tasks:
                right = set(re.findall(r"[a-z0-9#.%_<>-]+", _norm(task["request"])))
                score = _jaccard(left, right)
                if score > maximum:
                    maximum = score
                    pair = [row["id"], task["id"]]
        report[label] = {
            "exactRequestOverlap": sum(_norm(row["request"]) in exact for row in rows),
            "maxWordJaccard": round(maximum, 6),
            "maxPair": pair,
        }
    return report


def _scenario_core(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["selector"],
        row["operation"],
        row["property"],
        row["sourceValue"],
        row["targetValue"],
        row["inputCss"],
        row["instruction"],
        row["editPlan"],
    )


def verify() -> dict[str, Any]:
    if not CANDIDATE.is_file() or not REVIEW_JSON.is_file():
        raise ValueError("P2-17 candidate or review metadata is missing")
    if _file_sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-17 candidate SHA-256 changed")
    if _file_sha(P2_14) != P2_14_SHA256:
        raise ValueError("P2-14 development set SHA-256 changed")
    if _file_sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("P2-01b development set SHA-256 changed")

    rows = _rows()
    if len(rows) != 180 or _encoded(rows) != _canonical_text_bytes(CANDIDATE):
        raise ValueError("P2-17 candidate count or canonical JSONL encoding changed")

    ids = [row.get("id") for row in rows]
    requests = [row.get("request") for row in rows]
    if len(set(ids)) != 180 or len(set(requests)) != 180:
        raise ValueError("P2-17 candidate IDs and requests must be unique")

    split_counts = Counter(row.get("candidateSplit") for row in rows)
    if split_counts != Counter({"train": 120, "evaluation": 60}):
        raise ValueError(f"unexpected P2-17 split counts: {split_counts}")
    train = [row for row in rows if row["candidateSplit"] == "train"]
    evaluation = [row for row in rows if row["candidateSplit"] == "evaluation"]
    if Counter(row.get("taskKind") for row in train) != EXPECTED_TRAIN_KINDS:
        raise ValueError("P2-17 training task-kind balance changed")
    if Counter(row.get("evaluationTier") for row in evaluation) != EXPECTED_TIERS:
        raise ValueError("P2-17 evaluation tier balance changed")
    if any(row.get("evaluationTier") is not None for row in train):
        raise ValueError("P2-17 training rows must not have evaluation tiers")
    for tier, kind in EXPECTED_TIER_KINDS.items():
        if any(row["taskKind"] != kind for row in evaluation if row["evaluationTier"] == tier):
            raise ValueError(f"P2-17 Tier {tier} task kind changed")

    required = {
        "schemaVersion", "approvalStatus", "candidateSplit", "evaluationTier", "scenarioId",
        "id", "taskKind", "language", "selector", "operation", "property", "sourceValue",
        "targetValue", "inputCss", "instruction", "editPlan", "request", "solution", "checks",
        "provenance",
    }
    plan_passes = 0
    css_passes = 0
    for row in rows:
        if not required.issubset(row):
            raise ValueError(f"{row.get('id')} is missing required metadata")
        if (
            row["schemaVersion"] != 1
            or row["approvalStatus"] != PENDING
            or row["language"] != "css"
            or row["provenance"] != PROVENANCE
        ):
            raise ValueError(f"{row['id']} has invalid fixed metadata")
        if row["instruction"] != _instruction(row):
            raise ValueError(f"{row['id']} instruction drifted")
        if row["editPlan"] != _plan(row):
            raise ValueError(f"{row['id']} edit plan drifted")
        fields = _plan_fields(row["editPlan"])
        expected_fields = {
            "selector": row["selector"],
            "operation": row["operation"],
            "property": row["property"],
            "old": row["sourceValue"] if row["sourceValue"] is not None else "<none>",
            "new": row["targetValue"] if row["targetValue"] is not None else "<none>",
        }
        if fields != expected_fields:
            raise ValueError(f"{row['id']} plan fields differ from metadata")
        if row["request"] != _request(row):
            raise ValueError(f"{row['id']} request drifted")

        selector, before = _parse_rule(row["inputCss"])
        if selector != row["selector"]:
            raise ValueError(f"{row['id']} input selector differs from metadata")
        after = _apply(
            before, row["operation"], row["property"], row["sourceValue"], row["targetValue"]
        )
        expected_css = _render_rule(row["selector"], after)

        if row["taskKind"] == "extract-plan":
            if row["solution"] != row["editPlan"] or row["checks"] != []:
                raise ValueError(f"{row['id']} extraction target changed")
            _plan_fields(row["solution"])
            plan_passes += 1
        else:
            if row["solution"] != expected_css:
                raise ValueError(f"{row['id']} CSS solution differs from deterministic edit")
            expected_check = [{
                "kind": "css_stylesheet_exact",
                "rules": {row["selector"]: {name: value for name, value in after}},
            }]
            if row["checks"] != expected_check:
                raise ValueError(f"{row['id']} CSS checker metadata drifted")
            checked = _check_task(
                {"id": row["id"], "language": "css", "difficulty": "basic", "checks": row["checks"]},
                row["solution"],
                None,
                5.0,
            )
            if not checked["passed"]:
                raise ValueError(f"{row['id']} authored CSS fails repository checker: {checked}")
            css_passes += 1

    if _sha(_encoded(train)) != TRAIN_SHA256:
        raise ValueError("P2-17 training partition SHA-256 changed")
    for tier, digest in TIER_SHA256.items():
        subset = [row for row in evaluation if row["evaluationTier"] == tier]
        if _sha(_encoded(subset)) != digest:
            raise ValueError(f"P2-17 Tier {tier} SHA-256 changed")

    train_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    eval_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in train:
        train_groups[row["scenarioId"]].append(row)
    for row in evaluation:
        eval_groups[row["scenarioId"]].append(row)
    if len(train_groups) != 60 or any(len(group) != 2 for group in train_groups.values()):
        raise ValueError("P2-17 must have exactly 60 paired training scenarios")
    if len(eval_groups) != 20 or any(len(group) != 3 for group in eval_groups.values()):
        raise ValueError("P2-17 must have exactly 20 three-way evaluation scenarios")
    for scenario_id, group in train_groups.items():
        if {row["taskKind"] for row in group} != {"extract-plan", "apply-plan"}:
            raise ValueError(f"{scenario_id} does not contain extract+apply training rows")
        if len({_scenario_core(row) for row in group}) != 1:
            raise ValueError(f"{scenario_id} paired training rows disagree")
    for scenario_id, group in eval_groups.items():
        if {row["evaluationTier"] for row in group} != {"A", "B", "C"}:
            raise ValueError(f"{scenario_id} does not contain all three evaluation tiers")
        if len({_scenario_core(row) for row in group}) != 1:
            raise ValueError(f"{scenario_id} evaluation rows disagree")

    train_scenarios = [group[0] for group in train_groups.values()]
    if Counter(row["operation"] for row in train_scenarios) != EXPECTED_OPERATIONS:
        raise ValueError("P2-17 training operation balance changed")
    if Counter(row["property"] for row in train_scenarios) != EXPECTED_PROPERTIES:
        raise ValueError("P2-17 training property balance changed")

    train_selectors = {row["selector"] for row in train_scenarios}
    eval_scenarios = [group[0] for group in eval_groups.values()]
    eval_selectors = {row["selector"] for row in eval_scenarios}
    if train_selectors & eval_selectors:
        raise ValueError("P2-17 evaluation selector leaked from training")
    if any("train" in selector.casefold() or "eval" in selector.casefold() or "tier" in selector.casefold()
           for selector in train_selectors | eval_selectors):
        raise ValueError("P2-17 selectors must not encode split/tier identity")

    def literal_values(items: list[dict[str, Any]]) -> set[str]:
        return {
            value
            for row in items
            for value in (row["sourceValue"], row["targetValue"])
            if value is not None
        }

    train_values = literal_values(train_scenarios)
    eval_values = literal_values(eval_scenarios)
    if train_values & eval_values:
        raise ValueError("P2-17 evaluation literal value leaked from training")

    if any(row["taskKind"] == "chain-edit" for row in train):
        raise ValueError("P2-17 direct chain tasks must remain absent from training")

    dev_stats = _dev_stats(rows)
    if any(value["exactRequestOverlap"] for value in dev_stats.values()):
        raise ValueError("P2-17 duplicates an existing development request")
    if any(value["maxWordJaccard"] >= 0.70 for value in dev_stats.values()):
        raise ValueError("P2-17 request is unexpectedly close to an existing development request")

    review = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    fixed = {
        "candidate": "p2-17-semantic-binding-candidate-v1",
        "approvalStatus": PENDING,
        "records": 180,
        "trainingRecords": 120,
        "evaluationRecords": 60,
        "trainingScenarioCount": 60,
        "evaluationScenarioCount": 20,
        "trainingTaskKindCounts": dict(EXPECTED_TRAIN_KINDS),
        "evaluationTierCounts": dict(EXPECTED_TIERS),
        "evaluationTierTaskKinds": EXPECTED_TIER_KINDS,
        "trainingOperationScenarioCounts": dict(EXPECTED_OPERATIONS),
        "trainingPropertyScenarioCounts": dict(EXPECTED_PROPERTIES),
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "p214DevelopmentTaskSetSha256": P2_14_SHA256,
        "p201bDevelopmentTaskSetSha256": P2_01B_SHA256,
        "trainEvaluationSelectorOverlap": 0,
        "trainEvaluationLiteralValueOverlap": 0,
        "evaluationLiteralsAreHeldOut": True,
        "directChainTasksIncludedInTraining": False,
        "tokenizerFitted": False,
        "checkpointInitialized": False,
        "trainingRunCreated": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(review.get(key) != value for key, value in fixed.items()):
        raise ValueError("P2-17 review metadata differs from the pinned candidate")

    forbidden_names = {"tokenizer", "initialization", "checkpoint", "run", "pilot"}
    for path in REVIEW_DIR.rglob("*"):
        if any(part.casefold() in forbidden_names for part in path.parts):
            raise ValueError(f"P2-17 candidate review directory contains forbidden artifact: {path}")

    return {
        "verified": True,
        "records": 180,
        "trainingRecords": 120,
        "evaluationRecords": 60,
        "trainingScenarioCount": 60,
        "evaluationScenarioCount": 20,
        "trainingTaskKindCounts": dict(EXPECTED_TRAIN_KINDS),
        "evaluationTierCounts": dict(EXPECTED_TIERS),
        "trainingOperationScenarioCounts": dict(EXPECTED_OPERATIONS),
        "trainingPropertyScenarioCounts": dict(EXPECTED_PROPERTIES),
        "planAuthoredSolutionsPassed": plan_passes,
        "cssAuthoredSolutionsPassed": css_passes,
        "trainEvaluationSelectorOverlap": 0,
        "trainEvaluationLiteralValueOverlap": 0,
        "developmentPromptAudit": dev_stats,
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "approvalStatus": PENDING,
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
        print(f"plex-p2-17-candidate-verify: {exc}", file=sys.stderr)
        raise SystemExit(2)
