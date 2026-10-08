"""Portable regressions for the P2-48 request-grounded training preflight."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.config import DEFAULT_CONFIG
from plex_training.request_grounded_coding_training import (
    EXPECTED_EXAMPLES,
    EXPECTED_REAL_TARGET_POSITIONS,
    EXPECTED_STAGE_CHECKPOINT_SHA256,
    EXPECTED_VALIDATION_BATCHES,
    _contract,
    preflight_request_grounded_training,
)

CONTRACT = Path("training/pretraining/p2-48-training-preflight-contract.json")


class _FakeModel(torch.nn.Module):
    config = DEFAULT_CONFIG

    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([1.0]))

    def to(self, device):
        return self


class _FakeTrainCorpus:
    sampler_record = {
        "kind": "complete-record-v1",
        "selection": "uniform-record-with-replacement",
        "records": 72,
    }

    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get("expected_text_prefix") != (
            "Map the coding request to one request-grounded change record.\n"
        ):
            raise AssertionError("P2-48 must use the request-grounded prompt prefix")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def replay_progress(self, seed: int, draws: int):
        if seed != 1337 or draws != EXPECTED_EXAMPLES:
            raise AssertionError("unexpected sampler replay")
        return EXPECTED_REAL_TARGET_POSITIONS, None


class _FakeValidationCorpus:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class RequestGroundedTrainingPreflightTests(unittest.TestCase):
    def test_contract_pins_stage_schedule_and_keeps_training_disabled(self) -> None:
        value = _contract(CONTRACT)
        self.assertTrue(value["trainingPreflightAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertFalse(value["optimizerStepAuthorized"])
        self.assertFalse(value["checkpointWriteAuthorized"])
        self.assertFalse(value["automaticContinuation"])
        self.assertEqual(value["stage"]["sha256"], EXPECTED_STAGE_CHECKPOINT_SHA256)
        self.assertEqual(value["stage"]["step"], 0)
        self.assertEqual(value["stage"]["tokensProcessed"], 0)
        self.assertEqual(value["proposal"]["maximumSteps"], 100)
        self.assertEqual(value["proposal"]["microBatch"], 1)
        self.assertEqual(value["proposal"]["gradientAccumulation"], 16)
        self.assertEqual(value["proposal"]["expectedExamplesAt100Steps"], 1600)
        self.assertEqual(
            value["proposal"]["expectedRealTargetPositionsAt100Steps"],
            EXPECTED_REAL_TARGET_POSITIONS,
        )
        self.assertFalse(value["proposal"]["resumeAllowed"])
        self.assertFalse(value["proposal"]["automaticContinuation"])

    def test_preflight_measures_baseline_without_optimizer_or_checkpoint_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "artifacts"
            bundle_root = root / "request-grounded" / "p2-48-training-bundle"
            bundle_root.mkdir(parents=True)
            (bundle_root / "manifest.json").write_text("{}\n", encoding="utf-8")
            stage = root / "request-grounded" / "p2-48-stage0" / "stage-checkpoint.pt"
            stage.parent.mkdir(parents=True)
            stage.write_bytes(b"stage")
            output = root / "request-grounded" / "p2-48-first-run"

            bundle = {
                "root": bundle_root,
                "trainPath": bundle_root / "train.tokens.u16le",
                "validationPath": bundle_root / "validation.tokens.u16le",
                "dataset": {
                    "sourceDatasetManifestSha256":
                        "6cab42b964f4d11680c4109cf4787f9074ba62a9cbff23f92b301d497f77771c",
                    "trainJsonlSha256":
                        "39879c1199e975096ba962fcad023b3b112c2c8b6444c0a3a9f35971a945d530",
                    "validationJsonlSha256":
                        "9f9514e0feda3e29eb63ee4308e87b94666f05229cfbd26a619a5a35a9708226",
                    "trainTokensSha256":
                        "2aa8cb0d7970ae8ac329f71fd5d2df00df2345181ae9e8e79534f44409b46785",
                    "validationTokensSha256":
                        "8e8307953e2c1c4afcb7dc20c32f5a797611bf2371912a2480312f2094fc004c",
                    "trainIndexSha256":
                        "5d94bf9c3f0a0867cf945abd965f763c800444cba7162d6cbc522d5de049235f",
                    "validationIndexSha256":
                        "2151edd14d340377feb42e2f1baa8fcbefe02aad070429e2dbf9ba519a79f52a",
                    "trainRecords": 72,
                    "validationRecords": 36,
                    "trainTokenCount": 19377,
                    "validationTokenCount": 9763,
                },
                "tokenizer": {
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
            }

            with patch(
                "plex_training.request_grounded_coding_training._verify_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.request_grounded_coding_training._verify_stage",
                return_value=(_FakeModel(), {}),
            ), patch(
                "plex_training.request_grounded_coding_training.PlexTokenizer.load",
                return_value=object(),
            ), patch(
                "plex_training.request_grounded_coding_training.StructuredPlanCompleteRecordCorpus",
                side_effect=_FakeTrainCorpus,
            ), patch(
                "plex_training.request_grounded_coding_training.TokenCorpus",
                return_value=_FakeValidationCorpus(),
            ), patch(
                "plex_training.request_grounded_coding_training._validation_loss",
                return_value=2.5,
            ):
                report = preflight_request_grounded_training(
                    bundle_dir=bundle_root,
                    stage_checkpoint=stage,
                    contract_path=CONTRACT,
                    output_dir=output,
                    artifact_root=root,
                    require_cuda=False,
                )

        self.assertEqual(
            report["status"],
            "training-preflight-passed-awaiting-owner-authorization",
        )
        self.assertFalse(report["authorized"])
        self.assertTrue(report["trainingPreflightAuthorized"])
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertFalse(report["optimizerStepAuthorized"])
        self.assertFalse(report["checkpointWriteAuthorized"])
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])
        self.assertEqual(report["stageCheckpointSha256"], EXPECTED_STAGE_CHECKPOINT_SHA256)
        self.assertEqual(report["expectedExamplesAt100Steps"], EXPECTED_EXAMPLES)
        self.assertEqual(
            report["expectedRealTargetPositionsAt100Steps"],
            EXPECTED_REAL_TARGET_POSITIONS,
        )
        self.assertEqual(report["baselineValidationLoss"], 2.5)
        self.assertEqual(report["baselineValidationBatches"], EXPECTED_VALIDATION_BATCHES)
        self.assertEqual(report["proposedValidationSteps"], [0, 25, 50, 75, 100])
        self.assertEqual(report["proposedCheckpointSteps"], [25, 50, 75, 100])
        self.assertEqual(report["proposedDevice"], "cpu")
        self.assertEqual(report["outputWouldBe"], "request-grounded/p2-48-first-run")
        self.assertFalse(report["automaticContinuation"])
        self.assertFalse(report["resumeAllowed"])


if __name__ == "__main__":
    unittest.main()
