"""Portable regressions for P2-44 training preflight."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.config import DEFAULT_CONFIG
from plex_training.structured_plan_evidence_composition_training import (
    EXPECTED_EXAMPLES,
    EXPECTED_REAL_TARGET_POSITIONS,
    EXPECTED_STAGE_CHECKPOINT_SHA256,
    _contract,
    preflight_evidence_composition_training,
)

CONTRACT = Path("training/pretraining/p2-44-training-preflight-contract.json")


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
        "records": 108,
    }

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


class EvidenceCompositionTrainingPreflightTests(unittest.TestCase):
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
            bundle_root = root / "structured-plan" / "p2-44-training-bundle"
            bundle_root.mkdir(parents=True)
            (bundle_root / "manifest.json").write_text("{}\n", encoding="utf-8")
            stage = root / "structured-plan" / "p2-44-stage0" / "stage-checkpoint.pt"
            stage.parent.mkdir(parents=True)
            stage.write_bytes(b"stage")
            output = root / "structured-plan" / "p2-44-first-run"

            dataset = {
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
                "trainRecords": 108,
                "validationRecords": 54,
                "trainTokenCount": 38280,
                "validationTokenCount": 19186,
            }
            bundle = {
                "root": bundle_root,
                "trainPath": bundle_root / "train.tokens.u16le",
                "validationPath": bundle_root / "validation.tokens.u16le",
                "dataset": dataset,
                "tokenizer": {
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
            }

            def fake_sha(path: Path) -> str:
                if Path(path) == bundle_root / "manifest.json":
                    return "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6"
                raise AssertionError(f"unexpected hash path: {path}")

            with patch(
                "plex_training.structured_plan_evidence_composition_training.inspect_evidence_composition_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.structured_plan_evidence_composition_training._verify_stage",
                return_value=(_FakeModel(), {}),
            ), patch(
                "plex_training.structured_plan_evidence_composition_training.sha256_file",
                side_effect=fake_sha,
            ), patch(
                "plex_training.structured_plan_evidence_composition_training.PlexTokenizer.load",
                return_value=object(),
            ), patch(
                "plex_training.structured_plan_evidence_composition_training.StructuredPlanCompleteRecordCorpus",
                return_value=_FakeTrainCorpus(),
            ), patch(
                "plex_training.structured_plan_evidence_composition_training.TokenCorpus",
                return_value=_FakeValidationCorpus(),
            ), patch(
                "plex_training.structured_plan_evidence_composition_training._validation_loss",
                return_value=2.75,
            ):
                report = preflight_evidence_composition_training(
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
        self.assertEqual(report["baselineValidationLoss"], 2.75)
        self.assertEqual(report["baselineValidationBatches"], 37)
        self.assertEqual(report["proposedValidationSteps"], [0, 25, 50, 75, 100])
        self.assertEqual(report["proposedCheckpointSteps"], [25, 50, 75, 100])
        self.assertEqual(report["proposedDevice"], "cpu")
        self.assertEqual(report["outputWouldBe"], "structured-plan/p2-44-first-run")
        self.assertFalse(report["automaticContinuation"])
        self.assertFalse(report["resumeAllowed"])


if __name__ == "__main__":
    unittest.main()
