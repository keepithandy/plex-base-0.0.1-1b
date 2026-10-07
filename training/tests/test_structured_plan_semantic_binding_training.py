"""Safety tests for the locked P2-38 semantic-binding execution path."""

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
from plex_training.structured_plan_semantic_binding_training import (
    StructuredPlanCompleteRecordCorpus,
    _draft_authorization,
    _structured_plan_training_step,
    _validate_authorization,
    create_structured_plan_stage,
    preflight_structured_plan_training,
    run_structured_plan_training,
)
from plex_training.tokenizer import CODEC, sha256_file


class FakeTokenizer:
    def encode(self, text: str) -> list[int]:
        return [4 + (byte % 20) for byte in text.encode("utf-8")]

    def decode(self, ids: list[int]) -> str:
        raise NotImplementedError


def production_text(language: str, request: str, role: str) -> str:
    kind = {
        "html": "html-element",
        "css": "css-rule",
        "javascript": "js-function",
    }[language]
    plan = json.dumps({
        "schemaVersion": 1,
        "language": language,
        "action": "create",
        "targetKind": kind,
        "targetRole": role,
        "constraints": [{"kind": "behavior", "key": "mode", "value": role}],
        "searchHints": [role],
    }, separators=(",", ":"))
    return (
        "Convert the repository-style request into one semantic edit plan.\n"
        f"Language: {language}\n"
        f"Request: {request}\n"
        "Return exactly one compact JSON object matching the plan schema.\n"
        f"JSON:{plan}"
    )


class P238LockedTrainingTests(unittest.TestCase):
    def test_committed_contract_is_complete_draft_and_blocks_training(self) -> None:
        path = Path("training/pretraining/p2-38-first-run-contract.draft.json")
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(_draft_authorization(contract))
        self.assertFalse(contract["approvalPacketComplete"])
        self.assertFalse(contract["modelTrainingAuthorized"])
        self.assertIsNone(contract["approvedBy"])
        self.assertIsNone(contract["baseStage"]["checkpointSha256"])
        self.assertIsNone(contract["data"]["bundleManifestSha256"])
        self.assertIsNone(contract["training"]["sampler"])
        self.assertIsNone(contract["training"]["expectedRealTargetPositionsAt100Steps"])
        self.assertIsNone(contract["evaluation"]["baselineLoss"])
        self.assertIsNone(contract["command"])
        with self.assertRaises(ValueError):
            _validate_authorization(contract)

    def test_cli_has_no_runtime_step_or_resume_override(self) -> None:
        parser = build_parser()
        for extra in (["--steps", "101"], ["--resume", "checkpoint.pt"]):
            with self.subTest(extra=extra), self.assertRaises(SystemExit):
                parser.parse_args([
                    "plan-semantic-binding-run",
                    "--bundle-dir", "bundle",
                    "--stage-checkpoint", "stage.pt",
                    *extra,
                ])

    def _corpus(self, root: Path, texts: list[str]):
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

    def test_complete_record_sampler_requires_production_prompt_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            texts = [
                production_text("html", "Create one semantic region.", "sample-html-role"),
                production_text("javascript", "Create one helper.", "sample-js-role"),
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

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jsonl, token_path, index_path, tokenizer = self._corpus(
                root,
                ["Practice exact JSON serialization.\nJSON:{\"schemaVersion\":1}"],
            )
            with self.assertRaises(ValueError):
                StructuredPlanCompleteRecordCorpus(
                    token_path,
                    dataset_jsonl=jsonl,
                    index_path=index_path,
                    tokenizer=tokenizer,
                    expected_jsonl_sha256=sha256_file(jsonl),
                )

    def test_p238_training_step_uses_masked_complete_record_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            texts = [
                production_text("css", "Create the first style.", "first-style"),
                production_text("css", "Create the second style.", "second-style"),
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

    def test_weights_only_stage_uses_p235_endpoint_provenance_and_resets_state(self) -> None:
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
                    "kind": "plex-serialization-stability-stage-transition-v1",
                    "milestone": "P2-35",
                },
                tokenizer_record={
                    "tokenizerSha256":
                        "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                    "actualVocabularySize": 16384,
                },
                dataset_record={"synthetic": True},
                training_settings={"kind": "p2-35-authorized-serialization-stability-training-v1"},
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
                "milestone": "P2-38",
                "kind": "plex-p2-38-semantic-binding-preparation-contract-v1",
                "status": "design-preparation-only",
                "dataPreparationAuthorized": True,
                "modelTrainingAuthorized": False,
                "automaticTrainingExtension": False,
                "baseCheckpoint": {"sha256": sha256_file(base)},
            }), encoding="utf-8")
            output = root / "stage"
            with patch(
                "plex_training.structured_plan_semantic_binding_training.BASE_CHECKPOINT_SHA256",
                sha256_file(base),
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.DEFAULT_CONFIG", config,
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.inspect_structured_plan_bundle",
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
            self.assertEqual(report["p238StageStep"], 0)
            self.assertEqual(report["p238TokensProcessed"], 0)
            self.assertTrue(report["modelWeightsPreserved"])
            self.assertEqual(report["stageTransition"]["baseMilestone"], "P2-35")
            self.assertEqual(
                report["stageTransition"]["kind"],
                "plex-semantic-binding-stage-transition-v1",
            )
            payload = torch.load(output / "stage-checkpoint.pt", weights_only=True)
            self.assertEqual(payload["optimizerStateDict"]["state"], {})
            self.assertEqual(payload["samplingRngState"], random.Random(1337).getstate())

    def test_preflight_exposes_all_dataset_identities_while_unauthorized(self) -> None:
        class FakeCorpus:
            sampler_record = {
                "kind": "complete-record-v1",
                "records": 72,
                "indexSha256": "train-index",
                "trainJsonlSha256": "train-jsonl",
            }

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def replay_progress(self, seed, draws):
                return 222222, None

        class FakeValidation:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage.pt"
            stage.write_bytes(b"stage")
            draft = Path("training/pretraining/p2-38-first-run-contract.draft.json")
            bundle = {
                "root": root,
                "trainPath": root / "train.tokens.u16le",
                "validationPath": root / "validation.tokens.u16le",
                "tokenizer": {
                    "actualVocabularySize": 16384,
                    "tokenizerSha256": "tok",
                },
                "dataset": {
                    "trainJsonlSha256": "train-jsonl",
                    "validationJsonlSha256": "validation-jsonl",
                    "trainIndexSha256": "train-index",
                    "validationIndexSha256": "validation-index",
                    "trainTokenCount": 24793,
                    "validationTokenCount": 12409,
                },
            }
            (root / "manifest.json").write_text("{}", encoding="utf-8")
            model = PlexLanguageModel(ModelConfig(
                vocab_size=64, width=16, layers=1, heads=2,
                feed_forward_width=32, dropout=0.0,
            ))
            with patch(
                "plex_training.structured_plan_semantic_binding_training._preparation_contract",
                return_value={},
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.inspect_structured_plan_bundle",
                return_value=bundle,
            ), patch(
                "plex_training.structured_plan_semantic_binding_training._verify_stage",
                return_value=(model, {}),
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.PlexTokenizer.load",
                return_value=FakeTokenizer(),
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.StructuredPlanCompleteRecordCorpus",
                return_value=FakeCorpus(),
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.TokenCorpus",
                return_value=FakeValidation(),
            ), patch(
                "plex_training.structured_plan_semantic_binding_training._validation_loss",
                return_value=3.5,
            ), patch(
                "plex_training.structured_plan_semantic_binding_training.select_device",
                return_value=torch.device("cpu"),
            ):
                report = preflight_structured_plan_training(
                    bundle_dir=root,
                    stage_checkpoint=stage,
                    authorization_contract_path=draft,
                    preparation_contract_path=root / "prep.json",
                    output_dir=root / "structured-plan" / "p2-38-first-run",
                    artifact_root=root,
                    require_cuda=False,
                )
        self.assertFalse(report["authorized"])
        self.assertEqual(report["trainRecords"], 72)
        self.assertEqual(report["validationRecords"], 36)
        self.assertEqual(report["trainJsonlSha256"], "train-jsonl")
        self.assertEqual(report["validationJsonlSha256"], "validation-jsonl")
        self.assertEqual(report["trainIndexSha256"], "train-index")
        self.assertEqual(report["validationIndexSha256"], "validation-index")
        self.assertEqual(report["expectedRealTargetPositionsAt100Steps"], 222222)

    def test_draft_run_rejects_before_optimizer_update(self) -> None:
        path = Path("training/pretraining/p2-38-first-run-contract.draft.json")
        with patch.object(
            torch.optim.AdamW, "step",
            side_effect=AssertionError("draft P2-38 contract must never update weights"),
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
