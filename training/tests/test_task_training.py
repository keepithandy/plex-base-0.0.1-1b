import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.checkpoint import save_checkpoint
from plex_training.cli import build_parser
from plex_training.config import ModelConfig
from plex_training.model import PlexLanguageModel
from plex_training.task_training import (
    _preflight,
    _validate_authorization,
    _verify_stage,
    preflight_first_finetune,
)
from plex_training.tokenizer import CODEC, sha256_file


class P230AuthorizedRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = ModelConfig(
            vocab_size=512, context_length=512, width=16, layers=1, heads=2,
            feed_forward_width=32, dropout=0.1,
        )
        patcher = patch("plex_training.task_training.DEFAULT_CONFIG", self.config)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.bundle_root = self.root / "bundle"
        self.bundle_root.mkdir()
        (self.bundle_root / "manifest.json").write_text("{}\n", encoding="utf-8")
        (self.bundle_root / "train.index.json").write_text("[]\n", encoding="utf-8")
        self.tokenizer = {
            "codec": CODEC,
            "actualVocabularySize": 16384,
            "modelVocabularyCapacity": 16384,
            "tokenizerSha256": "tokenizer-sha",
            "bundleManifestSha256": "bundle-sha",
            "modelConfigSha256": "model-config-sha",
        }
        self.dataset = {
            "sourceDatasetManifestSha256": "dataset-manifest-sha",
            "trainJsonlSha256": "train-jsonl-sha",
            "validationJsonlSha256": "validation-jsonl-sha",
            "trainRecords": 156,
            "validationRecords": 78,
            "trainTokenCount": 17883,
            "validationTokenCount": 8661,
            "trainTokensSha256": "train-token-sha",
            "validationTokensSha256": "validation-token-sha",
        }
        self.bundle = {
            "root": self.bundle_root,
            "trainPath": self.bundle_root / "train.tokens.u16le",
            "validationPath": self.bundle_root / "validation.tokens.u16le",
            "tokenizer": self.tokenizer,
            "dataset": self.dataset,
        }
        self.base_web_sha = "3" * 64
        self.stage = self.root / "stage.pt"
        self._write_stage()

        self.authorization = self._authorization()
        self.authorization_path = self.root / "authorization.json"
        self.preparation_path = self.root / "preparation.json"
        self._write_json(self.authorization_path, self.authorization)
        self._write_json(self.preparation_path, {
            "milestone": "P2-30",
            "status": "preparation-gate-passed",
            "firstCurriculum": {},
            "tokenizer": {},
        })

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _stage_transition(self):
        return {
            "schemaVersion": 1,
            "kind": "plex-task-finetune-stage-transition-v1",
            "milestone": "P2-30",
            "baseCheckpointSha256": self.base_web_sha,
            "baseCheckpointStep": 500,
            "baseDatasetRecord": {"sourceDatasetManifestSha256": "web"},
            "baseTokenizerRecord": self.tokenizer,
            "taskDatasetRecord": self.dataset,
            "taskTokenizerRecord": self.tokenizer,
            "modelWeightsLoadedFromBase": True,
            "pretrainingOptimizerStateReused": False,
            "pretrainingSamplerStateReused": False,
            "pretrainingStepReusedAsTaskStep": False,
            "taskStageStep": 0,
            "modelTrainingPerformed": False,
        }

    def _write_stage(self, *, optimizer_has_state=False) -> None:
        self.stage.unlink(missing_ok=True)
        model = PlexLanguageModel(self.config)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=3e-4, betas=(0.9, 0.95), weight_decay=0.1, eps=1e-8
        )
        if optimizer_has_state:
            parameter = next(model.parameters())
            optimizer.state[parameter] = {
                "step": torch.tensor(1.0),
                "exp_avg": torch.zeros_like(parameter),
                "exp_avg_sq": torch.zeros_like(parameter),
            }
        torch.manual_seed(1337)
        save_checkpoint(
            model,
            optimizer,
            step=0,
            seed=1337,
            codec=CODEC,
            sampling_rng=random.Random(1337),
            device=torch.device("cpu"),
            destination=self.stage,
            artifact_root=self.root,
            initialization_record={
                "pretrainedCheckpointLoaded": False,
                "pretrainedModelWeightsLoaded": False,
                "initialModelWeightsSha256": "synthetic",
            },
            stage_transition_record=self._stage_transition(),
            tokenizer_record=self.tokenizer,
            dataset_record=self.dataset,
            training_settings=None,
            schedule_state=None,
            tokens_processed_total=0,
        )

    def _authorization(self):
        return {
            "schemaVersion": 1,
            "milestone": "P2-30",
            "kind": "plex-p2-30-first-task-finetune-contract-v1",
            "status": "owner-approved-first-run",
            "modelTrainingAuthorized": True,
            "approvedBy": "keepithandy",
            "outputDirectory": "task-finetune/p2-30-first-run",
            "executionState": {
                "trainingExecuted": False,
                "researchOptimizerUpdates": 0,
                "finalHoldoutOpened": False,
            },
            "baseStage": {
                "checkpointSha256": sha256_file(self.stage),
                "taskStep": 0,
                "baseWebCheckpointSha256": self.base_web_sha,
                "parameterCount": self.config.parameter_count(),
            },
            "data": {
                "bundleManifestSha256": sha256_file(self.bundle_root / "manifest.json"),
                "tokenizerSha256": self.tokenizer["tokenizerSha256"],
                "vocabularySize": 16384,
                "sourceDatasetManifestSha256": self.dataset["sourceDatasetManifestSha256"],
                "trainJsonlSha256": self.dataset["trainJsonlSha256"],
                "validationJsonlSha256": self.dataset["validationJsonlSha256"],
                "trainRecords": 156,
                "validationRecords": 78,
                "additionalCurricula": [],
            },
            "training": {
                "sampler": {
                    "kind": "complete-record-v1",
                    "selection": "uniform-record-with-replacement",
                    "endPolicy": "stop-at-record-eos-v1",
                    "records": 156,
                    "trainJsonlSha256": self.dataset["trainJsonlSha256"],
                    "indexSha256": sha256_file(self.bundle_root / "train.index.json"),
                    "paddingPolicy": "right-pad-to-batch-longest-zero-target-weight-v1",
                    "tokenAccounting": "nonpadding-next-token-targets-v1",
                    "lossReduction": "mean-real-targets-per-microbatch-then-mean-accumulation-v1",
                },
                "objective": "ordinary-next-token-v1",
                "answerWeight": 1,
                "optimizer": "AdamW",
                "optimizerStatePolicy": "fresh-empty-task-stage-optimizer; never P2-29 moments",
                "learningRate": 0.0003,
                "betas": [0.9, 0.95],
                "epsilon": 1e-8,
                "weightDecay": 0.1,
                "gradientClippingNorm": 1.0,
                "schedule": "constant-v1",
                "microBatch": 1,
                "gradientAccumulation": 16,
                "maximumSteps": 100,
                "maximumWallTimeSeconds": 600,
                "device": "cuda",
                "seed": 1337,
                "contextLength": 512,
                "dropout": 0.1,
                "tokenAccounting": "nonpadding-next-token-targets-v1",
                "expectedSamplesAt100Steps": 1600,
                "expectedRealTargetPositionsAt100Steps": 181849,
                "resumeAllowed": False,
                "automaticContinuation": False,
                "timeLimitPolicy": "Stop before the next optimizer update when the run deadline is reached; save/report completed updates only.",
            },
            "evaluation": {
                "taskValidation": {
                    "method": "sequential-packed-next-token-loss",
                    "maximumBatches": 100,
                    "steps": [0, 25, 50, 75, 100],
                    "baselineLoss": 6.821033537387848,
                    "baselineTokens": 8192,
                    "baselineBatches": 16,
                    "tailTargetPositionsExcluded": 468,
                },
                "checkpointSteps": [25, 50, 75, 100],
                "alwaysSaveFinalCompletedStep": True,
                "checkpointSelection": "Report fixed step-100 endpoint or early-stop endpoint; do not select the lowest-validation checkpoint",
                "development": {
                    "taskSet": "training/phase2/evaluation/p2-01b-dev-v1.json",
                    "taskSetSha256": "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4",
                    "runAt": "final completed step only; existing stage-zero baseline retained",
                    "temperature": 0,
                    "seed": 1337,
                    "maxNewTokens": {"css": 128, "html": 192, "javascript": 192},
                    "baselinePassed": 0,
                    "baselineTasks": 30,
                    "baselineTruncated": 30,
                },
            },
            "protectedEvaluation": {
                "validationExcludedFromGradients": True,
                "p2_01bExcludedFromGradients": True,
                "finalProjectHoldoutMustRemainClosed": True,
                "developmentBaselineMustNotBeUsedForOptimization": True,
            },
        }

    def _rewrite_payload(self, mutate):
        payload = torch.load(self.stage, weights_only=True)
        mutate(payload)
        torch.save(payload, self.stage)
        self.authorization["baseStage"]["checkpointSha256"] = sha256_file(self.stage)

    def test_owner_authorization_is_exact_and_has_no_runtime_overrides(self):
        _validate_authorization(self.authorization)
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "task-finetune-run",
                "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt",
                "--steps", "101",
            ])
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "task-finetune-run",
                "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt",
                "--resume", "anything.pt",
            ])

    def test_unauthorized_or_extended_contract_is_rejected(self):
        for field, value in (
            ("modelTrainingAuthorized", False),
            ("approvedBy", "someone-else"),
        ):
            candidate = copy.deepcopy(self.authorization)
            candidate[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                _validate_authorization(candidate)
        candidate = copy.deepcopy(self.authorization)
        candidate["training"]["maximumSteps"] = 101
        with self.assertRaisesRegex(ValueError, "maximumSteps"):
            _validate_authorization(candidate)
        candidate = copy.deepcopy(self.authorization)
        candidate["training"]["resumeAllowed"] = True
        with self.assertRaisesRegex(ValueError, "resumeAllowed"):
            _validate_authorization(candidate)

    def test_stage_requires_exact_hash_zero_progress_empty_optimizer_and_matching_identity(self):
        model, payload = _verify_stage(
            checkpoint_path=self.stage, bundle=self.bundle, contract=self.authorization
        )
        self.assertEqual(payload["step"], 0)
        self.assertEqual(model.config, self.config)

        bad_hash = copy.deepcopy(self.authorization)
        bad_hash["baseStage"]["checkpointSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact authorized"):
            _verify_stage(checkpoint_path=self.stage, bundle=self.bundle, contract=bad_hash)

        for name, mutate, message in (
            ("step", lambda p: p.__setitem__("step", 1), "task step zero"),
            ("tokens", lambda p: p.__setitem__("tokensProcessedTotal", 1), "task step zero"),
            ("dataset", lambda p: p.__setitem__("datasetRecord", {"wrong": True}), "tokenizer or task dataset"),
            ("tokenizer", lambda p: p.__setitem__("tokenizerRecord", {"wrong": True}), "tokenizer or task dataset"),
            (
                "provenance",
                lambda p: p["stageTransitionRecord"].__setitem__("pretrainingOptimizerStateReused", True),
                "stageTransitionRecord",
            ),
        ):
            self._write_stage()
            self._rewrite_payload(mutate)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, message):
                _verify_stage(
                    checkpoint_path=self.stage, bundle=self.bundle, contract=self.authorization
                )

        self.stage.unlink()
        self._write_stage(optimizer_has_state=True)
        self.authorization["baseStage"]["checkpointSha256"] = sha256_file(self.stage)
        with self.assertRaisesRegex(ValueError, "fresh and empty"):
            _verify_stage(checkpoint_path=self.stage, bundle=self.bundle, contract=self.authorization)

    def test_preflight_rejects_output_reuse_and_data_contract_tampering(self):
        self._write_stage()
        self.authorization = self._authorization()
        self._write_json(self.authorization_path, self.authorization)

        with patch("plex_training.task_training.inspect_task_bundle", return_value=self.bundle), \
             patch("plex_training.task_training._verify_stage",
                   return_value=(PlexLanguageModel(self.config), {"step": 0})):
            checked = _preflight(
                bundle_dir=self.bundle_root,
                stage_checkpoint=self.stage,
                authorization_contract_path=self.authorization_path,
                preparation_contract_path=self.preparation_path,
                output_dir=self.root / "task-finetune/p2-30-first-run",
                artifact_root=self.root,
                require_cuda=False,
            )
            self.assertEqual(checked["bundle"]["dataset"]["trainRecords"], 156)

            tampered = copy.deepcopy(self.authorization)
            tampered["data"]["trainJsonlSha256"] = "changed"
            self._write_json(self.authorization_path, tampered)
            with self.assertRaisesRegex(ValueError, "data.trainJsonlSha256"):
                _preflight(
                    bundle_dir=self.bundle_root,
                    stage_checkpoint=self.stage,
                    authorization_contract_path=self.authorization_path,
                    preparation_contract_path=self.preparation_path,
                    output_dir=self.root / "task-finetune/p2-30-first-run",
                    artifact_root=self.root,
                    require_cuda=False,
                )

            existing = self.root / "task-finetune/p2-30-first-run"
            existing.mkdir()
            with self.assertRaisesRegex(FileExistsError, "resume and overwrite"):
                _preflight(
                    bundle_dir=self.bundle_root,
                    stage_checkpoint=self.stage,
                    authorization_contract_path=self.authorization_path,
                    preparation_contract_path=self.preparation_path,
                    output_dir=existing,
                    artifact_root=self.root,
                    require_cuda=False,
                )

    def test_public_preflight_performs_no_optimizer_update_and_creates_no_output(self):
        self._write_stage()
        self.authorization = self._authorization()
        self._write_json(self.authorization_path, self.authorization)
        output = self.root / "task-finetune/p2-30-first-run"
        with patch("plex_training.task_training.inspect_task_bundle", return_value=self.bundle), \
             patch("plex_training.task_training._verify_stage",
                   return_value=(PlexLanguageModel(self.config), {"step": 0})), \
             patch("plex_training.task_training.select_device", return_value=torch.device("cpu")), \
             patch.object(torch.optim.AdamW, "step",
                          side_effect=AssertionError("preflight must never update weights")):
            result = preflight_first_finetune(
                bundle_dir=self.bundle_root,
                stage_checkpoint=self.stage,
                authorization_contract_path=self.authorization_path,
                preparation_contract_path=self.preparation_path,
                output_dir=output,
                artifact_root=self.root,
            )
        self.assertFalse(result["trainingPerformed"])
        self.assertEqual(result["researchOptimizerUpdates"], 0)
        self.assertFalse(output.exists())


class P230CommittedContractTests(unittest.TestCase):
    def test_committed_owner_contract_matches_the_locked_runner(self):
        path = Path("training/pretraining/p2-30-first-finetune-contract.json")
        contract = json.loads(path.read_text(encoding="utf-8"))
        _validate_authorization(contract)
        self.assertFalse(contract["executionState"]["trainingExecuted"])
        self.assertEqual(contract["executionState"]["researchOptimizerUpdates"], 0)
        self.assertIsInstance(contract["command"], str)
        self.assertIn("task-finetune-run", contract["command"])


if __name__ == "__main__":
    unittest.main()
