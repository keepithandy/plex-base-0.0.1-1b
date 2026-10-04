"""Check candidate provenance, grouping, contracts, and pipeline integration."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from plex_training.dataset import build_dataset

MODULE_PATH = Path(__file__).resolve().parents[1] / "phase2" / "prepare_code_pair_candidate.py"
spec = importlib.util.spec_from_file_location("code_pair_candidate", MODULE_PATH)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


@unittest.skipUnless(shutil.which("node"), "Node syntax checking is required for authored solutions")
class CodePairCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = candidate.load_records()
        cls.tasks = json.loads(candidate.DEV_SET.read_text(encoding="utf-8"))
        cls.report = candidate.validate_records(cls.rows, cls.tasks)
        cls.report["candidateJsonlSha256"] = candidate._digest(candidate.INPUT.read_bytes())
        cls.report["developmentTaskSetSha256"] = candidate._digest(candidate.DEV_SET.read_bytes())

    def test_all_solutions_and_balanced_group_splits_are_checked(self):
        self.assertEqual(self.report["staticSolutionsPassed"], 36)
        self.assertEqual(self.report["staticChecksPassed"], self.report["staticChecksTotal"])
        self.assertEqual(self.report["recordsBySplit"], {"train": 24, "validation": 12})
        self.assertEqual(set(self.report["recordsBySplitAndLanguage"].values()), {8, 4})
        self.assertFalse(self.report["javascriptBehaviorExecuted"])
        self.assertFalse(self.report["finalHoldoutOpened"])
        groups = {}
        for row in self.rows:
            groups.setdefault(row["splitGroupId"], set()).add(row["candidateSplit"])
        self.assertTrue(all(len(splits) == 1 for splits in groups.values()))

    def test_development_request_copy_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        row = next(row for row in rows if row["language"] == "html")
        row["request"] = next(task["request"] for task in self.tasks["tasks"] if task["language"] == "html")
        with self.assertRaisesRegex(ValueError, "duplicates"):
            candidate.validate_records(rows, self.tasks)

    def test_final_holdout_is_rejected_without_evaluating_it(self):
        task_set = copy.deepcopy(self.tasks)
        task_set["kind"] = "final"
        with self.assertRaisesRegex(ValueError, "must not open a final"):
            candidate.validate_records(self.rows, task_set)

    def test_previous_supplement_requests_are_not_reused(self):
        previous = candidate.PHASE2 / "drafts" / "p2-02-authored-examples-v1.jsonl"
        previous_requests = {candidate._normalized(json.loads(line)["request"])
                             for line in previous.read_text(encoding="utf-8").splitlines()}
        self.assertFalse(previous_requests & {candidate._normalized(row["request"]) for row in self.rows})

    def test_checked_in_preview_matches_current_records(self):
        preview = candidate.OUTPUT
        expected = {candidate.source_text(row, self.tasks["outputContracts"]) for row in self.rows}
        self.assertEqual({p.read_text(encoding="utf-8") for p in (preview / "sources").rglob("*.txt")}, expected)
        self.assertEqual(json.loads((preview / "review.json").read_text(encoding="utf-8")), self.report)
        catalog = json.loads((preview / "dataset-sources.candidate.json").read_text(encoding="utf-8"))
        self.assertTrue(all(source["rightsReviewStatus"] == candidate.PENDING
                            and source["revision"] == self.report["candidateJsonlSha256"]
                            for source in catalog["sources"]))

    def test_valid_css_with_wrong_required_value_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        row = next(row for row in rows if row["language"] == "css")
        row["solution"] = 'input[type="radio"] { accent-color: red; }'
        with self.assertRaisesRegex(ValueError, "Static solution review failed"):
            candidate.validate_records(rows, self.tasks)

    def test_variant_cannot_move_to_other_split(self):
        rows = copy.deepcopy(self.rows)
        rows[-1]["candidateSplit"] = "train" if rows[-1]["candidateSplit"] == "validation" else "validation"
        with self.assertRaisesRegex(ValueError, "split disagrees"):
            candidate.validate_records(rows, self.tasks)

    def test_draft_cannot_claim_owner_approval(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["approvalStatus"] = "approved"
        with self.assertRaisesRegex(ValueError, "pending owner review"):
            candidate.validate_records(rows, self.tasks)

    def test_sources_reproduce_and_pending_catalog_blocks_dataset_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b = root / "a", root / "b"
            candidate.prepare(self.rows, self.tasks, self.report, a)
            candidate.prepare(self.rows, self.tasks, self.report, b)
            files_a = {p.relative_to(a): p.read_bytes() for p in a.rglob("*") if p.is_file()}
            files_b = {p.relative_to(b): p.read_bytes() for p in b.rglob("*") if p.is_file()}
            self.assertEqual(files_a, files_b)
            sources = list((a / "sources").rglob("*.txt"))
            self.assertEqual(len(sources), 36)
            expected = {candidate.source_text(row, self.tasks["outputContracts"]) for row in self.rows}
            self.assertEqual({p.read_text(encoding="utf-8") for p in sources}, expected)
            self.assertTrue(all("```" not in text and "<|eos|>" not in text for text in expected))
            with self.assertRaisesRegex(ValueError, "not approved"):
                build_dataset(a / "dataset-sources.candidate.json", root / "blocked", validation_percent=30, seed=51,
                              storage_limit_bytes=200 * 1024**3)
            self.assertFalse((root / "blocked").exists())
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                candidate.prepare(self.rows, self.tasks, self.report, a)


if __name__ == "__main__":
    unittest.main()
