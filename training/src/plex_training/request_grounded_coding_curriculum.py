"""Deterministic P2-47 request-grounded coding representation curriculum."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import canonical_text_sha256, validate_plan_task_set

MILESTONE = "P2-47"
CONTRACT_KIND = "plex-p2-47-request-grounded-coding-preparation-contract-v1"
GENERATOR_VERSION = "p2-47-request-grounded-coding-generator-v1"
REPRESENTATION = "plex-request-grounded-change-v1"
PROVENANCE = "project-authored-p2-47-request-grounded-coding"
EXPECTED_DEV_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_CANDIDATE_SHA256 = "6e39259cc8fc1646fb7a16d2056706312f8736d330f94a642690aaf9d1c1489a"
EXPECTED_CANDIDATE_BYTES = 81032
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_BUNDLE_SHA256 = "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6"

LANGUAGES = ("html", "css", "javascript")
ACTIONS = ("create", "modify", "remove")
FAMILIES = (
    "target-binding",
    "requirement-binding",
    "action-binding",
    "near-neighbor",
)
LANGUAGE_CODES = {"html": "html", "css": "css", "javascript": "js"}
ROW_FIELDS = {
    "schemaVersion", "id", "candidateSplit", "contrastGroupId", "contrastFamily",
    "language", "provenance", "request", "solution", "action",
    "targetEvidence", "bindingEvidence",
}
SOLUTION_FIELDS = {
    "schemaVersion", "language", "action", "targetEvidence", "bindings",
}
BINDING_FIELDS = {"evidence", "kind", "key", "value"}

TARGETS = {
    "html": (
        "primary navigation", "email field", "status message",
        "shipping section", "notification options", "checkout form",
    ),
    "css": (
        "profile card", "product grid", "navigation menu",
        "notice banner", "dialog panel", "settings form",
    ),
    "javascript": (
        "filter helper", "format helper", "clamp helper",
        "sort helper", "lookup helper", "toggle helper",
    ),
}

REQUIREMENTS: dict[str, tuple[tuple[str, dict[str, str]], ...]] = {
    "html": (
        ("use a section element", {"kind": "element", "key": "semantic-element", "value": "section"}),
        ("be required", {"kind": "attribute", "key": "required", "value": "true"}),
        ("use type email", {"kind": "element", "key": "input-type", "value": "email"}),
        ("announce updates politely", {"kind": "attribute", "key": "aria-live", "value": "polite"}),
        ("be labeled Main", {"kind": "attribute", "key": "aria-label", "value": "Main"}),
        ("mark the current page", {"kind": "state", "key": "aria-current", "value": "page"}),
    ),
    "css": (
        ("use display grid", {"kind": "declaration", "key": "display", "value": "grid"}),
        ("stack vertically", {"kind": "declaration", "key": "flex-direction", "value": "column"}),
        ("use a 16px gap", {"kind": "declaration", "key": "gap", "value": "16px"}),
        ("hide it with display none", {"kind": "declaration", "key": "display", "value": "none"}),
        ("space items apart", {"kind": "declaration", "key": "justify-content", "value": "space-between"}),
        ("use position sticky", {"kind": "declaration", "key": "position", "value": "sticky"}),
    ),
    "javascript": (
        ("ignore inactive items", {"kind": "behavior", "key": "include", "value": "active-only"}),
        ("preserve input order", {"kind": "behavior", "key": "order", "value": "preserve"}),
        ("return null for null input", {"kind": "behavior", "key": "null-input", "value": "return-null"}),
        ("clamp inclusively", {"kind": "behavior", "key": "bounds", "value": "inclusive"}),
        ("avoid mutating the input", {"kind": "nonmutation", "key": "input", "value": "unchanged"}),
        ("use Array.isArray", {"kind": "api", "key": "array-check", "value": "Array.isArray"}),
    ),
}

FAMILY_CONFIGS: dict[str, dict[str, tuple[tuple[tuple[int, tuple[int, ...], str], ...], ...]]] = {
    "target-binding": {
        "train": (
            ((0, (0, 1), "modify"), (1, (0, 1), "modify"), (2, (0, 1), "modify")),
            ((3, (2, 3), "modify"), (4, (2, 3), "modify"), (5, (2, 3), "modify")),
        ),
        "validation": (
            ((0, (0, 3), "modify"), (2, (0, 3), "modify"), (4, (0, 3), "modify")),
        ),
    },
    "requirement-binding": {
        "train": (
            ((0, (0, 2), "modify"), (0, (1, 3), "modify"), (0, (0, 4), "modify")),
            ((3, (1, 5), "modify"), (3, (2, 4), "modify"), (3, (3, 5), "modify")),
        ),
        "validation": (
            ((0, (1, 2), "modify"), (3, (2, 5), "modify"), (3, (4, 5), "modify")),
        ),
    },
    "action-binding": {
        "train": (
            ((1, (0, 4), "create"), (1, (0, 4), "modify"), (1, (), "remove")),
            ((4, (1, 5), "create"), (4, (1, 5), "modify"), (4, (), "remove")),
        ),
        "validation": (
            ((2, (4, 5), "create"), (2, (4, 5), "modify"), (2, (), "remove")),
        ),
    },
    "near-neighbor": {
        "train": (
            ((5, (0, 1), "modify"), (5, (0, 2), "modify"), (5, (0, 4), "modify")),
            ((2, (1, 3), "modify"), (2, (1, 5), "modify"), (2, (3, 5), "modify")),
        ),
        "validation": (
            ((5, (1, 2), "modify"), (2, (2, 5), "modify"), (1, (0, 3), "modify")),
        ),
    },
}

TRAIN_MODIFY_TEMPLATES = (
    "Update the {target} so it will {r1} and {r2}.",
    "For the {target}, make it {r1} while it also {r2}.",
    "Modify the {target}: it should {r1} and {r2}.",
)
VALIDATION_MODIFY_TEMPLATES = (
    "Please change the {target}; it needs to {r1} and {r2}.",
    "The {target} should {r1}, and it should also {r2}.",
    "Adjust the {target} so it can {r1} while continuing to {r2}.",
)
TRAIN_CREATE_TEMPLATES = (
    "Add a {target} that will {r1} and {r2}.",
    "Create a {target} that should {r1} while it also {r2}.",
    "Introduce a {target}; it must {r1} and {r2}.",
)
VALIDATION_CREATE_TEMPLATES = (
    "Please add a {target} that can {r1} and {r2}.",
    "We need a new {target} that will {r1} while also {r2}.",
    "Create the {target} so it will {r1} and {r2}.",
)
TRAIN_REMOVE_TEMPLATES = (
    "Remove the {target}.",
    "Delete the {target}.",
    "Take out the {target}.",
)
VALIDATION_REMOVE_TEMPLATES = (
    "Please remove the {target}.",
    "The {target} should be deleted.",
    "Get rid of the {target}.",
)


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _contract(path: Path) -> dict[str, Any]:
    value = _read_json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != CONTRACT_KIND
        or value.get("status") != "candidate-preparation-authorized"
        or value.get("dataPreparationAuthorized") is not True
        or value.get("modelTrainingAuthorized") is not False
        or value.get("automaticTrainingExtension") is not False
        or value.get("trainingCommand") is not None
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-47 preparation contract is invalid")
    identity = value.get("candidateIdentity")
    if identity != {
        "candidateId": "p2-47-request-grounded-coding-v1",
        "sha256": EXPECTED_CANDIDATE_SHA256,
        "bytes": EXPECTED_CANDIDATE_BYTES,
    }:
        raise ValueError("P2-47 candidate identity changed")
    return value


def validate_request_grounded_change(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != SOLUTION_FIELDS:
        raise ValueError("P2-47 solution fields are invalid")
    if value.get("schemaVersion") != 1:
        raise ValueError("P2-47 solution schemaVersion must be 1")
    language = value.get("language")
    action = value.get("action")
    target = value.get("targetEvidence")
    bindings = value.get("bindings")
    if language not in LANGUAGES:
        raise ValueError("P2-47 solution language is invalid")
    if action not in ACTIONS:
        raise ValueError("P2-47 solution action is invalid")
    if not isinstance(target, str) or not target or target != target.strip():
        raise ValueError("P2-47 targetEvidence must be a nonempty trimmed string")
    if not isinstance(bindings, list) or len(bindings) > 4:
        raise ValueError("P2-47 bindings must contain zero through four entries")
    if action == "remove" and bindings:
        raise ValueError("P2-47 remove solutions must not carry behavior bindings")
    if action != "remove" and not bindings:
        raise ValueError("P2-47 create/modify solutions require behavior bindings")
    normalized = []
    seen = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
            raise ValueError("P2-47 binding fields are invalid")
        if not all(
            isinstance(binding.get(key), str)
            and binding[key]
            and binding[key] == binding[key].strip()
            for key in BINDING_FIELDS
        ):
            raise ValueError("P2-47 binding values must be nonempty trimmed strings")
        signature = (
            binding["evidence"].casefold(),
            binding["kind"],
            binding["key"],
            binding["value"],
        )
        if signature in seen:
            raise ValueError("P2-47 bindings must be unique")
        seen.add(signature)
        normalized.append(dict(binding))
    return {
        "schemaVersion": 1,
        "language": language,
        "action": action,
        "targetEvidence": target,
        "bindings": normalized,
    }


def render_request_grounded_change_prompt(language: str, request: str) -> str:
    if language not in LANGUAGES or not isinstance(request, str) or not request.strip():
        raise ValueError("P2-47 prompt input is invalid")
    prompt = (
        "Map the coding request to one request-grounded change record.\n"
        "Return exactly one JSON object with schemaVersion, language, action, targetEvidence, and bindings.\n"
        "targetEvidence must be copied from the request and name what the user wants changed.\n"
        "Each binding must contain evidence, kind, key, and value. binding.evidence must be copied from the request, "
        "and kind/key/value must express the concrete coding meaning of that evidence.\n"
        "Do not invent target roles, search hints, file paths, or synthetic labels.\n"
        "Remove requests use an empty bindings array.\n"
        f"Language: {language}\n"
        f"Request: {request}\n"
        "JSON:"
    )
    if len(prompt.encode("utf-8")) > 4096:
        raise ValueError("P2-47 prompt exceeds 4096 UTF-8 bytes")
    return prompt


def _render_request(
    *,
    split: str,
    action: str,
    target: str,
    requirements: list[tuple[str, dict[str, str]]],
    variant: int,
) -> str:
    if action == "remove":
        templates = TRAIN_REMOVE_TEMPLATES if split == "train" else VALIDATION_REMOVE_TEMPLATES
        return templates[variant].format(target=target)
    r1, r2 = requirements[0][0], requirements[1][0]
    if action == "create":
        templates = TRAIN_CREATE_TEMPLATES if split == "train" else VALIDATION_CREATE_TEMPLATES
    else:
        templates = TRAIN_MODIFY_TEMPLATES if split == "train" else VALIDATION_MODIFY_TEMPLATES
    return templates[variant].format(target=target, r1=r1, r2=r2)


def _solution(
    *,
    language: str,
    action: str,
    target: str,
    requirements: list[tuple[str, dict[str, str]]],
) -> dict[str, Any]:
    value = {
        "schemaVersion": 1,
        "language": language,
        "action": action,
        "targetEvidence": target,
        "bindings": [
            {"evidence": evidence, **intent}
            for evidence, intent in requirements
        ],
    }
    return validate_request_grounded_change(value)


def build_candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group_numbers = {language: 0 for language in LANGUAGES}
    for language in LANGUAGES:
        for family in FAMILIES:
            for split in ("train", "validation"):
                for group in FAMILY_CONFIGS[family][split]:
                    group_numbers[language] += 1
                    group_id = (
                        f"p247-{LANGUAGE_CODES[language]}-g{group_numbers[language]:02d}"
                    )
                    for variant, (target_index, requirement_indexes, action) in enumerate(group):
                        target = TARGETS[language][target_index]
                        requirements = [
                            REQUIREMENTS[language][index]
                            for index in requirement_indexes
                        ]
                        request = _render_request(
                            split=split,
                            action=action,
                            target=target,
                            requirements=requirements,
                            variant=variant,
                        )
                        solution = _solution(
                            language=language,
                            action=action,
                            target=target,
                            requirements=requirements,
                        )
                        rows.append({
                            "schemaVersion": 1,
                            "id": f"{group_id}-{variant + 1:02d}",
                            "candidateSplit": split,
                            "contrastGroupId": group_id,
                            "contrastFamily": family,
                            "language": language,
                            "provenance": PROVENANCE,
                            "request": request,
                            "solution": json.dumps(
                                solution,
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                            "action": action,
                            "targetEvidence": target,
                            "bindingEvidence": [
                                evidence for evidence, _ in requirements
                            ],
                        })
    return rows


def _candidate_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        for row in rows
    ).encode("utf-8")


def _binding_signature(solution: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    return tuple(sorted(
        (binding["kind"], binding["key"], binding["value"])
        for binding in solution["bindings"]
    ))


def _development_requests(path: Path) -> set[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("P2-31 development task set is missing, linked, or oversized")
    raw = path.read_bytes()
    if canonical_text_sha256(raw) != EXPECTED_DEV_SHA256:
        raise ValueError("P2-31 development task set SHA-256 changed")
    task_set = validate_plan_task_set(json.loads(raw.decode("utf-8")))
    return {task["request"] for task in task_set["tasks"]}


def _validate_rows(
    rows: list[dict[str, Any]],
    development_task_set_path: Path,
) -> dict[str, Any]:
    if len(rows) != 108:
        raise ValueError("P2-47 requires exactly 108 records")
    dev_requests = _development_requests(development_task_set_path)
    ids: set[str] = set()
    requests: set[str] = set()
    groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    counts = Counter()
    family_counts = Counter()
    targets: dict[str, set[tuple[str, str]]] = {"train": set(), "validation": set()}
    intents: dict[str, set[tuple[str, str, str]]] = {"train": set(), "validation": set()}
    nonempty_binding_sets: dict[str, set[tuple[tuple[str, str, str], ...]]] = {
        "train": set(), "validation": set()
    }
    exact_solutions: dict[str, set[str]] = {"train": set(), "validation": set()}
    actions: dict[str, set[str]] = {"train": set(), "validation": set()}

    for row in rows:
        if set(row) != ROW_FIELDS or row.get("schemaVersion") != 1:
            raise ValueError("P2-47 row fields differ from the candidate schema")
        record_id = row.get("id")
        split = row.get("candidateSplit")
        language = row.get("language")
        family = row.get("contrastFamily")
        group_id = row.get("contrastGroupId")
        request = row.get("request")
        solution_text = row.get("solution")
        if (
            not isinstance(record_id, str) or not record_id or record_id in ids
            or split not in {"train", "validation"}
            or language not in LANGUAGES
            or family not in FAMILIES
            or not isinstance(group_id, str) or not group_id
            or not isinstance(request, str) or not request or request in requests
            or not isinstance(solution_text, str) or not solution_text
            or row.get("provenance") != PROVENANCE
            or row.get("action") not in ACTIONS
            or not isinstance(row.get("targetEvidence"), str)
            or not isinstance(row.get("bindingEvidence"), list)
        ):
            raise ValueError(f"Invalid P2-47 row metadata: {record_id}")
        try:
            solution = validate_request_grounded_change(json.loads(solution_text))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid P2-47 solution JSON: {record_id}") from exc

        if (
            solution["language"] != language
            or solution["action"] != row["action"]
            or solution["targetEvidence"] != row["targetEvidence"]
            or [binding["evidence"] for binding in solution["bindings"]]
                != row["bindingEvidence"]
        ):
            raise ValueError(f"P2-47 row metadata differs from solution: {record_id}")

        request_folded = request.casefold()
        if solution["targetEvidence"].casefold() not in request_folded:
            raise ValueError(f"P2-47 targetEvidence is not grounded in request: {record_id}")
        for binding in solution["bindings"]:
            if binding["evidence"].casefold() not in request_folded:
                raise ValueError(f"P2-47 binding evidence is not grounded in request: {record_id}")

        ids.add(record_id)
        requests.add(request)
        groups[group_id].append(row)
        counts[(split, language)] += 1
        family_counts[(split, family)] += 1
        targets[split].add((language, solution["targetEvidence"]))
        actions[split].add(solution["action"])
        for binding in solution["bindings"]:
            intents[split].add((binding["kind"], binding["key"], binding["value"]))
        signature = _binding_signature(solution)
        if signature:
            nonempty_binding_sets[split].add(signature)
        exact_solutions[split].add(
            json.dumps(solution, sort_keys=True, separators=(",", ":"))
        )

    if any(len(group) != 3 for group in groups.values()) or len(groups) != 36:
        raise ValueError("P2-47 requires 36 three-record contrast groups")
    if any(counts[("train", language)] != 24 for language in LANGUAGES):
        raise ValueError("P2-47 train language balance changed")
    if any(counts[("validation", language)] != 12 for language in LANGUAGES):
        raise ValueError("P2-47 validation language balance changed")
    if any(family_counts[("train", family)] != 18 for family in FAMILIES):
        raise ValueError("P2-47 train contrast-family balance changed")
    if any(family_counts[("validation", family)] != 9 for family in FAMILIES):
        raise ValueError("P2-47 validation contrast-family balance changed")
    if targets["validation"] - targets["train"]:
        raise ValueError("P2-47 validation contains unseen target evidence")
    if intents["validation"] - intents["train"]:
        raise ValueError("P2-47 validation contains unseen coding intents")
    if actions["validation"] - actions["train"]:
        raise ValueError("P2-47 validation contains unseen actions")
    if nonempty_binding_sets["train"] & nonempty_binding_sets["validation"]:
        raise ValueError("P2-47 validation reuses an exact nonempty training binding set")
    if exact_solutions["train"] & exact_solutions["validation"]:
        raise ValueError("P2-47 validation reuses an exact training solution")
    train_requests = {
        row["request"] for row in rows if row["candidateSplit"] == "train"
    }
    validation_requests = {
        row["request"] for row in rows if row["candidateSplit"] == "validation"
    }
    if train_requests & validation_requests:
        raise ValueError("P2-47 validation reuses an exact training request")
    if requests & dev_requests:
        raise ValueError("P2-47 candidate overlaps an exact P2-31 request")

    return {
        "records": 108,
        "groups": 36,
        "trainRecords": 72,
        "validationRecords": 36,
        "uniqueRequests": len(requests),
        "trainValidationExactRequestOverlap": 0,
        "trainValidationExactSolutionOverlap": 0,
        "trainValidationNonemptyBindingSetOverlap": 0,
        "validationTargetsSeenInTrain": len(targets["validation"]),
        "validationTargetCount": len(targets["validation"]),
        "validationBindingIntentsSeenInTrain": len(intents["validation"]),
        "validationBindingIntentCount": len(intents["validation"]),
        "validationActionsSeenInTrain": len(actions["validation"]),
        "validationActionCount": len(actions["validation"]),
        "p231ExactRequestOverlap": 0,
        "perLanguage": {
            language: {
                "train": counts[("train", language)],
                "validation": counts[("validation", language)],
            }
            for language in LANGUAGES
        },
        "contrastFamilies": {
            family: {
                "train": family_counts[("train", family)],
                "validation": family_counts[("validation", family)],
            }
            for family in FAMILIES
        },
    }


def generate_request_grounded_coding_candidate(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    _contract(contract_path)
    if candidate_path.exists() or review_path.exists():
        raise FileExistsError("P2-47 candidate/review output already exists; choose fresh paths")
    rows = build_candidate_rows()
    summary = _validate_rows(rows, development_task_set_path)
    raw = _candidate_bytes(rows)
    candidate_sha = canonical_text_sha256(raw)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256 or len(raw) != EXPECTED_CANDIDATE_BYTES:
        raise ValueError("Deterministic P2-47 generator differs from the frozen candidate")
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw)
    review = {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "candidateId": "p2-47-request-grounded-coding-v1",
        "representation": REPRESENTATION,
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
        json.dumps(review, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return review


def review_request_grounded_coding_curriculum(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    contract_path: Path,
    bundle_dir: Path | None = None,
) -> dict[str, Any]:
    _contract(contract_path)
    if (
        candidate_path.is_symlink()
        or not candidate_path.is_file()
        or candidate_path.stat().st_size > 8 * 1024 * 1024
    ):
        raise ValueError("P2-47 candidate must be a regular JSONL file under 8 MiB")
    raw = candidate_path.read_bytes()
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-47 JSONL line {number}")
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid P2-47 JSONL line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"P2-47 line {number} is not an object")
        rows.append(row)

    summary = _validate_rows(rows, development_task_set_path)
    review = _read_json(review_path)
    candidate_sha = canonical_text_sha256(raw)
    if candidate_sha != EXPECTED_CANDIDATE_SHA256 or len(raw) != EXPECTED_CANDIDATE_BYTES:
        raise ValueError("P2-47 candidate differs from the frozen candidate")
    required_review = {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "candidateId": "p2-47-request-grounded-coding-v1",
        "representation": REPRESENTATION,
        "status": "candidate-generated-pending-review",
        "generatorVersion": GENERATOR_VERSION,
        "candidateSha256": candidate_sha,
        "byteCount": len(raw),
    }
    for key, expected in required_review.items():
        if review.get(key) != expected:
            raise ValueError(f"P2-47 review metadata differs on {key}")
    for key, expected in summary.items():
        if review.get(key) != expected:
            raise ValueError(f"P2-47 review summary differs on {key}")

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
            or identity.get("bundleManifestSha256") != EXPECTED_BUNDLE_SHA256
            or tokenizer.vocabulary_size != 16384
        ):
            raise ValueError("P2-47 requires the frozen P2-44 tokenizer bundle")
        token_counts = Counter()
        maximum = 0
        for row in rows:
            text = (
                render_request_grounded_change_prompt(
                    row["language"],
                    row["request"],
                )
                + row["solution"]
            )
            ids = tokenizer.encode(text)
            if tokenizer.decode(ids) != text:
                raise ValueError(f"P2-47 tokenizer roundtrip failed: {row['id']}")
            count = len(ids) + 1
            if count > DEFAULT_CONFIG.context_length:
                raise ValueError(f"P2-47 record exceeds context: {row['id']} ({count})")
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

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "candidate-review-passed",
        "representation": REPRESENTATION,
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
