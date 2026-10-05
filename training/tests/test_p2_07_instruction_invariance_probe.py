from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_instruction_invariance_probe import FAMILIES, build, prepare, validate


class P207InstructionInvarianceProbeTests(unittest.TestCase):
    def test_counts_and_family_matrix(self) -> None:
        train, evaluation = build()
        self.assertEqual(len(train), 24)
        self.assertEqual(len(evaluation), 6)
        self.assertEqual(Counter(row["operationFamily"] for row in train), {
            "selector-copy": 12, "gap-copy": 12,
        })
        self.assertEqual(Counter(row["operationFamily"] for row in evaluation), {
            "selector-copy": 3, "gap-copy": 3,
        })
        validate(train, evaluation)

    def test_each_training_phrase_is_crossed_with_every_value(self) -> None:
        train, _ = build()
        for family, spec in FAMILIES.items():
            rows = [row for row in train if row["operationFamily"] == family]
            self.assertEqual({(row["phrasingId"], row["value"]) for row in rows}, {
                (phrase_id, value) for phrase_id, _ in spec["phrases"] for value in spec["values"]
            })
            self.assertEqual(Counter(row["value"] for row in rows),
                             Counter({value: 4 for value in spec["values"]}))

    def test_evaluation_uses_seen_values_and_never_trained_wording(self) -> None:
        train, evaluation = build()
        for family, spec in FAMILIES.items():
            family_train = [row for row in train if row["operationFamily"] == family]
            family_eval = [row for row in evaluation if row["operationFamily"] == family]
            self.assertEqual({row["value"] for row in family_eval}, set(spec["values"]))
            self.assertTrue({row["phrasingId"] for row in family_train}.isdisjoint(
                {row["phrasingId"] for row in family_eval}
            ))
        self.assertTrue({row["request"] for row in train}.isdisjoint(
            {row["request"] for row in evaluation}
        ))

    def test_ids_and_review_boundaries(self) -> None:
        train, evaluation = build()
        rows = train + evaluation
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        self.assertTrue(all(row["approvalStatus"] == "pending-owner-review" for row in train))
        self.assertTrue(all(row["use"] == "training-candidate" for row in train))
        self.assertTrue(all(row["approvalStatus"] == "evaluation-only" for row in evaluation))
        self.assertTrue(all(row["use"] == "evaluation-only-never-train" for row in evaluation))

    def test_generation_is_deterministic(self) -> None:
        self.assertEqual(build(), build())

    def test_validation_rejects_evaluation_phrase_leakage(self) -> None:
        train, evaluation = build()
        train[0]["phrasingId"] = evaluation[0]["phrasingId"]
        with self.assertRaises(ValueError):
            validate(train, evaluation)

    def test_preparation_records_frozen_tokenizer_and_hashes(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp:
            target = Path(temp) / "candidate"
            review = prepare(target)
            on_disk = json.loads((target / "review.json").read_text(encoding="utf-8"))
            self.assertIs(review["tokenizerRefitted"], False)
            self.assertEqual(review["tokenizerSha256"],
                             "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573")
            self.assertIs(review["modelTrained"], False)
            self.assertIs(review["finalHoldoutOpened"], False)
            self.assertEqual(review["trainingRecords"], 24)
            self.assertEqual(review["evaluationOnlyRecords"], 6)
            self.assertEqual(review["candidateJsonlSha256"], on_disk["candidateJsonlSha256"])
            self.assertEqual(review["evaluationJsonlSha256"], on_disk["evaluationJsonlSha256"])
            self.assertTrue(review["reviewMarkdownSha256"])
            self.assertTrue((target / "candidate.jsonl").read_bytes().endswith(b"\n"))
            self.assertTrue((target / "evaluation-only.jsonl").read_bytes().endswith(b"\n"))

    def test_prepare_refuses_existing_output_path(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp:
            target = Path(temp) / "existing"
            target.mkdir()
            with self.assertRaisesRegex(FileExistsError, "fresh path"):
                prepare(target)


if __name__ == "__main__":
    unittest.main()
