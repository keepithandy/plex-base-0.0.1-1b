"""Read-only error decomposition for structured-plan bridge outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .structured_plan import (
    MAX_PLAN_RESPONSE_BYTES,
    MAX_PLAN_TASK_SET_BYTES,
    canonical_text_sha256,
    parse_plan_response,
    validate_plan_task_set,
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _contract(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Bridge diagnostic contract must be a regular JSON file under 1 MiB")
    value = json.loads(path.read_text(encoding="utf-8"))
    allowed = {
        "P2-37": "plex-p2-37-bridge-error-decomposition-contract-v1",
        "P2-40": "plex-p2-40-bridge-error-decomposition-contract-v1",
    }
    milestone = value.get("milestone") if isinstance(value, dict) else None
    if (not isinstance(value, dict)
            or value.get("schemaVersion") != 1
            or milestone not in allowed
            or value.get("kind") != allowed[milestone]
            or value.get("status") != "diagnostic-authorized"
            or value.get("modelTrainingAuthorized") is not False):
        raise ValueError("Bridge diagnostic contract is invalid")
    protected = value.get("protectedEvaluation")
    if (not isinstance(protected, dict)
            or protected.get("noResponseRepair") is not True
            or protected.get("noRescoring") is not True
            or protected.get("noGradientUpdates") is not True
            or protected.get("finalProjectHoldoutMustRemainClosed") is not True):
        raise ValueError("Bridge protected diagnostic boundary is invalid")
    return value


def _load_responses(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-37 responses must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid response JSONL at line {line_number}") from exc
        if (not isinstance(row, dict)
                or set(row) - {"taskId", "text", "truncated"}
                or not isinstance(row.get("taskId"), str)
                or not isinstance(row.get("text"), str)
                or ("truncated" in row and not isinstance(row["truncated"], bool))):
            raise ValueError(f"Invalid response row at line {line_number}")
        if len(row["text"].encode("utf-8")) > MAX_PLAN_RESPONSE_BYTES:
            raise ValueError(f"Response text at line {line_number} exceeds limit")
        rows.append(row)
    return rows, raw


def _constraint_set(plan: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {(item["kind"], item["key"], item["value"]) for item in plan["constraints"]}


def diagnose_bridge_errors(
    *,
    task_set_path: Path,
    responses_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    if (task_set_path.is_symlink() or not task_set_path.is_file()
            or task_set_path.stat().st_size > MAX_PLAN_TASK_SET_BYTES):
        raise ValueError("Bridge task set is missing, linked, or oversized")
    task_raw = task_set_path.read_bytes()
    task_set = validate_plan_task_set(json.loads(task_raw.decode("utf-8")))
    responses, responses_raw = _load_responses(responses_path)
    task_sha = canonical_text_sha256(task_raw)
    responses_sha = hashlib.sha256(responses_raw).hexdigest()

    contract = _contract(contract_path)
    expected_task = contract.get("taskSet")
    expected_responses = contract.get("responses")
    if (not isinstance(expected_task, dict)
            or expected_task.get("sha256") != task_sha
            or expected_task.get("tasks") != len(task_set["tasks"])):
        raise ValueError("Bridge task set differs from authorized diagnostic input")
    if (not isinstance(expected_responses, dict)
            or expected_responses.get("sha256") != responses_sha):
        raise ValueError("Bridge responses differ from authorized diagnostic input")

    by_response: dict[str, dict[str, Any]] = {}
    for row in responses:
        task_id = row["taskId"]
        if task_id in by_response:
            raise ValueError(f"Duplicate bridge response for task {task_id}")
        by_response[task_id] = row

    failure_classes = Counter()
    schema_valid_by_language = Counter()
    field_correct = Counter()
    tasks_out: list[dict[str, Any]] = []

    for task in task_set["tasks"]:
        row = by_response.get(task["id"])
        if row is None:
            failure_classes["missing-response"] += 1
            tasks_out.append({
                "taskId": task["id"],
                "language": task["language"],
                "classification": "missing-response",
            })
            continue

        text = row["text"]
        truncated = bool(row.get("truncated", False))
        strict_plan = None
        strict_error = None
        try:
            strict_plan = parse_plan_response(text)
        except ValueError as exc:
            strict_error = str(exc)

        if strict_plan is None:
            try:
                parsed = json.loads(text, object_pairs_hook=_unique_object)
                parseable_object = isinstance(parsed, dict)
            except (json.JSONDecodeError, ValueError):
                parseable_object = False
            if parseable_object:
                classification = "parseable-json-invalid-plan-schema"
            else:
                classification = "invalid-json"
            failure_classes[classification] += 1
            tasks_out.append({
                "taskId": task["id"],
                "language": task["language"],
                "difficulty": task["difficulty"],
                "classification": classification,
                "truncated": truncated,
                "strictError": strict_error,
                "preview": text[:280].replace("\r", "\\r").replace("\n", "\\n"),
            })
            continue

        schema_valid_by_language[task["language"]] += 1
        expected = task["expectedPlan"]
        joined_hints = " ".join(strict_plan["searchHints"]).casefold()
        checks = {
            "language": strict_plan["language"] == task["language"],
            "action": strict_plan["action"] == expected["action"],
            "targetKind": strict_plan["targetKind"] == expected["targetKind"],
            "targetRole": strict_plan["targetRole"] == expected["targetRole"],
            "constraintsExact": _constraint_set(strict_plan) == _constraint_set(expected),
            "hintCoverage": all(keyword in joined_hints for keyword in expected["hintKeywords"]),
        }
        for name, passed in checks.items():
            if passed:
                field_correct[name] += 1
        all_semantic = all(checks.values())
        classification = "schema-valid-semantic-pass" if all_semantic else "schema-valid-semantic-mismatch"
        failure_classes[classification] += 1
        tasks_out.append({
            "taskId": task["id"],
            "language": task["language"],
            "difficulty": task["difficulty"],
            "classification": classification,
            "truncated": truncated,
            "checks": checks,
            "actual": {
                "language": strict_plan["language"],
                "action": strict_plan["action"],
                "targetKind": strict_plan["targetKind"],
                "targetRole": strict_plan["targetRole"],
                "constraints": strict_plan["constraints"],
                "searchHints": strict_plan["searchHints"],
            },
            "expected": {
                "language": task["language"],
                "action": expected["action"],
                "targetKind": expected["targetKind"],
                "targetRole": expected["targetRole"],
                "constraints": expected["constraints"],
                "hintKeywords": expected["hintKeywords"],
            },
        })

    schema_valid = sum(schema_valid_by_language.values())
    return {
        "schemaVersion": 1,
        "milestone": contract["milestone"],
        "kind": f"plex-{contract['milestone'].lower()}-bridge-error-decomposition-result-v1",
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "taskSetId": task_set["setId"],
        "taskSetSha256": task_sha,
        "responsesSha256": responses_sha,
        "contractSha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "tasksExpected": len(task_set["tasks"]),
        "responsesPresent": len(responses),
        "schemaValid": schema_valid,
        "schemaValidByLanguage": {
            language: schema_valid_by_language[language]
            for language in ("html", "css", "javascript")
        },
        "classifications": dict(sorted(failure_classes.items())),
        "schemaValidFieldCorrect": {
            name: field_correct[name]
            for name in ("language", "action", "targetKind", "targetRole", "constraintsExact", "hintCoverage")
        },
        "tasks": tasks_out,
    }
