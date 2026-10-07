"""Safety tests for the P2-35 serialization-stability training path."""

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
from plex_training.structured_plan_serialization_training import (
    StructuredPlanCompleteRecordCorpus,
    _draft_authorization,
    _structured_plan_training_step,
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


class P235LockedTrainingTests(unittest.TestCase):
    def test_committed_contract_is_draft_and_blocks_training(self) -> None:
        path = Path("training/pretraining/p2-35-first-run-contract.draft.json")
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(_draft_authorization(contract))
        self.assertFalse(contract["modelTrainingAuthorized"])
        self.assertIsNone(contract["approvedBy"])
        self.assertIsNone(contract["baseStage"]["checkpointSha256"])
        self.assertIsNone(contract["data"]["bundleManifestSha256"])
        self.assertIsNone(contract["training"]["sampler"])
        self.assertIsNone(contract["training"]["expectedRealTargetPositionsAt100Steps"])
        self.assertIsNone(contract["evaluation"]["baselineLoss"])
        with self.assertRaises(ValueError):
            _validate_authorization(contract)

    def test_cli_has_no_runtime_step_or_resume_override(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "plan-serialization-run",
                "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt",
                "--steps", "101",
            ])
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "plan-serialization-run",
                "--bundle-dir", "bundle",
                "--stage-checkpoint", "stage.pt",
                "--resume", "checkpoint.pt",
            ])

    def _corpus(self, root: Path, texts: list[str]) -> tuple[Path, Path, Path, FakeTokenizer]:
        tokenizer = FakeTokenizer()
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
                index.append({
                    "recordId": record_id,
                    "startToken": offset,
                    "tokenCount": len(encoded),
                })
                offset += len(encoded)
        token_path.write_bytes(tokens.tobytes())
        index_path.write_text(json.dumps(index), encoding="utf-8")
        return jsonl, token_path, index_path, tokenizer

    def test_complete_record_sampler_accepts_micro_and_production_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            texts = [
                "Practice exact JSON serialization.\n"
                "Return exactly one compact JSON object and no extra text.\n"
                "Task: Serialization concept sample. Serialize a flat object.\n"
                "JSON:{\"schemaVersion\":1}",
                "Convert the repository-style request into one semantic edit plan.\n"
                "Language: html\n"
                "Request: Modify a sample region.\n"
                "Return exactly one compact JSON object matching the plan schema.\n"
                "JSON:{\"schemaVersion\":1}",
            ]
            jsonl, token_path, index_path, tokenizer = self._corpus(root, texts)
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
                self.assertEqual(corpus.sampler_record["records"], 2)
                positions, _ = corpus.replay_progress(1337, 16)
                self.assertGreater(positions, 0)

    def test_p235_training_step_uses_masked_complete_record_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            texts = [
                "Practice exact JSON serialization.\n"
                "Return exactly one compact JSON object and no extra text.\n"
                "Task: Serialization concept first. Serialize a flat object.\n"
                "JSON:{\"schemaVersion\":1}",
                "Practice exact JSON serialization.\n"
                "Return exactly one compact JSON object and no extra text.\n"
                "Task: Serialization concept second. Serialize a constraint.\n"
                "JSON:{\"kind\":\"state\",\"key\":\"open\",\"value\":\"true\"}",
            ]
            jsonl, token_path, index_path, tokenizer = self._corpus(root, texts)
            config = ModelConfig(
                vocab_size=64, width=16, layers=1, heads=2,
                feed_forward_width=32, dropout=0.0,
            )
            model = PlexLanguageModel(config)
            optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
            before = next(model.parameters()).detach().clone()
            with StructuredPlanCompleteRecordCorpus(
                token_path,
                dataset_jsonl=jsonl,
                index_path=index_path,
                tokenizer=tokenizer,
                expected_jsonl_sha256=sha256_file(jsonl),
            ) as corpus:
                loss, real, padding = _structured_plan_training_step(
                    model,
                    optimizer,
                    corpus,
                    random.Random(1337),
                    torch.device("cpu"),
                    micro_batch=1,
                    accumulation_steps=2,
                    loss_vocabulary_size=64,
                )
                audit = corpus.sampling_audit()
            self.assertGreater(loss, 0.0)
            self.assertGreater(real, 0)
            self.assertGreaterEqual(padding, 0)
            self.assertEqual(audit["examples"], 2)
            self.assertEqual(audit["realTargetPositions"], real)
            self.assertTrue(optimizer.state)
            self.assertFalse(torch.equal(before, next(model.parameters()).detach()))

    def test_weights_only_stage_uses_p232_endpoint_provenance_and_resets_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = ModelConfig(
                vocab_size=64, width=16, layers=1, heads=2,
                feed_forward_width=32, dropout=0.0,
            )
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
                stage_transition_record={
                    "kind": "plex-structured-plan-stage-transition-v1",
                    "milestone": "P2-32",
                },
                tokenizer_record={
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
                dataset_record={"synthetic": True},
                training_settings={"kind": "p2-32-authorized-structured-plan-training-v1"},
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
                "schemaVersion": 1,
                "milestone": "P2-35",
                "kind": "plex-p2-35-serialization-stability-preparation-contract-v1",
                "status": "preparation-only-awaiting-owner-review",
                "dataPreparationAuthorized": True,
                "modelTrainingAuthorized": False,
                "automaticTrainingExtension": False,
                "baseCheckpoint": {"sha256": sha256_file(base)},
            }), encoding="utf-8")
            output = root / "stage"
            with patch(
                "plex_training.structured_plan_serialization_training.BASE_CHECKPOINT_SHA256",
                sha256_file(base),
            ), patch(
                "plex_training.structured_plan_serialization_training.DEFAULT_CONFIG", config,
            ), patch(
                "plex_training.structured_plan_serialization_training.inspect_structured_plan_bundle",
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
            self.assertEqual(report["p235StageStep"], 0)
            self.assertEqual(report["p235TokensProcessed"], 0)
            self.assertTrue(report["modelWeightsPreserved"])
            self.assertEqual(report["stageTransition"]["baseMilestone"], "P2-32")
            self.assertEqual(
                report["stageTransition"]["kind"],
                "plex-serialization-stability-stage-transition-v1",
            )
            payload = torch.load(output / "stage-checkpoint.pt", weights_only=True)
            self.assertEqual(payload["optimizerStateDict"]["state"], {})
            self.assertEqual(payload["samplingRngState"], random.Random(1337).getstate())

    def test_draft_run_rejects_before_optimizer_update(self) -> None:
        path = Path("training/pretraining/p2-35-first-run-contract.draft.json")
        with patch.object(
            torch.optim.AdamW, "step",
            side_effect=AssertionError("draft P2-35 contract must never update weights"),
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
