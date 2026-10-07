"""Safety tests for the P2-32 locked training path."""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from array import array
from pathlib import Path
from unittest.mock import patch

import torch

from plex_training.checkpoint import save_checkpoint
from plex_training.cli import build_parser
from plex_training.config import ModelConfig
from plex_training.model import PlexLanguageModel
from plex_training.structured_plan_training import (
    BASE_CHECKPOINT_SHA256,
    StructuredPlanCompleteRecordCorpus,
    _draft_authorization,
    _validate_authorization,
    create_structured_plan_stage,
    run_structured_plan_training,
)
from plex_training.tokenizer import CODEC, sha256_file


class FakeTokenizer:
    def encode(self, text: str) -> list[int]:
        return [4 + (byte % 20) for byte in text.encode("utf-8")]

    def decode(self, ids: list[int]) -> str:
        raise NotImplementedError


class P232LockedTrainingTests(unittest.TestCase):
    def test_committed_contract_is_draft_and_training_false(self) -> None:
        path = Path("training/pretraining/p2-32-first-run-contract.draft.json")
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(_draft_authorization(contract))
        self.assertFalse(contract["modelTrainingAuthorized"])
        self.assertIsNone(contract["approvedBy"])
        self.assertIsNone(contract["command"])
        with self.assertRaises(ValueError):
            _validate_authorization(contract)

    def test_cli_has_no_runtime_step_or_resume_override(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "plan-train-run", "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt", "--steps", "101",
            ])
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "plan-train-run", "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt", "--resume", "checkpoint.pt",
            ])

    def test_complete_record_sampler_accepts_p232_shape_and_masks_padding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tokenizer = FakeTokenizer()
            texts = [
                "Convert the repository-style request into one semantic edit plan.\nJSON:{\"a\":1}",
                "Convert the repository-style request into one semantic edit plan.\nJSON:{\"longer\":2}",
            ]
            jsonl = root / "train.jsonl"
            token_path = root / "train.tokens.u16le"
            index_path = root / "train.index.json"
            index, offset = [], 0
            tokens = array("H")
            with jsonl.open("w", encoding="utf-8", newline="\n") as stream:
                for number, text in enumerate(texts):
                    record_id = f"r{number}"
                    stream.write(json.dumps({"recordId": record_id, "text": text}) + "\n")
                    encoded = tokenizer.encode(text) + [3]
                    tokens.extend(encoded)
                    index.append({"recordId": record_id, "startToken": offset,
                                  "tokenCount": len(encoded)})
                    offset += len(encoded)
            with token_path.open("wb") as stream:
                stream.write(tokens.tobytes())
            index_path.write_text(json.dumps(index), encoding="utf-8")

            with StructuredPlanCompleteRecordCorpus(
                token_path,
                dataset_jsonl=jsonl,
                index_path=index_path,
                tokenizer=tokenizer,
                expected_jsonl_sha256=sha256_file(jsonl),
            ) as corpus:
                inputs, targets, weights = corpus.sample_masked_batch(
                    random.Random(1337), batch_size=2, sequence_length=512
                )
                self.assertEqual(inputs.shape, targets.shape)
                self.assertEqual(targets.shape, weights.shape)
                self.assertGreater(int(weights.sum().item()), 0)
                self.assertEqual(corpus.sampler_record["kind"], "complete-record-v1")
                positions, _ = corpus.replay_progress(1337, 16)
                self.assertGreater(positions, 0)

    def test_weights_only_stage_resets_optimizer_step_and_sampler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = ModelConfig(vocab_size=64, width=16, layers=1, heads=2,
                                 feed_forward_width=32, dropout=0.0)
            model = PlexLanguageModel(config)
            optimizer = torch.optim.AdamW(model.parameters())
            base = root / "base.pt"
            save_checkpoint(
                model, optimizer, step=100, seed=1337, codec=CODEC,
                sampling_rng=random.Random(9), device=torch.device("cpu"),
                destination=base, artifact_root=root,
                initialization_record={
                    "pretrainedCheckpointLoaded": False,
                    "pretrainedModelWeightsLoaded": False,
                    "initialModelWeightsSha256": "synthetic",
                },
                stage_transition_record={"milestone": "P2-30"},
                tokenizer_record={
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
                dataset_record={"synthetic": True},
                training_settings={"kind": "p2-30-authorized-task-finetune-v1"},
                schedule_state={"kind": "constant-v1", "step": 100},
                tokens_processed_total=1,
            )
            bundle = {
                "root": root,
                "tokenizer": {"tokenizerSha256": "fixture"},
                "dataset": {"candidateSha256": "fixture"},
            }
            (root / "manifest.json").write_text("{}", encoding="utf-8")
            preparation = root / "prep.json"
            preparation.write_text(json.dumps({
                "schemaVersion": 1, "milestone": "P2-32",
                "kind": "plex-p2-32-structured-plan-preparation-contract-v1",
                "status": "preparation-only-awaiting-owner-review",
                "dataPreparationAuthorized": True,
                "modelTrainingAuthorized": False,
                "automaticTrainingExtension": False,
                "baseCheckpoint": {"sha256": sha256_file(base)},
            }), encoding="utf-8")
            output = root / "stage"
            with patch(
                "plex_training.structured_plan_training.BASE_CHECKPOINT_SHA256",
                sha256_file(base),
            ), patch(
                "plex_training.structured_plan_training.DEFAULT_CONFIG", config
            ), patch(
                "plex_training.structured_plan_training.inspect_structured_plan_bundle",
                return_value=bundle,
            ):
                report = create_structured_plan_stage(
                    base_checkpoint=base,
                    bundle_dir=root,
                    output_dir=output,
                    artifact_root=root,
                    preparation_contract_path=preparation,
                    storage_limit_bytes=16 * 1024**2,
                )
            self.assertFalse(report["trainingPerformed"])
            self.assertEqual(report["researchOptimizerUpdates"], 0)
            self.assertEqual(report["p232StageStep"], 0)
            self.assertEqual(report["p232TokensProcessed"], 0)
            self.assertTrue(report["modelWeightsPreserved"])
            payload = torch.load(output / "stage-checkpoint.pt", weights_only=True)
            self.assertEqual(payload["optimizerStateDict"]["state"], {})
            self.assertEqual(payload["samplingRngState"], random.Random(1337).getstate())

    def test_run_rejects_committed_draft_before_optimizer_update(self) -> None:
        path = Path("training/pretraining/p2-32-first-run-contract.draft.json")
        with patch.object(
            torch.optim.AdamW, "step",
            side_effect=AssertionError("draft P2-32 must never update weights"),
        ), self.assertRaises(ValueError):
            run_structured_plan_training(
                bundle_dir=Path("missing"),
                stage_checkpoint=Path("missing.pt"),
                authorization_contract_path=path,
                preparation_contract_path=Path("missing-prep.json"),
                output_dir=Path("missing-output"),
                artifact_root=Path("."),
            )


if __name__ == "__main__":
    unittest.main()
