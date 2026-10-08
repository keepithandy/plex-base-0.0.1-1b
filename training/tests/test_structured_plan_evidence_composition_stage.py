"""Portable P2-44 stage-source preflight regressions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.config import DEFAULT_CONFIG
from plex_training.structured_plan_evidence_composition_stage import (
    EXPECTED_BASE_CHECKPOINT_SHA256,
    EXPECTED_BASE_STAGE_KIND,
    EXPECTED_BASE_TRAINING_KIND,
    _contract,
    preflight_evidence_composition_stage_source,
)

CONTRACT = Path("training/pretraining/p2-44-stage-source-preparation-contract.json")


class _FakeModel:
    config = DEFAULT_CONFIG


class EvidenceCompositionStageSourceTests(unittest.TestCase):
    def test_contract_is_read_only_and_pins_p241_endpoint(self) -> None:
        value = _contract(CONTRACT)
        self.assertEqual(value["milestone"], "P2-44")
        self.assertTrue(value["stageSourcePreflightAuthorized"])
        self.assertFalse(value["checkpointStagingAuthorized"])
        self.assertFalse(value["optimizerCreationAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["baseCheckpoint"]["sha256"],
            EXPECTED_BASE_CHECKPOINT_SHA256,
        )
        self.assertEqual(value["baseCheckpoint"]["step"], 100)
        self.assertEqual(value["baseCheckpoint"]["tokensProcessedTotal"], 567311)
        self.assertEqual(
            value["baseCheckpoint"]["requiredProvenance"]["stageKind"],
            EXPECTED_BASE_STAGE_KIND,
        )
        self.assertEqual(
            value["baseCheckpoint"]["requiredProvenance"]["trainingSettingsKind"],
            EXPECTED_BASE_TRAINING_KIND,
        )

    def test_stage_source_preflight_verifies_without_staging_or_optimizer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary) / "step-0100.pt"
            base.write_bytes(b"fake checkpoint bytes")
            bundle_root = Path(temporary) / "p2-44-training-bundle"
            bundle_root.mkdir()
            manifest = bundle_root / "manifest.json"
            manifest.write_text("{}\n", encoding="utf-8")

            bundle = {
                "root": bundle_root,
                "dataset": {
                    "sourceDatasetManifestSha256":
                        "18d827d2e6bef3aaee41afacee163f16367dc6fc5198334f321c88f7623515b8",
                    "trainJsonlSha256":
                        "0141dbd0209d10e2138a0a90ff688e97b4b1de39f91c28ca367ed7267b309789",
                    "validationJsonlSha256":
                        "8b690e91335aab703a331de41ea0d6d801d68058f0dc1a3eada716d952fede2c",
                    "trainIndexSha256":
                        "5364aef18ff9ce5c702989953bf19268c7f4a8af079e84fc2f90672e8a63fc09",
                    "validationIndexSha256":
                        "5c409f624474173648d5068fd1961ea3659ceb304dc65fe66382343cff29ea59",
                },
                "tokenizer": {
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                },
            }
            payload = {
                "step": 100,
                "tokensProcessedTotal": 567311,
                "seed": 1337,
                "codec": "plex-bpe-v1",
                "initializationRecord": {
                    "pretrainedCheckpointLoaded": False,
                    "pretrainedModelWeightsLoaded": False,
                },
                "stageTransitionRecord": {
                    "kind": "plex-request-conditioned-plan-binding-stage-transition-v1",
                    "milestone": "P2-41",
                },
                "trainingSettings": {
                    "kind": "p2-41-authorized-request-binding-training-v1",
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
                if Path(path) == manifest:
                    return "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6"
                raise AssertionError(f"unexpected hash path: {path}")

            with patch(
                "plex_training.structured_plan_evidence_composition_stage.inspect_evidence_composition_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.structured_plan_evidence_composition_stage.read_checkpoint",
                return_value=(_FakeModel(), payload),
            ), patch(
                "plex_training.structured_plan_evidence_composition_stage.sha256_file",
                side_effect=fake_sha,
            ), patch(
                "plex_training.structured_plan_evidence_composition_stage.parameter_count",
                return_value=DEFAULT_CONFIG.parameter_count(),
            ):
                report = preflight_evidence_composition_stage_source(
                    base_checkpoint=base,
                    bundle_dir=bundle_root,
                    contract_path=CONTRACT,
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
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])
        self.assertEqual(report["proposedStageTransition"]["p244StageStep"], 0)
        self.assertEqual(report["proposedStageTransition"]["p244TokensProcessed"], 0)


if __name__ == "__main__":
    unittest.main()
