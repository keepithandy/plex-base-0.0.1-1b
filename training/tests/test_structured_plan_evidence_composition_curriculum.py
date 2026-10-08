"""Portable regressions for P2-44 evidence-first semantic composition."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from plex_training.cli import main

from plex_training.structured_plan_evidence_composition_curriculum import (
    FAMILIES,
    _contract,
    _validate_rows,
    build_candidate_rows,
    generate_evidence_composition_candidate,
    review_evidence_composition_curriculum,
)

TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
CONTRACT = Path(
    "training/pretraining/p2-44-evidence-first-semantic-composition-preparation-contract.json"
)


class EvidenceCompositionCurriculumTests(unittest.TestCase):
    def test_contract_preserves_zero_update_composition_boundary(self) -> None:
        value = _contract(CONTRACT)
        self.assertEqual(value["milestone"], "P2-44")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertFalse(value["automaticTrainingExtension"])
        self.assertIsNone(value["trainingCommand"])
        self.assertEqual(value["researchOptimizerUpdates"], 0)
        self.assertFalse(value["finalHoldoutOpened"])
        self.assertEqual(value["design"]["records"], 162)
        self.assertEqual(value["design"]["groups"], 54)
        self.assertEqual(value["design"]["trainRecords"], 108)
        self.assertEqual(value["design"]["validationRecords"], 54)
        self.assertTrue(value["design"]["opaqueSyntheticRoleIdentifiersProhibited"])
        self.assertTrue(value["design"]["heldoutCombinationGeneralizationRequired"])
        self.assertTrue(value["splitPolicy"]["validationMayNotReuseExactTargetRoles"])
        self.assertTrue(value["splitPolicy"]["validationMayNotReuseExactSemanticBundles"])
        self.assertTrue(value["splitPolicy"]["validationMayNotReuseExactFullPlans"])

    def test_candidate_has_novel_combinations_of_familiar_atoms(self) -> None:
        rows = build_candidate_rows()
        summary = _validate_rows(rows, TASK_SET)

        self.assertEqual(summary["records"], 162)
        self.assertEqual(summary["groups"], 54)
        self.assertEqual(summary["trainRecords"], 108)
        self.assertEqual(summary["validationRecords"], 54)
        self.assertEqual(summary["uniqueRequests"], 162)
        self.assertEqual(summary["uniqueTargetRoles"], 108)
        self.assertEqual(summary["trainUniqueTargetRoles"], 72)
        self.assertEqual(summary["validationUniqueTargetRoles"], 36)

        self.assertEqual(summary["trainValidationExactTargetRoleOverlap"], 0)
        self.assertEqual(summary["trainValidationExactSemanticBundleOverlap"], 0)
        self.assertEqual(summary["trainValidationExactFullPlanOverlap"], 0)

        self.assertEqual(
            summary["validationRoleAtomsSeenInTrain"],
            summary["validationRoleAtomCount"],
        )
        self.assertEqual(
            summary["validationConstraintAtomsSeenInTrain"],
            summary["validationConstraintAtomCount"],
        )
        self.assertEqual(
            summary["validationHintAtomsSeenInTrain"],
            summary["validationHintAtomCount"],
        )

        self.assertEqual(summary["p231ExactRequestOverlap"], 0)
        self.assertEqual(summary["p231TargetRoleOverlap"], 0)
        self.assertEqual(summary["p231ExpectedPlanOverlap"], 0)

        for language in ("html", "css", "javascript"):
            self.assertEqual(summary["perLanguage"][language], {"train": 36, "validation": 18})
        for family in FAMILIES:
            self.assertEqual(
                summary["contrastFamilies"][family],
                {"trainGroups": 6, "validationGroups": 3, "records": 27},
            )

    def test_every_semantic_target_is_request_grounded_and_has_no_p2_prefix(self) -> None:
        for row in build_candidate_rows():
            self.assertFalse(row["targetRole"].startswith("p2"))
            request = row["request"].casefold()
            for phrase in row["evidence"]["rolePhrases"]:
                self.assertIn(phrase.casefold(), request)
            for phrase in row["evidence"]["constraintPhrases"]:
                self.assertIn(phrase.casefold(), request)
            for phrase in row["evidence"]["hintPhrases"]:
                self.assertIn(phrase.casefold(), request)
            self.assertEqual(
                row["targetRole"],
                "-".join(row["semanticAtoms"]["role"]),
            )

    def test_cli_wires_generate_and_review_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            report = root / "review-report.json"

            with redirect_stdout(StringIO()):
                status = main([
                    "plan-evidence-composition-generate",
                    "--candidate", str(candidate),
                    "--review", str(review),
                    "--development-task-set", str(TASK_SET),
                    "--contract", str(CONTRACT),
                ])
            self.assertEqual(status, 0)

            output = StringIO()
            with redirect_stdout(output):
                status = main([
                    "plan-evidence-composition-review",
                    "--candidate", str(candidate),
                    "--review", str(review),
                    "--development-task-set", str(TASK_SET),
                    "--contract", str(CONTRACT),
                    "--report", str(report),
                ])
            self.assertEqual(status, 0)
            parsed = json.loads(output.getvalue())
            self.assertEqual(parsed["status"], "candidate-review-passed")
            self.assertFalse(parsed["modelTrainingAuthorized"])
            self.assertTrue(report.is_file())

    def test_generate_and_review_roundtrip_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"

            generated = generate_evidence_composition_candidate(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=CONTRACT,
            )
            checked = review_evidence_composition_curriculum(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=CONTRACT,
            )

            self.assertEqual(generated["candidateSha256"], checked["candidateSha256"])
            self.assertEqual(generated["records"], 162)
            self.assertEqual(checked["status"], "candidate-review-passed")
            self.assertFalse(checked["tokenizerPreflight"]["checked"])
            self.assertFalse(checked["modelTrainingAuthorized"])
            self.assertFalse(checked["trainingPerformed"])
            self.assertEqual(checked["researchOptimizerUpdates"], 0)
            self.assertFalse(checked["finalHoldoutOpened"])

            rows = [
                json.loads(line)
                for line in candidate.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 162)


if __name__ == "__main__":
    unittest.main()
