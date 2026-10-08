"""Deterministic P2-41 request-conditioned plan-binding candidate generation and review."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import (
    TARGET_KINDS,
    canonical_text_sha256,
    parse_plan_response,
    render_plan_request_prompt,
    validate_plan_task_set,
)

MILESTONE = "P2-41"
CONTRACT_KIND = "plex-p2-41-request-conditioned-plan-binding-preparation-contract-v1"
GENERATOR_VERSION = "p2-41-request-binding-generator-v1"
PROVENANCE = "project-authored-p2-41-request-conditioned-plan-binding"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_TOKENIZER_BUNDLE_SHA256 = "17f02f7f0b786be770f964b445854684fee0a010793672149e7fcc6c611aae5d"
LANGUAGE_CODES = {"html": "html", "css": "css", "javascript": "js"}
CONTRAST_FAMILIES = ("role", "constraints", "action", "hints")
ACTIONS = ("create", "modify", "remove")
VARIANTS = ("primary", "secondary", "tertiary")
CONTEXTS = ("settings", "onboarding", "account")
ROW_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "contrastGroupId", "contrastFamily",
    "language", "provenance", "request", "solution", "targetRole", "targetKind", "action",
}
TOPICS = {
    "html": (
        "contact-region", "address-control", "navigation-region", "alert-message",
        "help-disclosure", "pricing-table", "search-control", "language-selector",
        "media-caption", "status-banner", "pagination-control", "consent-options",
    ),
    "css": (
        "card-layout", "profile-grid", "focus-treatment", "sticky-toolbar",
        "expanded-panel", "button-row", "notice-spacing", "content-columns",
        "print-summary", "modal-layer", "badge-alignment", "form-density",
    ),
    "javascript": (
        "currency-format", "unique-records", "score-average", "item-toggle",
        "sum-by-key", "name-sort", "email-normalizer", "range-clamp",
        "record-index", "retry-policy", "selection-filter", "date-label",
    ),
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


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


def _contract(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    design = value.get("design")
    protected = value.get("protectedEvaluation")
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != CONTRACT_KIND
        or value.get("status") != "design-preparation-only"
        or value.get("dataPreparationAuthorized") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("automaticTrainingExtension") is not False
        or value.get("trainingCommand") is not None
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-41 preparation contract does not preserve zero-update status")
    if (
        not isinstance(design, dict)
        or design.get("generatorVersion") != GENERATOR_VERSION
        or design.get("records") != 108
        or design.get("groups") != 36
        or design.get("recordsPerGroup") != 3
        or design.get("trainGroups") != 24
        or design.get("validationGroups") != 12
        or design.get("trainRecords") != 72
        or design.get("validationRecords") != 36
        or design.get("groupsPerLanguage") != 12
        or design.get("groupsPerContrastFamily") != 9
        or design.get("renderMode") != "structured-plan-production-prompt-only"
        or design.get("targetFormat") != "strict-full-plan-only"
        or design.get("tokenizerRefit") is not False
    ):
        raise ValueError("P2-41 design contract differs from the deterministic topology")
    if (
        not isinstance(protected, dict)
        or protected.get("p231DevelopmentExactRequestsExcluded") is not True
        or protected.get("p231DevelopmentTargetRolesExcluded") is not True
        or protected.get("p231DevelopmentExpectedPlansExcluded") is not True
        or protected.get("finalProjectHoldoutMustRemainClosed") is not True
    ):
        raise ValueError("P2-41 protected evaluation boundary is invalid")
    return value


def _constraint(language: str, topic: str, variant: str) -> list[dict[str, str]]:
    if language == "html":
        return [
            {"kind": "element", "key": "semantic-element", "value": variant},
            {"kind": "behavior", "key": "purpose", "value": topic},
        ]
    if language == "css":
        return [
            {"kind": "declaration", "key": "layout-mode", "value": variant},
            {"kind": "relationship", "key": "applies-to", "value": topic},
        ]
    return [
        {"kind": "behavior", "key": "operation", "value": variant},
        {"kind": "nonmutation", "key": "input-policy", "value": topic},
    ]


def _shared_constraint(language: str, topic: str) -> list[dict[str, str]]:
    if language == "html":
        return [
            {"kind": "element", "key": "semantic-element", "value": "section"},
            {"kind": "behavior", "key": "purpose", "value": topic},
        ]
    if language == "css":
        return [
            {"kind": "declaration", "key": "display", "value": "grid"},
            {"kind": "relationship", "key": "applies-to", "value": topic},
        ]
    return [
        {"kind": "behavior", "key": "result-policy", "value": "deterministic"},
        {"kind": "nonmutation", "key": "input-policy", "value": topic},
    ]


def _family_for_group(index: int) -> str:
    return CONTRAST_FAMILIES[(index - 1) % len(CONTRAST_FAMILIES)]


def _split_for_group(index: int) -> str:
    return "train" if index <= 8 else "validation"


def _row(language: str, topic: str, group_index: int, variant_index: int) -> dict[str, Any]:
    family = _family_for_group(group_index)
    variant = VARIANTS[variant_index]
    context = CONTEXTS[variant_index]
    split = _split_for_group(group_index)
    code = LANGUAGE_CODES[language]
    group_id = f"p241-{code}-g{group_index:02d}"
    record_id = f"{group_id}-{variant_index + 1:02d}"
    target_kind = TARGET_KINDS[language]

    if family == "role":
        action = "modify"
        role = f"p241-{topic}-{variant}"
        constraints = _constraint(language, topic, variant)
        hints = [topic.replace("-", " "), variant]
        request = (
            f"Modify the {topic.replace('-', ' ')} request for the {variant} semantic target. "
            f"Keep the language-specific target kind but bind the plan to the {variant} role and requirement."
        )
    elif family == "constraints":
        action = "modify"
        role = f"p241-{topic}-target"
        constraints = _constraint(language, topic, variant)
        hints = [topic.replace("-", " "), "requirements"]
        request = (
            f"Modify the {topic.replace('-', ' ')} target using the {variant} requirement. "
            "The semantic target stays the same; only the requested constraint meaning changes."
        )
    elif family == "action":
        action = ACTIONS[variant_index]
        role = f"p241-{topic}-target"
        constraints = _shared_constraint(language, topic)
        hints = [topic.replace("-", " "), "lifecycle"]
        request = (
            f"{action.capitalize()} the {topic.replace('-', ' ')} semantic target. "
            "Keep its target role and behavior stable so the requested lifecycle action is the discriminating field."
        )
    else:
        action = "modify"
        role = f"p241-{topic}-target"
        constraints = _shared_constraint(language, topic)
        hints = [topic.replace("-", " "), context]
        request = (
            f"Modify the {topic.replace('-', ' ')} target in the {context} context. "
            "Keep the semantic role and constraints unchanged; use the request context to derive the lookup hints."
        )

    plan = {
        "schemaVersion": 1,
        "language": language,
        "action": action,
        "targetKind": target_kind,
        "targetRole": role,
        "constraints": constraints,
        "searchHints": hints,
    }
    solution = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
    parse_plan_response(solution)
    return {
        "schemaVersion": 1,
        "id": record_id,
        "candidateSplit": split,
        "contrastGroupId": group_id,
        "contrastFamily": family,
        "language": language,
        "provenance": PROVENANCE,
        "request": request,
        "solution": solution,
        "targetRole": role,
        "targetKind": target_kind,
        "action": action,
    }


def build_candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for language in ("html", "css", "javascript"):
        for group_index, topic in enumerate(TOPICS[language], start=1):
            for variant_index in range(3):
                rows.append(_row(language, topic, group_index, variant_index))
    return rows


def _candidate_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _development_identity(path: Path) -> tuple[set[str], set[str], set[str]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("P2-31 development task set is missing, linked, or oversized")
    raw = path.read_bytes()
    if canonical_text_sha256(raw) != EXPECTED_DEV_SHA256:
        raise ValueError("P2-31 development task set SHA-256 changed")
    task_set = validate_plan_task_set(
        json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    )
    requests = {task["request"] for task in task_set["tasks"]}
    roles = {task["expectedPlan"]["targetRole"] for task in task_set["tasks"]}
    plans = {
        json.dumps(task["expectedPlan"], sort_keys=True, separators=(",", ":"))
        for task in task_set["tasks"]
    }
    return requests, roles, plans


def _validate_rows(rows: list[dict[str, Any]], development_task_set_path: Path) -> dict[str, Any]:
    if len(rows) != 108:
        raise ValueError("P2-41 requires exactly 108 records")
    dev_requests, dev_roles, dev_plans = _development_identity(development_task_set_path)
    ids: set[str] = set()
    requests: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter()
    roles: set[str] = set()
    exact_dev_plan_overlap = 0

    for row in rows:
        if set(row) != ROW_FIELDS or row.get("schemaVersion") != 1:
            raise ValueError("P2-41 row fields differ from the exact candidate schema")
        record_id = row.get("id")
        language = row.get("language")
        split = row.get("candidateSplit")
        group_id = row.get("contrastGroupId")
        family = row.get("contrastFamily")
        request = row.get("request")
        solution = row.get("solution")
        role = row.get("targetRole")
        if (
            not isinstance(record_id, str)
            or not record_id
            or record_id in ids
            or language not in TARGET_KINDS
            or split not in {"train", "validation"}
            or family not in CONTRAST_FAMILIES
            or not isinstance(group_id, str)
            or not group_id
            or not isinstance(request, str)
            or not request
            or request in requests
            or row.get("provenance") != PROVENANCE
            or row.get("targetKind") != TARGET_KINDS[language]
            or row.get("action") not in {"create", "modify", "remove"}
            or not isinstance(role, str)
            or not role.startswith("p241-")
            or not isinstance(solution, str)
            or not solution
        ):
            raise ValueError(f"Invalid P2-41 row metadata: {record_id}")
        plan = parse_plan_response(solution)
        if any(plan[key] != row[key] for key in ("language", "action", "targetKind", "targetRole")):
            raise ValueError(f"P2-41 plan identity differs from row metadata: {record_id}")
        ids.add(record_id)
        requests.add(request)
        roles.add(role)
        groups[group_id].append(row)
        counts[(split, language)] += 1
        normalized = {
            "action": plan["action"],
            "targetKind": plan["targetKind"],
            "targetRole": plan["targetRole"],
            "constraints": plan["constraints"],
            "hintKeywords": [hint.casefold() for hint in plan["searchHints"]],
        }
        if json.dumps(normalized, sort_keys=True, separators=(",", ":")) in dev_plans:
            exact_dev_plan_overlap += 1

    if requests & dev_requests or roles & dev_roles or exact_dev_plan_overlap:
        raise ValueError("P2-41 candidate overlaps protected P2-31 development targets")
    if len(groups) != 36:
        raise ValueError("P2-41 requires exactly 36 intact contrast groups")
    expected_counts = {
        ("train", language): 24 for language in TARGET_KINDS
    } | {
        ("validation", language): 12 for language in TARGET_KINDS
    }
    if dict(counts) != expected_counts:
        raise ValueError("P2-41 language/split balance changed")

    family_counts = Counter()
    for group_id, members in groups.items():
        if len(members) != 3:
            raise ValueError(f"P2-41 contrast group must contain three records: {group_id}")
        if len({row["candidateSplit"] for row in members}) != 1 or len({row["language"] for row in members}) != 1:
            raise ValueError(f"P2-41 contrast group crosses split or language: {group_id}")
        if len({row["contrastFamily"] for row in members}) != 1:
            raise ValueError(f"P2-41 contrast group mixes contrast families: {group_id}")
        family = members[0]["contrastFamily"]
        plans = [parse_plan_response(row["solution"]) for row in members]
        family_counts[(members[0]["candidateSplit"], members[0]["language"], family)] += 1

        if family == "role":
            if len({plan["targetRole"] for plan in plans}) != 3 or len({plan["action"] for plan in plans}) != 1:
                raise ValueError(f"P2-41 role contrast is not discriminating: {group_id}")
        elif family == "constraints":
            if (
                len({plan["targetRole"] for plan in plans}) != 1
                or len({plan["action"] for plan in plans}) != 1
                or len({json.dumps(plan["searchHints"]) for plan in plans}) != 1
                or len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}) != 3
            ):
                raise ValueError(f"P2-41 constraint contrast is not isolated: {group_id}")
        elif family == "action":
            if (
                {plan["action"] for plan in plans} != {"create", "modify", "remove"}
                or len({plan["targetRole"] for plan in plans}) != 1
                or len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}) != 1
                or len({json.dumps(plan["searchHints"]) for plan in plans}) != 1
            ):
                raise ValueError(f"P2-41 action contrast is not isolated: {group_id}")
        else:
            if (
                len({plan["targetRole"] for plan in plans}) != 1
                or len({plan["action"] for plan in plans}) != 1
                or len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}) != 1
                or len({json.dumps(plan["searchHints"]) for plan in plans}) != 3
            ):
                raise ValueError(f"P2-41 hint contrast is not isolated: {group_id}")

    for language in TARGET_KINDS:
        for family in CONTRAST_FAMILIES:
            if family_counts[("train", language, family)] != 2:
                raise ValueError("P2-41 requires two train groups per language/family")
            if family_counts[("validation", language, family)] != 1:
                raise ValueError("P2-41 requires one validation group per language/family")

    return {
        "records": 108,
        "groups": 36,
        "trainRecords": 72,
        "validationRecords": 36,
        "uniqueRequests": len(requests),
        "uniqueTargetRoles": len(roles),
        "p231ExactRequestOverlap": len(requests & dev_requests),
        "p231TargetRoleOverlap": len(roles & dev_roles),
        "p231ExpectedPlanOverlap": exact_dev_plan_overlap,
        "perLanguage": {
            language: {
                "train": counts[("train", language)],
                "validation": counts[("validation", language)],
            }
            for language in TARGET_KINDS
        },
        "contrastFamilies": {
            family: {
                "groups": sum(
                    count for (split, language, item), count in family_counts.items()
                    if item == family
                ),
                "records": 27,
            }
            for family in CONTRAST_FAMILIES
        },
    }


def generate_request_binding_candidate(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    _contract(contract_path)
    if candidate_path.exists() or review_path.exists():
        raise FileExistsError("P2-41 candidate/review output already exists; choose fresh paths")
    rows = build_candidate_rows()
    summary = _validate_rows(rows, development_task_set_path)
    raw = _candidate_bytes(rows)
    candidate_sha = canonical_text_sha256(raw)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw)
    review = {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "candidateId": "p2-41-request-conditioned-plan-binding-v1",
        "status": "candidate-generated-pending-review",
        "generatorVersion": GENERATOR_VERSION,
        "candidateSha256": candidate_sha,
        "byteCount": len(raw),
        **summary,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
    review_path.write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return review


def review_request_binding_curriculum(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    contract_path: Path,
    bundle_dir: Path | None = None,
) -> dict[str, Any]:
    _contract(contract_path)
    if candidate_path.is_symlink() or not candidate_path.is_file() or candidate_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-41 candidate must be a regular JSONL file under 4 MiB")
    raw = candidate_path.read_bytes()
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-41 JSONL line {number}")
        try:
            row = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-41 JSONL line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-41 line {number} is not an object")
        rows.append(row)

    summary = _validate_rows(rows, development_task_set_path)
    review = _read_json(review_path)
    candidate_sha = canonical_text_sha256(raw)
    if (
        review.get("schemaVersion") != 1
        or review.get("milestone") != MILESTONE
        or review.get("candidateId") != "p2-41-request-conditioned-plan-binding-v1"
        or review.get("status") != "candidate-generated-pending-review"
        or review.get("generatorVersion") != GENERATOR_VERSION
        or review.get("candidateSha256") != candidate_sha
        or review.get("byteCount") != len(raw)
    ):
        raise ValueError("P2-41 review metadata differs from the generated candidate")
    for key, value in summary.items():
        if review.get(key) != value:
            raise ValueError(f"P2-41 review metadata differs on {key}")

    tokenizer_result: dict[str, Any] = {
        "checked": False,
        "tokenizerSha256": None,
        "maximumRecordTokensIncludingEos": None,
        "trainTokenCount": None,
        "validationTokenCount": None,
    }
    if bundle_dir is not None:
        tokenizer, identity = _completion_tokenizer(bundle_dir)
        if (
            identity.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
            or identity.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
            or tokenizer.vocabulary_size != 16384
        ):
            raise ValueError("P2-41 requires the frozen 16,384-token tokenizer")
        token_counts = Counter()
        maximum = 0
        for row in rows:
            text = render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            ids = tokenizer.encode(text)
            if tokenizer.decode(ids) != text:
                raise ValueError(f"P2-41 tokenizer roundtrip failed: {row['id']}")
            count = len(ids) + 1
            if count > DEFAULT_CONFIG.context_length:
                raise ValueError(f"P2-41 record exceeds context: {row['id']} ({count})")
            maximum = max(maximum, count)
            token_counts[row["candidateSplit"]] += count
        tokenizer_result = {
            "checked": True,
            "tokenizerSha256": identity["tokenizerSha256"],
            "maximumRecordTokensIncludingEos": maximum,
            "trainTokenCount": token_counts["train"],
            "validationTokenCount": token_counts["validation"],
        }

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "candidate-review-passed",
        "generatorVersion": GENERATOR_VERSION,
        "candidateSha256": candidate_sha,
        "byteCount": len(raw),
        **summary,
        "tokenizerPreflight": tokenizer_result,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
