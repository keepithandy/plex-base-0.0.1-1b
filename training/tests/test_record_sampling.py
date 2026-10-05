"""Check prompt boundaries, circular target alignment, and sampler resume identity."""
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
from plex_training.pilot import run_pilot
from plex_training.record_sampling import RecordStartTokenCorpus
from plex_training.runner import _verify_bpe_resume_policy, run_training
from plex_training.tokenizer import CODEC


class FixtureTokenizer:
    def encode(self, text):
        return [ord(char) + 4 for char in text]


class RecordSamplingTests(unittest.TestCase):
    def fixture(self, root):
        rows, entries, tokens = [], [], []
        for index in range(3):
            text = (f"Write a small CSS coding solution.\nRequest: Set width to {index + 1}px.\n"
                    f"Output contract: CSS only.\n{PROMPT_END}\n.box {{ width: {index + 1}px; }}")
            encoded = FixtureTokenizer().encode(text) + [3]
            rows.append({"recordId": f"example-{index}", "text": text})
            entries.append({"recordId": rows[-1]["recordId"], "startToken": len(tokens),
                            "tokenCount": len(encoded)})
            tokens.extend(encoded)
        token_path = root / "train.tokens.u16le"
        token_path.write_bytes(struct.pack(f"<{len(tokens)}H", *tokens))
        dataset = root / "train.jsonl"
        dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        index_path = root / "train.index.json"
        index_path.write_text(json.dumps(entries), encoding="utf-8")
        kwargs = dict(dataset_jsonl=dataset, index_path=index_path, tokenizer=FixtureTokenizer(),
                      expected_jsonl_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest())
        return token_path, kwargs, tokens, entries

    def test_uniform_verified_starts_and_circular_next_token_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path, kwargs, tokens, entries = self.fixture(Path(temporary))
            with RecordStartTokenCorpus(token_path, **kwargs) as source:
                rng = random.Random(1337)
                starts = [rng.choice(source.starts) for _ in range(50)]
                inputs, targets = source.sample_batch(random.Random(1337), 50, 512)
                self.assertEqual(tuple(inputs.shape), (50, 512))
                for number, start in enumerate(starts):
                    expected = [tokens[(start + offset) % len(tokens)] for offset in range(513)]
                    self.assertEqual(inputs[number].tolist(), expected[:-1])
                    self.assertEqual(targets[number].tolist(), expected[1:])
                    first_length = next(row["tokenCount"] for row in entries if row["startToken"] == start)
                    self.assertEqual(int(targets[number, first_length - 2]), 3)
                self.assertEqual(source.sampling_audit()["recordsSelected"], 3)
                self.assertGreater(source.sampling_audit()["wrappedWindows"], 0)

    def test_tampered_text_index_and_tokens_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, kwargs, _, entries = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "text differs"):
                RecordStartTokenCorpus(token_path, **{**kwargs, "expected_jsonl_sha256": "0" * 64})
            entries[1]["startToken"] += 1
            kwargs["index_path"].write_text(json.dumps(entries), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index differs"):
                RecordStartTokenCorpus(token_path, **kwargs)
            token_path, kwargs, _, entries = self.fixture(root)
            kwargs["index_path"].write_text(json.dumps(entries[:-1]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "row counts"):
                RecordStartTokenCorpus(token_path, **kwargs)
            token_path, kwargs, _, _ = self.fixture(root)
            raw = bytearray(token_path.read_bytes())
            raw[4] ^= 1
            token_path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "index differs"):
                RecordStartTokenCorpus(token_path, **kwargs)

    def test_context_cannot_truncate_the_first_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path, kwargs, _, _ = self.fixture(Path(temporary))
            with RecordStartTokenCorpus(token_path, **kwargs) as source:
                with self.assertRaisesRegex(ValueError, "complete first records"):
                    source.sample_batch(random.Random(0), 1, 8)

    def test_checkpoint_records_sampler_and_rejects_changed_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, kwargs, _, _ = self.fixture(root)
            # Tiny model uses a 32-token context: a compact tokenizer keeps each record below it.
            class CompactTokenizer:
                def encode(self, text):
                    return [ord(char) + 4 for char in text[-20:]]
            kwargs["tokenizer"] = CompactTokenizer()
            rows = [json.loads(line) for line in kwargs["dataset_jsonl"].read_text().splitlines()]
            tokens, entries = [], []
            for row in rows:
                encoded = kwargs["tokenizer"].encode(row["text"]) + [3]
                entries.append({"recordId": row["recordId"], "startToken": len(tokens), "tokenCount": len(encoded)})
                tokens.extend(encoded)
            token_path.write_bytes(struct.pack(f"<{len(tokens)}H", *tokens))
            kwargs["index_path"].write_text(json.dumps(entries), encoding="utf-8")
            common = dict(device_name="cpu", minutes=0.1, step_limit=1, artifact_root=root,
                          seed=1337, micro_batch=1, accumulation_steps=1,
                          config=tiny_test_config(), allow_tiny_config=True, codec=CODEC,
                          tokenizer_record={"codec": CODEC, "actualVocabularySize": 256},
                          dataset_record={"trainTokensSha256": "fixture"}, loss_vocabulary_size=256,
                          validation_maximum_batches=2)
            previous_threads = torch.get_num_threads()
            torch.set_num_threads(1)
            try:
                with RecordStartTokenCorpus(token_path, **kwargs) as source, TokenCorpus(token_path) as validation:
                    checkpoint = root / "first/checkpoint.pt"
                    run_training(train_source=source, validation=validation,
                                 output_checkpoint=checkpoint, metrics_path=root / "first/metrics.jsonl", **common)
                    _, payload = read_checkpoint(checkpoint, torch.device("cpu"))
                    self.assertEqual(payload["trainingSettings"]["samplingPolicy"], source.sampler_record)
                    legacy_settings = {**payload["trainingSettings"], "microBatch": 1,
                                       "gradientAccumulation": 16, "validationMaximumBatches": 100}
                    with self.assertRaisesRegex(ValueError, "original batch"):
                        _verify_bpe_resume_policy({"step": 1}, None, legacy_settings)
                    resumed = run_training(train_source=source, validation=validation, resume_from=checkpoint,
                                           output_checkpoint=root / "resume/checkpoint.pt",
                                           metrics_path=root / "resume/metrics.jsonl", **common)
                    self.assertEqual(resumed["step"], 2)
                with TokenCorpus(token_path) as ordinary, TokenCorpus(token_path) as validation:
                    with self.assertRaisesRegex(ValueError, "training settings"):
                        run_training(train_source=ordinary, validation=validation, resume_from=checkpoint,
                                     output_checkpoint=root / "invalid/checkpoint.pt",
                                     metrics_path=root / "invalid/metrics.jsonl", **common)
            finally:
                torch.set_num_threads(previous_threads)

    def test_record_start_pilot_enforces_experiment_bounds_before_loading(self):
        for minutes, steps, weight in ((11, 100, 1), (10, 101, 1), (10, None, 1), (10, 100, 4)):
            with self.subTest(minutes=minutes, steps=steps, weight=weight):
                with self.assertRaisesRegex(ValueError, "at most 100 steps"):
                    run_pilot(bundle_dir=Path("missing"), initialization=Path("missing.pt"),
                              output_dir=Path("missing"), artifact_root=Path("missing"),
                              minutes=minutes, steps=steps, answer_weight=weight,
                              sampling_policy="record-start-v1", dataset_dir=Path("missing"))


if __name__ == "__main__":
    unittest.main()
