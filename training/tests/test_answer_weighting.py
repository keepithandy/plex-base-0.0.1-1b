"""Check packed answer spans and unchanged random window sampling."""
import hashlib
import json
import random
import struct
import tempfile
import unittest
from pathlib import Path

import torch

from plex_training.answer_weighting import AnswerWeightedTokenCorpus, PROMPT_END
from plex_training.checkpoint import read_checkpoint
from plex_training.config import tiny_test_config
from plex_training.data import TokenCorpus
from plex_training.runner import run_training
from plex_training.tokenizer import CODEC


class AsciiTokenizer:
    def encode(self, text: str) -> list[int]:
        return [ord(char) + 4 for char in text]


class AnswerWeightingTests(unittest.TestCase):
    @staticmethod
    def _fixture(root: Path) -> tuple[Path, Path, Path, str, list[int]]:
        tokenizer = AsciiTokenizer()
        texts = [
            "Write a small JavaScript coding solution.\nRequest: Sum two values.\nOutput contract: Code only.\n"
            + PROMPT_END + "\nfunction add(a, b) { return a + b; }",
            "Write a small CSS coding solution.\nRequest: Make a box red.\nOutput contract: CSS only.\n"
            + PROMPT_END + "\n.box { color: red; }",
        ]
        token_ids, rows, index, prompt_lengths = [], [], [], []
        for number, value in enumerate(texts):
            start = len(token_ids)
            encoded = tokenizer.encode(value) + [3]
            token_ids.extend(encoded)
            rows.append({"recordId": f"sample-{number}", "text": value})
            index.append({"recordId": f"sample-{number}", "startToken": start, "tokenCount": len(encoded)})
            prompt_lengths.append(len(tokenizer.encode(value.split(PROMPT_END)[0] + PROMPT_END)))
        token_path = root / "train.tokens.u16le"
        token_path.write_bytes(struct.pack(f"<{len(token_ids)}H", *token_ids))
        dataset = root / "train.jsonl"
        dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        index_path = root / "train.index.json"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        return token_path, dataset, index_path, hashlib.sha256(dataset.read_bytes()).hexdigest(), prompt_lengths

    def test_answers_and_eos_are_weighted_but_prompt_and_sampling_are_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, dataset, index_path, digest, prompt_lengths = self._fixture(root)
            with TokenCorpus(token_path) as ordinary, AnswerWeightedTokenCorpus(
                token_path, dataset_jsonl=dataset, index_path=index_path,
                tokenizer=AsciiTokenizer(), expected_jsonl_sha256=digest,
            ) as weighted:
                first_length = json.loads(index_path.read_text(encoding="utf-8"))[0]["tokenCount"]
                self.assertEqual(weighted._weights[prompt_lengths[0] - 1], 1)
                self.assertEqual(weighted._weights[prompt_lengths[0]], 4)
                self.assertEqual(weighted._weights[first_length - 1], 4)
                self.assertEqual(weighted._weights[first_length], 1)
                self.assertEqual(weighted._weights[first_length + prompt_lengths[1]], 4)
                seed = 33
                expected_inputs, expected_targets = ordinary.sample_batch(random.Random(seed), 4, 32)
                inputs, targets, weights = weighted.sample_weighted_batch(random.Random(seed), 4, 32)
                self.assertTrue(torch.equal(inputs, expected_inputs))
                self.assertTrue(torch.equal(targets, expected_targets))
                self.assertEqual(weights.shape, targets.shape)
                self.assertEqual(weighted.objective_record["records"], 2)

    def test_dataset_row_count_must_exactly_match_index(self):
        for row_count in (1, 2, 3, 4):
            with self.subTest(row_count=row_count):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    token_path, dataset, index_path, _, _ = self._fixture(root)
                    rows = [
                        json.loads(line)
                        for line in dataset.read_text(encoding="utf-8").splitlines()
                    ]
                    while len(rows) < row_count:
                        extra = dict(rows[-1])
                        extra["recordId"] = f"extra-{len(rows)}"
                        rows.append(extra)
                    rows = rows[:row_count]
                    dataset.write_text(
                        "".join(json.dumps(row) + "\n" for row in rows),
                        encoding="utf-8",
                    )
                    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()

                    if row_count == 2:
                        with AnswerWeightedTokenCorpus(
                            token_path,
                            dataset_jsonl=dataset,
                            index_path=index_path,
                            tokenizer=AsciiTokenizer(),
                            expected_jsonl_sha256=digest,
                        ) as weighted:
                            self.assertEqual(weighted.objective_record["records"], 2)
                    else:
                        direction = "fewer" if row_count < 2 else "more"
                        with self.assertRaisesRegex(
                            ValueError,
                            f"{direction} rows than its token index",
                        ):
                            AnswerWeightedTokenCorpus(
                                token_path,
                                dataset_jsonl=dataset,
                                index_path=index_path,
                                tokenizer=AsciiTokenizer(),
                                expected_jsonl_sha256=digest,
                            )

    def test_wrong_text_identity_or_shifted_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, dataset, index_path, digest, _ = self._fixture(root)
            with self.assertRaisesRegex(ValueError, "differs from the verified"):
                AnswerWeightedTokenCorpus(
                    token_path, dataset_jsonl=dataset, index_path=index_path,
                    tokenizer=AsciiTokenizer(), expected_jsonl_sha256="0" * 64,
                )
            entries = json.loads(index_path.read_text(encoding="utf-8"))
            entries[1]["startToken"] += 1
            index_path.write_text(json.dumps(entries), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differ from packed"):
                AnswerWeightedTokenCorpus(
                    token_path, dataset_jsonl=dataset, index_path=index_path,
                    tokenizer=AsciiTokenizer(), expected_jsonl_sha256=digest,
                )

    def test_checkpoint_records_objective_and_rejects_ordinary_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, dataset, index_path, digest, _ = self._fixture(root)
            tokenizer_record = {"codec": CODEC, "actualVocabularySize": 256, "tokenizerSha256": "fixture"}
            dataset_record = {"trainTokensSha256": "fixture-train", "validationTokensSha256": "fixture-validation"}
            previous_threads = torch.get_num_threads()
            torch.set_num_threads(1)
            try:
                with AnswerWeightedTokenCorpus(
                    token_path, dataset_jsonl=dataset, index_path=index_path,
                    tokenizer=AsciiTokenizer(), expected_jsonl_sha256=digest,
                ) as weighted, TokenCorpus(token_path) as validation:
                    output = root / "weighted" / "checkpoint.pt"
                    result = run_training(
                        train_source=weighted, validation=validation, device_name="cpu",
                        minutes=0.1, step_limit=1, output_checkpoint=output,
                        metrics_path=root / "weighted" / "metrics.jsonl", artifact_root=root,
                        seed=1337, micro_batch=1, accumulation_steps=1,
                        config=tiny_test_config(), allow_tiny_config=True,
                        codec=CODEC, tokenizer_record=tokenizer_record,
                        dataset_record=dataset_record, loss_vocabulary_size=256,
                        validation_maximum_batches=2, answer_weight=4,
                    )
                self.assertEqual(result["step"], 1)
                _, payload = read_checkpoint(output, torch.device("cpu"))
                self.assertEqual(payload["trainingSettings"]["answerObjective"]["answerAndEosWeight"], 4)
                with TokenCorpus(token_path) as ordinary, TokenCorpus(token_path) as validation:
                    with self.assertRaisesRegex(ValueError, "training settings"):
                        run_training(
                            train_source=ordinary, validation=validation, device_name="cpu",
                            minutes=0.1, step_limit=1,
                            output_checkpoint=root / "invalid-resume" / "checkpoint.pt",
                            metrics_path=root / "invalid-resume" / "metrics.jsonl",
                            artifact_root=root, seed=1337, micro_batch=1, accumulation_steps=1,
                            resume_from=output, config=tiny_test_config(), allow_tiny_config=True,
                            codec=CODEC, tokenizer_record=tokenizer_record,
                            dataset_record=dataset_record, loss_vocabulary_size=256,
                            validation_maximum_batches=2,
                        )
            finally:
                torch.set_num_threads(previous_threads)


if __name__ == "__main__":
    unittest.main()
