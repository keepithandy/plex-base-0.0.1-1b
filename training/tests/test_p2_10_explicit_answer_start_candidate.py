from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_explicit_answer_start_candidate import (
    DEFAULT_OUTPUT, EXPERIMENT, OUTPUT_CONTRACT, build, prepare,
)
from prepare_selector_format_probe import build as build_baseline


class P210ExplicitAnswerStartCandidateTests(unittest.TestCase):
    def test_counts_and_crossed_matrix_match_p2_08(self) -> None:
        train, evaluation, _ = build()
        old_train, old_eval = build_baseline()
        self.assertEqual((len(train), len(evaluation)), (64, 16))
        self.assertEqual([(r["request"], r["value"], r["layoutId"]) for r in train],
                         [(r["request"], r["value"], r["layoutId"]) for r in old_train])
        self.assertEqual([(r["request"], r["value"], r["layoutId"]) for r in evaluation],
                         [(r["request"], r["value"], r["layoutId"]) for r in old_eval])
        self.assertEqual({r["contract"] for r in train + evaluation}, {OUTPUT_CONTRACT})

    def test_output_contract_is_the_only_content_change(self) -> None:
        train, evaluation, _ = build()
        old_train, old_eval = build_baseline()
        for new_rows, old_rows in ((train, old_train), (evaluation, old_eval)):
            for new, old in zip(new_rows, old_rows):
                self.assertEqual(new["request"], old["request"])
                self.assertEqual(new["solution"], old["solution"])
                self.assertEqual(new["value"], old["value"])
                self.assertNotEqual(new["contract"], old["contract"])
                self.assertEqual(new["sourceId"], EXPERIMENT)
                self.assertEqual(new["splitGroupId"], EXPERIMENT)

    def test_training_and_evaluation_boundaries_remain_pending_and_closed(self) -> None:
        train, evaluation, _ = build()
        self.assertTrue(all(r["approvalStatus"] == "pending-owner-review"
                            and r["use"] == "training-candidate" for r in train))
        self.assertTrue(all(r["approvalStatus"] == "evaluation-only"
                            and r["use"] == "evaluation-only-never-train" for r in evaluation))
        self.assertNotIn("give-back-no-changes", {r["phrasingId"] for r in train})
        self.assertEqual({r["value"] for r in train}, {r["value"] for r in evaluation})

    def test_generation_is_deterministic_with_unique_ids(self) -> None:
        train, evaluation, _ = build()
        self.assertEqual((train, evaluation), build()[:2])
        ids = [row["id"] for row in train + evaluation]
        self.assertEqual(len(ids), len(set(ids)))

    def test_preparation_pins_hashes_and_does_not_approve_training(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p2-10-test-", dir=DEFAULT_OUTPUT.parent) as temp:
            target = Path(temp) / "candidate"
            review = prepare(target)
            saved = json.loads((target / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["candidateJsonlSha256"], saved["candidateJsonlSha256"])
            self.assertEqual(review["evaluationJsonlSha256"], saved["evaluationJsonlSha256"])
            self.assertEqual(review["reviewMarkdownSha256"], saved["reviewMarkdownSha256"])
            self.assertEqual(review["trainingRecords"], 64)
            self.assertEqual(review["evaluationOnlyRecords"], 16)
            self.assertIs(review["modelTrained"], False)
            self.assertIs(review["trainingApprovalCreated"], False)
            self.assertIs(review["finalHoldoutOpened"], False)
            self.assertEqual(review["candidate"], EXPERIMENT)
            self.assertEqual(review["tokenizerSha256"],
                             "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573")
            markdown = (target / "REVIEW.md").read_text(encoding="utf-8")
            self.assertIn("Copy this selector unchanged: {value}", markdown)
            self.assertIn("inline (`: {value}`) and the selector on the following line", markdown)

    def test_prepare_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p2-10-test-", dir=DEFAULT_OUTPUT.parent) as temp:
            target = Path(temp) / "existing"
            target.mkdir()
            with self.assertRaisesRegex(FileExistsError, "fresh path"):
                prepare(target)


if __name__ == "__main__":
    unittest.main()
