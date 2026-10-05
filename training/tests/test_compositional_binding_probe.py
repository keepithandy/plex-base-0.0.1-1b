import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2"))

from inspect_answer_focused_failure import inspect
from prepare_compositional_binding_candidate import SUPPORTED, build, validate


class CompositionalBindingProbeTests(unittest.TestCase):
    def test_each_supported_probe_holds_out_only_unseen_recombinations(self):
        for source_id in SUPPORTED:
            with self.subTest(source_id=source_id):
                train, evaluation, design = build(source_id)
                self.assertEqual(len(train), 6)
                self.assertEqual(len(evaluation), 3)
                train_pairs = {tuple(sorted(row["bindings"].items())) for row in train}
                eval_pairs = {tuple(sorted(row["bindings"].items())) for row in evaluation}
                self.assertTrue(train_pairs.isdisjoint(eval_pairs))
                for slot, values in ((design["slotA"], design["slotAValues"]),
                                     (design["slotB"], design["slotBValues"])):
                    for value in values:
                        self.assertGreaterEqual(sum(row["bindings"][slot] == value for row in train), 2)
                        self.assertEqual(sum(row["bindings"][slot] == value for row in evaluation), 1)

    def test_failure_inspector_returns_exact_single_failed_source(self):
        candidate_rows = [
            {"id": "a", "sourceId": "gap-css-layout-01", "language": "css",
             "request": "a request", "solution": ".a { gap: 6px; }"},
            {"id": "b", "sourceId": "gap-css-layout-01", "language": "css",
             "request": "b request", "solution": ".b { gap: 14px; }"},
        ]
        score = {
            "records": [
                {"id": "a", "kind": "candidate-new", "completion": candidate_rows[0]["solution"],
                 "exact": True, "bindingPass": True, "staticPass": True, "syntaxPass": True},
                {"id": "b", "kind": "candidate-new", "completion": ".b { gap: 28px; }",
                 "exact": False, "bindingPass": False, "staticPass": False, "syntaxPass": True,
                 "oldBindingPresent": 1, "repeatedOriginalReference": 0},
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            candidate.write_text("".join(json.dumps(row) + "\n" for row in candidate_rows), encoding="utf-8")
            score_path = root / "score.json"
            score_path.write_text(json.dumps(score), encoding="utf-8")
            result = inspect(score_path, candidate)
        self.assertTrue(result["singleFailure"])
        self.assertEqual(result["candidateFailures"], 1)
        self.assertEqual(result["recommendedSourceId"], "gap-css-layout-01")
        self.assertEqual(result["failures"][0]["id"], "b")


if __name__ == "__main__":
    unittest.main()
