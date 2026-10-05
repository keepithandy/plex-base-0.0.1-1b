import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
from prepare_binding_candidate import build, prepare, validate


@unittest.skipUnless(shutil.which("node"), "Node syntax parser unavailable")
class BindingCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.approved = [json.loads(line) for line in
                        (PHASE2 / "drafts/p2-02-request-following-v3/candidate.jsonl").read_text().splitlines()]
        cls.dev = json.loads((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_text())
        cls.reserved = [r for r in json.loads(
            (PHASE2.parent / "artifacts/diagnostics/p2-transfer-v1/cases.json").read_text())["cases"]
                        if r["kind"] == "variation"]

    def test_build_preserves_sources_and_pending_training_status(self):
        original = copy.deepcopy(self.approved)
        train, evaluation = build(self.approved)
        validate(train, evaluation, self.approved, self.reserved, self.dev, shutil.which("node"))
        self.assertEqual(self.approved, original)
        self.assertEqual(len(train), 24)
        self.assertEqual(len(evaluation), 12)
        self.assertTrue(all(r["approvalStatus"] == "pending-owner-review" for r in train))
        self.assertTrue(all(r["use"] == "evaluation-only-never-train" for r in evaluation))

    def test_holdout_binding_in_training_request_is_rejected(self):
        train, evaluation = build(self.approved)
        train[1]["request"] += ' Do not use Riga.'
        with self.assertRaisesRegex(ValueError, "Reserved evaluation binding"):
            validate(train, evaluation, self.approved, self.reserved, self.dev, shutil.which("node"))

    def test_wrong_reference_binding_is_rejected(self):
        train, evaluation = build(self.approved)
        train[1]["solution"] = '<p><bdi>Wrong</bdi></p>'
        with self.assertRaisesRegex(ValueError, "Reference failed"):
            validate(train, evaluation, self.approved, self.reserved, self.dev, shutil.which("node"))

    def test_repeat_preparation_is_byte_identical_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = prepare(root / "first"), prepare(root / "second")
            self.assertEqual(first, second)
            for name in ("candidate.jsonl", "evaluation-only.jsonl", "review.json", "REVIEW.md"):
                self.assertEqual((root / "first" / name).read_bytes(), (root / "second" / name).read_bytes())
            self.assertEqual(first["referencesPassed"], 36)
            self.assertEqual(first["staleAnswersRejected"], 30)
            self.assertFalse(first["modelTrained"])
            with self.assertRaises(FileExistsError):
                prepare(root / "first")


if __name__ == "__main__":
    unittest.main()
