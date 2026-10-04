"""Guard the unapproved failure-gap data against repetition and leakage."""
import copy
import re
import sys
import tempfile
import unittest
from pathlib import Path

from plex_training.dataset import build_dataset

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
import check_failure_gap_candidate as checker
import prepare_failure_gap_candidate as candidate


class FailureGapCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = candidate.records()

    def test_reviewed_source_files_match_canonical_pending_rows(self):
        report = checker.check()
        self.assertEqual(report["recordsChecked"], 234)
        self.assertEqual(report["approvalStatus"], "pending-owner-review")

    def test_repeating_a_javascript_function_name_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        first, second = [row for row in rows if row["language"] == "javascript"][:2]
        first_name = re.search(r"function (\w+)\(", first["solution"]).group(1)
        second_name = re.search(r"function (\w+)\(", second["solution"]).group(1)
        second["request"] = second["request"].replace(second_name, first_name)
        second["solution"] = second["solution"].replace(second_name, first_name)
        second["checks"][0]["name"] = first_name
        with self.assertRaisesRegex(ValueError, "Repeated or missing JS name"):
            candidate.validate(rows)

    def test_cross_split_group_move_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["candidateSplit"] = "validation" if rows[0]["candidateSplit"] == "train" else "train"
        with self.assertRaisesRegex(ValueError, "Whole-group split mismatch"):
            candidate.validate(rows)

    def test_pending_catalog_cannot_build_a_training_corpus(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dataset"
            with self.assertRaises(ValueError):
                build_dataset(candidate.OUTPUT / "dataset-sources.candidate.json", output,
                              validation_percent=30, seed=51, storage_limit_bytes=200 * 1024**3)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
