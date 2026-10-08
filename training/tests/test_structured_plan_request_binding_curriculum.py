"""P2-41 request-conditioned plan-binding curriculum preparation regressions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from plex_training.cli import main
from plex_training.structured_plan import parse_plan_response
from plex_training import structured_plan_request_binding_curriculum as curriculum

DEV = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
CONTRACT = Path("training/pretraining/p2-41-request-conditioned-plan-binding-preparation-contract.json")


class RequestBindingCurriculumTests(unittest.TestCase):
    def test_generator_is_deterministic_and_balanced(self):
        first = curriculum.build_candidate_rows()
        second = curriculum.build_candidate_rows()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 108)
        report = curriculum._validate_rows(first, DEV)
        self.assertEqual((report["records"], report["groups"]), (108, 36))
        self.assertEqual((report["trainRecords"], report["validationRecords"]), (72, 36))
        self.assertEqual(report["p231ExactRequestOverlap"], 0)
        self.assertEqual(report["p231TargetRoleOverlap"], 0)
        self.assertEqual(report["p231ExpectedPlanOverlap"], 0)
        for language in ("html", "css", "javascript"):
            self.assertEqual(report["perLanguage"][language], {"train": 24, "validation": 12})
        for family in curriculum.CONTRAST_FAMILIES:
            self.assertEqual(report["contrastFamilies"][family], {"groups": 9, "records": 27})

    def test_contrast_families_isolate_the_intended_dimension(self):
        groups = {}
        for row in curriculum.build_candidate_rows():
            groups.setdefault(row["contrastGroupId"], []).append(row)
        self.assertEqual(len(groups), 36)
        for group_id, rows in groups.items():
            plans = [parse_plan_response(row["solution"]) for row in rows]
            family = rows[0]["contrastFamily"]
            self.assertEqual(len(rows), 3)
            self.assertEqual(len({row["candidateSplit"] for row in rows}), 1)
            self.assertEqual(len({row["language"] for row in rows}), 1)
            if family == "role":
                self.assertEqual(len({plan["targetRole"] for plan in plans}), 3)
                self.assertEqual(len({plan["action"] for plan in plans}), 1)
            elif family == "constraints":
                self.assertEqual(len({plan["targetRole"] for plan in plans}), 1)
                self.assertEqual(len({plan["action"] for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["searchHints"]) for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}), 3)
            elif family == "action":
                self.assertEqual({plan["action"] for plan in plans}, {"create", "modify", "remove"})
                self.assertEqual(len({plan["targetRole"] for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["searchHints"]) for plan in plans}), 1)
            elif family == "hints":
                self.assertEqual(len({plan["targetRole"] for plan in plans}), 1)
                self.assertEqual(len({plan["action"] for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["constraints"], sort_keys=True) for plan in plans}), 1)
                self.assertEqual(len({json.dumps(plan["searchHints"]) for plan in plans}), 3)
            else:
                self.fail(f"unexpected contrast family for {group_id}: {family}")

    def test_contract_preserves_zero_update_state(self):
        contract = curriculum._contract(CONTRACT)
        self.assertTrue(contract["dataPreparationAuthorized"])
        self.assertFalse(contract["modelTrainingAuthorized"])
        self.assertIsNone(contract["trainingCommand"])
        self.assertFalse(contract["trainingPerformed"])
        self.assertEqual(contract["researchOptimizerUpdates"], 0)
        self.assertFalse(contract["finalHoldoutOpened"])

    def test_cli_generate_then_review_is_read_only_for_model_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            metadata = root / "candidate.review.json"
            report = root / "review-report.json"
            self.assertEqual(main([
                "plan-request-binding-generate",
                "--candidate", str(candidate),
                "--review", str(metadata),
            ]), 0)
            self.assertTrue(candidate.is_file())
            self.assertTrue(metadata.is_file())
            self.assertEqual(main([
                "plan-request-binding-review",
                "--candidate", str(candidate),
                "--review", str(metadata),
                "--report", str(report),
            ]), 0)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "candidate-review-passed")
            self.assertEqual(result["records"], 108)
            self.assertFalse(result["modelTrainingAuthorized"])
            self.assertFalse(result["trainingPerformed"])
            self.assertEqual(result["researchOptimizerUpdates"], 0)
            self.assertFalse(result["finalHoldoutOpened"])
            self.assertEqual(main([
                "plan-request-binding-generate",
                "--candidate", str(candidate),
                "--review", str(metadata),
            ]), 2)

    def test_review_rejects_candidate_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            metadata = root / "candidate.review.json"
            curriculum.generate_request_binding_candidate(
                candidate_path=candidate,
                review_path=metadata,
                development_task_set_path=DEV,
                contract_path=CONTRACT,
            )
            lines = candidate.read_text(encoding="utf-8").splitlines()
            row = json.loads(lines[0])
            row["request"] = json.loads(DEV.read_text(encoding="utf-8"))["tasks"][0]["request"]
            lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
            candidate.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                curriculum.review_request_binding_curriculum(
                    candidate_path=candidate,
                    review_path=metadata,
                    development_task_set_path=DEV,
                    contract_path=CONTRACT,
                )


if __name__ == "__main__":
    unittest.main()
