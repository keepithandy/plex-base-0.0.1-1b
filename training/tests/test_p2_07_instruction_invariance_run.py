from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_compositional_experiment import ARTIFACT_ROOT
from prepare_instruction_invariance_experiment import EXPECTED, prepare, verify_prepared
from run_instruction_invariance_experiment import _interpret, _score_record, validate_bounds


class P207InstructionInvarianceRunTests(unittest.TestCase):
    def test_exact_approved_inputs_prepare_and_verify(self) -> None:
        with TemporaryDirectory(prefix="p2-07-test-", dir=ARTIFACT_ROOT) as temp:
            prepared = Path(temp) / "prepared"
            plan = prepare(prepared)
            verified = verify_prepared(prepared)
            self.assertEqual(plan, verified)
            self.assertEqual(plan["candidateJsonlSha256"], EXPECTED["candidate"])
            self.assertEqual(plan["evaluationJsonlSha256"], EXPECTED["evaluation"])
            self.assertEqual(plan["trainingRecords"], 24)
            self.assertEqual(plan["evaluationOnlyRecords"], 6)
            self.assertFalse(plan["evaluationUsedForTraining"])
            self.assertFalse(plan["evaluationUsedForRuntimeValidationLoss"])
            self.assertFalse(plan["tokenizerRefitted"])
            self.assertFalse(plan["modelTrained"])
            self.assertFalse(plan["finalHoldoutOpened"])

    def test_verifier_rejects_tampered_heldout_file(self) -> None:
        with TemporaryDirectory(prefix="p2-07-test-", dir=ARTIFACT_ROOT) as temp:
            prepared = Path(temp) / "prepared"
            prepare(prepared)
            target = prepared / "evaluation-only/evaluation-only.jsonl"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "file changed"):
                verify_prepared(prepared)

    def test_bounds_are_exactly_limited(self) -> None:
        validate_bounds(100, 10.0)
        for steps, minutes in ((101, 10.0), (100, 10.01), (0, 1.0), (1, 0.0), (1, float("nan"))):
            with self.subTest(steps=steps, minutes=minutes), self.assertRaises(ValueError):
                validate_bounds(steps, minutes)

    def test_interpretation_requires_all_supplied_examples(self) -> None:
        evaluation = {"representationPass": 6}
        self.assertEqual(_interpret({"representationPass": 23}, evaluation),
                         "inconclusive-instruction-invariance: supplied paraphrase matrix did not fully converge")
        for score, diagnosis in (
            (6, "instruction-invariance-demonstrated-within-single-copy-probe"),
            (5, "partial-instruction-invariance-within-single-copy-probe"),
            (3, "limited-instruction-invariance-within-single-copy-probe"),
            (0, "no-heldout-paraphrase-transfer-after-supplied-convergence"),
        ):
            with self.subTest(score=score):
                self.assertEqual(_interpret({"representationPass": 24}, {"representationPass": score}), diagnosis)

    def test_record_score_preserves_exact_eos_and_binding_metrics(self) -> None:
        row = {
            "operationFamily": "gap-copy",
            "value": "14px",
            "solution": "14px",
        }
        metrics = _score_record(row, "\n14px", True, {"\n14px", "\n6px"})
        self.assertTrue(metrics["exact"])
        self.assertTrue(metrics["representationPass"])
        self.assertTrue(metrics["bindingPass"])
        self.assertTrue(metrics["eos"])
        self.assertTrue(metrics["gapCopyPass"])
        self.assertFalse(metrics["selectorCopyPass"])
        self.assertTrue(metrics["replayedTrainingSolution"])
        bad = _score_record(row, "\n6px", True, {"\n14px", "\n6px"})
        self.assertFalse(bad["representationPass"])
        self.assertFalse(bad["bindingPass"])


if __name__ == "__main__":
    unittest.main()
