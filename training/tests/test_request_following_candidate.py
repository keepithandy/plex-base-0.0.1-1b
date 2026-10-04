"""Guard against renamed-template leakage and accidental use of pending data."""
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
spec = importlib.util.spec_from_file_location("request_candidate", PHASE2 / "prepare_request_following_candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class RequestFollowingCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = candidate.records()
        cls.tasks = json.loads(candidate.DEV.read_text(encoding="utf-8"))

    def test_renamed_numeric_templates_cannot_have_separate_split_groups(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            if row["templateLineage"].startswith("javascript/bound/"):
                row["splitGroupId"] = "javascript-bound"
        with self.assertRaisesRegex(ValueError, "template crosses split groups"):
            candidate.validate(rows, self.tasks)

    def test_incorrect_css_answer_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        row = next(row for row in rows if row["language"] == "css")
        row["solution"] = row["solution"].replace("2px", "9px")
        with self.assertRaisesRegex(ValueError, "Static checks failed"):
            candidate.validate(rows, self.tasks)

    def test_pending_catalog_cannot_build_training_data(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_dataset(candidate.OUTPUT / "dataset-sources.candidate.json", Path(directory) / "dataset",
                              validation_percent=30, seed=51, storage_limit_bytes=200 * 1024**3)
            self.assertFalse((Path(directory) / "dataset").exists())

    def test_exact_approved_samples_are_preserved_and_unseen_data_is_not_approved(self):
        approval = json.loads((PHASE2 / "approvals/p2-02-expansion-samples-v1.json").read_text(encoding="utf-8"))
        raw = (PHASE2 / "drafts/p2-02-expansion-samples-v1.json").read_bytes()
        self.assertEqual(approval["candidateJsonSha256"], candidate.hashlib.sha256(raw).hexdigest())
        self.assertEqual(approval["records"], 12)
        self.assertFalse(approval["unseenExpandedCorpusApproved"])
        self.assertTrue(all(row["approvalStatus"] == "pending-owner-review" for row in self.rows))


if __name__ == "__main__":
    unittest.main()
