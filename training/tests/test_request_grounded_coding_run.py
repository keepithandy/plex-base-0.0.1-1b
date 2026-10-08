"""Regressions for guarded P2-48 final bounded training authorization."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.request_grounded_coding_run import (
    AUTHORIZED_DATE,
    AUTHORIZED_STATUS,
    FROZEN_BASELINE_BATCHES,
    FROZEN_BASELINE_LOSS,
    _training_settings,
    _validate_authorization,
    run_request_grounded_training,
)

CONTRACT = Path("training/pretraining/p2-48-first-run-contract.json")


class RequestGroundedRunAuthorizationTests(unittest.TestCase):
    def _draft(self) -> dict:
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _approved(self) -> dict:
        value = copy.deepcopy(self._draft())
        value["status"] = AUTHORIZED_STATUS
        value["modelTrainingAuthorized"] = True
        value["approvedBy"] = "keepithandy"
        value["approvedDate"] = AUTHORIZED_DATE
        return value

    def test_repository_contract_is_exact_owner_approved_packet(self) -> None:
        value = self._draft()
        self.assertEqual(value["status"], AUTHORIZED_STATUS)
        self.assertTrue(value["approvalPacketComplete"])
        self.assertTrue(value["modelTrainingAuthorized"])
        self.assertEqual(value["approvedBy"], "keepithandy")
        self.assertEqual(value["approvedDate"], AUTHORIZED_DATE)
        self.assertEqual(value["evaluation"]["baselineLoss"], FROZEN_BASELINE_LOSS)
        self.assertEqual(value["evaluation"]["baselineBatches"], FROZEN_BASELINE_BATCHES)
        self.assertEqual(value["training"]["maximumSteps"], 100)
        self.assertEqual(value["training"]["maximumWallTimeSeconds"], 600)
        self.assertEqual(
            value["training"]["expectedRealTargetPositionsAt100Steps"],
            429375,
        )
        self.assertFalse(value["training"]["resumeAllowed"])
        self.assertFalse(value["training"]["automaticContinuation"])

        _validate_authorization(value)

    def test_exact_owner_approved_projection_is_accepted(self) -> None:
        value = self._approved()
        _validate_authorization(value)

    def test_approval_validator_rejects_baseline_schedule_or_sampler_drift(self) -> None:
        value = self._approved()

        changed_loss = copy.deepcopy(value)
        changed_loss["evaluation"]["baselineLoss"] = FROZEN_BASELINE_LOSS + 0.001
        with self.assertRaisesRegex(ValueError, "baselineLoss"):
            _validate_authorization(changed_loss)

        changed_steps = copy.deepcopy(value)
        changed_steps["training"]["maximumSteps"] = 101
        with self.assertRaisesRegex(ValueError, "maximumSteps"):
            _validate_authorization(changed_steps)

        changed_sampler = copy.deepcopy(value)
        changed_sampler["training"]["sampler"]["records"] = 71
        with self.assertRaisesRegex(ValueError, "training.sampler"):
            _validate_authorization(changed_sampler)

    def test_runner_fails_closed_before_preflight_with_unsigned_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "artifacts"
            unsigned = copy.deepcopy(self._draft())
            unsigned["status"] = "owner-approval-required"
            unsigned["modelTrainingAuthorized"] = False
            unsigned["approvedBy"] = None
            unsigned["approvedDate"] = None
            unsigned_path = Path(temporary) / "unsigned-contract.json"
            unsigned_path.write_text(
                json.dumps(unsigned, indent=2) + "\n",
                encoding="utf-8",
            )
            with patch(
                "plex_training.request_grounded_coding_run.preflight_request_grounded_training",
                side_effect=AssertionError(
                    "preflight must not run before explicit owner approval"
                ),
            ):
                with self.assertRaisesRegex(ValueError, "status"):
                    run_request_grounded_training(
                        bundle_dir=root / "bundle",
                        stage_checkpoint=root / "stage.pt",
                        authorization_contract_path=unsigned_path,
                        output_dir=root / "request-grounded" / "p2-48-first-run",
                        artifact_root=root,
                    )

    def test_training_settings_remain_bounded_and_nonresumable(self) -> None:
        draft = self._draft()
        settings = _training_settings(
            "authorization-sha",
            draft["training"]["sampler"],
        )
        self.assertEqual(
            settings["kind"],
            "p2-48-authorized-request-grounded-training-v1",
        )
        self.assertEqual(settings["maximumSteps"], 100)
        self.assertEqual(settings["maximumWallTimeSeconds"], 600)
        self.assertEqual(settings["microBatch"], 1)
        self.assertEqual(settings["gradientAccumulation"], 16)
        self.assertFalse(settings["resumeAllowed"])
        self.assertFalse(settings["automaticContinuation"])


if __name__ == "__main__":
    unittest.main()
