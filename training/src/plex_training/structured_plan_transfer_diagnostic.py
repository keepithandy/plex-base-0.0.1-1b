"""P2-46 read-only semantic-transfer failure diagnostic."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .structured_plan import (
    MAX_PLAN_RESPONSE_BYTES,
    MAX_PLAN_TASK_SET_BYTES,
    canonical_text_sha256,
    parse_plan_response,
    validate_plan_task_set,
)

MILESTONE = "P2-46"
KIND = "plex-p2-46-semantic-transfer-failure-diagnostic-contract-v1"
DEFAULT_CONTRACT = Path(
    "training/pretraining/p2-46-semantic-transfer-diagnostic-contract.json"
)
DEFAULT_TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
DEFAULT_P244_CANDIDATE = Path(
    "training/phase2/drafts/p2-44-evidence-first-semantic-composition-v1.jsonl"
)
DEFAULT_P243_RESULT = Path(
    "training/pretraining/p2-43-semantic-bundle-reuse-result.json"
)

EXPECTED_TASK_SET_SHA256 = (
    "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
)
EXPECTED_P244_CANDIDATE_SHA256 = (
    "fc56eca2186e2b7f643af9fbec514c1d5d34248eba2ac380b9f93c482b945c30"
)
EXPECTED_P242_RESPONSES_SHA256 = (
    "3a935e10fb8d7deab057c3776446f1151ec3f0945b195c5350f93b6a54af30ee"
)
EXPECTED_P245_RESPONSES_SHA256 = (
    "ca1e8c8abb8dc419ef2fd2d2c3834964e5baad448b3dd439678decadbf1919a9"
)
EXPECTED_P242_CHECKPOINT_SHA256 = (
    "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc"
)
EXPECTED_P244_CHECKPOINT_SHA256 = (
    "69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e"
)
EXPECTED_TOKENIZER_SHA256 = (
    "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
)
EXPECTED_P241_BUNDLE_SHA256 = (
    "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a"
)
EXPECTED_P244_BUNDLE_SHA256 = (
    "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6"
)

_TOKEN = re.compile(r"[a-z0-9]+")
_GENERIC = {
    "a", "an", "and", "as", "be", "by", "code", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "return", "the", "to", "use", "using", "with",
}


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _jsonl(path: Path, *, maximum_bytes: int = 8 * 1024 * 1024) -> tuple[list[dict[str, Any]], bytes]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSONL file: {path}")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(raw.splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSONL at line {line_number}: {path}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} is not an object: {path}")
        rows.append(row)
    return rows, raw


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path, 1024 * 1024)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != KIND
        or value.get("status") != "diagnostic-authorized"
        or value.get("modelTrainingAuthorized") is not False
    ):
        raise ValueError("P2-46 diagnostic contract is invalid")

    protected = value.get("protectedEvaluation")
    if protected != {
        "developmentOnly": True,
        "noGradientUpdates": True,
        "noOptimizerCreation": True,
        "noResponseRepair": True,
        "noCheckpointSelection": True,
        "noNewCurriculum": True,
        "finalProjectHoldoutMustRemainClosed": True,
    }:
        raise ValueError("P2-46 protected-evaluation boundary changed")

    task = value.get("taskSet")
    if not isinstance(task, dict) or (
        task.get("sha256") != EXPECTED_TASK_SET_SHA256
        or task.get("tasks") != 18
    ):
        raise ValueError("P2-46 task-set identity changed")

    candidate = value.get("p244Candidate")
    if not isinstance(candidate, dict) or (
        candidate.get("sha256") != EXPECTED_P244_CANDIDATE_SHA256
        or candidate.get("records") != 162
        or candidate.get("trainRecords") != 108
        or candidate.get("validationRecords") != 54
    ):
        raise ValueError("P2-46 P2-44 candidate identity changed")

    before = value.get("before")
    after = value.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("P2-46 before/after identities are missing")
    expected_before = {
        "milestone": "P2-42",
        "responsesSha256": EXPECTED_P242_RESPONSES_SHA256,
        "checkpointSha256": EXPECTED_P242_CHECKPOINT_SHA256,
        "checkpointStep": 100,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "tokenizerBundleManifestSha256": EXPECTED_P241_BUNDLE_SHA256,
    }
    expected_after = {
        "milestone": "P2-45",
        "responsesSha256": EXPECTED_P245_RESPONSES_SHA256,
        "checkpointSha256": EXPECTED_P244_CHECKPOINT_SHA256,
        "checkpointStep": 100,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "tokenizerBundleManifestSha256": EXPECTED_P244_BUNDLE_SHA256,
    }
    if before != expected_before or after != expected_after:
        raise ValueError("P2-46 before/after frozen identities changed")
    return value


def _tokens(text: str) -> set[str]:
    return {
        token for token in _TOKEN.findall(text.casefold())
        if token not in _GENERIC
    }


def _jaccard(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _constraint_signature(plan: dict[str, Any]) -> tuple[tuple[str, str, str], ...] | None:
    constraints = plan.get("constraints")
    if not isinstance(constraints, list):
        return None
    triples: list[tuple[str, str, str]] = []
    for item in constraints:
        if not isinstance(item, dict):
            return None
        kind, key, value = item.get("kind"), item.get("key"), item.get("value")
        if not all(isinstance(x, str) for x in (kind, key, value)):
            return None
        triples.append((kind, key, value))
    return tuple(sorted(triples))


def _hint_signature(plan: dict[str, Any]) -> tuple[str, ...] | None:
    hints = plan.get("searchHints")
    if not isinstance(hints, list) or not all(isinstance(x, str) for x in hints):
        return None
    return tuple(x.casefold() for x in hints)


def _bundle_signature(plan: dict[str, Any]) -> tuple[Any, ...] | None:
    role = plan.get("targetRole")
    constraints = _constraint_signature(plan)
    hints = _hint_signature(plan)
    if not isinstance(role, str) or constraints is None or hints is None:
        return None
    return (role, constraints, hints)


def _full_signature(plan: dict[str, Any]) -> str:
    return json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _loose_plan(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _response_rows(
    path: Path,
    *,
    expected_sha256: str,
    task_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], str]:
    rows, raw = _jsonl(path)
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha256:
        raise ValueError(f"Response SHA-256 differs from frozen P2-46 input: {path}")

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if set(row) - {"taskId", "text", "truncated"}:
            raise ValueError("P2-46 response row contains unsupported fields")
        task_id = row.get("taskId")
        text = row.get("text")
        if (
            not isinstance(task_id, str)
            or task_id not in task_ids
            or task_id in by_id
            or not isinstance(text, str)
            or len(text.encode("utf-8")) > MAX_PLAN_RESPONSE_BYTES
            or ("truncated" in row and not isinstance(row["truncated"], bool))
        ):
            raise ValueError("P2-46 response row is invalid")
        by_id[task_id] = row
    if set(by_id) != task_ids:
        raise ValueError("P2-46 requires exactly one response for every P2-31 task")
    return by_id, actual_sha


def _verify_manifest(
    path: Path,
    *,
    milestone: str,
    response_sha: str,
    checkpoint_sha: str,
    bundle_sha: str,
) -> dict[str, Any]:
    manifest = _json(path)
    expected = {
        "milestone": milestone,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "taskSetSha256": EXPECTED_TASK_SET_SHA256,
        "taskCount": 18,
        "checkpointSha256": checkpoint_sha,
        "checkpointStep": 100,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "tokenizerBundleManifestSha256": bundle_sha,
        "temperature": 0,
        "seed": 1337,
        "maxNewTokens": 256,
        "responsesSha256": response_sha,
    }
    for key, wanted in expected.items():
        if manifest.get(key) != wanted:
            raise ValueError(f"P2-46 {milestone} manifest mismatch: {key}")
    return manifest


def _load_candidate(path: Path) -> dict[str, Any]:
    rows, raw = _jsonl(path)
    if canonical_text_sha256(raw) != EXPECTED_P244_CANDIDATE_SHA256:
        raise ValueError("P2-46 requires the exact frozen P2-44 candidate")
    if len(rows) != 162:
        raise ValueError("P2-44 candidate record count changed")

    records: list[dict[str, Any]] = []
    train_role_atoms: set[str] = set()
    train_constraint_atoms: set[str] = set()
    train_hint_atoms: set[str] = set()
    constraint_atom_by_triple: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)

    for row in rows:
        if row.get("candidateSplit") not in {"train", "validation"}:
            raise ValueError("P2-44 candidate split is invalid")
        request = row.get("request")
        solution = row.get("solution")
        semantic_atoms = row.get("semanticAtoms")
        if (
            not isinstance(request, str)
            or not isinstance(solution, str)
            or not isinstance(semantic_atoms, dict)
        ):
            raise ValueError("P2-44 diagnostic candidate row is invalid")
        plan = parse_plan_response(solution)
        role_atoms = semantic_atoms.get("role")
        constraint_atoms = semantic_atoms.get("constraints")
        hint_atoms = semantic_atoms.get("hints")
        if (
            not isinstance(role_atoms, list)
            or not all(isinstance(x, str) for x in role_atoms)
            or not isinstance(constraint_atoms, list)
            or not all(isinstance(x, str) for x in constraint_atoms)
            or not isinstance(hint_atoms, list)
            or not all(isinstance(x, str) for x in hint_atoms)
        ):
            raise ValueError("P2-44 semantic atom metadata is invalid")
        constraints = plan["constraints"]
        if len(constraints) != len(constraint_atoms):
            raise ValueError("P2-44 constraint atoms do not align with plan constraints")

        split = row["candidateSplit"]
        record = {
            "id": row.get("id"),
            "split": split,
            "language": row.get("language"),
            "family": row.get("contrastFamily"),
            "request": request,
            "plan": plan,
            "roleAtoms": role_atoms,
            "constraintAtoms": constraint_atoms,
            "hintAtoms": hint_atoms,
        }
        records.append(record)

        if split == "train":
            train_role_atoms.update(x.casefold() for x in role_atoms)
            train_constraint_atoms.update(x.casefold() for x in constraint_atoms)
            train_hint_atoms.update(x.casefold() for x in hint_atoms)
            for item, atom in zip(constraints, constraint_atoms, strict=True):
                triple = (item["kind"], item["key"], item["value"])
                constraint_atom_by_triple[triple].add(atom)

    if sum(record["split"] == "train" for record in records) != 108:
        raise ValueError("P2-44 training-record count changed")
    return {
        "records": records,
        "trainRoleAtoms": train_role_atoms,
        "trainConstraintAtoms": train_constraint_atoms,
        "trainHintAtoms": train_hint_atoms,
        "constraintAtomByTriple": constraint_atom_by_triple,
    }


def _matches(records: list[dict[str, Any]], *, split: str, predicate: Any) -> list[dict[str, Any]]:
    return [
        record for record in records
        if record["split"] == split and predicate(record["plan"])
    ]


def _correctness(task: dict[str, Any], plan: dict[str, Any] | None) -> dict[str, bool]:
    fields = {
        "language": False,
        "action": False,
        "targetKind": False,
        "targetRole": False,
        "constraintsExact": False,
        "hintCoverage": False,
    }
    if plan is None:
        return fields
    expected = task["expectedPlan"]
    constraints = _constraint_signature(plan)
    expected_constraints = tuple(sorted(
        (x["kind"], x["key"], x["value"]) for x in expected["constraints"]
    ))
    hints = _hint_signature(plan)
    joined_hints = " ".join(hints or ())
    fields.update({
        "language": plan.get("language") == task["language"],
        "action": plan.get("action") == expected["action"],
        "targetKind": plan.get("targetKind") == expected["targetKind"],
        "targetRole": plan.get("targetRole") == expected["targetRole"],
        "constraintsExact": constraints == expected_constraints,
        "hintCoverage": bool(hints) and all(
            keyword in joined_hints for keyword in expected["hintKeywords"]
        ),
    })
    return fields


def _analyze_response(
    *,
    task: dict[str, Any],
    row: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    text = row["text"]
    truncated = bool(row.get("truncated", False))
    strict = None
    strict_error = None
    if not truncated:
        try:
            strict = parse_plan_response(text)
        except ValueError as exc:
            strict_error = str(exc)
    loose = _loose_plan(text) if not truncated else None
    comparison_plan = strict or loose
    correctness = _correctness(task, strict)
    loose_correctness = _correctness(task, loose)

    result: dict[str, Any] = {
        "strictSchemaValid": strict is not None,
        "strictError": strict_error,
        "truncated": truncated,
        "correctness": correctness,
        "looseJsonObject": loose is not None,
        "looseCorrectness": loose_correctness,
    }
    if comparison_plan is None:
        return result

    records = candidate["records"]
    role = comparison_plan.get("targetRole")
    constraints = _constraint_signature(comparison_plan)
    hints = _hint_signature(comparison_plan)
    bundle = _bundle_signature(comparison_plan)
    full = _full_signature(comparison_plan)

    train_role = bool(role) and bool(_matches(
        records, split="train", predicate=lambda p: p["targetRole"] == role
    ))
    train_constraints = constraints is not None and bool(_matches(
        records, split="train",
        predicate=lambda p: _constraint_signature(p) == constraints,
    ))
    train_hints = hints is not None and bool(_matches(
        records, split="train",
        predicate=lambda p: _hint_signature(p) == hints,
    ))
    train_bundle = bundle is not None and bool(_matches(
        records, split="train",
        predicate=lambda p: _bundle_signature(p) == bundle,
    ))
    train_full = bool(_matches(
        records, split="train",
        predicate=lambda p: _full_signature(p) == full,
    ))
    validation_role = bool(role) and bool(_matches(
        records, split="validation", predicate=lambda p: p["targetRole"] == role
    ))
    validation_bundle = bundle is not None and bool(_matches(
        records, split="validation",
        predicate=lambda p: _bundle_signature(p) == bundle,
    ))

    request_tokens = _tokens(task["request"])
    role_tokens = set(_TOKEN.findall(role.casefold())) if isinstance(role, str) else set()
    role_grounded = bool(role_tokens) and role_tokens <= request_tokens
    role_atoms_known = bool(role_tokens) and role_tokens <= candidate["trainRoleAtoms"]

    hint_grounding: list[dict[str, Any]] = []
    for hint in hints or ():
        hint_tokens = _tokens(hint)
        hint_grounding.append({
            "hint": hint,
            "tokens": sorted(hint_tokens),
            "groundedInRequest": bool(hint_tokens) and hint_tokens <= request_tokens,
        })

    constraint_atoms: list[dict[str, Any]] = []
    for triple in constraints or ():
        atoms = sorted(candidate["constraintAtomByTriple"].get(triple, set()))
        constraint_atoms.append({
            "constraint": {"kind": triple[0], "key": triple[1], "value": triple[2]},
            "knownTrainingAtoms": atoms,
            "seenInP244Train": bool(atoms),
        })

    same_language_train = [
        record for record in records
        if record["split"] == "train" and record["language"] == task["language"]
    ]
    nearest = max(
        same_language_train,
        key=lambda record: _jaccard(task["request"], record["request"]),
    )
    nearest_similarity = _jaccard(task["request"], nearest["request"])

    result.update({
        "actual": {
            "language": comparison_plan.get("language"),
            "action": comparison_plan.get("action"),
            "targetKind": comparison_plan.get("targetKind"),
            "targetRole": role,
            "constraints": comparison_plan.get("constraints"),
            "searchHints": comparison_plan.get("searchHints"),
        },
        "p244Reuse": {
            "trainTargetRole": train_role,
            "trainConstraintSet": bool(train_constraints),
            "trainSearchHints": bool(train_hints),
            "trainSemanticBundle": bool(train_bundle),
            "trainFullPlan": train_full,
            "validationTargetRole": validation_role,
            "validationSemanticBundle": bool(validation_bundle),
            "validationOnlyTargetRole": validation_role and not train_role,
            "validationOnlySemanticBundle": bool(validation_bundle) and not bool(train_bundle),
            "trainComponentRecombination": (
                bool(train_role)
                and bool(train_constraints)
                and bool(train_hints)
                and not bool(train_bundle)
            ),
        },
        "grounding": {
            "targetRoleTokens": sorted(role_tokens),
            "targetRoleGroundedInRequest": role_grounded,
            "targetRoleAtomsKnownInP244Train": role_atoms_known,
            "searchHints": hint_grounding,
            "allSearchHintsGroundedInRequest": (
                bool(hint_grounding)
                and all(item["groundedInRequest"] for item in hint_grounding)
            ),
            "constraints": constraint_atoms,
            "allConstraintTriplesSeenInP244Train": (
                bool(constraint_atoms)
                and all(item["seenInP244Train"] for item in constraint_atoms)
            ),
        },
        "nearestP244TrainRequest": {
            "recordId": nearest["id"],
            "family": nearest["family"],
            "similarity": nearest_similarity,
        },
    })
    return result


def diagnose_semantic_transfer_failure(
    *,
    p242_responses_path: Path,
    p242_manifest_path: Path,
    p245_responses_path: Path,
    p245_manifest_path: Path,
    task_set_path: Path = DEFAULT_TASK_SET,
    p244_candidate_path: Path = DEFAULT_P244_CANDIDATE,
    p243_result_path: Path = DEFAULT_P243_RESULT,
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Compare P2-42 and P2-45 while measuring transfer against P2-44 training evidence."""
    contract = _contract(contract_path)

    if (
        task_set_path.is_symlink()
        or not task_set_path.is_file()
        or task_set_path.stat().st_size > MAX_PLAN_TASK_SET_BYTES
    ):
        raise ValueError("P2-46 task set is missing, linked, or oversized")
    task_raw = task_set_path.read_bytes()
    task_sha = canonical_text_sha256(task_raw)
    if task_sha != EXPECTED_TASK_SET_SHA256:
        raise ValueError("P2-46 requires the unchanged P2-31 development set")
    task_set = validate_plan_task_set(json.loads(task_raw.decode("utf-8")))
    if task_set["kind"] != "development" or len(task_set["tasks"]) != 18:
        raise ValueError("P2-46 is development-only and requires 18 tasks")

    task_ids = {task["id"] for task in task_set["tasks"]}
    before_rows, before_sha = _response_rows(
        p242_responses_path,
        expected_sha256=EXPECTED_P242_RESPONSES_SHA256,
        task_ids=task_ids,
    )
    after_rows, after_sha = _response_rows(
        p245_responses_path,
        expected_sha256=EXPECTED_P245_RESPONSES_SHA256,
        task_ids=task_ids,
    )
    _verify_manifest(
        p242_manifest_path,
        milestone="P2-42",
        response_sha=before_sha,
        checkpoint_sha=EXPECTED_P242_CHECKPOINT_SHA256,
        bundle_sha=EXPECTED_P241_BUNDLE_SHA256,
    )
    _verify_manifest(
        p245_manifest_path,
        milestone="P2-45",
        response_sha=after_sha,
        checkpoint_sha=EXPECTED_P244_CHECKPOINT_SHA256,
        bundle_sha=EXPECTED_P244_BUNDLE_SHA256,
    )

    candidate = _load_candidate(p244_candidate_path)
    p243 = _json(p243_result_path)
    expected_p243 = contract["p243Baseline"]
    if (
        p243.get("milestone") != "P2-43"
        or p243.get("schemaValid") != expected_p243["schemaValid"]
        or p243.get("semanticPass") != expected_p243["semanticPass"]
        or p243.get("fieldCorrect") != expected_p243["fieldCorrect"]
    ):
        raise ValueError("P2-43 comparison baseline changed")
    for key, expected in expected_p243["trainingReuse"].items():
        if p243.get("trainingReuse", {}).get(key) != expected:
            raise ValueError(f"P2-43 training-reuse baseline changed: {key}")

    aggregates = {
        "before": Counter(),
        "after": Counter(),
        "afterReuse": Counter(),
        "afterGrounding": Counter(),
        "delta": Counter(),
    }
    action_by_language: dict[str, Counter[str]] = {
        language: Counter() for language in ("html", "css", "javascript")
    }
    schema_errors = Counter()
    field_transitions = {
        field: Counter()
        for field in (
            "language", "action", "targetKind", "targetRole",
            "constraintsExact", "hintCoverage",
        )
    }
    tasks_out: list[dict[str, Any]] = []
    similarities: list[float] = []

    for task in task_set["tasks"]:
        before = _analyze_response(
            task=task, row=before_rows[task["id"]], candidate=candidate
        )
        after = _analyze_response(
            task=task, row=after_rows[task["id"]], candidate=candidate
        )
        if before["strictSchemaValid"]:
            aggregates["before"]["schemaValid"] += 1
        if after["strictSchemaValid"]:
            aggregates["after"]["schemaValid"] += 1
        else:
            schema_errors[after["strictError"] or "unknown"] += 1

        for field in field_transitions:
            before_ok = before["correctness"][field]
            after_ok = after["correctness"][field]
            if before_ok:
                aggregates["before"][f"correct.{field}"] += 1
            if after_ok:
                aggregates["after"][f"correct.{field}"] += 1
            transition = (
                "improved" if (not before_ok and after_ok)
                else "regressed" if (before_ok and not after_ok)
                else "unchanged-correct" if before_ok
                else "unchanged-wrong"
            )
            field_transitions[field][transition] += 1

        before_score = sum(before["correctness"].values())
        after_score = sum(after["correctness"].values())
        task_delta = (
            "improved" if after_score > before_score
            else "regressed" if after_score < before_score
            else "unchanged"
        )
        aggregates["delta"][task_delta] += 1

        loose_action = after["looseCorrectness"]["action"]
        action_by_language[task["language"]]["looseCorrect"] += int(loose_action)
        action_by_language[task["language"]]["tasks"] += 1
        if after["strictSchemaValid"]:
            action_by_language[task["language"]]["strictSchemaValid"] += 1
            action_by_language[task["language"]]["strictCorrect"] += int(
                after["correctness"]["action"]
            )

        reuse = after.get("p244Reuse", {})
        for key, used in reuse.items():
            if used:
                aggregates["afterReuse"][key] += 1
        grounding = after.get("grounding", {})
        for key in (
            "targetRoleGroundedInRequest",
            "targetRoleAtomsKnownInP244Train",
            "allSearchHintsGroundedInRequest",
            "allConstraintTriplesSeenInP244Train",
        ):
            if grounding.get(key) is True:
                aggregates["afterGrounding"][key] += 1

        nearest = after.get("nearestP244TrainRequest")
        if isinstance(nearest, dict):
            similarities.append(float(nearest["similarity"]))

        tasks_out.append({
            "taskId": task["id"],
            "language": task["language"],
            "request": task["request"],
            "expected": task["expectedPlan"],
            "delta": task_delta,
            "before": before,
            "after": after,
        })

    field_names = tuple(field_transitions)
    after_fields = {
        field: aggregates["after"][f"correct.{field}"] for field in field_names
    }
    before_fields = {
        field: aggregates["before"][f"correct.{field}"] for field in field_names
    }
    p243_reuse = p243["trainingReuse"]
    reuse_summary = {
        "targetRole": aggregates["afterReuse"]["trainTargetRole"],
        "constraintSet": aggregates["afterReuse"]["trainConstraintSet"],
        "searchHints": aggregates["afterReuse"]["trainSearchHints"],
        "semanticBundle": aggregates["afterReuse"]["trainSemanticBundle"],
        "fullPlan": aggregates["afterReuse"]["trainFullPlan"],
        "componentRecombination": aggregates["afterReuse"]["trainComponentRecombination"],
    }

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "kind": "plex-p2-46-semantic-transfer-failure-diagnostic-result-v1",
        "status": "diagnostic-complete-awaiting-interpretation",
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "optimizerCreated": False,
        "finalHoldoutOpened": False,
        "taskSetId": task_set["setId"],
        "taskSetSha256": task_sha,
        "p242ResponsesSha256": before_sha,
        "p245ResponsesSha256": after_sha,
        "p244CandidateSha256": EXPECTED_P244_CANDIDATE_SHA256,
        "strictComparison": {
            "beforeP242": {
                "schemaValid": aggregates["before"]["schemaValid"],
                "fieldCorrect": before_fields,
            },
            "afterP245": {
                "schemaValid": aggregates["after"]["schemaValid"],
                "fieldCorrect": after_fields,
            },
            "delta": {
                "schemaValid": (
                    aggregates["after"]["schemaValid"]
                    - aggregates["before"]["schemaValid"]
                ),
                "fieldCorrect": {
                    field: after_fields[field] - before_fields[field]
                    for field in field_names
                },
            },
        },
        "taskDelta": {
            "improved": aggregates["delta"]["improved"],
            "regressed": aggregates["delta"]["regressed"],
            "unchanged": aggregates["delta"]["unchanged"],
            "fieldTransitions": {
                field: dict(field_transitions[field]) for field in field_names
            },
        },
        "p244TrainingReuse": reuse_summary,
        "p243TrainingReuseBaseline": {
            key: p243_reuse[key] for key in (
                "targetRole", "constraintSet", "searchHints",
                "semanticBundle", "fullPlan", "componentRecombination",
            )
        },
        "p244ReuseDeltaFromP243": {
            key: reuse_summary[key] - p243_reuse[key]
            for key in reuse_summary
        },
        "p244ValidationReuse": {
            "targetRole": aggregates["afterReuse"]["validationTargetRole"],
            "semanticBundle": aggregates["afterReuse"]["validationSemanticBundle"],
            "validationOnlyTargetRole":
                aggregates["afterReuse"]["validationOnlyTargetRole"],
            "validationOnlySemanticBundle":
                aggregates["afterReuse"]["validationOnlySemanticBundle"],
        },
        "requestGrounding": {
            "targetRoleGroundedInRequest":
                aggregates["afterGrounding"]["targetRoleGroundedInRequest"],
            "targetRoleAtomsKnownInP244Train":
                aggregates["afterGrounding"]["targetRoleAtomsKnownInP244Train"],
            "allSearchHintsGroundedInRequest":
                aggregates["afterGrounding"]["allSearchHintsGroundedInRequest"],
            "allConstraintTriplesSeenInP244Train":
                aggregates["afterGrounding"]["allConstraintTriplesSeenInP244Train"],
        },
        "schemaFailureReasons": dict(schema_errors),
        "actionByLanguage": {
            language: dict(action_by_language[language])
            for language in ("html", "css", "javascript")
        },
        "nearestP244TrainRequestSimilarity": {
            "tasksMeasured": len(similarities),
            "mean": sum(similarities) / len(similarities) if similarities else None,
            "minimum": min(similarities) if similarities else None,
            "maximum": max(similarities) if similarities else None,
        },
        "signals": {
            "semanticPassStillAbsent": (
                after_fields["targetRole"] == 0
                and after_fields["constraintsExact"] == 0
                and after_fields["hintCoverage"] == 0
            ),
            "strictSchemaRegressedFromP243": (
                aggregates["after"]["schemaValid"] < p243["schemaValid"]
            ),
            "actionRegressedFromP243": (
                after_fields["action"] < p243["fieldCorrect"]["action"]
            ),
            "exactTrainingBundleReuseReducedFromP243": (
                reuse_summary["semanticBundle"] < p243_reuse["semanticBundle"]
            ),
            "exactTrainingRoleReuseReducedFromP243": (
                reuse_summary["targetRole"] < p243_reuse["targetRole"]
            ),
        },
        "tasks": tasks_out,
    }
