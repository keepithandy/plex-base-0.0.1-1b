"""P2-43 read-only diagnosis of P2-41 semantic-bundle reuse on P2-42 outputs."""

from __future__ import annotations

import hashlib
import json
import re
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

MILESTONE = "P2-43"
KIND = "plex-p2-43-semantic-bundle-reuse-diagnostic-contract-v1"
DEFAULT_CONTRACT = Path("training/pretraining/p2-43-semantic-bundle-reuse-contract.json")
EXPECTED_TASK_SET_SHA256 = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
EXPECTED_P241_CANDIDATE_SHA256 = "20f309181adbd4c86ff0c5a7ad833792d754e3a9102000003922696a237b64ba"
EXPECTED_P242_CHECKPOINT_SHA256 = "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
EXPECTED_P241_BUNDLE_SHA256 = "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a"
_TOKEN = re.compile(r"[a-z0-9]+")
_GENERIC_REQUEST_TOKENS = {
    "a", "an", "and", "as", "be", "by", "do", "for", "from", "in", "into", "is",
    "it", "keep", "only", "or", "plan", "request", "requested", "requirement",
    "requirements", "return", "semantic", "so", "target", "the", "to", "using",
    "with", "without", "modify", "create", "remove",
}


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path, 1024 * 1024)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != KIND
        or value.get("status") != "diagnostic-authorized"
        or value.get("modelTrainingAuthorized") is not False
    ):
        raise ValueError("P2-43 diagnostic contract is invalid")
    protected = value.get("protectedEvaluation")
    if (
        not isinstance(protected, dict)
        or protected.get("noGradientUpdates") is not True
        or protected.get("noResponseRepair") is not True
        or protected.get("noCheckpointSelection") is not True
        or protected.get("finalProjectHoldoutMustRemainClosed") is not True
    ):
        raise ValueError("P2-43 protected-evaluation boundary is invalid")
    return value


def _jsonl(path: Path, *, maximum_bytes: int) -> tuple[list[dict[str, Any]], bytes]:
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


def _constraint_signature(plan: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    return tuple(sorted((x["kind"], x["key"], x["value"]) for x in plan["constraints"]))


def _hint_signature(plan: dict[str, Any]) -> tuple[str, ...]:
    return tuple(x.casefold() for x in plan["searchHints"])


def _bundle_signature(plan: dict[str, Any]) -> tuple[Any, ...]:
    return (plan["targetRole"], _constraint_signature(plan), _hint_signature(plan))


def _full_signature(plan: dict[str, Any]) -> str:
    return json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(text.casefold()) if token not in _GENERIC_REQUEST_TOKENS}


def _jaccard(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _candidate_records(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    rows, raw = _jsonl(path, maximum_bytes=4 * 1024 * 1024)
    if canonical_text_sha256(raw) != EXPECTED_P241_CANDIDATE_SHA256:
        raise ValueError("P2-43 requires the exact frozen P2-41 candidate")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        record_id = row.get("id")
        split = row.get("candidateSplit")
        request = row.get("request")
        solution = row.get("solution")
        if (
            not isinstance(record_id, str)
            or record_id in seen
            or split not in {"train", "validation"}
            or not isinstance(request, str)
            or not isinstance(solution, str)
        ):
            raise ValueError("P2-41 diagnostic candidate row is invalid")
        seen.add(record_id)
        plan = parse_plan_response(solution)
        records.append({
            "id": record_id,
            "split": split,
            "family": row.get("contrastFamily"),
            "group": row.get("contrastGroupId"),
            "request": request,
            "plan": plan,
        })
    if len(records) != 108 or sum(x["split"] == "train" for x in records) != 72:
        raise ValueError("P2-41 candidate topology changed")
    return records, raw


def _match_records(
    records: list[dict[str, Any]],
    *,
    split: str,
    predicate: Any,
) -> list[dict[str, Any]]:
    return [record for record in records if record["split"] == split and predicate(record["plan"])]


def diagnose_semantic_bundle_reuse(
    *,
    task_set_path: Path,
    responses_path: Path,
    p241_candidate_path: Path,
    p242_manifest_path: Path,
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Measure whether P2-42 outputs reuse P2-41 semantic bundles instead of request evidence."""
    contract = _contract(contract_path)

    if (
        task_set_path.is_symlink()
        or not task_set_path.is_file()
        or task_set_path.stat().st_size > MAX_PLAN_TASK_SET_BYTES
    ):
        raise ValueError("P2-43 task set is missing, linked, or oversized")
    task_raw = task_set_path.read_bytes()
    task_sha = canonical_text_sha256(task_raw)
    task_set = validate_plan_task_set(json.loads(task_raw.decode("utf-8")))
    if task_set["kind"] != "development":
        raise ValueError("P2-43 is development-only")
    if task_sha != EXPECTED_TASK_SET_SHA256 or len(task_set["tasks"]) != 18:
        raise ValueError("P2-43 requires the unchanged P2-31 development set")

    responses, responses_raw = _jsonl(responses_path, maximum_bytes=4 * 1024 * 1024)
    response_sha = hashlib.sha256(responses_raw).hexdigest()
    manifest = _json(p242_manifest_path)
    expected_run = contract.get("p242Run")
    if not isinstance(expected_run, dict):
        raise ValueError("P2-43 contract is missing the P2-42 run identity")
    for key, expected in {
        "milestone": "P2-42",
        "checkpointSha256": EXPECTED_P242_CHECKPOINT_SHA256,
        "checkpointStep": 100,
        "taskSetSha256": EXPECTED_TASK_SET_SHA256,
        "taskCount": 18,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "tokenizerBundleManifestSha256": EXPECTED_P241_BUNDLE_SHA256,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }.items():
        if manifest.get(key) != expected:
            raise ValueError(f"P2-43 P2-42 manifest mismatch: {key}")
    if manifest.get("responsesSha256") != response_sha:
        raise ValueError("P2-43 responses differ from the P2-42 run manifest")
    for key, expected in {
        "checkpointSha256": EXPECTED_P242_CHECKPOINT_SHA256,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "tokenizerBundleManifestSha256": EXPECTED_P241_BUNDLE_SHA256,
        "taskSetSha256": EXPECTED_TASK_SET_SHA256,
    }.items():
        if expected_run.get(key) != expected:
            raise ValueError(f"P2-43 contract P2-42 identity mismatch: {key}")

    candidate, candidate_raw = _candidate_records(p241_candidate_path)
    if canonical_text_sha256(candidate_raw) != contract.get("p241Candidate", {}).get("sha256"):
        raise ValueError("P2-43 contract does not pin the frozen P2-41 candidate")

    by_response: dict[str, dict[str, Any]] = {}
    task_ids = {task["id"] for task in task_set["tasks"]}
    for row in responses:
        if set(row) - {"taskId", "text", "truncated"}:
            raise ValueError("P2-43 response rows contain unsupported fields")
        task_id = row.get("taskId")
        text = row.get("text")
        if (
            not isinstance(task_id, str)
            or task_id not in task_ids
            or task_id in by_response
            or not isinstance(text, str)
            or len(text.encode("utf-8")) > MAX_PLAN_RESPONSE_BYTES
            or ("truncated" in row and not isinstance(row["truncated"], bool))
        ):
            raise ValueError("P2-43 response row is invalid")
        by_response[task_id] = row

    aggregate = Counter()
    role_distribution = Counter()
    bundle_distribution = Counter()
    tasks_out: list[dict[str, Any]] = []

    for task in task_set["tasks"]:
        row = by_response.get(task["id"])
        if row is None:
            aggregate["missingResponse"] += 1
            tasks_out.append({
                "taskId": task["id"],
                "language": task["language"],
                "classification": "missing-response",
            })
            continue

        text = row["text"]
        truncated = bool(row.get("truncated", False))
        plan = None
        error = None
        if not truncated:
            try:
                plan = parse_plan_response(text)
            except ValueError as exc:
                error = str(exc)
        if plan is None:
            aggregate["schemaInvalid"] += 1
            tasks_out.append({
                "taskId": task["id"],
                "language": task["language"],
                "classification": "schema-invalid",
                "truncated": truncated,
                "strictError": error,
                "preview": text[:280],
            })
            continue

        aggregate["schemaValid"] += 1
        expected = task["expectedPlan"]
        joined_hints = " ".join(plan["searchHints"]).casefold()
        correctness = {
            "language": plan["language"] == task["language"],
            "action": plan["action"] == expected["action"],
            "targetKind": plan["targetKind"] == expected["targetKind"],
            "targetRole": plan["targetRole"] == expected["targetRole"],
            "constraintsExact": _constraint_signature(plan)
            == tuple(sorted((x["kind"], x["key"], x["value"]) for x in expected["constraints"])),
            "hintCoverage": all(keyword in joined_hints for keyword in expected["hintKeywords"]),
        }
        for name, passed in correctness.items():
            if passed:
                aggregate[f"correct.{name}"] += 1

        role_distribution[plan["targetRole"]] += 1
        bundle_key = json.dumps(
            {
                "targetRole": plan["targetRole"],
                "constraints": _constraint_signature(plan),
                "searchHints": _hint_signature(plan),
            },
            sort_keys=True,
            default=list,
        )
        bundle_distribution[bundle_key] += 1

        train_role = _match_records(
            candidate, split="train", predicate=lambda p: p["targetRole"] == plan["targetRole"]
        )
        train_constraints = _match_records(
            candidate,
            split="train",
            predicate=lambda p: _constraint_signature(p) == _constraint_signature(plan),
        )
        train_hints = _match_records(
            candidate, split="train", predicate=lambda p: _hint_signature(p) == _hint_signature(plan)
        )
        train_bundle = _match_records(
            candidate, split="train", predicate=lambda p: _bundle_signature(p) == _bundle_signature(plan)
        )
        train_full = _match_records(
            candidate, split="train", predicate=lambda p: _full_signature(p) == _full_signature(plan)
        )
        validation_role = _match_records(
            candidate,
            split="validation",
            predicate=lambda p: p["targetRole"] == plan["targetRole"],
        )
        validation_bundle = _match_records(
            candidate,
            split="validation",
            predicate=lambda p: _bundle_signature(p) == _bundle_signature(plan),
        )

        reuse = {
            "trainTargetRole": bool(train_role),
            "trainConstraintSet": bool(train_constraints),
            "trainSearchHints": bool(train_hints),
            "trainSemanticBundle": bool(train_bundle),
            "trainFullPlan": bool(train_full),
            "validationTargetRole": bool(validation_role),
            "validationSemanticBundle": bool(validation_bundle),
        }
        for name, used in reuse.items():
            if used:
                aggregate[f"reuse.{name}"] += 1
        if not correctness["targetRole"] and reuse["trainTargetRole"]:
            aggregate["wrongTargetRoleButSeenInTrain"] += 1
        if not all(correctness.values()) and reuse["trainSemanticBundle"]:
            aggregate["wrongPlanButExactTrainSemanticBundle"] += 1

        bundle_owners = train_bundle or train_role
        owner_details = []
        for owner in bundle_owners[:12]:
            owner_details.append({
                "recordId": owner["id"],
                "family": owner["family"],
                "group": owner["group"],
                "requestTokenJaccard": _jaccard(task["request"], owner["request"]),
            })

        expected_tokens = set(_TOKEN.findall(expected["targetRole"].replace("-", " ")))
        for keyword in expected["hintKeywords"]:
            expected_tokens.update(_TOKEN.findall(keyword.casefold()))
        actual_semantic_text = " ".join([
            plan["targetRole"],
            *[x["key"] for x in plan["constraints"]],
            *[x["value"] for x in plan["constraints"]],
            *plan["searchHints"],
        ])
        actual_tokens = set(_TOKEN.findall(actual_semantic_text.casefold()))
        evidence_hits = sorted(expected_tokens & actual_tokens)
        evidence_coverage = len(evidence_hits) / len(expected_tokens) if expected_tokens else 1.0

        classification = (
            "semantic-pass"
            if all(correctness.values())
            else "wrong-plan-exact-train-bundle"
            if reuse["trainSemanticBundle"]
            else "wrong-plan-train-role-reuse"
            if reuse["trainTargetRole"]
            else "wrong-plan-novel-role-or-bundle"
        )
        aggregate[f"classification.{classification}"] += 1
        tasks_out.append({
            "taskId": task["id"],
            "language": task["language"],
            "difficulty": task["difficulty"],
            "classification": classification,
            "correctness": correctness,
            "reuse": reuse,
            "actualTargetRole": plan["targetRole"],
            "expectedTargetRole": expected["targetRole"],
            "expectedSemanticTokenCoverage": evidence_coverage,
            "expectedSemanticTokenHits": evidence_hits,
            "trainingOwners": owner_details,
        })

    schema_valid = aggregate["schemaValid"]
    summary = {
        "schemaValid": schema_valid,
        "schemaInvalid": aggregate["schemaInvalid"],
        "fieldCorrect": {
            name: aggregate[f"correct.{name}"]
            for name in (
                "language", "action", "targetKind", "targetRole",
                "constraintsExact", "hintCoverage",
            )
        },
        "trainingReuse": {
            "targetRole": aggregate["reuse.trainTargetRole"],
            "constraintSet": aggregate["reuse.trainConstraintSet"],
            "searchHints": aggregate["reuse.trainSearchHints"],
            "semanticBundle": aggregate["reuse.trainSemanticBundle"],
            "fullPlan": aggregate["reuse.trainFullPlan"],
            "wrongTargetRoleButSeenInTrain": aggregate["wrongTargetRoleButSeenInTrain"],
            "wrongPlanButExactTrainSemanticBundle": aggregate["wrongPlanButExactTrainSemanticBundle"],
        },
        "validationReuse": {
            "targetRole": aggregate["reuse.validationTargetRole"],
            "semanticBundle": aggregate["reuse.validationSemanticBundle"],
        },
        "classifications": {
            name: aggregate[f"classification.{name}"]
            for name in (
                "semantic-pass",
                "wrong-plan-exact-train-bundle",
                "wrong-plan-train-role-reuse",
                "wrong-plan-novel-role-or-bundle",
            )
        },
        "uniqueOutputTargetRoles": len(role_distribution),
        "repeatedTargetRoles": {
            role: count for role, count in sorted(role_distribution.items()) if count > 1
        },
        "repeatedSemanticBundles": sum(count > 1 for count in bundle_distribution.values()),
    }
    baseline = contract.get("comparisonBaseline", {})
    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "kind": "plex-p2-43-semantic-bundle-reuse-diagnostic-result-v1",
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "taskSetId": task_set["setId"],
        "taskSetSha256": task_sha,
        "responsesSha256": response_sha,
        "p242CheckpointSha256": manifest["checkpointSha256"],
        "p241CandidateSha256": EXPECTED_P241_CANDIDATE_SHA256,
        "tasksExpected": len(task_set["tasks"]),
        "responsesPresent": len(responses),
        "summary": summary,
        "comparisonBaseline": baseline,
        "diagnosis": {
            "schemaValidDeltaFromP239": schema_valid - int(baseline.get("schemaValid", 0)),
            "wrongTargetRoleButSeenInTrain": aggregate["wrongTargetRoleButSeenInTrain"],
            "wrongPlanButExactTrainSemanticBundle": aggregate["wrongPlanButExactTrainSemanticBundle"],
            "note": (
                "These are descriptive measurements, not retrospectively chosen pass/fail thresholds. "
                "P2-43 does not authorize more training, checkpoint selection, response repair, "
                "or final-holdout access."
            ),
        },
        "tasks": tasks_out,
    }
