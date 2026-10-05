import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
from diagnose_transfer import build_cases, check_completion, run


class TransferDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in
                    (PHASE2 / "drafts/p2-02-request-following-v3/candidate.jsonl").read_text().splitlines()]

    def test_cases_are_balanced_unique_and_leave_source_untouched(self):
        before = copy.deepcopy(self.rows)
        cases = build_cases(self.rows)
        self.assertEqual(self.rows, before)
        self.assertEqual(len(cases), 18)
        self.assertEqual(len({row["request"] for row in cases}), 18)
        for language in ("html", "css", "javascript"):
            selected = [r for r in cases if r["language"] == language]
            self.assertEqual(sum(r["kind"] == "original" for r in selected), 2)
            self.assertEqual(sum(r["kind"] == "variation" for r in selected), 4)

    @unittest.skipUnless(shutil.which("node"), "Node syntax parser unavailable")
    def test_references_pass_but_stale_answers_and_missing_eos_fail(self):
        node = shutil.which("node")
        for case in build_cases(self.rows):
            with self.subTest(case=case["id"]):
                result = check_completion(case, "\n" + case["solution"], True, node)
                self.assertTrue(result["exact"])
                self.assertTrue(result["staticPass"])
                self.assertFalse(check_completion(case, "\n" + case["solution"], False, node)["staticPass"])
                if case["kind"] == "variation":
                    stale = check_completion(case, "\n" + case["originalSolution"], True, node)
                    self.assertFalse(stale["bindingPass"])
                    self.assertFalse(stale["staticPass"])
                    self.assertTrue(stale["repeatedOriginalReference"])

    def test_validation_sources_and_noop_variations_are_rejected(self):
        for change in ("split", "request"):
            rows = copy.deepcopy(self.rows)
            row = next(r for r in rows if r["id"] == "gap-html-bidi-02")
            if change == "split":
                row["candidateSplit"] = "validation"
            else:
                row["request"] = "No replaceable detail"
            with self.assertRaises(ValueError):
                build_cases(rows)

    def test_existing_output_rejected_before_model_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                run(Path(directory), "cpu")

    @unittest.skipUnless(shutil.which("node"), "Node syntax parser unavailable")
    def test_preparation_saves_evaluation_only_cases_without_torch(self):
        from unittest.mock import patch
        import builtins
        original_import = builtins.__import__

        def reject_torch(name, *args, **kwargs):
            if name == "torch" or name.startswith("torch."):
                raise AssertionError("Preparation must not import torch")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch("builtins.__import__", side_effect=reject_torch):
            result = run(Path(directory) / "prepared", "cpu", prepare_only=True)
            self.assertEqual(result["referencesPassed"], 18)
            self.assertEqual(result["staleAnswersRejected"], 12)
            self.assertFalse(result["checkpointEvaluationRun"])
            plan = json.loads(Path(result["cases"]).read_text())
            self.assertEqual(plan["use"], "evaluation-only-never-train")


if __name__ == "__main__":
    unittest.main()
