"""Strict P2-31 semantic edit-plan schema, prompting, and evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

MAX_PLAN_TASK_SET_BYTES = 1024 * 1024
MAX_PLAN_RESPONSE_BYTES = 16 * 1024
PLAN_SCHEMA_VERSION = "plex-structured-edit-plan-v1"
PROMPT_TEMPLATE_VERSION = "plex-structured-plan-v1"
LANGUAGES = ("html", "css", "javascript")


def canonical_text_sha256(raw: bytes) -> str:
    """Hash UTF-8 text after normalizing platform line endings to LF."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Hash-pinned text input must be UTF-8") from exc
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
ACTIONS = {"create", "modify", "remove"}
TARGET_KINDS = {
    "html": "html-element",
    "css": "css-rule",
    "javascript": "js-function",
}
CONSTRAINT_KINDS = {
    "html": {"element", "attribute", "text", "state", "behavior"},
    "css": {"declaration", "state", "relationship"},
    "javascript": {"behavior", "api", "nonmutation", "state"},
}
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path, maximum_bytes: int) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value, raw


def _bounded_string(value: Any, *, label: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a nonempty trimmed string")
    if len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{label} exceeds its UTF-8 byte limit")
    return value


def _validate_constraint(value: Any, language: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"kind", "key", "value"}:
        raise ValueError("Each plan constraint must contain exactly kind, key, and value")
    kind = _bounded_string(value["kind"], label="constraint kind", maximum=32)
    if kind not in CONSTRAINT_KINDS[language]:
        raise ValueError(f"Constraint kind {kind!r} is not allowed for {language}")
    key = _bounded_string(value["key"], label="constraint key")
    val = _bounded_string(value["value"], label="constraint value")
    return {"kind": kind, "key": key, "value": val}


def validate_plan(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Structured plan must be a JSON object")
    expected_keys = {
        "schemaVersion", "language", "action", "targetKind",
        "targetRole", "constraints", "searchHints",
    }
    if set(value) != expected_keys:
        raise ValueError("Structured plan fields do not match the P2-31 schema")
    if value.get("schemaVersion") != 1:
        raise ValueError("Structured plan schemaVersion must be 1")
    language = value.get("language")
    if language not in LANGUAGES:
        raise ValueError("Structured plan language must be html, css, or javascript")
    action = value.get("action")
    if action not in ACTIONS:
        raise ValueError("Structured plan action must be create, modify, or remove")
    if value.get("targetKind") != TARGET_KINDS[language]:
        raise ValueError("Structured plan targetKind does not match its language")
    target_role = _bounded_string(value.get("targetRole"), label="targetRole", maximum=64)
    if not KEBAB.fullmatch(target_role):
        raise ValueError("targetRole must be lowercase kebab-case")

    constraints = value.get("constraints")
    if not isinstance(constraints, list) or not 1 <= len(constraints) <= 8:
        raise ValueError("Structured plan requires 1 through 8 constraints")
    normalized = [_validate_constraint(item, language) for item in constraints]
    tuples = [(item["kind"], item["key"], item["value"]) for item in normalized]
    if len(set(tuples)) != len(tuples):
        raise ValueError("Structured plan constraints must be unique")

    hints = value.get("searchHints")
    if not isinstance(hints, list) or not 1 <= len(hints) <= 5:
        raise ValueError("Structured plan requires 1 through 5 search hints")
    normalized_hints: list[str] = []
    for hint in hints:
        hint = _bounded_string(hint, label="search hint", maximum=64)
        if ("/" in hint or "\\" in hint or re.search(r"\.(?:html?|css|[cm]?js|jsx|tsx)\b", hint, re.I)):
            raise ValueError("Search hints must be semantic terms, not file paths")
        normalized_hints.append(hint)
    if len({hint.casefold() for hint in normalized_hints}) != len(normalized_hints):
        raise ValueError("Structured plan search hints must be unique")

    return {
        "schemaVersion": 1,
        "language": language,
        "action": action,
        "targetKind": TARGET_KINDS[language],
        "targetRole": target_role,
        "constraints": normalized,
        "searchHints": normalized_hints,
    }


def parse_plan_response(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Structured-plan response is empty")
    if len(text.encode("utf-8")) > MAX_PLAN_RESPONSE_BYTES:
        raise ValueError("Structured-plan response exceeds the 16 KiB limit")
    if "```" in text:
        raise ValueError("Structured-plan response must not contain Markdown fences")
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc:
        raise ValueError("Structured-plan response is not valid JSON") from exc
    return validate_plan(value)


def _validate_expected_plan(value: Any, language: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "action", "targetKind", "targetRole", "constraints", "hintKeywords"
    }:
        raise ValueError("Expected plan has invalid fields")
    action = value.get("action")
    if action not in ACTIONS:
        raise ValueError("Expected plan action is invalid")
    if value.get("targetKind") != TARGET_KINDS[language]:
        raise ValueError("Expected plan targetKind does not match language")
    target_role = _bounded_string(value.get("targetRole"), label="expected targetRole", maximum=64)
    if not KEBAB.fullmatch(target_role):
        raise ValueError("Expected targetRole must be lowercase kebab-case")
    constraints = value.get("constraints")
    if not isinstance(constraints, list) or not 1 <= len(constraints) <= 8:
        raise ValueError("Expected plan requires 1 through 8 constraints")
    normalized = [_validate_constraint(item, language) for item in constraints]
    triples = [(item["kind"], item["key"], item["value"]) for item in normalized]
    if len(set(triples)) != len(triples):
        raise ValueError("Expected constraints must be unique")
    keywords = value.get("hintKeywords")
    if not isinstance(keywords, list) or not 1 <= len(keywords) <= 5:
        raise ValueError("Expected plan requires 1 through 5 hint keywords")
    normalized_keywords = []
    for keyword in keywords:
        keyword = _bounded_string(keyword, label="hint keyword", maximum=32)
        normalized_keywords.append(keyword.casefold())
    if len(set(normalized_keywords)) != len(normalized_keywords):
        raise ValueError("Expected hint keywords must be unique")
    return {
        "action": action,
        "targetKind": value["targetKind"],
        "targetRole": target_role,
        "constraints": normalized,
        "hintKeywords": normalized_keywords,
    }


def validate_plan_task_set(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion", "setId", "kind", "provenance", "purpose",
        "planSchemaVersion", "inferenceDefaults", "gate", "tasks",
    }:
        raise ValueError("P2-31 task set has invalid top-level fields")
    if value.get("schemaVersion") != 1 or value.get("kind") not in {"development", "final"}:
        raise ValueError("P2-31 task set must be schemaVersion 1 and development or final")
    set_id = _bounded_string(value.get("setId"), label="setId", maximum=96)
    _bounded_string(value.get("provenance"), label="provenance", maximum=96)
    _bounded_string(value.get("purpose"), label="purpose", maximum=1024)
    if value.get("planSchemaVersion") != PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported P2-31 plan schema version")

    defaults = value.get("inferenceDefaults")
    if (not isinstance(defaults, dict)
            or set(defaults) != {"temperature", "seed", "maxNewTokens", "promptTemplateVersion"}
            or defaults.get("temperature") != 0.0
            or type(defaults.get("seed")) is not int
            or not 0 <= defaults["seed"] <= 2**63 - 1
            or type(defaults.get("maxNewTokens")) is not int
            or not 1 <= defaults["maxNewTokens"] <= 256
            or defaults.get("promptTemplateVersion") != PROMPT_TEMPLATE_VERSION):
        raise ValueError("P2-31 task set has invalid deterministic inference defaults")

    gate = value.get("gate")
    if (not isinstance(gate, dict)
            or set(gate) != {"minimumPassed", "minimumPerLanguage", "minimumSchemaValid"}
            or type(gate.get("minimumPassed")) is not int
            or type(gate.get("minimumPerLanguage")) is not int
            or type(gate.get("minimumSchemaValid")) is not int):
        raise ValueError("P2-31 task set has invalid gate")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or not tasks or len(tasks) > 60:
        raise ValueError("P2-31 task set must contain 1 through 60 tasks")
    if (not 0 <= gate["minimumPassed"] <= len(tasks)
            or not 0 <= gate["minimumSchemaValid"] <= len(tasks)):
        raise ValueError("P2-31 gate exceeds task count")

    seen: set[str] = set()
    per_language = Counter()
    normalized_tasks = []
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {
            "id", "language", "difficulty", "request", "expectedPlan"
        }:
            raise ValueError("P2-31 task has invalid fields")
        task_id = _bounded_string(task.get("id"), label="task id", maximum=96)
        if task_id in seen:
            raise ValueError("P2-31 task ids must be unique")
        seen.add(task_id)
        language = task.get("language")
        if language not in LANGUAGES:
            raise ValueError("P2-31 task language is invalid")
        if task.get("difficulty") not in {"basic", "edge"}:
            raise ValueError("P2-31 task difficulty is invalid")
        request = _bounded_string(task.get("request"), label="task request", maximum=1024)
        expected = _validate_expected_plan(task.get("expectedPlan"), language)
        normalized_tasks.append({**task, "request": request, "expectedPlan": expected})
        per_language[language] += 1

    if any(per_language[language] == 0 for language in LANGUAGES):
        raise ValueError("P2-31 task set must cover HTML, CSS, and JavaScript")
    if gate["minimumPerLanguage"] > min(per_language.values()):
        raise ValueError("P2-31 per-language gate exceeds available tasks")
    return {**value, "setId": set_id, "tasks": normalized_tasks}


def render_plan_request_prompt(language: str, request: str) -> str:
    if language not in LANGUAGES:
        raise ValueError("Structured-plan prompt language is invalid")
    request = _bounded_string(request, label="structured-plan request", maximum=1024)
    prompt = (
        "Convert the repository-style request into one semantic edit plan.\n"
        "Do not write code. Do not choose a file path, exact selector, or exact repository symbol.\n"
        "Return exactly one JSON object with these fields and no others:\n"
        '{"schemaVersion":1,"language":"html|css|javascript","action":"create|modify|remove",'
        '"targetKind":"html-element|css-rule|js-function","targetRole":"lowercase-kebab-role",'
        '"constraints":[{"kind":"...","key":"...","value":"..."}],'
        '"searchHints":["semantic term"]}\n'
        "The constraints must capture all requested behavior. Search hints are broad semantic terms for "
        "deterministic Plex Code lookup, never file paths.\n"
        f"Language: {language}\n"
        f"Request: {request}\n"
        "JSON:"
    )
    if len(prompt.encode("utf-8")) > 4096:
        raise ValueError("Rendered structured-plan prompt exceeds 4096 UTF-8 bytes")
    return prompt


def render_plan_prompt(task_set: dict[str, Any], task: dict[str, Any]) -> str:
    task_set = validate_plan_task_set(task_set)
    if task["id"] not in {item["id"] for item in task_set["tasks"]}:
        raise ValueError("Task does not belong to the validated P2-31 set")
    return render_plan_request_prompt(task["language"], task["request"])


def _constraint_set(plan: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {(item["kind"], item["key"], item["value"]) for item in plan["constraints"]}


def evaluate_plan_set(
    task_set: dict[str, Any],
    responses: Iterable[dict[str, Any]],
    *,
    task_set_sha256: str | None = None,
    responses_sha256: str | None = None,
) -> dict[str, Any]:
    task_set = validate_plan_task_set(task_set)
    by_id: dict[str, dict[str, Any]] = {}
    for response in responses:
        if not isinstance(response, dict) or set(response) - {"taskId", "text", "truncated"}:
            raise ValueError("P2-31 response rows may contain only taskId, text, and truncated")
        task_id = response.get("taskId")
        if task_id in by_id:
            raise ValueError(f"Duplicate response for task {task_id}")
        if task_id not in {task["id"] for task in task_set["tasks"]}:
            raise ValueError(f"Response references unknown task {task_id}")
        if not isinstance(response.get("text"), str):
            raise ValueError("P2-31 response text must be a string")
        if "truncated" in response and not isinstance(response["truncated"], bool):
            raise ValueError("P2-31 truncated must be boolean")
        by_id[task_id] = response

    results = []
    for task in task_set["tasks"]:
        response = by_id.get(task["id"])
        checks = []
        text = response["text"] if response is not None else ""
        truncated = bool(response.get("truncated", False)) if response else False
        checks.append({"name": "responsePresent", "passed": response is not None})
        checks.append({"name": "notTruncated", "passed": not truncated})
        plan = None
        parse_detail = None
        if response is not None and not truncated:
            try:
                plan = parse_plan_response(text)
            except ValueError as exc:
                parse_detail = str(exc)
        schema_valid = plan is not None
        checks.append({"name": "schemaValid", "passed": schema_valid, "detail": parse_detail})

        expected = task["expectedPlan"]
        if plan is not None:
            joined_hints = " ".join(plan["searchHints"]).casefold()
            semantic = [
                ("language", plan["language"] == task["language"]),
                ("action", plan["action"] == expected["action"]),
                ("targetKind", plan["targetKind"] == expected["targetKind"]),
                ("targetRole", plan["targetRole"] == expected["targetRole"]),
                ("constraintsExact", _constraint_set(plan) == _constraint_set(expected)),
                ("hintCoverage", all(keyword in joined_hints for keyword in expected["hintKeywords"])),
            ]
        else:
            semantic = [(name, False) for name in (
                "language", "action", "targetKind", "targetRole", "constraintsExact", "hintCoverage"
            )]
        checks.extend({"name": name, "passed": passed} for name, passed in semantic)
        passed = all(check["passed"] for check in checks)
        results.append({
            "taskId": task["id"],
            "language": task["language"],
            "difficulty": task["difficulty"],
            "passed": passed,
            "schemaValid": schema_valid,
            "truncated": truncated,
            "checksPassed": sum(check["passed"] for check in checks),
            "checksTotal": len(checks),
            "checks": checks,
        })

    per_language = {}
    for language in LANGUAGES:
        entries = [item for item in results if item["language"] == language]
        passed = sum(item["passed"] for item in entries)
        per_language[language] = {"tasks": len(entries), "passed": passed,
                                  "passRate": passed / len(entries) if entries else 0.0}
    passed_count = sum(item["passed"] for item in results)
    schema_valid_count = sum(item["schemaValid"] for item in results)
    gate = task_set["gate"]
    gate_passed = (
        passed_count >= gate["minimumPassed"]
        and schema_valid_count >= gate["minimumSchemaValid"]
        and all(per_language[language]["passed"] >= gate["minimumPerLanguage"]
                for language in LANGUAGES)
    )
    all_checks = [check for item in results for check in item["checks"]]
    return {
        "schemaVersion": 1,
        "evaluator": "plex-structured-plan-evaluator-v1",
        "taskSetId": task_set["setId"],
        "taskSetKind": task_set["kind"],
        "taskSetSha256": task_set_sha256,
        "responsesSha256": responses_sha256,
        "planSchemaVersion": task_set["planSchemaVersion"],
        "tasks": len(results),
        "passed": passed_count,
        "passRate": passed_count / len(results) if results else 0.0,
        "schemaValid": schema_valid_count,
        "schemaValidRate": schema_valid_count / len(results) if results else 0.0,
        "partialTaskCount": sum(0 < item["checksPassed"] < item["checksTotal"] for item in results),
        "checksPassed": sum(check["passed"] for check in all_checks),
        "checksTotal": len(all_checks),
        "perLanguage": per_language,
        "gate": gate,
        "gatePassed": gate_passed,
        "finalHoldoutOpened": False,
        "results": results,
    }


def evaluate_plan_files(task_set_path: Path, responses_path: Path) -> dict[str, Any]:
    task_set, task_raw = _read_json(task_set_path, MAX_PLAN_TASK_SET_BYTES)
    if responses_path.is_symlink() or not responses_path.is_file():
        raise ValueError("P2-31 responses must be a regular local JSONL file")
    if responses_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-31 responses exceed the 4 MiB limit")
    raw_responses = responses_path.read_bytes()
    responses = []
    for line_number, raw_line in enumerate(raw_responses.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-31 responses JSONL at line {line_number}") from exc
        responses.append(row)
    return evaluate_plan_set(
        task_set,
        responses,
        task_set_sha256=canonical_text_sha256(task_raw),
        responses_sha256=hashlib.sha256(raw_responses).hexdigest(),
    )
