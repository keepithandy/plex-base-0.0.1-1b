"""Regressions for the guarded P2-44 first-run authorization path."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.structured_plan_evidence_composition_run import (
    AUTHORIZED_DATE,
    AUTHORIZED_STATUS,
    FROZEN_BASELINE_BATCHES,
    FROZEN_BASELINE_LOSS,
    _training_settings,
    _validate_authorization,
    run_evidence_composition_training,
)

CONTRACT = Path("training/pretraining/p2-44-first-run-contract.json")


class EvidenceCompositionRunAuthorizationTests(unittest.TestCase):
    def _draft(self) -> dict:
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_repository_contract_is_complete_but_not_owner_approved(self) -> None:
        value = self._draft()
        self.assertEqual(value["status"], "owner-approval-required")
        self.assertTrue(value["approvalPacketComplete"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertIsNone(value["approvedBy"])
        self.assertIsNone(value["approvedDate"])
        self.assertEqual(value["evaluation"]["baselineLoss"], FROZEN_BASELINE_LOSS)
        self.assertEqual(value["evaluation"]["baselineBatches"], FROZEN_BASELINE_BATCHES)
        self.assertEqual(value["training"]["maximumSteps"], 100)
        self.assertEqual(value["training"]["maximumWallTimeSeconds"], 600)
        self.assertFalse(value["training"]["resumeAllowed"])
        self.assertFalse(value["training"]["automaticContinuation"])

        with self.assertRaisesRegex(ValueError, "status"):
            _validate_authorization(value)

    def test_exact_owner_approved_projection_passes_validator(self) -> None:
        value = copy.deepcopy(self._draft())
        value["status"] = AUTHORIZED_STATUS
        value["modelTrainingAuthorized"] = True
        value["approvedBy"] = "keepithandy"
        value["approvedDate"] = AUTHORIZED_DATE

        _validate_authorization(value)

    def test_approval_validator_rejects_schedule_or_baseline_drift(self) -> None:
        value = copy.deepcopy(self._draft())
        value["status"] = AUTHORIZED_STATUS
        value["modelTrainingAuthorized"] = True
        value["approvedBy"] = "keepithandy"
        value["approvedDate"] = AUTHORIZED_DATE

        changed_loss = copy.deepcopy(value)
        changed_loss["evaluation"]["baselineLoss"] = FROZEN_BASELINE_LOSS + 0.001
        with self.assertRaisesRegex(ValueError, "baselineLoss"):
            _validate_authorization(changed_loss)

        changed_steps = copy.deepcopy(value)
        changed_steps["training"]["maximumSteps"] = 101
        with self.assertRaisesRegex(ValueError, "maximumSteps"):
            _validate_authorization(changed_steps)

        changed_sampler = copy.deepcopy(value)
        changed_sampler["training"]["sampler"]["records"] = 107
        with self.assertRaisesRegex(ValueError, "training.sampler"):
            _validate_authorization(changed_sampler)

    def test_runner_fails_closed_before_preflight_when_owner_approval_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "artifacts"
            with patch(
                "plex_training.structured_plan_evidence_composition_run.preflight_evidence_composition_training",
                side_effect=AssertionError("preflight must not run before owner approval"),
            ):
                with self.assertRaisesRegex(ValueError, "status"):
                    run_evidence_composition_training(
                        bundle_dir=root / "bundle",
                        stage_checkpoint=root / "stage.pt",
                        authorization_contract_path=CONTRACT,
                        output_dir=root / "structured-plan" / "p2-44-first-run",
                        artifact_root=root,
                    )

    def test_training_settings_remain_bounded_and_nonresumable(self) -> None:
        draft = self._draft()
        settings = _training_settings(
            "authorization-sha",
            draft["training"]["sampler"],
        )
        self.assertEqual(settings["kind"], "p2-44-authorized-evidence-composition-training-v1")
        self.assertEqual(settings["maximumSteps"], 100)
        self.assertEqual(settings["maximumWallTimeSeconds"], 600)
        self.assertEqual(settings["microBatch"], 1)
        self.assertEqual(settings["gradientAccumulation"], 16)
        self.assertFalse(settings["resumeAllowed"])
        self.assertFalse(settings["automaticContinuation"])


if __name__ == "__main__":
    unittest.main()
