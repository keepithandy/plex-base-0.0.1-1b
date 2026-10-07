"""P2-32 structured-plan curriculum review and tokenizer preflight."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import (
    canonical_text_sha256,
    parse_plan_response,
    render_plan_request_prompt,
    validate_plan_task_set,
)
from .tokenizer import EOS_ID

EXPECTED_CANDIDATE_SHA256 = "608cf988b96e8578fa2c7948a12e298c4ed25c640098a2bf3710f3b3cc6802d3"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_TOKENIZER_BUNDLE_SHA256 = "7753b1518b737e7f6b8e0b64f4f829b027ed3aad5b33a7613b3715481448eec5"
EXPECTED_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "splitGroupId", "language",
    "level", "taskKind", "provenance", "approvalStatus", "request",
    "solution", "targetRole", "targetKind", "action",
}
EXPECTED_TASK_KIND = {
    "A": "structured-plan-serialization",
    "B": "structured-plan-field-binding",
    "C": "structured-plan-semantic-composition",
}


def _json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _candidate_rows(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-32 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-32 JSONL at line {line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-32 line {line_number} is not an object")
        rows.append(row)
    return rows, raw


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (value.get("schemaVersion") != 1
            or value.get("milestone") != "P2-32"
            or value.get("kind") != "plex-p2-32-structured-plan-preparation-contract-v1"
            or value.get("status") != "preparation-only-awaiting-owner-review"
            or value.get("dataPreparationAuthorized") is not True
            or value.get("modelTrainingAuthorized") is not False
            or value.get("automaticTrainingExtension") is not False):
        raise ValueError("P2-32 preparation contract is invalid")
    protected = value.get("protectedEvaluation")
    if (not isinstance(protected, dict)
            or protected.get("p231DevelopmentExcludedFromTraining") is not True
            or protected.get("p201bExcludedFromTraining") is not True
            or protected.get("finalProjectHoldoutMustRemainClosed") is not True):
        raise ValueError("P2-32 protected-evaluation boundary is invalid")
    return value


def review_structured_plan_curriculum(
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
        raise ValueError("P2-32 candidate SHA-256 differs from the reviewed candidate")
    if (review.get("schemaVersion") != 1
            or review.get("milestone") != "P2-32"
            or review.get("candidateId") != "p2-32-structured-plan-candidate-v1"
            or review.get("status") != "pending-owner-review"
            or review.get("candidateSha256") != candidate_sha):
        raise ValueError("P2-32 review metadata does not match the candidate")
    curriculum = contract.get("curriculum")
    if (not isinstance(curriculum, dict)
            or curriculum.get("candidateSha256") != candidate_sha
            or curriculum.get("records") != 96
            or curriculum.get("trainRecords") != 72
            or curriculum.get("validationRecords") != 24):
        raise ValueError("P2-32 preparation contract does not pin the reviewed curriculum")

    dev_raw = development_task_set_path.read_bytes()
    if canonical_text_sha256(dev_raw) != EXPECTED_DEV_SHA256:
        raise ValueError("P2-31 development task set identity changed")
    dev = validate_plan_task_set(json.loads(dev_raw.decode("utf-8")))
    if dev.get("kind") != "development" or dev.get("setId") != "p2-31-plan-dev-v1":
        raise ValueError("P2-31 development task set is not the expected sealed development evidence")
    dev_roles = {task["expectedPlan"]["targetRole"] for task in dev["tasks"]}
    dev_requests = {task["request"] for task in dev["tasks"]}

    ids: set[str] = set()
    requests: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    split_language = Counter()
    rendered: list[tuple[dict[str, Any], str]] = []

    for row in rows:
        if set(row) != EXPECTED_FIELDS:
            raise ValueError("P2-32 candidate row fields differ from the reviewed schema")
        if row.get("schemaVersion") != 1:
            raise ValueError("P2-32 row schemaVersion must be 1")
        record_id = row.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in ids:
            raise ValueError("P2-32 record ids must be unique nonempty strings")
        ids.add(record_id)
        split = row.get("candidateSplit")
        if split not in {"train", "validation"}:
            raise ValueError("P2-32 candidateSplit must be train or validation")
        group = row.get("splitGroupId")
        language = row.get("language")
        level = row.get("level")
        request = row.get("request")
        solution = row.get("solution")
        if (not isinstance(group, str) or not group
                or language not in {"html", "css", "javascript"}
                or level not in EXPECTED_TASK_KIND
                or row.get("taskKind") != EXPECTED_TASK_KIND[level]
                or row.get("provenance") != "project-authored-p2-32-structured-plan-candidate"
                or row.get("approvalStatus") != "pending-owner-review"
                or not isinstance(request, str) or not request.strip()
                or not isinstance(solution, str) or not solution.strip()):
            raise ValueError("P2-32 row metadata is invalid")
        if request in requests:
            raise ValueError("P2-32 candidate requests must be unique")
        requests.add(request)
        if request in dev_requests:
            raise ValueError("P2-32 candidate contains an exact P2-31 development request")
        plan = parse_plan_response(solution)
        if (plan["language"] != language
                or plan["action"] != row.get("action")
                or plan["targetKind"] != row.get("targetKind")
                or plan["targetRole"] != row.get("targetRole")):
            raise ValueError("P2-32 solution identity fields differ from its row metadata")
        if plan["targetRole"] in dev_roles:
            raise ValueError("P2-32 targetRole overlaps P2-31 development")
        groups[group].append(row)
        split_language[(split, language)] += 1
        rendered.append((row, render_plan_request_prompt(language, request) + solution))

    if len(rows) != 96 or len(groups) != 24:
        raise ValueError("P2-32 candidate must contain exactly 96 records in 24 semantic groups")
    expected_counts = {
        ("train", "html"): 24, ("train", "css"): 24, ("train", "javascript"): 24,
        ("validation", "html"): 8, ("validation", "css"): 8, ("validation", "javascript"): 8,
    }
    if dict(split_language) != expected_counts:
        raise ValueError("P2-32 split/language counts differ from the reviewed design")

    train_groups = validation_groups = 0
    for group_id, entries in groups.items():
        if len(entries) != 4:
            raise ValueError(f"P2-32 group {group_id} must contain exactly four records")
        splits = {entry["candidateSplit"] for entry in entries}
        languages = {entry["language"] for entry in entries}
        roles = {entry["targetRole"] for entry in entries}
        level_counts = Counter(entry["level"] for entry in entries)
        if len(splits) != 1 or len(languages) != 1 or len(roles) != 1:
            raise ValueError("P2-32 semantic groups may not cross split/language/targetRole")
        if level_counts != {"A": 1, "B": 1, "C": 2}:
            raise ValueError("P2-32 each semantic group must contain A=1, B=1, C=2")
        if "train" in splits:
            train_groups += 1
        else:
            validation_groups += 1
    if (train_groups, validation_groups) != (18, 6):
        raise ValueError("P2-32 group split must be 18 train / 6 validation")

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
            raise ValueError("P2-32 local preflight requires the frozen P2-30 tokenizer bundle")
        maximum = 0
        token_counts = {"train": 0, "validation": 0}
        for row, text in rendered:
            ids_for_text = tokenizer.encode(text)
            if tokenizer.decode(ids_for_text) != text:
                raise ValueError("P2-32 rendered training record failed tokenizer roundtrip")
            count = len(ids_for_text) + 1
            if count > DEFAULT_CONFIG.context_length + 1:
                raise ValueError(f"P2-32 record {row['id']} exceeds the model context limit")
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
        "milestone": "P2-32",
        "status": "candidate-review-passed",
        "candidateSha256": candidate_sha,
        "records": len(rows),
        "trainRecords": 72,
        "validationRecords": 24,
        "groups": len(groups),
        "trainGroups": train_groups,
        "validationGroups": validation_groups,
        "perLanguage": {
            language: {
                "train": split_language[("train", language)],
                "validation": split_language[("validation", language)],
            }
            for language in ("html", "css", "javascript")
        },
        "solutionsSchemaValid": len(rows),
        "developmentTargetRoleOverlap": 0,
        "developmentExactRequestOverlap": 0,
        "tokenizerPreflight": tokenizer_result,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
