from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_selector_format_probe import (
    ADDITIONAL_SELECTORS, BASELINE_SELECTORS, HELD_OUT_PHRASE, LAYOUTS,
    SELECTORS, TRAINING_PHRASES, build, prepare, validate,
)


class P208SelectorFormatProbeTests(unittest.TestCase):
    def test_counts_and_fully_crossed_training_matrix(self) -> None:
        train, evaluation = build()
        self.assertEqual((len(train), len(evaluation)), (64, 16))
        self.assertEqual(Counter((r["phrasingId"], r["layoutId"]) for r in train),
                         Counter({(phrase_id, layout): 8 for phrase_id, _ in TRAINING_PHRASES
                                  for layout in LAYOUTS}))
        self.assertEqual(Counter((r["layoutId"], r["value"]) for r in evaluation),
                         Counter({(layout, value): 1 for layout in LAYOUTS for value in SELECTORS}))
        validate(train, evaluation)

    def test_selectors_expand_baseline_with_five_distinct_values(self) -> None:
        self.assertEqual(len(BASELINE_SELECTORS), 3)
        self.assertEqual(len(ADDITIONAL_SELECTORS), 5)
        self.assertEqual(len(SELECTORS), 8)
        self.assertFalse(set(BASELINE_SELECTORS) & set(ADDITIONAL_SELECTORS))

    def test_both_layouts_are_crossed_with_all_phrases_and_values(self) -> None:
        train, evaluation = build()
        for phrase_id, _ in TRAINING_PHRASES:
            rows = [r for r in train if r["phrasingId"] == phrase_id]
            self.assertEqual({(r["layoutId"], r["value"]) for r in rows},
                             {(layout, value) for layout in LAYOUTS for value in SELECTORS})
        self.assertEqual({(r["phrasingId"], r["layoutId"], r["value"]) for r in evaluation},
                         {(HELD_OUT_PHRASE[0], layout, value)
                          for layout in LAYOUTS for value in SELECTORS})

    def test_evaluation_values_are_seen_and_wording_is_held_out(self) -> None:
        train, evaluation = build()
        self.assertEqual({r["value"] for r in train}, {r["value"] for r in evaluation})
        self.assertEqual({r["phrasingId"] for r in evaluation}, {HELD_OUT_PHRASE[0]})
        self.assertNotIn(HELD_OUT_PHRASE[0], {r["phrasingId"] for r in train})
        self.assertFalse({r["request"] for r in train} & {r["request"] for r in evaluation})

    def test_candidate_records_remain_pending_and_evaluation_only(self) -> None:
        train, evaluation = build()
        self.assertTrue(all(r["approvalStatus"] == "pending-owner-review"
                            and r["use"] == "training-candidate" for r in train))
        self.assertTrue(all(r["approvalStatus"] == "evaluation-only"
                            and r["use"] == "evaluation-only-never-train" for r in evaluation))

    def test_generation_is_deterministic_and_ids_unique(self) -> None:
        train, evaluation = build()
        self.assertEqual((train, evaluation), build())
        ids = [r["id"] for r in train + evaluation]
        self.assertEqual(len(ids), len(set(ids)))

    def test_validation_rejects_layout_leak_or_contract_drift(self) -> None:
        train, evaluation = build()
        train[0]["layoutId"] = "colon-newline"
        with self.assertRaises(ValueError):
            validate(train, evaluation)
        train, evaluation = build()
        evaluation[0]["contract"] = "Return CSS rules only."
        with self.assertRaises(ValueError):
            validate(train, evaluation)
        train, evaluation = build()
        train[0]["request"] = "Copy this selector unchanged: .actions"
        with self.assertRaises(ValueError):
            validate(train, evaluation)

    def test_preparation_records_hashes_tokenizer_and_closed_holdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p2-08-test-", dir=PHASE2 / "drafts") as temp:
            result = prepare(Path(temp) / "candidate")
            target = Path(temp) / "candidate"
            on_disk = json.loads((target / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(result["candidateJsonlSha256"], on_disk["candidateJsonlSha256"])
            self.assertEqual(result["evaluationJsonlSha256"], on_disk["evaluationJsonlSha256"])
            self.assertEqual(result["reviewMarkdownSha256"], on_disk["reviewMarkdownSha256"])
            self.assertEqual(result["trainingRecords"], 64)
            self.assertEqual(result["evaluationOnlyRecords"], 16)
            self.assertEqual(result["tokenizerSha256"],
                             "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573")
            self.assertIs(result["modelTrained"], False)
            self.assertIs(result["tokenizerRefitted"], False)
            self.assertIs(result["finalHoldoutOpened"], False)
            self.assertLessEqual(result["tokenMaxima"]["recordIncludingEos"], 512)
            self.assertTrue((target / "candidate.jsonl").read_bytes().endswith(b"\n"))
            self.assertTrue((target / "evaluation-only.jsonl").read_bytes().endswith(b"\n"))

    def test_prepare_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p2-08-test-", dir=PHASE2 / "drafts") as temp:
            target = Path(temp) / "existing"
            target.mkdir()
            with self.assertRaisesRegex(FileExistsError, "fresh path"):
                prepare(target)


if __name__ == "__main__":
    unittest.main()
