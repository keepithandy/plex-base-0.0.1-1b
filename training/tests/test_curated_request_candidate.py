"""Exercise failures that the earlier loose supplied-answer checks missed."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from plex_training.dataset import build_dataset

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
spec = importlib.util.spec_from_file_location("curated_candidate", PHASE2 / "prepare_curated_request_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class CuratedCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = candidate.records()
        cls.tasks = json.loads(candidate.original.DEV.read_text(encoding="utf-8"))

    def test_required_tags_in_wrong_tree_are_rejected(self):
        rows = copy.deepcopy(self.rows)
        row = rows[0]
        row["solution"] = "<ruby>Kyoto</ruby><rt>Kyo-to</rt>"
        with self.assertRaisesRegex(ValueError, "HTML nesting"):
            candidate.validate(rows, self.tasks)

    def test_unrequested_css_declaration_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if r["language"] == "css")
        row["solution"] = row["solution"].replace("\n}", "\n  opacity: 0.5;\n}")
        with self.assertRaisesRegex(ValueError, "Extra or missing CSS"):
            candidate.validate(rows, self.tasks)

    def test_value_only_variant_is_not_a_new_structure(self):
        rows = copy.deepcopy(self.rows)
        first, second = [r for r in rows if r["language"] == "css"][:2]
        second["solution"] = first["solution"].replace("2px", "3px")
        with self.assertRaisesRegex(ValueError, "structural duplicate"):
            candidate.validate(rows, self.tasks)

    def test_template_relative_cannot_move_to_another_split(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["candidateSplit"] = "validation" if rows[0]["candidateSplit"] == "train" else "train"
        with self.assertRaisesRegex(ValueError, "Wrong whole-group split"):
            candidate.validate(rows, self.tasks)

    def test_pending_curated_catalog_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dataset"
            with self.assertRaises(ValueError):
                build_dataset(candidate.OUTPUT / "dataset-sources.candidate.json", output,
                              validation_percent=30, seed=51, storage_limit_bytes=200 * 1024**3)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
