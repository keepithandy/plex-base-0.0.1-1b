"""Read-only diagnostics for structured-plan free-generation failures."""

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


def _load_responses(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Structured-plan responses must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid responses JSONL at line {line_number}") from exc
        if (not isinstance(row, dict)
                or set(row) - {"taskId", "text", "truncated"}
                or not isinstance(row.get("taskId"), str)
                or not isinstance(row.get("text"), str)
                or ("truncated" in row and not isinstance(row["truncated"], bool))):
            raise ValueError(f"Invalid structured-plan response row at line {line_number}")
        if len(row["text"].encode("utf-8")) > MAX_PLAN_RESPONSE_BYTES:
            raise ValueError(f"Structured-plan response at line {line_number} exceeds limit")
        rows.append(row)
    return rows, raw


def _embedded_object(text: str) -> tuple[bool, bool]:
    """Return (JSON object substring parseable, strict plan valid)."""
    first = text.find("{")
    last = text.rfind("}")
    if first < 0 or last < first:
        return False, False
    candidate = text[first:last + 1]
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return False, False
    if not isinstance(value, dict):
        return False, False
    try:
        parse_plan_response(candidate)
    except ValueError:
        return True, False
    return True, True


def _diagnostic_contract(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("P2-34 diagnostic contract must be a regular JSON file under 1 MiB")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict)
            or value.get("schemaVersion") != 1
            or value.get("milestone") != "P2-34"
            or value.get("kind") != "plex-p2-34-output-boundary-diagnostic-contract-v1"
            or value.get("status") != "diagnostic-authorized"
            or value.get("modelTrainingAuthorized") is not False):
        raise ValueError("P2-34 diagnostic contract is invalid")
    protected = value.get("protectedEvaluation")
    if (not isinstance(protected, dict)
            or protected.get("noResponseRepair") is not True
            or protected.get("noRescoring") is not True
            or protected.get("noGradientUpdates") is not True
            or protected.get("finalProjectHoldoutMustRemainClosed") is not True):
        raise ValueError("P2-34 protected diagnostic boundary is invalid")
    return value


def diagnose_structured_plan_responses(
    *,
    task_set_path: Path,
    responses_path: Path,
    contract_path: Path | None = None,
) -> dict[str, Any]:
    """Classify raw output-boundary failures without changing or repairing responses."""
    if (task_set_path.is_symlink() or not task_set_path.is_file()
            or task_set_path.stat().st_size > MAX_PLAN_TASK_SET_BYTES):
        raise ValueError("Structured-plan task set is missing, linked, or oversized")
    task_raw = task_set_path.read_bytes()
    task_set = validate_plan_task_set(json.loads(task_raw.decode("utf-8")))
    responses, response_raw = _load_responses(responses_path)
    task_sha = canonical_text_sha256(task_raw)
    responses_sha = hashlib.sha256(response_raw).hexdigest()
    contract = None
    if contract_path is not None:
        contract = _diagnostic_contract(contract_path)
        expected_task = contract.get("taskSet")
        expected_responses = contract.get("responses")
        if (not isinstance(expected_task, dict)
                or expected_task.get("sha256") != task_sha
                or expected_task.get("tasks") != len(task_set["tasks"])):
            raise ValueError("P2-34 task set differs from the authorized diagnostic input")
        if (not isinstance(expected_responses, dict)
                or expected_responses.get("sha256") != responses_sha):
            raise ValueError("P2-34 responses differ from the authorized diagnostic input")

    task_ids = {task["id"] for task in task_set["tasks"]}
    seen: set[str] = set()
    details: list[dict[str, Any]] = []
    classifications = Counter()
    first_chars = Counter()
    prefix_counts = Counter()
    unique_texts = Counter()

    for row in responses:
        task_id = row["taskId"]
        if task_id not in task_ids:
            raise ValueError(f"Diagnostic response references unknown task {task_id}")
        if task_id in seen:
            raise ValueError(f"Duplicate diagnostic response for task {task_id}")
        seen.add(task_id)

        text = row["text"]
        stripped = text.lstrip()
        unique_texts[text] += 1
        first = stripped[:1] if stripped else "<empty>"
        first_chars[first] += 1
        prefix_counts[stripped[:24]] += 1

        strict_valid = False
        strict_error = None
        try:
            parse_plan_response(text)
            strict_valid = True
        except ValueError as exc:
            strict_error = str(exc)

        embedded_json, embedded_plan = _embedded_object(text)
        has_fence = (chr(96) * 3) in text
        has_open = "{" in text
        has_close = "}" in text
        has_schema = '"schemaVersion"' in text
        begins_brace = stripped.startswith("{")
        ends_brace = text.rstrip().endswith("}")

        if strict_valid:
            classification = "strict-valid-plan"
        elif has_fence:
            classification = "markdown-fenced"
        elif embedded_plan:
            classification = "extra-text-around-valid-plan"
        elif embedded_json:
            classification = "embedded-json-wrong-schema"
        elif has_open:
            classification = "malformed-json-candidate"
        else:
            classification = "no-json-object-start"
        classifications[classification] += 1

        details.append({
            "taskId": task_id,
            "truncated": bool(row.get("truncated", False)),
            "classification": classification,
            "strictError": strict_error,
            "bytes": len(text.encode("utf-8")),
            "characters": len(text),
            "firstNonWhitespace": first,
            "startsWithOpeningBrace": begins_brace,
            "endsWithClosingBrace": ends_brace,
            "containsOpeningBrace": has_open,
            "containsClosingBrace": has_close,
            "containsSchemaVersionKey": has_schema,
            "containsMarkdownFence": has_fence,
            "embeddedJsonObjectParseable": embedded_json,
            "embeddedStrictPlanValid": embedded_plan,
            "preview": text[:240].replace("\r", "\\r").replace("\n", "\\n"),
        })

    missing = sorted(task_ids - seen)
    duplicate_outputs = sum(count - 1 for count in unique_texts.values() if count > 1)
    return {
        "schemaVersion": 1,
        "milestone": "P2-34",
        "kind": "plex-structured-plan-output-boundary-diagnostic-v1",
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "taskSetId": task_set["setId"],
        "taskSetSha256": task_sha,
        "responsesSha256": responses_sha,
        "contractSha256": hashlib.sha256(contract_path.read_bytes()).hexdigest() if contract_path is not None else None,
        "tasksExpected": len(task_ids),
        "responsesPresent": len(responses),
        "missingResponses": missing,
        "truncatedResponses": sum(bool(row.get("truncated", False)) for row in responses),
        "uniqueResponseTexts": len(unique_texts),
        "duplicateResponseTexts": duplicate_outputs,
        "strictValidPlans": classifications["strict-valid-plan"],
        "classifications": dict(sorted(classifications.items())),
        "firstNonWhitespaceCharacters": dict(sorted(first_chars.items())),
        "mostCommonPrefixes": [
            {"prefix": prefix, "count": count}
            for prefix, count in prefix_counts.most_common(10)
        ],
        "signals": {
            "startsWithOpeningBrace": sum(item["startsWithOpeningBrace"] for item in details),
            "endsWithClosingBrace": sum(item["endsWithClosingBrace"] for item in details),
            "containsOpeningBrace": sum(item["containsOpeningBrace"] for item in details),
            "containsClosingBrace": sum(item["containsClosingBrace"] for item in details),
            "containsSchemaVersionKey": sum(item["containsSchemaVersionKey"] for item in details),
            "containsMarkdownFence": sum(item["containsMarkdownFence"] for item in details),
            "embeddedJsonObjectParseable": sum(item["embeddedJsonObjectParseable"] for item in details),
            "embeddedStrictPlanValid": sum(item["embeddedStrictPlanValid"] for item in details),
        },
        "responses": details,
    }
