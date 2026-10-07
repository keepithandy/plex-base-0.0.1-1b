"""Portable P2-38 contrast-candidate and zero-update review regressions."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.cli import main
from plex_training.structured_plan import parse_plan_response, render_plan_request_prompt
from plex_training import structured_plan_semantic_binding_curriculum as curriculum

CANDIDATE = Path("training/phase2/drafts/p2-38-semantic-binding-candidate-v1.jsonl")
REVIEW = Path("training/phase2/drafts/p2-38-semantic-binding-candidate-v1.review.json")
DEV = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
P235 = Path("training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl")
CONTRACT = Path("training/pretraining/p2-38-semantic-binding-preparation-contract.json")


def review(candidate=CANDIDATE, metadata=REVIEW):
    return curriculum.review_semantic_binding_curriculum(
        candidate_path=candidate, review_path=metadata,
        development_task_set_path=DEV, p235_candidate_path=P235,
        contract_path=CONTRACT,
    )


def change_role(rows, role):
    rows[0]["targetRole"] = role
    plan = json.loads(rows[0]["solution"])
    plan["targetRole"] = role
    rows[0]["solution"] = json.dumps(plan, separators=(",", ":"))


class SemanticBindingCurriculumTests(unittest.TestCase):
    def test_committed_candidate_and_contract(self):
        report = review()
        self.assertEqual(report["candidateSha256"], curriculum.EXPECTED_CANDIDATE_SHA256)
        self.assertEqual((report["records"], report["groups"]), (108, 36))
        self.assertEqual((report["trainRecords"], report["validationRecords"]), (72, 36))
        self.assertEqual((report["trainGroups"], report["validationGroups"]), (24, 12))
        self.assertEqual(report["perLanguage"], {
            language: {"train": 24, "validation": 12}
            for language in ("html", "css", "javascript")
        })
        self.assertEqual((report["uniqueRequests"], report["uniqueTargetRoles"]), (108, 108))
        self.assertEqual(report["strictFullPlanSolutions"], 108)
        for key in ("p231ExactRequestOverlap", "p231TargetRoleOverlap", "p235TargetRoleOverlap"):
            self.assertEqual(report[key], 0)
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])
        contract = curriculum._contract(CONTRACT)
        self.assertFalse(contract["modelTrainingAuthorized"])
        self.assertIsNone(contract["trainingCommand"])

    def test_every_group_uses_three_distinct_complete_production_plans(self):
        rows = [json.loads(line) for line in CANDIDATE.read_text(encoding="utf-8").splitlines()]
        groups = {}
        for row in rows:
            groups.setdefault(row["contrastGroupId"], []).append(row)
            self.assertEqual(
                curriculum.render_p238_record(row),
                render_plan_request_prompt(row["language"], row["request"]) + row["solution"],
            )
            plan = parse_plan_response(row["solution"])
            self.assertEqual(plan["targetRole"], row["targetRole"])
        self.assertEqual(len(groups), 36)
        for entries in groups.values():
            self.assertEqual(len(entries), 3)
            for key in ("id", "request", "targetRole", "solution"):
                self.assertEqual(len({row[key] for row in entries}), 3)
            for key in ("language", "candidateSplit"):
                self.assertEqual(len({row[key] for row in entries}), 1)

    def test_reviewer_rejects_leakage_and_split_changes(self):
        original = [json.loads(line) for line in CANDIDATE.read_text(encoding="utf-8").splitlines()]
        dev = json.loads(DEV.read_text(encoding="utf-8"))["tasks"][0]
        p235_role = json.loads(P235.read_text(encoding="utf-8").splitlines()[0])["targetRole"]
        for label, change in (
            ("duplicate role", lambda rows: rows[1].update(targetRole=rows[0]["targetRole"])),
            ("split group", lambda rows: rows[1].update(candidateSplit="validation")),
            ("P2-31 request", lambda rows: rows[0].update(request=dev["request"])),
            ("P2-31 role", lambda rows: change_role(rows, dev["expectedPlan"]["targetRole"])),
            ("P2-35 role", lambda rows: change_role(rows, p235_role)),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                rows = [dict(row) for row in original]
                change(rows)
                raw = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows).encode()
                candidate = Path(temporary) / "candidate.jsonl"
                candidate.write_bytes(raw)
                metadata = json.loads(REVIEW.read_text(encoding="utf-8"))
                metadata["candidateSha256"] = hashlib.sha256(raw).hexdigest()
                metadata["byteCount"] = len(raw)
                review_path = Path(temporary) / "review.json"
                review_path.write_text(json.dumps(metadata), encoding="utf-8")
                with patch.object(curriculum, "EXPECTED_CANDIDATE_SHA256", metadata["candidateSha256"]):
                    with self.assertRaises(ValueError):
                        review(candidate, review_path)

    def test_cli_report_is_read_only_and_non_destructive(self):
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "review.json"
            self.assertEqual(main(["plan-semantic-binding-review", "--report", str(report_path)]), 0)
            output = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(output["records"], 108)
            self.assertFalse(output["trainingPerformed"])
            self.assertEqual(output["researchOptimizerUpdates"], 0)
            before = report_path.read_bytes()
            self.assertEqual(main(["plan-semantic-binding-review", "--report", str(report_path)]), 2)
            self.assertEqual(report_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
