from __future__ import annotations

from pathlib import Path
import sys
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_selector_format_probe import build
from run_selector_format_experiment import _classify, validate_bounds


class P208SelectorFormatExperimentTests(unittest.TestCase):
    def test_run_bounds_are_capped(self) -> None:
        validate_bounds(100, 10.0)
        for steps, minutes in ((101, 1.0), (1, 10.01), (0, 1.0)):
            with self.assertRaises(ValueError):
                validate_bounds(steps, minutes)

    def test_score_categories_distinguish_wrong_value_and_extra_text(self) -> None:
        _, evaluation = build()
        actions = next(row for row in evaluation if row["value"] == ".actions")
        self.assertEqual(_classify(actions, "\n.actions", True), "exact_selector")
        self.assertEqual(_classify(actions, "\n.filters", True), "wrong_known_selector")
        self.assertEqual(_classify(actions, "\n.\n.actions", True),
                         "expected_selector_with_extra_text")
        self.assertEqual(_classify(actions, "\nactions", True), "other_or_no_eos")
        self.assertEqual(_classify(actions, "\n.actions", False), "other_or_no_eos")


if __name__ == "__main__":
    unittest.main()
