import hashlib
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from torch.nn import functional as F

from plex_training.artifacts import atomic_write_checkpoint
from plex_training.checkpoint import save_checkpoint
from plex_training.config import tiny_test_config
from plex_training.model import PlexLanguageModel
from plex_training.pilot import evaluate_pilot, inspect_pilot_bundle, run_pilot
from plex_training.tokenizer import CODEC, train_tokenizer


class PilotSafetyTests(unittest.TestCase):
    def _bundle(self, root: Path) -> Path:
        dataset = root / "dataset"
        (dataset / "licenses").mkdir(parents=True)
        notice = b"Fixture permission notice.\n"
        (dataset / "licenses/fixture.txt").write_bytes(notice)
        summary = {}
        sources = []
        for split, text in (
            ("train", "function add(left, right) { return left + right; }\n" * 300),
            ("validation", "Held-out example: const value = document.title;\n" * 300),
        ):
            row = {"recordId": split, "sourceId": split, "groupId": split,
                   "path": "fixture.js", "text": text,
                   "contentSha256": hashlib.sha256(text.encode()).hexdigest()}
            raw = (json.dumps(row) + "\n").encode()
            (dataset / f"{split}.jsonl").write_bytes(raw)
            summary[f"{split}Records"] = 1
            summary[f"{split}JsonlSha256"] = hashlib.sha256(raw).hexdigest()
            sources.append({"id": split, "groupId": split, "rightsReviewStatus": "approved",
                            "licenseNoticeFile": "licenses/fixture.txt",
                            "licenseNoticeSha256": hashlib.sha256(notice).hexdigest()})
        (dataset / "manifest.json").write_text(json.dumps({
            "schemaVersion": 1, "pipelineVersion": "p1-14.2",
            "sources": sources, "summary": summary,
        }))
        bundle = root / "bundle"
        train_tokenizer(dataset, bundle, vocab_size=300)
        return bundle

    def test_checkpoint_serialization_is_bounded_before_overallocation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            filler = root / "filler.bin"
            filler.write_bytes(b"123456")
            destination = root / "model.pt"
            observed = {}

            def fake_save(_checkpoint, stream) -> None:
                observed["stream"] = stream
                self.assertEqual(stream.write(b"abc"), 3)
                with self.assertRaisesRegex(RuntimeError, "during checkpoint serialization"):
                    stream.write(b"de")
                raise RuntimeError("stop after bounded-write assertion")

            with patch("plex_training.artifacts.torch.save", side_effect=fake_save):
                with self.assertRaisesRegex(RuntimeError, "stop after bounded-write assertion"):
                    atomic_write_checkpoint(
                        {"fixture": True},
                        destination,
                        root,
                        storage_limit_bytes=10,
                    )

            self.assertEqual(observed["stream"].bytes_written, 3)
            self.assertEqual(filler.read_bytes(), b"123456")
            self.assertFalse(destination.exists())
            self.assertFalse((root / "model.pt.tmp").exists())

    def test_checkpoint_overwrite_budget_counts_old_checkpoint_during_temp_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "model.pt"
            destination.write_bytes(b"GOOD")
            filler = root / "filler.bin"
            filler.write_bytes(b"12")

            def fake_save(_checkpoint, stream) -> None:
                self.assertEqual(stream.write(b"abcd"), 4)
                stream.write(b"e")

            with patch("plex_training.artifacts.torch.save", side_effect=fake_save):
                with self.assertRaisesRegex(RuntimeError, "11 bytes requested, limit is 10 bytes"):
                    atomic_write_checkpoint(
                        {"fixture": True},
                        destination,
                        root,
                        overwrite=True,
                        storage_limit_bytes=10,
                    )

            self.assertEqual(destination.read_bytes(), b"GOOD")
            self.assertEqual(filler.read_bytes(), b"12")
            self.assertFalse((root / "model.pt.tmp").exists())

    def test_pilot_bundle_rejects_modified_validation_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = self._bundle(Path(temporary))
            inspected = inspect_pilot_bundle(bundle)
            self.assertNotEqual(inspected["dataset"]["trainTokensSha256"],
                                inspected["dataset"]["validationTokensSha256"])
            self.assertGreaterEqual(inspected["dataset"]["validationTokenCount"], 513)
            with (bundle / "validation.tokens.u16le").open("ab") as stream:
                stream.write(b"\x00\x00")
            with self.assertRaisesRegex(ValueError, "bundle hash"):
                inspect_pilot_bundle(bundle)

    def test_evaluation_rejects_checkpoint_from_another_tokenizer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._bundle(root)
            model = PlexLanguageModel(tiny_test_config())
            optimizer = torch.optim.AdamW(model.parameters())
            checkpoint = root / "wrong.pt"
            save_checkpoint(
                model, optimizer, step=1, seed=7, codec=CODEC,
                sampling_rng=random.Random(7), device=torch.device("cpu"),
                destination=checkpoint, artifact_root=root,
                tokenizer_record={"tokenizerSha256": "wrong"},
                dataset_record={"trainTokensSha256": "wrong"},
            )
            with self.assertRaisesRegex(ValueError, "does not match"):
                evaluate_pilot(bundle_dir=bundle, checkpoint_path=checkpoint,
                               device_name="cpu", maximum_batches=1)

    def test_loss_masks_model_capacity_above_trained_vocabulary(self) -> None:
        model = PlexLanguageModel(tiny_test_config()).eval()
        inputs = torch.tensor([[4, 5, 6, 7]], dtype=torch.long)
        targets = torch.tensor([[5, 6, 7, 8]], dtype=torch.long)
        logits, loss = model(inputs, targets, loss_vocabulary_size=128)
        self.assertIsNotNone(loss)
        expected = F.cross_entropy(logits[..., :128].reshape(-1, 128), targets.reshape(-1))
        self.assertTrue(torch.allclose(loss, expected))
        with self.assertRaisesRegex(ValueError, "loss vocabulary"):
            model(inputs, torch.tensor([[5, 6, 7, 129]]), loss_vocabulary_size=128)

    def test_pilot_rejects_over_two_hours_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "pilot"
            with self.assertRaisesRegex(ValueError, "120 minutes"):
                run_pilot(bundle_dir=root / "missing", initialization=root / "missing.pt",
                          output_dir=output, artifact_root=root, minutes=120.01)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
