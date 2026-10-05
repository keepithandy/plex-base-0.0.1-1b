"""Focused checks for the P2-03 answer/EOS-only complete-record objective."""
import hashlib
import json
import random
import struct
import tempfile
import unittest
from pathlib import Path
import sys

from plex_training.answer_focused_records import AnswerFocusedCompleteRecordTokenCorpus
from plex_training.answer_weighting import PROMPT_END

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2"))
from run_answer_focused_experiment import validate_bounds


class FixtureTokenizer:
    def encode(self, text):
        return [ord(char) + 4 for char in text[::8]]


class AnswerFocusedCompleteRecordTests(unittest.TestCase):
    def fixture(self, root: Path):
        rows, entries, tokens = [], [], []
        answers = (".x{color:red;}", ".long{width:20px;height:30px;}")
        for number, answer in enumerate(answers):
            text = (
                "Write a small CSS coding solution.\n"
                "Request: Style a box.\n"
                "Output contract: CSS only.\n"
                f"{PROMPT_END}\n{answer}"
            )
            encoded = FixtureTokenizer().encode(text) + [3]
            rows.append({"recordId": f"record-{number}", "text": text})
            entries.append({
                "recordId": rows[-1]["recordId"],
                "startToken": len(tokens),
                "tokenCount": len(encoded),
            })
            tokens.extend(encoded)
        dataset = root / "train.jsonl"
        dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        index = root / "train.index.json"
        index.write_text(json.dumps(entries), encoding="utf-8")
        token_path = root / "train.tokens.u16le"
        token_path.write_bytes(struct.pack(f"<{len(tokens)}H", *tokens))
        return token_path, {
            "dataset_jsonl": dataset,
            "index_path": index,
            "tokenizer": FixtureTokenizer(),
            "expected_jsonl_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        }

    def test_prompt_stays_in_context_but_only_answer_and_eos_are_supervised(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path, kwargs = self.fixture(Path(temporary))
            with AnswerFocusedCompleteRecordTokenCorpus(token_path, **kwargs) as source:
                rng = random.Random(7)
                starts = [rng.choice(source.starts) for _ in range(20)]
                inputs, targets, weights = source.sample_masked_batch(random.Random(7), 20, 64)
                for row, start in enumerate(starts):
                    target_length = source._length_by_start[start] - 1
                    first_supervised = source._first_supervised_by_start[start]
                    expected = source._window(start, target_length + 1)
                    self.assertEqual(inputs[row, :target_length].tolist(), expected[:-1].tolist())
                    self.assertEqual(targets[row, :target_length].tolist(), expected[1:].tolist())
                    self.assertTrue(bool((weights[row, :first_supervised] == 0).all()))
                    self.assertTrue(bool((weights[row, first_supervised:target_length] == 1).all()))
                    self.assertTrue(bool((weights[row, target_length:] == 0).all()))
                    self.assertEqual(int(targets[row, target_length - 1]), 3)
                    self.assertEqual(float(weights[row, target_length - 1]), 1.0)

                audit = source.sampling_audit()
                self.assertEqual(
                    audit["realTargetPositions"],
                    audit["supervisedTargetPositions"] + audit["excludedPromptTargetPositions"],
                )
                self.assertEqual(int(weights.sum().item()), audit["supervisedTargetPositions"])
                self.assertEqual(source.sampler_record["kind"], "complete-record-v1")
                self.assertEqual(
                    source.sampler_record["answerObjective"]["kind"],
                    "answer-eos-only-complete-record-v1",
                )
                self.assertEqual(source.objective_record["promptTargetWeight"], 0)
                self.assertEqual(source.objective_record["answerAndEosTargetWeight"], 1)

    def test_objective_requires_verified_unchanged_training_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            token_path, kwargs = self.fixture(root)
            original_hash = kwargs["expected_jsonl_sha256"]
            kwargs["dataset_jsonl"].write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "text differs"):
                AnswerFocusedCompleteRecordTokenCorpus(
                    token_path,
                    **{**kwargs, "expected_jsonl_sha256": original_hash},
                )

    def test_experiment_bounds_reject_extensions(self):
        validate_bounds(100, 10)
        for steps, minutes in (
            (101, 10),
            (0, 10),
            (True, 10),
            (100, 11),
            (100, 0),
            (100, float("nan")),
        ):
            with self.subTest(steps=steps, minutes=minutes), self.assertRaises(ValueError):
                validate_bounds(steps, minutes)


if __name__ == "__main__":
    unittest.main()
