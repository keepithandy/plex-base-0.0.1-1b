"""Check record isolation, padding loss, real-token accounting, and exact resume."""
import hashlib
import json
import random
import struct
import tempfile
import unittest
from pathlib import Path

import torch

from plex_training.answer_weighting import PROMPT_END
from plex_training.checkpoint import read_checkpoint
from plex_training.config import tiny_test_config
from plex_training.data import TokenCorpus
from plex_training.model import PlexLanguageModel
from plex_training.pilot import run_pilot
from plex_training.record_sampling import CompleteRecordTokenCorpus, RecordStartTokenCorpus
from plex_training.runner import run_training
from plex_training.tokenizer import CODEC


class FixtureTokenizer:
    def encode(self, text):
        # A deterministic fixture codec; no external tokenizer or checkpoint.
        return [ord(char) + 4 for char in text[::8]]


class CompleteRecordTests(unittest.TestCase):
    def fixture(self, root):
        rows, entries, tokens = [], [], []
        for number, answer in enumerate((".x{color:red;}", ".long{width:20px;height:30px;}")):
            text = ("Write a small CSS coding solution.\nRequest: Style a box.\n"
                    f"Output contract: CSS only.\n{PROMPT_END}\n{answer}")
            encoded = FixtureTokenizer().encode(text) + [3]
            rows.append({"recordId": f"record-{number}", "text": text})
            entries.append({"recordId": rows[-1]["recordId"], "startToken": len(tokens),
                            "tokenCount": len(encoded)})
            tokens.extend(encoded)
        dataset = root / "train.jsonl"
        dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        index = root / "train.index.json"
        index.write_text(json.dumps(entries), encoding="utf-8")
        token_path = root / "train.tokens.u16le"
        token_path.write_bytes(struct.pack(f"<{len(tokens)}H", *tokens))
        return token_path, dict(dataset_jsonl=dataset, index_path=index, tokenizer=FixtureTokenizer(),
                               expected_jsonl_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest())

    def test_rows_stop_at_eos_and_padding_never_has_loss_weight(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path, kwargs = self.fixture(Path(temporary))
            with CompleteRecordTokenCorpus(token_path, **kwargs) as source:
                starts = [random.Random(seed).choice(source.starts) for seed in range(20)]
                # Replay a single RNG stream, matching sample_masked_batch's draw order.
                rng = random.Random(7)
                starts = [rng.choice(source.starts) for _ in range(20)]
                inputs, targets, weights = source.sample_masked_batch(random.Random(7), 20, 32)
                self.assertGreater(int((weights == 0).sum()), 0)
                for row, start in enumerate(starts):
                    length = source._length_by_start[start]
                    expected = source._window(start, length).tolist()
                    self.assertEqual(inputs[row, :length - 1].tolist(), expected[:-1])
                    self.assertEqual(targets[row, :length - 1].tolist(), expected[1:])
                    self.assertEqual(int(targets[row, length - 2]), 3)
                    self.assertTrue(bool((weights[row, :length - 1] == 1).all()))
                    self.assertTrue(bool((weights[row, length - 1:] == 0).all()))
                audit = source.sampling_audit()
                self.assertEqual(audit["realTargetPositions"], int(weights.sum()))
                self.assertEqual(audit["paddingTargetPositions"], targets.numel() - int(weights.sum()))

    def test_masked_padding_changes_neither_real_logits_nor_loss(self):
        previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        try:
            model = PlexLanguageModel(tiny_test_config()).eval()
            inputs = torch.tensor([[4, 5, 6, 7, 0, 0]])
            targets = torch.tensor([[5, 6, 7, 3, 0, 0]])
            weights = torch.tensor([[1., 1., 1., 1., 0., 0.]])
            logits, padded_loss = model(inputs, targets, target_weights=weights)
            plain_logits, plain_loss = model(inputs[:, :4], targets[:, :4])
            self.assertTrue(torch.allclose(logits[:, :4], plain_logits, atol=1e-6))
            self.assertTrue(torch.allclose(padded_loss, plain_loss, atol=1e-6))
            altered = inputs.clone()
            altered[:, 4:] = 99
            changed_logits, changed_loss = model(altered, targets, target_weights=weights)
            self.assertTrue(torch.allclose(logits[:, :4], changed_logits[:, :4], atol=1e-6))
            self.assertTrue(torch.allclose(padded_loss, changed_loss, atol=1e-6))
        finally:
            torch.set_num_threads(previous_threads)

    def test_context_and_missing_mask_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path, kwargs = self.fixture(Path(temporary))
            with CompleteRecordTokenCorpus(token_path, **kwargs) as source:
                with self.assertRaisesRegex(ValueError, "without truncation"):
                    source.sample_masked_batch(random.Random(0), 1, 8)
                with self.assertRaisesRegex(ValueError, "requires the padding mask"):
                    source.sample_batch(random.Random(0), 1, 32)

    def test_variable_token_progress_and_resumed_weights_match_uninterrupted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, kwargs = self.fixture(root)
            common = dict(device_name="cpu", minutes=0.1, artifact_root=root,
                          seed=1337, micro_batch=2, accumulation_steps=2,
                          config=tiny_test_config(), allow_tiny_config=True, codec=CODEC,
                          tokenizer_record={"codec": CODEC, "actualVocabularySize": 256},
                          dataset_record={"trainTokensSha256": "fixture"}, loss_vocabulary_size=256,
                          validation_maximum_batches=2)
            previous_threads = torch.get_num_threads()
            torch.set_num_threads(1)
            try:
                def train(name, steps, resume=None):
                    with CompleteRecordTokenCorpus(token_path, **kwargs) as source, TokenCorpus(token_path) as validation:
                        result = run_training(train_source=source, validation=validation, step_limit=steps,
                                              output_checkpoint=root / name / "checkpoint.pt",
                                              metrics_path=root / name / "metrics.jsonl", resume_from=resume, **common)
                        return result, source.sampling_audit()
                first, audit = train("first", 1)
                self.assertEqual(first["tokensProcessedThisRun"], audit["realTargetPositions"])
                self.assertEqual(first["paddingTargetPositionsThisRun"], audit["paddingTargetPositions"])
                self.assertLess(first["tokensProcessedThisRun"], 2 * 2 * 32)
                resumed, _ = train("resume", 1, root / "first/checkpoint.pt")
                uninterrupted, _ = train("full", 2)
                self.assertEqual(resumed["tokensProcessedTotal"], uninterrupted["tokensProcessedTotal"])
                _, full = read_checkpoint(root / "full/checkpoint.pt", torch.device("cpu"))
                _, continued = read_checkpoint(root / "resume/checkpoint.pt", torch.device("cpu"))
                for key, tensor in full["modelStateDict"].items():
                    self.assertTrue(torch.equal(tensor, continued["modelStateDict"][key]), key)
                self.assertEqual(full["samplingRngState"], continued["samplingRngState"])
                # Changing the recorded progress or dropping the sampler cannot be a valid resume.
                _, bad = read_checkpoint(root / "first/checkpoint.pt", torch.device("cpu"))
                bad["tokensProcessedTotal"] += 1
                torch.save(bad, root / "bad.pt")
                with self.assertRaisesRegex(ValueError, "token progress"):
                    train("bad-resume", 1, root / "bad.pt")
                with RecordStartTokenCorpus(token_path, **kwargs) as source, TokenCorpus(token_path) as validation:
                    with self.assertRaisesRegex(ValueError, "training settings"):
                        run_training(train_source=source, validation=validation, step_limit=1,
                                     output_checkpoint=root / "changed/checkpoint.pt",
                                     metrics_path=root / "changed/metrics.jsonl",
                                     resume_from=root / "first/checkpoint.pt", **common)
            finally:
                torch.set_num_threads(previous_threads)

    def test_complete_record_pilot_enforces_bounds_before_loading(self):
        for minutes, steps, weight, dataset in ((11, 100, 1, Path("missing")),
                                               (10, 101, 1, Path("missing")),
                                               (10, None, 1, Path("missing")),
                                               (10, 100, 4, Path("missing")),
                                               (10, 100, 1, None)):
            with self.subTest(minutes=minutes, steps=steps, weight=weight, dataset=dataset):
                with self.assertRaises(ValueError):
                    run_pilot(bundle_dir=Path("missing"), initialization=Path("missing.pt"),
                              output_dir=Path("missing"), artifact_root=Path("missing"),
                              minutes=minutes, steps=steps, answer_weight=weight,
                              sampling_policy="complete-record-v1", dataset_dir=dataset)


if __name__ == "__main__":
    unittest.main()
