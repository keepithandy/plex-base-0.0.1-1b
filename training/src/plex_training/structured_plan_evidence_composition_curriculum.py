"""Deterministic P2-44 evidence-first semantic-composition curriculum."""

from __future__ import annotations

import json
import re
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

MILESTONE = "P2-44"
CONTRACT_KIND = "plex-p2-44-evidence-first-semantic-composition-preparation-contract-v1"
GENERATOR_VERSION = "p2-44-evidence-first-composition-generator-v1"
PROVENANCE = "project-authored-p2-44-evidence-first-semantic-composition"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_TOKENIZER_BUNDLE_SHA256 = "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a"
EXPECTED_CANDIDATE_SHA256 = "fc56eca2186e2b7f643af9fbec514c1d5d34248eba2ac380b9f93c482b945c30"
EXPECTED_CANDIDATE_BYTES = 182492
EXPECTED_MAX_RECORD_TOKENS = 375
EXPECTED_TRAIN_TOKEN_COUNT = 38280
EXPECTED_VALIDATION_TOKEN_COUNT = 19186
LANGUAGE_CODES = {"html": "html", "css": "css", "javascript": "js"}
FAMILIES = (
    "role-composition",
    "constraint-binding",
    "hint-grounding",
    "action-discrimination",
    "cross-field-coherence",
    "near-neighbor",
)
ACTIONS = ("create", "modify", "remove")
CONTEXTS = ("overview", "details", "editor")
ROW_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "contrastGroupId", "contrastFamily",
    "language", "provenance", "request", "solution", "targetRole", "targetKind",
    "action", "semanticAtoms", "evidence",
}
ROLE_DOMAINS = {
    "html": ("profile", "billing", "account", "checkout", "support", "search"),
    "css": ("profile", "account", "product", "notice", "menu", "content"),
    "javascript": ("record", "score", "text", "date", "price", "selection"),
}
ROLE_OBJECTS = {
    "html": ("panel", "form", "message", "summary", "control", "region"),
    "css": ("surface", "stack", "strip", "cluster", "block", "shell"),
    "javascript": ("filter", "mapper", "reducer", "formatter", "indexer", "validator"),
}
REQUIREMENTS = {
    "html": (
        ("html-section", {"kind": "element", "key": "semantic-element", "value": "section"}, "Use a section element"),
        ("html-article", {"kind": "element", "key": "semantic-element", "value": "article"}, "Use an article element"),
        ("html-aside", {"kind": "element", "key": "semantic-element", "value": "aside"}, "Use an aside element"),
        ("html-required", {"kind": "attribute", "key": "required", "value": "true"}, "Mark the control as required"),
        ("html-live", {"kind": "attribute", "key": "aria-live", "value": "polite"}, "Announce updates politely"),
        ("html-visible", {"kind": "state", "key": "hidden", "value": "false"}, "Keep the target exposed rather than hidden"),
    ),
    "css": (
        ("css-flex", {"kind": "declaration", "key": "display", "value": "flex"}, "Use flex layout"),
        ("css-grid", {"kind": "declaration", "key": "display", "value": "grid"}, "Use grid layout"),
        ("css-gap", {"kind": "declaration", "key": "gap", "value": "0.75rem"}, "Keep a 0.75rem gap"),
        ("css-padding", {"kind": "declaration", "key": "padding", "value": "1.25rem"}, "Use 1.25rem padding"),
        ("css-center", {"kind": "declaration", "key": "align-items", "value": "center"}, "Center items on the cross axis"),
        ("css-between", {"kind": "declaration", "key": "justify-content", "value": "space-between"}, "Distribute items with space between"),
    ),
    "javascript": (
        ("js-preserve", {"kind": "nonmutation", "key": "input-array", "value": "preserve"}, "Preserve the input array"),
        ("js-empty", {"kind": "behavior", "key": "empty-input", "value": "return-empty"}, "Return an empty result for empty input"),
        ("js-order", {"kind": "behavior", "key": "order", "value": "preserve-input"}, "Preserve input order"),
        ("js-invalid", {"kind": "behavior", "key": "invalid-value", "value": "ignore"}, "Ignore invalid values"),
        ("js-stable", {"kind": "behavior", "key": "result", "value": "deterministic"}, "Return a deterministic result"),
        ("js-null", {"kind": "behavior", "key": "null-input", "value": "return-null"}, "Return null for null input"),
    ),
}

PAIR_ALLOCATION = {
    "role-composition": {
        "train": (((0, 3), (0, 4), (0, 5)), ((1, 3), (1, 4), (1, 5))),
        "validation": (((0, 0), (0, 1), (0, 2)),),
    },
    "constraint-binding": {
        "train": (((2, 3),), ((2, 4),)),
        "validation": (((3, 0),),),
    },
    "hint-grounding": {
        "train": (((2, 5),), ((3, 3),)),
        "validation": (((3, 1),),),
    },
    "action-discrimination": {
        "train": (((3, 4),), ((3, 5),)),
        "validation": (((3, 2),),),
    },
    "cross-field-coherence": {
        "train": (((4, 0), (4, 1), (4, 2)), ((5, 0), (5, 1), (5, 2))),
        "validation": (((2, 0), (2, 1), (2, 2)),),
    },
    "near-neighbor": {
        "train": (((4, 3), (4, 4), (4, 5)), ((5, 3), (5, 4), (5, 5))),
        "validation": (((1, 0), (1, 1), (1, 2)),),
    },
}
_P2_PREFIX = re.compile(r"^p2\d+(?:-|$)")


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
    split = value.get("splitPolicy")
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != CONTRACT_KIND
        or value.get("status") != "candidate-review-passed-awaiting-training-preparation"
        or value.get("dataPreparationAuthorized") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("automaticTrainingExtension") is not False
        or value.get("trainingCommand") is not None
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-44 preparation contract does not preserve zero-update status")
    if (
        not isinstance(design, dict)
        or design.get("generatorVersion") != GENERATOR_VERSION
        or design.get("records") != 162
        or design.get("groups") != 54
        or design.get("recordsPerGroup") != 3
        or design.get("trainGroups") != 36
        or design.get("validationGroups") != 18
        or design.get("trainRecords") != 108
        or design.get("validationRecords") != 54
        or design.get("groupsPerLanguage") != 18
        or design.get("groupsPerContrastFamily") != 9
        or design.get("productionPromptOnly") is not True
        or design.get("strictFullPlanTargetsOnly") is not True
        or design.get("tokenizerRefit") is not False
        or design.get("opaqueSyntheticRoleIdentifiersProhibited") is not True
        or design.get("heldoutCombinationGeneralizationRequired") is not True
        or design.get("exactTrainingBundleReuseInValidationProhibited") is not True
        or design.get("continuationFromP241NotAuthorized") is not True
    ):
        raise ValueError("P2-44 design contract differs from deterministic topology")
    if (
        not isinstance(split, dict)
        or split.get("validationMustContainNovelAtomCombinations") is not True
        or split.get("validationMayReuseIndividualAtoms") is not True
        or split.get("validationMayNotReuseExactTargetRoles") is not True
        or split.get("validationMayNotReuseExactSemanticBundles") is not True
        or split.get("validationMayNotReuseExactFullPlans") is not True
    ):
        raise ValueError("P2-44 split policy does not preserve compositional holdout")
    if (
        not isinstance(protected, dict)
        or protected.get("p231DevelopmentExactRequestsExcluded") is not True
        or protected.get("p231DevelopmentTargetRolesExcluded") is not True
        or protected.get("p231DevelopmentExpectedPlansExcluded") is not True
        or protected.get("p242ResponsesExcludedFromTraining") is not True
        or protected.get("p243DiagnosticExcludedFromTraining") is not True
        or protected.get("finalProjectHoldoutMustRemainClosed") is not True
    ):
        raise ValueError("P2-44 protected evaluation boundary is invalid")
    frozen = value.get("frozenInputs")
    if (
        not isinstance(frozen, dict)
        or frozen.get("developmentTaskSetSha256") != EXPECTED_DEV_SHA256
        or frozen.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or frozen.get("tokenizerBundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
    ):
        raise ValueError("P2-44 frozen input identity is invalid")
    if value.get("candidateIdentity") != {
        "candidateId": "p2-44-evidence-first-semantic-composition-v1",
        "sha256": EXPECTED_CANDIDATE_SHA256,
        "bytes": EXPECTED_CANDIDATE_BYTES,
    }:
        raise ValueError("P2-44 candidate identity is invalid")
    if value.get("tokenizerPreflight") != {
        "checked": True,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "bundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
        "maximumRecordTokensIncludingEos": EXPECTED_MAX_RECORD_TOKENS,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
    }:
        raise ValueError("P2-44 tokenizer preflight identity is invalid")
    reviewed = value.get("reviewedCandidate")
    if not isinstance(reviewed, dict):
        raise ValueError("P2-44 reviewed candidate metadata is missing")
    expected_reviewed = {
        "records": 162,
        "groups": 54,
        "trainRecords": 108,
        "validationRecords": 54,
        "trainUniqueTargetRoles": 72,
        "validationUniqueTargetRoles": 36,
        "trainValidationExactTargetRoleOverlap": 0,
        "trainValidationExactConstraintSetOverlap": 27,
        "trainValidationExactSearchHintOverlap": 0,
        "trainValidationExactSemanticBundleOverlap": 0,
        "trainValidationExactFullPlanOverlap": 0,
        "validationRoleAtomsSeenInTrain": 19,
        "validationRoleAtomCount": 19,
        "validationConstraintAtomsSeenInTrain": 18,
        "validationConstraintAtomCount": 18,
        "validationHintAtomsSeenInTrain": 22,
        "validationHintAtomCount": 22,
        "p231ExactRequestOverlap": 0,
        "p231TargetRoleOverlap": 0,
        "p231ExpectedPlanOverlap": 0,
    }
    if reviewed != expected_reviewed:
        raise ValueError("P2-44 reviewed candidate metrics changed")
    return value


def _pair(language: str, indexes: tuple[int, int]) -> tuple[str, str]:
    domain_index, object_index = indexes
    return ROLE_DOMAINS[language][domain_index], ROLE_OBJECTS[language][object_index]


def _role(pair: tuple[str, str]) -> str:
    return f"{pair[0]}-{pair[1]}"


def _requirement(language: str, index: int) -> tuple[str, dict[str, str], str]:
    return REQUIREMENTS[language][index % len(REQUIREMENTS[language])]


def _default_requirement_indexes(pair_indexes: tuple[int, int]) -> tuple[int, int]:
    left, right = pair_indexes
    first = (left + right) % 6
    second = (left + 2 * right + 1) % 6
    if second == first:
        second = (second + 1) % 6
    return first, second


def _render_request(
    *, action: str, pair: tuple[str, str], requirement_phrases: list[str],
    hints: list[str], family: str, context: str | None = None,
) -> str:
    role_text = f"{pair[0]} {pair[1]}"
    if action == "create":
        lead = f"Create the {role_text}."
    elif action == "remove":
        lead = f"Remove the existing {role_text} identified by the stated requirements."
    else:
        lead = f"Modify the {role_text}."
    requirements = ". ".join(requirement_phrases) + "."
    hint_text = ", ".join(hints)
    if context is None:
        evidence = f"Use {hint_text} as semantic lookup evidence."
    else:
        evidence = f"In the {context} context, use {hint_text} as semantic lookup evidence."
    if family == "near-neighbor":
        lead += " Distinguish this target from the nearby alternatives with similar wording."
    return f"{lead} {requirements} {evidence} Return only the semantic edit plan."


def _plan(
    *, language: str, action: str, pair: tuple[str, str],
    requirement_indexes: tuple[int, int], hints: list[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    requirements = [_requirement(language, index) for index in requirement_indexes]
    constraints = [item[1] for item in requirements]
    requirement_ids = [item[0] for item in requirements]
    requirement_phrases = [item[2] for item in requirements]
    value = {
        "schemaVersion": 1,
        "language": language,
        "action": action,
        "targetKind": TARGET_KINDS[language],
        "targetRole": _role(pair),
        "constraints": constraints,
        "searchHints": hints,
    }
    parse_plan_response(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return value, requirement_ids, requirement_phrases


def _row(
    *, language: str, split: str, family: str, group_number: int, variant: int,
    pair_indexes: tuple[int, int], requirement_indexes: tuple[int, int],
    action: str = "modify", context: str | None = None,
) -> dict[str, Any]:
    pair = _pair(language, pair_indexes)
    hints = [pair[0], pair[1]]
    if context is not None:
        hints.append(context)
    plan, requirement_ids, requirement_phrases = _plan(
        language=language,
        action=action,
        pair=pair,
        requirement_indexes=requirement_indexes,
        hints=hints,
    )
    request = _render_request(
        action=action,
        pair=pair,
        requirement_phrases=requirement_phrases,
        hints=hints,
        family=family,
        context=context,
    )
    code = LANGUAGE_CODES[language]
    group_id = f"p244-{code}-g{group_number:02d}"
    record_id = f"{group_id}-{variant + 1:02d}"
    return {
        "schemaVersion": 1,
        "id": record_id,
        "candidateSplit": split,
        "contrastGroupId": group_id,
        "contrastFamily": family,
        "language": language,
        "provenance": PROVENANCE,
        "request": request,
        "solution": json.dumps(plan, ensure_ascii=False, separators=(",", ":")),
        "targetRole": plan["targetRole"],
        "targetKind": plan["targetKind"],
        "action": action,
        "semanticAtoms": {
            "role": [pair[0], pair[1]],
            "constraints": requirement_ids,
            "hints": hints,
        },
        "evidence": {
            "rolePhrases": [pair[0], pair[1]],
            "constraintPhrases": requirement_phrases,
            "hintPhrases": hints,
        },
    }


def _rows_for_group(
    *, language: str, split: str, family: str, group_number: int,
    pair_indexes: tuple[tuple[int, int], ...], ordinal: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if family in {"role-composition", "cross-field-coherence", "near-neighbor"}:
        for variant, pair_index in enumerate(pair_indexes):
            base = _default_requirement_indexes(pair_index)
            if family == "cross-field-coherence":
                base = ((base[0] + variant) % 6, (base[1] + variant + 1) % 6)
                if base[0] == base[1]:
                    base = (base[0], (base[1] + 1) % 6)
            rows.append(_row(
                language=language, split=split, family=family,
                group_number=group_number, variant=variant,
                pair_indexes=pair_index, requirement_indexes=base,
            ))
        return rows

    pair_index = pair_indexes[0]
    base = _default_requirement_indexes(pair_index)
    if family == "constraint-binding":
        fixed = base[0]
        variants = [index for index in range(6) if index != fixed][:3]
        for variant, requirement in enumerate(variants):
            rows.append(_row(
                language=language, split=split, family=family,
                group_number=group_number, variant=variant,
                pair_indexes=pair_index, requirement_indexes=(fixed, requirement),
            ))
    elif family == "hint-grounding":
        for variant, context in enumerate(CONTEXTS):
            rows.append(_row(
                language=language, split=split, family=family,
                group_number=group_number, variant=variant,
                pair_indexes=pair_index, requirement_indexes=base,
                context=context,
            ))
    elif family == "action-discrimination":
        for variant, action in enumerate(ACTIONS):
            rows.append(_row(
                language=language, split=split, family=family,
                group_number=group_number, variant=variant,
                pair_indexes=pair_index, requirement_indexes=base,
                action=action,
            ))
    else:
        raise ValueError(f"Unsupported P2-44 contrast family: {family}")
    return rows


def build_candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for language in ("html", "css", "javascript"):
        group_number = 0
        for family in FAMILIES:
            for split in ("train", "validation"):
                for ordinal, pair_indexes in enumerate(PAIR_ALLOCATION[family][split]):
                    group_number += 1
                    rows.extend(_rows_for_group(
                        language=language,
                        split=split,
                        family=family,
                        group_number=group_number,
                        pair_indexes=pair_indexes,
                        ordinal=ordinal,
                    ))
        if group_number != 18:
            raise RuntimeError("P2-44 deterministic group topology is invalid")
    return rows


def _candidate_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _constraint_signature(plan: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    return tuple(sorted((x["kind"], x["key"], x["value"]) for x in plan["constraints"]))


def _hint_signature(plan: dict[str, Any]) -> tuple[str, ...]:
    return tuple(x.casefold() for x in plan["searchHints"])


def _bundle_signature(plan: dict[str, Any]) -> tuple[Any, ...]:
    return (plan["targetRole"], _constraint_signature(plan), _hint_signature(plan))


def _full_signature(plan: dict[str, Any]) -> str:
    return json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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


def _validate_grounding(row: dict[str, Any], plan: dict[str, Any]) -> None:
    request = row["request"].casefold()
    atoms = row.get("semanticAtoms")
    evidence = row.get("evidence")
    if not isinstance(atoms, dict) or set(atoms) != {"role", "constraints", "hints"}:
        raise ValueError(f"P2-44 semantic atom metadata is invalid: {row['id']}")
    if not isinstance(evidence, dict) or set(evidence) != {
        "rolePhrases", "constraintPhrases", "hintPhrases",
    }:
        raise ValueError(f"P2-44 grounding evidence metadata is invalid: {row['id']}")
    role_atoms = atoms["role"]
    constraint_atoms = atoms["constraints"]
    hint_atoms = atoms["hints"]
    if (
        not isinstance(role_atoms, list) or len(role_atoms) != 2
        or not all(isinstance(x, str) and x for x in role_atoms)
        or not isinstance(constraint_atoms, list) or len(constraint_atoms) != 2
        or not all(isinstance(x, str) and x for x in constraint_atoms)
        or not isinstance(hint_atoms, list) or not 2 <= len(hint_atoms) <= 3
        or not all(isinstance(x, str) and x for x in hint_atoms)
    ):
        raise ValueError(f"P2-44 semantic atoms are invalid: {row['id']}")
    if plan["targetRole"] != "-".join(role_atoms):
        raise ValueError(f"P2-44 targetRole is not composed from role atoms: {row['id']}")
    if _P2_PREFIX.match(plan["targetRole"]):
        raise ValueError(f"P2-44 targetRole contains a milestone prefix: {row['id']}")
    for key in ("rolePhrases", "constraintPhrases", "hintPhrases"):
        phrases = evidence[key]
        if not isinstance(phrases, list) or not phrases:
            raise ValueError(f"P2-44 evidence list is invalid: {row['id']}:{key}")
        for phrase in phrases:
            if not isinstance(phrase, str) or phrase.casefold() not in request:
                raise ValueError(f"P2-44 request does not contain declared evidence: {row['id']}:{phrase}")
    if [x.casefold() for x in evidence["hintPhrases"]] != [x.casefold() for x in plan["searchHints"]]:
        raise ValueError(f"P2-44 hints are not identical to declared request evidence: {row['id']}")


def _validate_rows(rows: list[dict[str, Any]], development_task_set_path: Path) -> dict[str, Any]:
    if len(rows) != 162:
        raise ValueError("P2-44 requires exactly 162 records")
    dev_requests, dev_roles, dev_plans = _development_identity(development_task_set_path)
    ids: set[str] = set()
    requests: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter()
    family_groups = Counter()
    roles_by_split: dict[str, set[str]] = {"train": set(), "validation": set()}
    role_atoms_by_split: dict[str, set[str]] = {"train": set(), "validation": set()}
    constraint_atoms_by_split: dict[str, set[str]] = {"train": set(), "validation": set()}
    hint_atoms_by_split: dict[str, set[str]] = {"train": set(), "validation": set()}
    constraints_by_split: dict[str, set[tuple[tuple[str, str, str], ...]]] = {
        "train": set(), "validation": set()
    }
    hints_by_split: dict[str, set[tuple[str, ...]]] = {"train": set(), "validation": set()}
    bundles_by_split: dict[str, set[tuple[Any, ...]]] = {"train": set(), "validation": set()}
    full_by_split: dict[str, set[str]] = {"train": set(), "validation": set()}
    exact_dev_plan_overlap = 0

    for row in rows:
        if set(row) != ROW_FIELDS or row.get("schemaVersion") != 1:
            raise ValueError("P2-44 row fields differ from the exact candidate schema")
        record_id = row.get("id")
        language = row.get("language")
        split = row.get("candidateSplit")
        group_id = row.get("contrastGroupId")
        family = row.get("contrastFamily")
        request = row.get("request")
        solution = row.get("solution")
        role = row.get("targetRole")
        if (
            not isinstance(record_id, str) or not record_id or record_id in ids
            or language not in TARGET_KINDS
            or split not in {"train", "validation"}
            or family not in FAMILIES
            or not isinstance(group_id, str) or not group_id
            or not isinstance(request, str) or not request or request in requests
            or row.get("provenance") != PROVENANCE
            or row.get("targetKind") != TARGET_KINDS[language]
            or row.get("action") not in {"create", "modify", "remove"}
            or not isinstance(role, str) or not role
            or _P2_PREFIX.match(role)
            or not isinstance(solution, str) or not solution
        ):
            raise ValueError(f"Invalid P2-44 row metadata: {record_id}")
        plan = parse_plan_response(solution)
        if any(plan[key] != row[key] for key in ("language", "action", "targetKind", "targetRole")):
            raise ValueError(f"P2-44 plan identity differs from row metadata: {record_id}")
        _validate_grounding(row, plan)

        ids.add(record_id)
        requests.add(request)
        groups[group_id].append(row)
        counts[(split, language)] += 1
        roles_by_split[split].add(role)
        role_atoms_by_split[split].update(row["semanticAtoms"]["role"])
        constraint_atoms_by_split[split].update(row["semanticAtoms"]["constraints"])
        hint_atoms_by_split[split].update(row["semanticAtoms"]["hints"])
        constraints_by_split[split].add(_constraint_signature(plan))
        hints_by_split[split].add(_hint_signature(plan))
        bundles_by_split[split].add(_bundle_signature(plan))
        full_by_split[split].add(_full_signature(plan))

        normalized = {
            "action": plan["action"],
            "targetKind": plan["targetKind"],
            "targetRole": plan["targetRole"],
            "constraints": plan["constraints"],
            "hintKeywords": [hint.casefold() for hint in plan["searchHints"]],
        }
        if json.dumps(normalized, sort_keys=True, separators=(",", ":")) in dev_plans:
            exact_dev_plan_overlap += 1

    if requests & dev_requests or (roles_by_split["train"] | roles_by_split["validation"]) & dev_roles:
        raise ValueError("P2-44 candidate overlaps protected P2-31 requests or target roles")
    if exact_dev_plan_overlap:
        raise ValueError("P2-44 candidate overlaps protected P2-31 expected plans")
    if len(groups) != 54:
        raise ValueError("P2-44 requires exactly 54 contrast groups")
    expected_counts = {
        ("train", language): 36 for language in TARGET_KINDS
    } | {
        ("validation", language): 18 for language in TARGET_KINDS
    }
    if dict(counts) != expected_counts:
        raise ValueError("P2-44 language/split balance changed")

    for group_id, members in groups.items():
        if len(members) != 3:
            raise ValueError(f"P2-44 contrast group must contain three records: {group_id}")
        if len({x["candidateSplit"] for x in members}) != 1:
            raise ValueError(f"P2-44 contrast group crosses split: {group_id}")
        if len({x["language"] for x in members}) != 1:
            raise ValueError(f"P2-44 contrast group crosses language: {group_id}")
        if len({x["contrastFamily"] for x in members}) != 1:
            raise ValueError(f"P2-44 contrast group mixes families: {group_id}")
        split = members[0]["candidateSplit"]
        language = members[0]["language"]
        family = members[0]["contrastFamily"]
        family_groups[(split, language, family)] += 1
        plans = [parse_plan_response(x["solution"]) for x in members]

        if family == "role-composition":
            if len({p["targetRole"] for p in plans}) != 3 or len({p["action"] for p in plans}) != 1:
                raise ValueError(f"P2-44 role composition group is invalid: {group_id}")
        elif family == "constraint-binding":
            if (
                len({p["targetRole"] for p in plans}) != 1
                or len({_constraint_signature(p) for p in plans}) != 3
                or len({_hint_signature(p) for p in plans}) != 1
                or len({p["action"] for p in plans}) != 1
            ):
                raise ValueError(f"P2-44 constraint binding group is invalid: {group_id}")
        elif family == "hint-grounding":
            if (
                len({p["targetRole"] for p in plans}) != 1
                or len({_constraint_signature(p) for p in plans}) != 1
                or len({_hint_signature(p) for p in plans}) != 3
                or len({p["action"] for p in plans}) != 1
            ):
                raise ValueError(f"P2-44 hint grounding group is invalid: {group_id}")
        elif family == "action-discrimination":
            if (
                {p["action"] for p in plans} != {"create", "modify", "remove"}
                or len({p["targetRole"] for p in plans}) != 1
                or len({_constraint_signature(p) for p in plans}) != 1
                or len({_hint_signature(p) for p in plans}) != 1
            ):
                raise ValueError(f"P2-44 action discrimination group is invalid: {group_id}")
        elif family in {"cross-field-coherence", "near-neighbor"}:
            if len({p["targetRole"] for p in plans}) != 3 or len({_bundle_signature(p) for p in plans}) != 3:
                raise ValueError(f"P2-44 coherent multi-field group is invalid: {group_id}")

    for language in TARGET_KINDS:
        for family in FAMILIES:
            if family_groups[("train", language, family)] != 2:
                raise ValueError("P2-44 requires two train groups per language/family")
            if family_groups[("validation", language, family)] != 1:
                raise ValueError("P2-44 requires one validation group per language/family")

    role_overlap = roles_by_split["train"] & roles_by_split["validation"]
    bundle_overlap = bundles_by_split["train"] & bundles_by_split["validation"]
    full_overlap = full_by_split["train"] & full_by_split["validation"]
    if role_overlap or bundle_overlap or full_overlap:
        raise ValueError("P2-44 validation leaks exact train roles, bundles, or full plans")
    if not role_atoms_by_split["validation"] <= role_atoms_by_split["train"]:
        raise ValueError("P2-44 validation contains unseen role atoms")
    if not constraint_atoms_by_split["validation"] <= constraint_atoms_by_split["train"]:
        raise ValueError("P2-44 validation contains unseen constraint atoms")
    if not hint_atoms_by_split["validation"] <= hint_atoms_by_split["train"]:
        raise ValueError("P2-44 validation contains unseen hint atoms")

    return {
        "records": 162,
        "groups": 54,
        "trainGroups": 36,
        "validationGroups": 18,
        "trainRecords": 108,
        "validationRecords": 54,
        "uniqueRequests": len(requests),
        "uniqueTargetRoles": len(roles_by_split["train"] | roles_by_split["validation"]),
        "trainUniqueTargetRoles": len(roles_by_split["train"]),
        "validationUniqueTargetRoles": len(roles_by_split["validation"]),
        "trainValidationExactTargetRoleOverlap": len(role_overlap),
        "trainValidationExactConstraintSetOverlap": len(
            constraints_by_split["train"] & constraints_by_split["validation"]
        ),
        "trainValidationExactSearchHintOverlap": len(
            hints_by_split["train"] & hints_by_split["validation"]
        ),
        "trainValidationExactSemanticBundleOverlap": len(bundle_overlap),
        "trainValidationExactFullPlanOverlap": len(full_overlap),
        "validationRoleAtomsSeenInTrain": len(
            role_atoms_by_split["validation"] & role_atoms_by_split["train"]
        ),
        "validationRoleAtomCount": len(role_atoms_by_split["validation"]),
        "validationConstraintAtomsSeenInTrain": len(
            constraint_atoms_by_split["validation"] & constraint_atoms_by_split["train"]
        ),
        "validationConstraintAtomCount": len(constraint_atoms_by_split["validation"]),
        "validationHintAtomsSeenInTrain": len(
            hint_atoms_by_split["validation"] & hint_atoms_by_split["train"]
        ),
        "validationHintAtomCount": len(hint_atoms_by_split["validation"]),
        "p231ExactRequestOverlap": len(requests & dev_requests),
        "p231TargetRoleOverlap": len(
            (roles_by_split["train"] | roles_by_split["validation"]) & dev_roles
        ),
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
                "trainGroups": sum(
                    family_groups[("train", language, family)] for language in TARGET_KINDS
                ),
                "validationGroups": sum(
                    family_groups[("validation", language, family)] for language in TARGET_KINDS
                ),
                "records": 27,
            }
            for family in FAMILIES
        },
    }


def generate_evidence_composition_candidate(
    *, candidate_path: Path, review_path: Path,
    development_task_set_path: Path, contract_path: Path,
) -> dict[str, Any]:
    _contract(contract_path)
    if candidate_path.exists() or review_path.exists():
        raise FileExistsError("P2-44 candidate/review output already exists; choose fresh paths")
    rows = build_candidate_rows()
    summary = _validate_rows(rows, development_task_set_path)
    raw = _candidate_bytes(rows)
    candidate_sha = canonical_text_sha256(raw)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256 or len(raw) != EXPECTED_CANDIDATE_BYTES:
        raise ValueError("Deterministic P2-44 generator output differs from the frozen reviewed candidate")
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw)
    review = {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "candidateId": "p2-44-evidence-first-semantic-composition-v1",
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
        encoding="utf-8", newline="\n",
    )
    return review


def review_evidence_composition_curriculum(
    *, candidate_path: Path, review_path: Path,
    development_task_set_path: Path, contract_path: Path,
    bundle_dir: Path | None = None,
) -> dict[str, Any]:
    _contract(contract_path)
    if (
        candidate_path.is_symlink()
        or not candidate_path.is_file()
        or candidate_path.stat().st_size > 8 * 1024 * 1024
    ):
        raise ValueError("P2-44 candidate must be a regular JSONL file under 8 MiB")
    raw = candidate_path.read_bytes()
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-44 JSONL line {number}")
        try:
            row = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-44 JSONL line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-44 line {number} is not an object")
        rows.append(row)

    summary = _validate_rows(rows, development_task_set_path)
    review = _read_json(review_path)
    candidate_sha = canonical_text_sha256(raw)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256 or len(raw) != EXPECTED_CANDIDATE_BYTES:
        raise ValueError("P2-44 candidate differs from the frozen reviewed candidate")
    if (
        review.get("schemaVersion") != 1
        or review.get("milestone") != MILESTONE
        or review.get("candidateId") != "p2-44-evidence-first-semantic-composition-v1"
        or review.get("status") != "candidate-generated-pending-review"
        or review.get("generatorVersion") != GENERATOR_VERSION
        or review.get("candidateSha256") != candidate_sha
        or review.get("byteCount") != len(raw)
    ):
        raise ValueError("P2-44 review metadata differs from generated candidate")
    for key, value in summary.items():
        if review.get(key) != value:
            raise ValueError(f"P2-44 review metadata differs on {key}")

    tokenizer_result: dict[str, Any] = {
        "checked": False,
        "tokenizerSha256": None,
        "bundleManifestSha256": None,
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
            raise ValueError("P2-44 requires the frozen P2-41 16,384-token tokenizer bundle")
        token_counts = Counter()
        maximum = 0
        for row in rows:
            text = render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            ids = tokenizer.encode(text)
            if tokenizer.decode(ids) != text:
                raise ValueError(f"P2-44 tokenizer roundtrip failed: {row['id']}")
            count = len(ids) + 1
            if count > DEFAULT_CONFIG.context_length:
                raise ValueError(f"P2-44 record exceeds context: {row['id']} ({count})")
            maximum = max(maximum, count)
            token_counts[row["candidateSplit"]] += count
        tokenizer_result = {
            "checked": True,
            "tokenizerSha256": identity["tokenizerSha256"],
            "bundleManifestSha256": identity["bundleManifestSha256"],
            "maximumRecordTokensIncludingEos": maximum,
            "trainTokenCount": token_counts["train"],
            "validationTokenCount": token_counts["validation"],
        }
        if tokenizer_result != {
            "checked": True,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "bundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
            "maximumRecordTokensIncludingEos": EXPECTED_MAX_RECORD_TOKENS,
            "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
            "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
        }:
            raise ValueError("P2-44 tokenizer accounting differs from the frozen reviewed preflight")

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
