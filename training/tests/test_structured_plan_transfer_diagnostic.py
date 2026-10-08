"""P2-46 semantic-transfer diagnostic regressions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.structured_plan import validate_plan_task_set
from plex_training.structured_plan_transfer_diagnostic import (
    DEFAULT_CONTRACT,
    DEFAULT_P244_CANDIDATE,
    DEFAULT_TASK_SET,
    EXPECTED_P242_RESPONSES_SHA256,
    EXPECTED_P245_RESPONSES_SHA256,
    _contract,
    _load_candidate,
    diagnose_semantic_transfer_failure,
)


class SemanticTransferDiagnosticTests(unittest.TestCase):
    def test_contract_is_diagnostic_only_and_pins_frozen_evidence(self) -> None:
        value = _contract(DEFAULT_CONTRACT)
        self.assertEqual(value["milestone"], "P2-46")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["before"]["responsesSha256"],
            EXPECTED_P242_RESPONSES_SHA256,
        )
        self.assertEqual(
            value["after"]["responsesSha256"],
            EXPECTED_P245_RESPONSES_SHA256,
        )
        protected = value["protectedEvaluation"]
        self.assertTrue(protected["developmentOnly"])
        self.assertTrue(protected["noGradientUpdates"])
        self.assertTrue(protected["noOptimizerCreation"])
        self.assertTrue(protected["noResponseRepair"])
        self.assertTrue(protected["noCheckpointSelection"])
        self.assertTrue(protected["noNewCurriculum"])
        self.assertTrue(protected["finalProjectHoldoutMustRemainClosed"])

    def test_frozen_p244_candidate_loads_expected_topology(self) -> None:
        candidate = _load_candidate(DEFAULT_P244_CANDIDATE)
        records = candidate["records"]
        self.assertEqual(len(records), 162)
        self.assertEqual(sum(x["split"] == "train" for x in records), 108)
        self.assertEqual(sum(x["split"] == "validation" for x in records), 54)
        self.assertTrue(candidate["trainRoleAtoms"])
        self.assertTrue(candidate["trainConstraintAtoms"])
        self.assertTrue(candidate["trainHintAtoms"])

    def test_diagnostic_compares_before_and_after_without_training(self) -> None:
        task_set = validate_plan_task_set(
            json.loads(DEFAULT_TASK_SET.read_text(encoding="utf-8"))
        )

        def response_text(task: dict, *, duplicate_constraint: bool = False) -> str:
            expected = task["expectedPlan"]
            constraints = list(expected["constraints"])
            if duplicate_constraint:
                constraints.append(dict(constraints[0]))
            return json.dumps(
                {
                    "schemaVersion": 1,
                    "language": task["language"],
                    "action": expected["action"],
                    "targetKind": expected["targetKind"],
                    "targetRole": expected["targetRole"],
                    "constraints": constraints,
                    "searchHints": expected["hintKeywords"],
                },
                separators=(",", ":"),
            )

        before = {
            task["id"]: {
                "taskId": task["id"],
                "text": response_text(task),
                "truncated": False,
            }
            for task in task_set["tasks"]
        }
        after = {
            task["id"]: {
                "taskId": task["id"],
                "text": response_text(task, duplicate_constraint=index == 0),
                "truncated": False,
            }
            for index, task in enumerate(task_set["tasks"])
        }

        def fake_rows(path: Path, *, expected_sha256: str, task_ids: set[str]):
            if "before" in path.name:
                self.assertEqual(expected_sha256, EXPECTED_P242_RESPONSES_SHA256)
                return before, EXPECTED_P242_RESPONSES_SHA256
            self.assertEqual(expected_sha256, EXPECTED_P245_RESPONSES_SHA256)
            return after, EXPECTED_P245_RESPONSES_SHA256

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "plex_training.structured_plan_transfer_diagnostic._response_rows",
                side_effect=fake_rows,
            ), patch(
                "plex_training.structured_plan_transfer_diagnostic._verify_manifest",
                return_value={},
            ):
                report = diagnose_semantic_transfer_failure(
                    p242_responses_path=root / "before.jsonl",
                    p242_manifest_path=root / "before-manifest.json",
                    p245_responses_path=root / "after.jsonl",
                    p245_manifest_path=root / "after-manifest.json",
                )

        self.assertEqual(
            report["status"],
            "diagnostic-complete-awaiting-interpretation",
        )
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["optimizerCreated"])
        self.assertFalse(report["finalHoldoutOpened"])
        self.assertEqual(report["strictComparison"]["beforeP242"]["schemaValid"], 18)
        self.assertEqual(report["strictComparison"]["afterP245"]["schemaValid"], 17)
        self.assertEqual(report["strictComparison"]["delta"]["schemaValid"], -1)
        self.assertEqual(report["taskDelta"]["regressed"], 1)
        self.assertEqual(
            report["schemaFailureReasons"]["Structured plan constraints must be unique"],
            1,
        )
        self.assertEqual(len(report["tasks"]), 18)


if __name__ == "__main__":
    unittest.main()
