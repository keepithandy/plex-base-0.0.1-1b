"""Portable regressions for P2-48 stage-source and zero-stage tooling."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.config import DEFAULT_CONFIG
from plex_training.request_grounded_coding_stage import (
    DEFAULT_SOURCE_CONTRACT,
    DEFAULT_STAGE_CONTRACT,
    EXPECTED_BASE_CHECKPOINT_SHA256,
    EXPECTED_BASE_STAGE_KIND,
    EXPECTED_BASE_TRAINING_KIND,
    EXPECTED_BUNDLE_MANIFEST_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    PROPOSED_STAGE_KIND,
    _source_contract,
    _stage_contract,
    create_request_grounded_stage,
    preflight_request_grounded_stage_source,
)
from plex_training.tokenizer import CODEC


class _FakeModel(torch.nn.Module):
    config = DEFAULT_CONFIG

    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([1.5, -0.25]))


class RequestGroundedStageTests(unittest.TestCase):
    def test_source_contract_is_read_only_and_pins_p244_endpoint(self) -> None:
        value = _source_contract(DEFAULT_SOURCE_CONTRACT)
        self.assertEqual(value["milestone"], "P2-48")
        self.assertTrue(value["stageSourcePreflightAuthorized"])
        self.assertFalse(value["checkpointStagingAuthorized"])
        self.assertFalse(value["optimizerCreationAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["baseCheckpoint"]["sha256"],
            EXPECTED_BASE_CHECKPOINT_SHA256,
        )
        self.assertEqual(value["baseCheckpoint"]["tokensProcessedTotal"], 565641)
        self.assertEqual(
            value["baseCheckpoint"]["requiredProvenance"]["stageKind"],
            EXPECTED_BASE_STAGE_KIND,
        )
        self.assertEqual(
            value["baseCheckpoint"]["requiredProvenance"]["trainingSettingsKind"],
            EXPECTED_BASE_TRAINING_KIND,
        )
        self.assertEqual(
            value["p248Bundle"]["bundleManifestSha256"],
            EXPECTED_BUNDLE_MANIFEST_SHA256,
        )
        self.assertEqual(
            value["samplerPreflight"]["expectedRealTargetPositions"],
            429375,
        )

    def test_stage_contract_allows_serialization_only(self) -> None:
        value = _stage_contract(DEFAULT_STAGE_CONTRACT)
        self.assertTrue(value["checkpointStagingAuthorized"])
        self.assertTrue(value["optimizerCreationAuthorized"])
        self.assertTrue(value["optimizerUseAuthorizedForSerializationOnly"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["optimizerSerialization"]["gradientUpdatesAuthorized"],
            0,
        )
        self.assertEqual(value["stage"]["p248StageStep"], 0)
        self.assertEqual(value["stage"]["p248TokensProcessed"], 0)
        self.assertTrue(value["stage"]["modelWeightsMustMatchBaseExactly"])

    def test_stage_source_preflight_verifies_without_state_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "step-0100.pt"
            base.write_bytes(b"base")
            bundle_root = root / "bundle"
            bundle_root.mkdir()

            bundle = {
                "root": bundle_root,
                "tokenizer": {
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
                "dataset": {},
            }
            payload = {
                "step": 100,
                "tokensProcessedTotal": 565641,
                "seed": 1337,
                "codec": CODEC,
                "initializationRecord": {
                    "pretrainedCheckpointLoaded": False,
                    "pretrainedModelWeightsLoaded": False,
                },
                "stageTransitionRecord": {
                    "kind": EXPECTED_BASE_STAGE_KIND,
                    "milestone": "P2-44",
                },
                "trainingSettings": {
                    "kind": EXPECTED_BASE_TRAINING_KIND,
                },
                "tokenizerRecord": {
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
            }

            def fake_sha(path: Path) -> str:
                if Path(path) == base:
                    return EXPECTED_BASE_CHECKPOINT_SHA256
                raise AssertionError(f"unexpected hash path: {path}")

            with patch(
                "plex_training.request_grounded_coding_stage._verify_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.request_grounded_coding_stage.read_checkpoint",
                return_value=(_FakeModel(), payload),
            ), patch(
                "plex_training.request_grounded_coding_stage.sha256_file",
                side_effect=fake_sha,
            ), patch(
                "plex_training.request_grounded_coding_stage.parameter_count",
                return_value=DEFAULT_CONFIG.parameter_count(),
            ):
                report = preflight_request_grounded_stage_source(
                    base_checkpoint=base,
                    bundle_dir=bundle_root,
                    contract_path=DEFAULT_SOURCE_CONTRACT,
                )

        self.assertEqual(
            report["status"],
            "stage-source-preflight-passed-awaiting-stage-authorization",
        )
        self.assertTrue(report["weightsSourceVerified"])
        self.assertTrue(report["bundleCompatibilityVerified"])
        self.assertFalse(report["stageCheckpointCreated"])
        self.assertFalse(report["optimizerCreated"])
        self.assertFalse(report["checkpointStagingAuthorized"])
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])
        self.assertEqual(
            report["proposedStageTransition"]["kind"],
            PROPOSED_STAGE_KIND,
        )
        self.assertEqual(report["proposedStageTransition"]["p248StageStep"], 0)
        self.assertEqual(report["proposedStageTransition"]["p248TokensProcessed"], 0)

    def test_step_zero_stage_preserves_weights_and_empty_optimizer_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "artifacts"
            base = (
                root / "structured-plan" / "p2-44-first-run"
                / "checkpoints" / "step-0100.pt"
            )
            bundle_root = root / "request-grounded" / "p2-48-training-bundle"
            output = root / "request-grounded" / "p2-48-stage0"
            base.parent.mkdir(parents=True)
            bundle_root.mkdir(parents=True)
            base.write_bytes(b"base")

            base_model = _FakeModel()
            saved_model = _FakeModel()
            saved_model.load_state_dict(base_model.state_dict())

            initialization = {
                "pretrainedCheckpointLoaded": False,
                "pretrainedModelWeightsLoaded": False,
            }
            base_payload = {"initializationRecord": initialization}
            dataset = {
                "sourceDatasetManifestSha256":
                    "6cab42b964f4d11680c4109cf4787f9074ba62a9cbff23f92b301d497f77771c",
                "candidateSha256": EXPECTED_CANDIDATE_SHA256,
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
            }
            tokenizer = {
                "tokenizerSha256":
                    "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                "actualVocabularySize": 16384,
            }
            bundle = {
                "root": bundle_root,
                "dataset": dataset,
                "tokenizer": tokenizer,
            }
            transition = {
                "schemaVersion": 1,
                "kind": PROPOSED_STAGE_KIND,
                "milestone": "P2-48",
                "baseCheckpointSha256": EXPECTED_BASE_CHECKPOINT_SHA256,
                "baseCheckpointStep": 100,
                "baseMilestone": "P2-44",
                "candidateSha256": EXPECTED_CANDIDATE_SHA256,
                "bundleManifestSha256": EXPECTED_BUNDLE_MANIFEST_SHA256,
                "modelWeightsLoadedFromBase": True,
                "baseOptimizerStateReused": False,
                "baseSamplerStateReused": False,
                "baseTrainingStepReusedAsP248Step": False,
                "p248StageStep": 0,
                "p248TokensProcessed": 0,
                "modelTrainingPerformed": False,
            }
            saved_payload = {
                "optimizerStateDict": {"state": {}},
                "step": 0,
                "tokensProcessedTotal": 0,
                "samplingRngState": random.Random(1337).getstate(),
                "stageTransitionRecord": transition,
                "tokenizerRecord": tokenizer,
                "datasetRecord": dataset,
                "trainingSettings": None,
                "scheduleState": None,
            }

            def fake_save(*args, **kwargs):
                self.assertEqual(kwargs["step"], 0)
                self.assertEqual(kwargs["tokens_processed_total"], 0)
                self.assertEqual(kwargs["stage_transition_record"], transition)
                self.assertIsNone(kwargs["training_settings"])
                self.assertIsNone(kwargs["schedule_state"])
                self.assertEqual(args[1].state, {})
                kwargs["destination"].write_bytes(b"stage")
                return {"path": "stage-checkpoint.pt", "bytes": 5}

            def fake_sha(path: Path) -> str:
                if Path(path) == output / "stage-checkpoint.pt":
                    return "p248-stage-sha"
                raise AssertionError(f"unexpected hash path: {path}")

            with patch(
                "plex_training.request_grounded_coding_stage.preflight_request_grounded_stage_source",
                return_value={
                    "status":
                        "stage-source-preflight-passed-awaiting-stage-authorization",
                    "weightsSourceVerified": True,
                    "bundleCompatibilityVerified": True,
                    "stageCheckpointCreated": False,
                    "optimizerCreated": False,
                    "proposedStageTransition": transition,
                },
            ), patch(
                "plex_training.request_grounded_coding_stage._verify_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.request_grounded_coding_stage.read_checkpoint",
                side_effect=[(base_model, base_payload), (saved_model, saved_payload)],
            ), patch(
                "plex_training.request_grounded_coding_stage.save_checkpoint",
                side_effect=fake_save,
            ), patch(
                "plex_training.request_grounded_coding_stage.sha256_file",
                side_effect=fake_sha,
            ), patch(
                "plex_training.request_grounded_coding_stage.parameter_count",
                return_value=DEFAULT_CONFIG.parameter_count(),
            ):
                report = create_request_grounded_stage(
                    base_checkpoint=base,
                    bundle_dir=bundle_root,
                    output_dir=output,
                    artifact_root=root,
                    source_contract_path=DEFAULT_SOURCE_CONTRACT,
                    stage_contract_path=DEFAULT_STAGE_CONTRACT,
                )

        self.assertEqual(report["status"], "stage-created-training-not-authorized")
        self.assertEqual(report["stageCheckpointSha256"], "p248-stage-sha")
        self.assertTrue(report["modelWeightsPreserved"])
        self.assertTrue(report["optimizerStateEmpty"])
        self.assertTrue(report["samplerStateReset"])
        self.assertEqual(report["p248StageStep"], 0)
        self.assertEqual(report["p248TokensProcessed"], 0)
        self.assertIsNone(report["trainingSettings"])
        self.assertIsNone(report["scheduleState"])
        self.assertTrue(report["checkpointStagingAuthorized"])
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)


if __name__ == "__main__":
    unittest.main()
