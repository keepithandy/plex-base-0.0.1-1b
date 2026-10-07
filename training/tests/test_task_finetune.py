import random
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.checkpoint import read_checkpoint, save_checkpoint
from plex_training.completion import _completion_tokenizer
from plex_training.config import DEFAULT_CONFIG, ModelConfig
from plex_training.model import PlexLanguageModel
from plex_training.pilot import _initialization_seed, evaluate_pilot, resume_pilot
from plex_training.runner import SyntheticTokenSource, run_training
from plex_training.task_finetune import create_task_stage, inspect_task_bundle, prepare_task_bundle
from plex_training.tokenizer import CODEC, sha256_file, train_tokenizer


class TaskPreparationTests(unittest.TestCase):
    """Small synthetic artifacts exercise gates without using research weights."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = ModelConfig(vocab_size=512, width=16, layers=1, heads=2,
                                  feed_forward_width=32, dropout=0.0)
        for module in ("task_finetune", "pilot", "tokenizer"):
            patcher = patch(f"plex_training.{module}.DEFAULT_CONFIG", self.config)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.dataset = self.root / "dataset"
        (self.dataset / "licenses").mkdir(parents=True)
        notice = b"Synthetic test fixture permission.\n"
        (self.dataset / "licenses/fixture.txt").write_bytes(notice)
        sources, summary = [], {"records": 40}
        for split in ("train", "validation"):
            rows = []
            for i in range(20):
                text = f"Write a small JavaScript answer.\nRequest: {split} example {i}.\nOutput contract: code only.\nAnswer:\nconst value{i} = {i};\n"
                rows.append({"recordId": f"{split}-{i}", "sourceId": split,
                             "groupId": split, "path": f"{i}.js", "text": text,
                             "contentSha256": hashlib.sha256(text.encode()).hexdigest()})
            raw = "".join(json.dumps(row) + "\n" for row in rows).encode()
            (self.dataset / f"{split}.jsonl").write_bytes(raw)
            summary[f"{split}Records"] = 20
            summary[f"{split}JsonlSha256"] = hashlib.sha256(raw).hexdigest()
            sources.append({"id": split, "groupId": split, "rightsReviewStatus": "approved",
                            "licenseNoticeFile": "licenses/fixture.txt",
                            "licenseNoticeSha256": hashlib.sha256(notice).hexdigest()})
        manifest = {"schemaVersion": 1, "pipelineVersion": "p1-14.2",
                    "sources": sources, "summary": summary}
        self.write_json(self.dataset / "manifest.json", manifest)
        self.frozen = self.root / "frozen"
        frozen_report = train_tokenizer(self.dataset, self.frozen, vocab_size=300)
        manifest["pipelineVersion"] = "p2-02.0"
        self.write_json(self.dataset / "manifest.json", manifest)
        self.contract = {
            "milestone": "P2-30", "status": "active-preparation-gate",
            "authorization": {"modelTrainingAuthorized": False},
            "firstCurriculum": {
                "existingSourceDatasetManifestSha256": sha256_file(self.dataset / "manifest.json"),
                "existingTrainJsonlSha256": summary["trainJsonlSha256"],
                "existingValidationJsonlSha256": summary["validationJsonlSha256"],
                "trainRecords": 20, "validationRecords": 20,
            },
            "tokenizer": {"actualVocabularySize": frozen_report["actualVocabularySize"],
                          "tokenizerSha256": frozen_report["tokenizerSha256"],
                          "bundleManifestSha256": sha256_file(self.frozen / "manifest.json")},
        }
        self.contract_path = self.root / "contract.json"
        self.write_json(self.contract_path, self.contract)
        self.bundle = self.root / "task"

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def repack(self, **overrides):
        arguments = dict(dataset_dir=self.dataset, tokenizer_dir=self.frozen,
                         output_dir=self.bundle, contract_path=self.contract_path,
                         storage_limit_bytes=16 * 1024**2)
        return prepare_task_bundle(**(arguments | overrides))

    def base(self):
        model = PlexLanguageModel(self.config)
        optimizer = torch.optim.AdamW(model.parameters())
        parameter = next(model.parameters())
        optimizer.state[parameter] = {"step": torch.tensor(500.),
                                      "exp_avg": torch.ones_like(parameter),
                                      "exp_avg_sq": torch.ones_like(parameter)}
        rng = random.Random(1337)
        rng.random()
        path = self.root / "base.pt"
        save_checkpoint(model, optimizer, step=500, seed=1337, codec=CODEC,
                        sampling_rng=rng, device=torch.device("cpu"), destination=path,
                        artifact_root=self.root,
                        initialization_record={"pretrainedCheckpointLoaded": False,
                                               "pretrainedModelWeightsLoaded": False,
                                               "initialModelWeightsSha256": "synthetic-scratch"},
                        tokenizer_record={"tokenizerSha256": self.contract["tokenizer"]["tokenizerSha256"]},
                        dataset_record={"sourceDatasetManifestSha256": "synthetic-web"},
                        tokens_processed_total=4096000)
        self.contract["baseModel"] = {"checkpointSha256": sha256_file(path),
                                      "checkpointStep": 500,
                                      "parameterCount": self.config.parameter_count()}
        self.write_json(self.contract_path, self.contract)
        return path

    def stage(self, base):
        return create_task_stage(base, self.bundle, self.root / "stage",
                                 contract_path=self.contract_path, artifact_root=self.root,
                                 storage_limit_bytes=16 * 1024**2)

    def test_repack_preserves_text_and_frozen_tokenizer_without_fitting(self):
        with patch("plex_training.tokenizer.train_tokenizer", side_effect=AssertionError("must not fit")):
            report = self.repack()
        self.assertFalse(report["trainingPerformed"])
        for split in ("train", "validation"):
            self.assertEqual((self.bundle / f"{split}.jsonl").read_bytes(),
                             (self.dataset / f"{split}.jsonl").read_bytes())
            self.assertEqual(report[split]["roundtripRecords"], 20)
            self.assertTrue(report[split]["contextLimitPassed"])
        self.assertEqual(sha256_file(self.bundle / "tokenizer.json"),
                         self.contract["tokenizer"]["tokenizerSha256"])
        inspect_task_bundle(self.bundle, self.contract)

    def test_rejects_changed_dataset_or_tokenizer_identity(self):
        for key, field in (("firstCurriculum", "existingTrainJsonlSha256"),
                           ("tokenizer", "tokenizerSha256")):
            with self.subTest(field=field):
                original = self.contract[key][field]
                self.contract[key][field] = "0" * 64
                self.write_json(self.contract_path, self.contract)
                with self.assertRaises(ValueError):
                    self.repack()
                self.contract[key][field] = original
                self.assertFalse(self.bundle.exists())

    def test_rejects_context_overflow_and_cleans_staging(self):
        with patch("plex_training.task_finetune.DEFAULT_CONFIG",
                   ModelConfig(vocab_size=512, context_length=2)):
            with self.assertRaisesRegex(ValueError, "context limit"):
                self.repack()
        self.assertFalse(self.bundle.exists())
        self.assertEqual(list(self.root.glob(".plex-p2-30-bundle-*")), [])

    def test_storage_failure_cleans_staging_and_existing_output_is_preserved(self):
        with self.assertRaisesRegex(ValueError, "storage allocation"):
            self.repack(storage_limit_bytes=100)
        self.assertEqual(list(self.root.glob(".plex-p2-30-bundle-*")), [])
        self.repack()
        original = sha256_file(self.bundle / "manifest.json")
        with self.assertRaises(FileExistsError):
            self.repack()
        self.assertEqual(sha256_file(self.bundle / "manifest.json"), original)

    def test_output_inside_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "separate"):
            self.repack(output_dir=self.dataset / "nested")
        self.assertFalse((self.dataset / "nested").exists())

    def test_missing_or_changed_license_is_rejected(self):
        (self.dataset / "licenses/fixture.txt").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "license notice"):
            self.repack()

    def test_rehashed_token_tampering_is_rejected_before_stage_creation(self):
        self.repack()
        base = self.base()
        path = self.bundle / "train.tokens.u16le"
        raw = bytearray(path.read_bytes())
        raw[0:2] = (4).to_bytes(2, "little")
        path.write_bytes(raw)
        manifest = json.loads((self.bundle / "manifest.json").read_text())
        manifest["train"]["sha256"] = sha256_file(path)
        self.write_json(self.bundle / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "tokens/EOS"):
            self.stage(base)
        self.assertFalse((self.root / "stage").exists())

    def test_index_tampering_is_rejected(self):
        self.repack()
        path = self.bundle / "train.index.json"
        index = json.loads(path.read_text())
        index[0]["startToken"] = 1
        self.write_json(path, index)
        with self.assertRaisesRegex(ValueError, "index/context"):
            inspect_task_bundle(self.bundle, self.contract)

    def test_completion_accepts_large_verified_tokenizer_but_keeps_hash_and_size_limits(self):
        path = self.frozen / "tokenizer.json"
        with path.open("ab") as stream:
            stream.write(b" " * (1024 * 1024))
        digest = sha256_file(path)
        for name in ("tokenizer-config.json", "manifest.json"):
            data = json.loads((self.frozen / name).read_text())
            data["tokenizerSha256"] = digest
            self.write_json(self.frozen / name, data)
        with patch("plex_training.initialization.DEFAULT_CONFIG", self.config):
            _, record = _completion_tokenizer(self.frozen)
            self.assertEqual(record["tokenizerSha256"], digest)
            with path.open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(ValueError, "hash"):
                _completion_tokenizer(self.frozen)
            with path.open("ab") as stream:
                stream.truncate(16 * 1024**2 + 1)
            with self.assertRaisesRegex(ValueError, "too large"):
                _completion_tokenizer(self.frozen)

    def test_stage_preserves_weights_and_resets_state_and_evaluates_read_only(self):
        self.repack()
        base = self.base()
        with patch.object(torch.optim.AdamW, "step", side_effect=AssertionError("must not train")):
            report = self.stage(base)
            result = evaluate_pilot(bundle_dir=self.bundle,
                                    checkpoint_path=self.root / "stage/stage-checkpoint.pt",
                                    device_name="cpu", maximum_batches=1)
        original_model, original = read_checkpoint(base, torch.device("cpu"))
        model, staged = read_checkpoint(self.root / "stage/stage-checkpoint.pt", torch.device("cpu"))
        for name, value in original_model.state_dict().items():
            self.assertTrue(torch.equal(value, model.state_dict()[name]))
        self.assertEqual(staged["optimizerStateDict"]["state"], {})
        self.assertNotEqual(original["samplingRngState"], staged["samplingRngState"])
        self.assertEqual(staged["samplingRngState"], random.Random(1337).getstate())
        self.assertEqual(staged["tokensProcessedTotal"], 0)
        self.assertEqual(staged["initializationRecord"], original["initializationRecord"])
        self.assertTrue(report["modelWeightsPreserved"])
        self.assertEqual(result["checkpointStep"], 0)

    def test_wrong_base_hash_is_rejected_without_output(self):
        self.repack()
        base = self.base()
        with base.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ValueError, "verified P2-29"):
            self.stage(base)
        self.assertFalse((self.root / "stage").exists())

    def test_stage_save_failure_cleans_output(self):
        self.repack()
        base = self.base()
        with patch("plex_training.task_finetune.save_checkpoint", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.stage(base)
        self.assertFalse((self.root / "stage").exists())

    def test_generic_runner_and_resume_reject_task_stage(self):
        self.repack()
        base = self.base()
        self.stage(base)
        path = self.root / "stage/stage-checkpoint.pt"
        with patch.object(torch.optim.AdamW, "step", side_effect=AssertionError("must not train")):
            with self.assertRaisesRegex(ValueError, "separately authorized"):
                run_training(train_source=SyntheticTokenSource(token_count=1024), validation=None,
                             device_name="cpu", minutes=0.1, step_limit=1,
                             output_checkpoint=self.root / "blocked.pt", metrics_path=self.root / "metrics.jsonl",
                             artifact_root=self.root, resume_from=path, config=self.config,
                             allow_tiny_config=True)
            # A positive task step must not make generic resume legal either.
            payload = torch.load(path, weights_only=True)
            payload["step"] = 1
            torch.save(payload, path)
            with self.assertRaisesRegex(ValueError, "matching scratch-trained"):
                resume_pilot(bundle_dir=self.bundle, checkpoint_path=path,
                             output_dir=self.root / "blocked-resume", artifact_root=self.root)
        self.assertFalse((self.root / "blocked.pt").exists())
        self.assertFalse((self.root / "blocked-resume").exists())


class TaskFineTuneSafetyTests(unittest.TestCase):
    def test_generic_pilot_rejects_task_stage_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "stage.pt"
            tokenizer_record = {
                "codec": CODEC,
                "actualVocabularySize": 16384,
                "modelVocabularyCapacity": 16384,
                "tokenizerSha256": "fixture",
                "bundleManifestSha256": "fixture-bundle",
                "modelConfigSha256": "fixture-config",
            }
            torch.save({
                "formatVersion": 1,
                "modelFamily": "plex-from-scratch",
                "modelConfig": DEFAULT_CONFIG.to_dict(),
                "step": 0,
                "seed": 1337,
                "codec": CODEC,
                "tokenizerRecord": tokenizer_record,
                "optimizerStateDict": {},
                "initializationRecord": {
                    "pretrainedCheckpointLoaded": False,
                    "pretrainedModelWeightsLoaded": False,
                },
                "stageTransitionRecord": {
                    "kind": "plex-task-finetune-stage-transition-v1",
                    "modelTrainingPerformed": False,
                },
                "samplingRngState": random.Random(1337).getstate(),
                "torchCpuRngState": torch.get_rng_state(),
                "torchCudaRngStates": [],
            }, checkpoint)
            with self.assertRaisesRegex(ValueError, "random initialization"):
                _initialization_seed(checkpoint, tokenizer_record)


if __name__ == "__main__":
    unittest.main()
