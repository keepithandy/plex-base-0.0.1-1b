"""P2-35 JSON serialization-stability curriculum review and tokenizer preflight."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import (
    CONSTRAINT_KINDS,
    TARGET_KINDS,
    canonical_text_sha256,
    parse_plan_response,
    render_plan_request_prompt,
    validate_plan_task_set,
)

EXPECTED_CANDIDATE_SHA256 = "2abd94ee05da241848e06500b0df43fd0f70e19af75c199ef6d73181fa8a1bad"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_TOKENIZER_BUNDLE_SHA256 = "a0d3663bf3ba9a9653ceb52e35594bf3271e4e56cc483dd66f9d149ca38bc6fd"
EXPECTED_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "splitGroupId", "language",
    "level", "taskKind", "renderMode", "provenance", "approvalStatus",
    "prompt", "solution", "targetRole", "targetKind", "action",
}
EXPECTED_TASK_KIND = {
    "A": "json-flat-prefix",
    "B": "json-plan-identity",
    "C": "json-constraint-object",
    "D": "json-nested-arrays",
    "E": "full-plan-explicit-serialization",
    "F": "full-plan-request-binding",
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key in P2-35 solution: {key}")
        value[key] = item
    return value


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _candidate_rows(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-35 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-35 JSONL at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-35 line {line_number} is not an object")
        rows.append(row)
    return rows, raw


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (value.get("schemaVersion") != 1
            or value.get("milestone") != "P2-35"
            or value.get("kind") != "plex-p2-35-serialization-stability-preparation-contract-v1"
            or value.get("status") != "preparation-only-awaiting-owner-review"
            or value.get("dataPreparationAuthorized") is not True
            or value.get("modelTrainingAuthorized") is not False
            or value.get("automaticTrainingExtension") is not False):
        raise ValueError("P2-35 preparation contract is invalid")
    protected = value.get("protectedEvaluation")
    if (not isinstance(protected, dict)
            or protected.get("p231DevelopmentExcludedFromTraining") is not True
            or protected.get("p233ResponsesExcludedFromTraining") is not True
            or protected.get("p201bExcludedFromTraining") is not True
            or protected.get("finalProjectHoldoutMustRemainClosed") is not True):
        raise ValueError("P2-35 protected-evaluation boundary is invalid")
    return value


def _micro_prompt(prompt: str) -> str:
    return (
        "Practice exact JSON serialization.\n"
        "Return exactly one compact JSON object and no extra text.\n"
        f"Task: {prompt}\n"
        "JSON:"
    )


def render_p235_record(row: dict[str, Any]) -> str:
    if row["renderMode"] == "structured-plan":
        prefix = render_plan_request_prompt(row["language"], row["prompt"])
    elif row["renderMode"] == "micro-json":
        prefix = _micro_prompt(row["prompt"])
    else:
        raise ValueError("P2-35 renderMode must be micro-json or structured-plan")
    return prefix + row["solution"]


def _solution_object(row: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(row["solution"], object_pairs_hook=_unique_object)
    except json.JSONDecodeError as exc:
        raise ValueError(f"P2-35 solution {row['id']} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("P2-35 every solution must be a JSON object")
    return value


def review_serialization_stability_curriculum(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    contract_path: Path,
    bundle_dir: Path | None = None,
) -> dict[str, Any]:
    contract = _contract(contract_path)
    review = _json(review_path)
    rows, raw_candidate = _candidate_rows(candidate_path)
    candidate_sha = canonical_text_sha256(raw_candidate)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("P2-35 candidate SHA-256 differs from the reviewed candidate")
    if (review.get("schemaVersion") != 1
            or review.get("milestone") != "P2-35"
            or review.get("candidateId") != "p2-35-serialization-stability-candidate-v1"
            or review.get("status") != "pending-owner-review"
            or review.get("candidateSha256") != candidate_sha):
        raise ValueError("P2-35 review metadata does not match the candidate")
    curriculum = contract.get("curriculum")
    if (not isinstance(curriculum, dict)
            or curriculum.get("candidateSha256") != candidate_sha
            or curriculum.get("records") != 144
            or curriculum.get("trainRecords") != 108
            or curriculum.get("validationRecords") != 36):
        raise ValueError("P2-35 preparation contract does not pin the reviewed curriculum")

    dev_raw = development_task_set_path.read_bytes()
    if canonical_text_sha256(dev_raw) != EXPECTED_DEV_SHA256:
        raise ValueError("P2-31 development task set identity changed")
    dev = validate_plan_task_set(json.loads(dev_raw.decode("utf-8")))
    dev_roles = {task["expectedPlan"]["targetRole"] for task in dev["tasks"]}
    dev_requests = {task["request"] for task in dev["tasks"]}

    ids: set[str] = set()
    prompts: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    split_language = Counter()
    level_counts = Counter()
    rendered: list[tuple[dict[str, Any], str]] = []
    full_plan_count = 0

    for row in rows:
        if set(row) != EXPECTED_FIELDS:
            raise ValueError("P2-35 candidate row fields differ from the reviewed schema")
        if row.get("schemaVersion") != 1:
            raise ValueError("P2-35 row schemaVersion must be 1")
        record_id = row.get("id")
        split = row.get("candidateSplit")
        group = row.get("splitGroupId")
        language = row.get("language")
        level = row.get("level")
        prompt = row.get("prompt")
        solution = row.get("solution")
        if (not isinstance(record_id, str) or not record_id or record_id in ids
                or split not in {"train", "validation"}
                or not isinstance(group, str) or not group
                or language not in {"html", "css", "javascript"}
                or level not in EXPECTED_TASK_KIND
                or row.get("taskKind") != EXPECTED_TASK_KIND[level]
                or row.get("renderMode") != ("structured-plan" if level == "F" else "micro-json")
                or row.get("provenance") != "project-authored-p2-35-serialization-stability-candidate"
                or row.get("approvalStatus") != "pending-owner-review"
                or not isinstance(prompt, str) or not prompt.strip()
                or not isinstance(solution, str) or not solution.strip()
                or row.get("targetKind") != TARGET_KINDS[language]
                or row.get("action") not in {"create", "modify", "remove"}
                or not isinstance(row.get("targetRole"), str) or not row["targetRole"]):
            raise ValueError("P2-35 row metadata is invalid")
        ids.add(record_id)
        if prompt in prompts:
            raise ValueError("P2-35 prompts must be unique")
        prompts.add(prompt)
        if row["targetRole"] in dev_roles:
            raise ValueError("P2-35 targetRole overlaps P2-31 development")
        if level == "F" and prompt in dev_requests:
            raise ValueError("P2-35 contains an exact P2-31 development request")

        value = _solution_object(row)
        if level == "A":
            if (list(value) != ["schemaVersion", "language", "action"]
                    or value != {"schemaVersion": 1, "language": language, "action": row["action"]}):
                raise ValueError("P2-35 level A solution shape is invalid")
        elif level == "B":
            expected = {
                "schemaVersion": 1,
                "language": language,
                "action": row["action"],
                "targetKind": row["targetKind"],
                "targetRole": row["targetRole"],
            }
            if list(value) != list(expected) or value != expected:
                raise ValueError("P2-35 level B solution shape is invalid")
        elif level == "C":
            if list(value) != ["kind", "key", "value"]:
                raise ValueError("P2-35 level C must serialize kind/key/value in order")
            if value.get("kind") not in CONSTRAINT_KINDS[language]:
                raise ValueError("P2-35 level C constraint kind is invalid")
            if any(not isinstance(value.get(key), str) or not value[key] for key in ("key", "value")):
                raise ValueError("P2-35 level C constraint strings are invalid")
        elif level == "D":
            if list(value) != ["constraints", "searchHints"]:
                raise ValueError("P2-35 level D must contain constraints then searchHints")
            if (not isinstance(value["constraints"], list) or len(value["constraints"]) != 2
                    or not isinstance(value["searchHints"], list) or len(value["searchHints"]) != 2):
                raise ValueError("P2-35 level D array cardinality is invalid")
            for item in value["constraints"]:
                if (not isinstance(item, dict) or list(item) != ["kind", "key", "value"]
                        or item.get("kind") not in CONSTRAINT_KINDS[language]):
                    raise ValueError("P2-35 level D constraint grammar is invalid")
        else:
            plan = parse_plan_response(solution)
            if (plan["language"] != language
                    or plan["action"] != row["action"]
                    or plan["targetKind"] != row["targetKind"]
                    or plan["targetRole"] != row["targetRole"]):
                raise ValueError("P2-35 full-plan solution identity differs from row metadata")
            full_plan_count += 1

        groups[group].append(row)
        split_language[(split, language)] += 1
        level_counts[level] += 1
        rendered.append((row, render_p235_record(row)))

    if len(rows) != 144 or len(groups) != 24:
        raise ValueError("P2-35 candidate must contain exactly 144 records in 24 groups")
    expected_counts = {
        ("train", "html"): 36, ("train", "css"): 36, ("train", "javascript"): 36,
        ("validation", "html"): 12, ("validation", "css"): 12, ("validation", "javascript"): 12,
    }
    if dict(split_language) != expected_counts:
        raise ValueError("P2-35 split/language counts differ from the reviewed design")
    if level_counts != {level: 24 for level in "ABCDEF"}:
        raise ValueError("P2-35 must contain 24 records at every curriculum level")
    if full_plan_count != 48:
        raise ValueError("P2-35 levels E/F must provide exactly 48 strict full plans")

    train_groups = validation_groups = 0
    for group_id, entries in groups.items():
        if len(entries) != 6:
            raise ValueError(f"P2-35 group {group_id} must contain exactly six records")
        if ({entry["level"] for entry in entries} != set("ABCDEF")
                or len({entry["candidateSplit"] for entry in entries}) != 1
                or len({entry["language"] for entry in entries}) != 1
                or len({entry["targetRole"] for entry in entries}) != 1
                or len({entry["targetKind"] for entry in entries}) != 1
                or len({entry["action"] for entry in entries}) != 1):
            raise ValueError("P2-35 group identity/syntax stages are inconsistent")
        by_level = {entry["level"]: _solution_object(entry) for entry in entries}
        full = by_level["E"]
        if by_level["F"] != full:
            raise ValueError("P2-35 E/F full plans must be byte-equivalent JSON values")
        if by_level["A"] != {
            "schemaVersion": full["schemaVersion"], "language": full["language"], "action": full["action"]
        }:
            raise ValueError("P2-35 level A does not match its group full plan")
        if by_level["B"] != {
            key: full[key]
            for key in ("schemaVersion", "language", "action", "targetKind", "targetRole")
        }:
            raise ValueError("P2-35 level B does not match its group full plan")
        if by_level["C"] != full["constraints"][0]:
            raise ValueError("P2-35 level C does not match its first full-plan constraint")
        if by_level["D"] != {
            "constraints": full["constraints"], "searchHints": full["searchHints"]
        }:
            raise ValueError("P2-35 level D does not match its group arrays")
        if entries[0]["candidateSplit"] == "train":
            train_groups += 1
        else:
            validation_groups += 1
    if (train_groups, validation_groups) != (18, 6):
        raise ValueError("P2-35 group split must be 18 train / 6 validation")

    tokenizer_result: dict[str, Any] = {
        "checked": False,
        "tokenizerSha256": None,
        "maximumRecordTokensIncludingEos": None,
        "trainTokenCount": None,
        "validationTokenCount": None,
    }
    if bundle_dir is not None:
        tokenizer, tokenizer_record = _completion_tokenizer(bundle_dir)
        if (tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
                or tokenizer_record.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
                or tokenizer.vocabulary_size != 16384):
            raise ValueError("P2-35 local preflight requires the frozen P2-32 tokenizer bundle")
        maximum = 0
        token_counts = {"train": 0, "validation": 0}
        for row, text in rendered:
            ids_for_text = tokenizer.encode(text)
            if tokenizer.decode(ids_for_text) != text:
                raise ValueError("P2-35 rendered record failed tokenizer roundtrip")
            count = len(ids_for_text) + 1
            if count > DEFAULT_CONFIG.context_length + 1:
                raise ValueError(f"P2-35 record {row['id']} exceeds the model context limit")
            maximum = max(maximum, count)
            token_counts[row["candidateSplit"]] += count
        tokenizer_result = {
            "checked": True,
            "tokenizerSha256": tokenizer_record["tokenizerSha256"],
            "maximumRecordTokensIncludingEos": maximum,
            "trainTokenCount": token_counts["train"],
            "validationTokenCount": token_counts["validation"],
        }

    return {
        "schemaVersion": 1,
        "milestone": "P2-35",
        "status": "candidate-review-passed",
        "candidateSha256": candidate_sha,
        "records": 144,
        "trainRecords": 108,
        "validationRecords": 36,
        "groups": 24,
        "trainGroups": train_groups,
        "validationGroups": validation_groups,
        "perLanguage": {
            language: {
                "train": split_language[("train", language)],
                "validation": split_language[("validation", language)],
            }
            for language in ("html", "css", "javascript")
        },
        "perLevel": {level: level_counts[level] for level in "ABCDEF"},
        "jsonObjectSolutions": 144,
        "strictFullPlanSolutions": full_plan_count,
        "developmentTargetRoleOverlap": 0,
        "developmentExactRequestOverlap": 0,
        "p233ResponsesUsedForTraining": False,
        "tokenizerPreflight": tokenizer_result,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
