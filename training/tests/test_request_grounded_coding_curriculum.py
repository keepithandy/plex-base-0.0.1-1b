"""Portable regressions for P2-47 request-grounded coding representation."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from plex_training.cli import main
from plex_training.request_grounded_coding_curriculum import (
    EXPECTED_CANDIDATE_BYTES,
    EXPECTED_CANDIDATE_SHA256,
    FAMILIES,
    _contract,
    _validate_rows,
    build_candidate_rows,
    generate_request_grounded_coding_candidate,
    review_request_grounded_coding_curriculum,
    validate_request_grounded_change,
)

TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
CONTRACT = Path(
    "training/pretraining/p2-47-request-grounded-coding-preparation-contract.json"
)


class RequestGroundedCodingCurriculumTests(unittest.TestCase):
    def test_contract_is_preparation_only_and_removes_old_primary_targets(self) -> None:
        value = _contract(CONTRACT)
        self.assertEqual(value["milestone"], "P2-47")
        self.assertTrue(value["dataPreparationAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertFalse(value["automaticTrainingExtension"])
        self.assertIsNone(value["trainingCommand"])
        self.assertEqual(value["researchOptimizerUpdates"], 0)
        self.assertFalse(value["finalHoldoutOpened"])
        representation = value["representation"]
        self.assertTrue(representation["targetRoleRemoved"])
        self.assertTrue(representation["searchHintsRemoved"])
        self.assertTrue(representation["exactRequestEvidenceRequired"])
        self.assertTrue(representation["concreteCodingIntentRequired"])
        self.assertEqual(
            value["candidateIdentity"],
            {
                "candidateId": "p2-47-request-grounded-coding-v1",
                "sha256": EXPECTED_CANDIDATE_SHA256,
                "bytes": EXPECTED_CANDIDATE_BYTES,
            },
        )

    def test_candidate_holds_out_combinations_not_coding_atoms(self) -> None:
        rows = build_candidate_rows()
        summary = _validate_rows(rows, TASK_SET)

        self.assertEqual(summary["records"], 108)
        self.assertEqual(summary["groups"], 36)
        self.assertEqual(summary["trainRecords"], 72)
        self.assertEqual(summary["validationRecords"], 36)
        self.assertEqual(summary["uniqueRequests"], 108)
        self.assertEqual(summary["trainValidationExactRequestOverlap"], 0)
        self.assertEqual(summary["trainValidationExactSolutionOverlap"], 0)
        self.assertEqual(summary["trainValidationNonemptyBindingSetOverlap"], 0)
        self.assertEqual(
            summary["validationTargetsSeenInTrain"],
            summary["validationTargetCount"],
        )
        self.assertEqual(
            summary["validationBindingIntentsSeenInTrain"],
            summary["validationBindingIntentCount"],
        )
        self.assertEqual(
            summary["validationActionsSeenInTrain"],
            summary["validationActionCount"],
        )
        self.assertEqual(summary["p231ExactRequestOverlap"], 0)

        for language in ("html", "css", "javascript"):
            self.assertEqual(
                summary["perLanguage"][language],
                {"train": 24, "validation": 12},
            )
        for family in FAMILIES:
            self.assertEqual(
                summary["contrastFamilies"][family],
                {"train": 18, "validation": 9},
            )

    def test_every_learning_target_is_request_grounded(self) -> None:
        for row in build_candidate_rows():
            solution = validate_request_grounded_change(json.loads(row["solution"]))
            self.assertNotIn("targetRole", solution)
            self.assertNotIn("searchHints", solution)
            request = row["request"].casefold()
            self.assertIn(solution["targetEvidence"].casefold(), request)
            for binding in solution["bindings"]:
                self.assertIn(binding["evidence"].casefold(), request)
                self.assertTrue(binding["kind"])
                self.assertTrue(binding["key"])
                self.assertTrue(binding["value"])
            if solution["action"] == "remove":
                self.assertEqual(solution["bindings"], [])
            else:
                self.assertGreaterEqual(len(solution["bindings"]), 1)

    def test_generate_and_review_roundtrip_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"

            generated = generate_request_grounded_coding_candidate(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=CONTRACT,
            )
            checked = review_request_grounded_coding_curriculum(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=CONTRACT,
            )

            self.assertEqual(
                generated["candidateSha256"],
                EXPECTED_CANDIDATE_SHA256,
            )
            self.assertEqual(generated["byteCount"], EXPECTED_CANDIDATE_BYTES)
            self.assertEqual(generated["candidateSha256"], checked["candidateSha256"])
            self.assertEqual(checked["status"], "candidate-review-passed")
            self.assertFalse(checked["tokenizerPreflight"]["checked"])
            self.assertFalse(checked["modelTrainingAuthorized"])
            self.assertFalse(checked["trainingPerformed"])
            self.assertEqual(checked["researchOptimizerUpdates"], 0)
            self.assertFalse(checked["finalHoldoutOpened"])

    def test_cli_wires_generate_and_review_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            report = root / "report.json"

            with redirect_stdout(StringIO()):
                status = main([
                    "request-grounded-coding-generate",
                    "--candidate", str(candidate),
                    "--review", str(review),
                    "--development-task-set", str(TASK_SET),
                    "--contract", str(CONTRACT),
                ])
            self.assertEqual(status, 0)

            output = StringIO()
            with redirect_stdout(output):
                status = main([
                    "request-grounded-coding-review",
                    "--candidate", str(candidate),
                    "--review", str(review),
                    "--development-task-set", str(TASK_SET),
                    "--contract", str(CONTRACT),
                    "--report", str(report),
                ])
            self.assertEqual(status, 0)
            parsed = json.loads(output.getvalue())
            self.assertEqual(parsed["status"], "candidate-review-passed")
            self.assertEqual(
                parsed["candidateSha256"],
                EXPECTED_CANDIDATE_SHA256,
            )
            self.assertFalse(parsed["modelTrainingAuthorized"])
            self.assertTrue(report.is_file())


if __name__ == "__main__":
    unittest.main()
