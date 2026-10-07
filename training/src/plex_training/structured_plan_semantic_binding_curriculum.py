"""Read-only P2-38 full-plan contrast candidate review and tokenizer preflight."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import (
    TARGET_KINDS, canonical_text_sha256, parse_plan_response,
    render_plan_request_prompt, validate_plan_task_set,
)

EXPECTED_CANDIDATE_SHA256 = "137e2ccf8e015ba74a109ce53f3c7adf502262a4d2a79382e21bfc69a1ea7ab8"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_P235_CANDIDATE_SHA256 = "2abd94ee05da241848e06500b0df43fd0f70e19af75c199ef6d73181fa8a1bad"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_TOKENIZER_BUNDLE_SHA256 = "17f02f7f0b786be770f964b445854684fee0a010793672149e7fcc6c611aae5d"
ROW_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "contrastGroupId", "language",
    "provenance", "approvalStatus", "request", "solution",
    "targetRole", "targetKind", "action",
}
EXPECTED_COUNTS = {
    ("train", "html"): 24, ("validation", "html"): 12,
    ("train", "css"): 24, ("validation", "css"): 12,
    ("train", "javascript"): 24, ("validation", "javascript"): 12,
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path, maximum_bytes: int = 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _candidate_rows(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-38 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    rows = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-38 JSONL line {number}")
        try:
            row = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-38 JSONL line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-38 line {number} is not an object")
        rows.append(row)
    return rows, raw


def _contract(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    design = value.get("design")
    protected = value.get("protectedEvaluation")
    if (value.get("schemaVersion") != 1 or value.get("milestone") != "P2-38"
            or value.get("kind") != "plex-p2-38-semantic-binding-preparation-contract-v1"
            or value.get("status") != "design-preparation-only"
            or value.get("dataPreparationAuthorized") is not True
            or value.get("modelTrainingAuthorized") is not False
            or value.get("automaticTrainingExtension") is not False
            or value.get("trainingCommand") is not None
            or value.get("trainingPerformed") is not False
            or type(value.get("researchOptimizerUpdates")) is not int
            or value["researchOptimizerUpdates"] != 0
            or value.get("finalHoldoutOpened") is not False):
        raise ValueError("P2-38 preparation contract does not preserve zero-update status")
    if (not isinstance(design, dict) or design.get("recordTarget") != 108
            or design.get("contrastGroups") != 36 or design.get("recordsPerGroup") != 3
            or design.get("trainGroups") != 24 or design.get("validationGroups") != 12
            or design.get("trainRecords") != 72 or design.get("validationRecords") != 36
            or design.get("renderMode") != "structured-plan-production-prompt-only"
            or design.get("targetFormat") != "strict-full-plan-only"
            or design.get("uniqueTargetRolePerRecord") is not True
            or design.get("noMicroJsonStages") is not True
            or design.get("tokenizerRefit") is not False):
        raise ValueError("P2-38 design contract differs from the candidate topology")
    for language in TARGET_KINDS:
        if design.get("perLanguage", {}).get(language) != {
            "trainGroups": 8, "validationGroups": 4,
            "trainRecords": 24, "validationRecords": 12,
        }:
            raise ValueError("P2-38 per-language contract is invalid")
    if (not isinstance(protected, dict)
            or any(protected.get(key) is not True for key in (
                "p231DevelopmentExactRequestsExcluded", "p231DevelopmentTargetRolesExcluded",
                "p235TargetRolesExcluded", "p236ResponsesExcludedFromTraining",
                "p201bExcludedFromTraining", "finalProjectHoldoutMustRemainClosed",
            ))):
        raise ValueError("P2-38 protected evaluation boundary is invalid")
    return value


def render_p238_record(row: dict[str, Any]) -> str:
    return render_plan_request_prompt(row["language"], row["request"]) + row["solution"]


def review_semantic_binding_curriculum(
    *, candidate_path: Path, review_path: Path, development_task_set_path: Path,
    p235_candidate_path: Path, contract_path: Path, bundle_dir: Path | None = None,
) -> dict[str, Any]:
    _contract(contract_path)
    rows, raw = _candidate_rows(candidate_path)
    candidate_sha = canonical_text_sha256(raw)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("P2-38 candidate SHA-256 differs from the reviewed candidate")
    review = _read_json(review_path)
    if (review.get("schemaVersion") != 1 or review.get("milestone") != "P2-38"
            or review.get("candidateId") != "p2-38-semantic-binding-candidate-v1"
            or review.get("status") != "pending-owner-review"
            or review.get("candidateSha256") != candidate_sha
            or review.get("byteCount") != len(raw)):
        raise ValueError("P2-38 review metadata differs from the candidate")

    if (development_task_set_path.is_symlink() or not development_task_set_path.is_file()
            or development_task_set_path.stat().st_size > 1024 * 1024):
        raise ValueError("P2-31 development task set is missing, linked, or oversized")
    dev_raw = development_task_set_path.read_bytes()
    if canonical_text_sha256(dev_raw) != EXPECTED_DEV_SHA256:
        raise ValueError("P2-31 development task set SHA-256 changed")
    dev = validate_plan_task_set(json.loads(dev_raw.decode("utf-8"), object_pairs_hook=_unique_object))
    dev_roles = {task["expectedPlan"]["targetRole"] for task in dev["tasks"]}
    dev_requests = {task["request"] for task in dev["tasks"]}
    p235_rows, p235_raw = _candidate_rows(p235_candidate_path)
    if canonical_text_sha256(p235_raw) != EXPECTED_P235_CANDIDATE_SHA256:
        raise ValueError("P2-35 reference candidate SHA-256 changed")
    p235_roles = {row["targetRole"] for row in p235_rows}

    if len(rows) != 108:
        raise ValueError("P2-38 requires exactly 108 full-plan records")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter()
    ids: set[str] = set()
    requests: set[str] = set()
    roles: set[str] = set()
    rendered = []
    for row in rows:
        if set(row) != ROW_FIELDS or row.get("schemaVersion") != 1:
            raise ValueError("P2-38 row fields differ from the exact candidate schema")
        language, split = row.get("language"), row.get("candidateSplit")
        group_id, record_id = row.get("contrastGroupId"), row.get("id")
        request, role, solution = row.get("request"), row.get("targetRole"), row.get("solution")
        if (language not in TARGET_KINDS or split not in {"train", "validation"}
                or not isinstance(group_id, str) or not group_id
                or not isinstance(record_id, str) or not record_id.startswith(group_id + "-")
                or not isinstance(request, str) or not request.strip()
                or not isinstance(role, str) or not role
                or not isinstance(solution, str) or not solution
                or row.get("provenance") != "project-authored-p2-38-semantic-binding-candidate"
                or row.get("approvalStatus") != "pending-owner-review"
                or row.get("targetKind") != TARGET_KINDS[language]
                or row.get("action") not in {"create", "modify", "remove"}):
            raise ValueError(f"Invalid P2-38 row metadata: {record_id}")
        if record_id in ids or request in requests or role in roles:
            raise ValueError("P2-38 IDs, requests, and target roles must be globally unique")
        ids.add(record_id)
        requests.add(request)
        roles.add(role)
        plan = parse_plan_response(solution)
        if any(plan[key] != row[key] for key in ("language", "action", "targetKind", "targetRole")):
            raise ValueError(f"P2-38 plan identity differs from row metadata: {record_id}")
        text = render_p238_record(row)
        groups[group_id].append(row)
        counts[(split, language)] += 1
        rendered.append((row, text))

    if len(groups) != 36 or dict(counts) != EXPECTED_COUNTS:
        raise ValueError("P2-38 group count or language/split balance is invalid")
    group_counts = Counter()
    for group_id, members in groups.items():
        if (len(members) != 3 or len({row["id"] for row in members}) != 3
                or len({row["request"] for row in members}) != 3
                or len({row["targetRole"] for row in members}) != 3
                or len({row["solution"] for row in members}) != 3
                or len({row["language"] for row in members}) != 1
                or len({row["candidateSplit"] for row in members}) != 1):
            raise ValueError(f"P2-38 contrast group is incoherent: {group_id}")
        group_counts[(members[0]["candidateSplit"], members[0]["language"])] += 1
    if dict(group_counts) != {(split, language): count // 3 for (split, language), count in EXPECTED_COUNTS.items()}:
        raise ValueError("P2-38 group split must be 8 train and 4 validation per language")

    overlaps = {
        "p231ExactRequestOverlap": len(requests & dev_requests),
        "p231TargetRoleOverlap": len(roles & dev_roles),
        "p235TargetRoleOverlap": len(roles & p235_roles),
    }
    if any(overlaps.values()):
        raise ValueError(f"Protected request or role overlap: {overlaps}")

    tokenizer_result: dict[str, Any] = {
        "checked": False, "tokenizerSha256": None,
        "maximumRecordTokensIncludingEos": None,
        "trainTokenCount": None, "validationTokenCount": None,
    }
    if bundle_dir is not None:
        tokenizer, identity = _completion_tokenizer(bundle_dir)
        if (identity.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
                or identity.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
                or tokenizer.vocabulary_size != 16384):
            raise ValueError("P2-38 requires the frozen 16,384-token tokenizer")
        token_counts = Counter()
        maximum = 0
        for row, text in rendered:
            token_ids = tokenizer.encode(text)
            if tokenizer.decode(token_ids) != text:
                raise ValueError(f"Tokenizer roundtrip failed: {row['id']}")
            count = len(token_ids) + 1  # one EOS token
            if count > DEFAULT_CONFIG.context_length:
                raise ValueError(f"P2-38 record exceeds 512-token context: {row['id']} ({count})")
            maximum = max(maximum, count)
            token_counts[row["candidateSplit"]] += count
        tokenizer_result = {
            "checked": True, "tokenizerSha256": identity["tokenizerSha256"],
            "maximumRecordTokensIncludingEos": maximum,
            "trainTokenCount": token_counts["train"],
            "validationTokenCount": token_counts["validation"],
        }

    result = {
        "schemaVersion": 1, "milestone": "P2-38", "status": "candidate-review-passed",
        "candidateSha256": candidate_sha, "byteCount": len(raw), "records": 108,
        "groups": 36, "trainGroups": 24, "validationGroups": 12,
        "trainRecords": 72, "validationRecords": 36,
        "perLanguage": {language: {"train": counts[("train", language)],
                                   "validation": counts[("validation", language)]}
                        for language in TARGET_KINDS},
        "uniqueRequests": len(requests), "uniqueTargetRoles": len(roles),
        "strictFullPlanSolutions": len(rendered), **overlaps,
        "tokenizerPreflight": tokenizer_result,
        "modelTrainingAuthorized": False, "trainingPerformed": False,
        "researchOptimizerUpdates": 0, "finalHoldoutOpened": False,
    }
    for key in ("records", "groups", "trainRecords", "validationRecords", "perLanguage",
                "uniqueRequests", "uniqueTargetRoles", "strictFullPlanSolutions", *overlaps):
        if review.get(key) != result[key]:
            raise ValueError(f"P2-38 review metadata differs on {key}")
    if (review.get("trainingPerformed") is not False
            or review.get("modelTrainingAuthorized") is not False
            or review.get("researchOptimizerUpdates") != 0
            or review.get("finalHoldoutOpened") is not False):
        raise ValueError("P2-38 review metadata violates zero-update status")
    if bundle_dir is not None:
        recorded_preflight = review.get("tokenizerPreflight")
        if (not isinstance(recorded_preflight, dict)
                or recorded_preflight.get("checked") is not True
                or recorded_preflight.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
                or any(recorded_preflight.get(key) != tokenizer_result[key] for key in (
                    "tokenizerSha256", "maximumRecordTokensIncludingEos",
                    "trainTokenCount", "validationTokenCount",
                ))):
            raise ValueError("P2-38 recorded tokenizer preflight differs from the local result")
    return result
