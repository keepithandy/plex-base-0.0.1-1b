"""Bind local v3 approval to the exact reviewed source bytes."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
import promote_failure_gap_sources as promotion


class FailureGapApprovalTests(unittest.TestCase):
    def test_approval_matches_reviewed_local_use_snapshot(self):
        approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
        digest = hashlib.sha256((promotion.candidate.OUTPUT / "candidate.jsonl").read_bytes()).hexdigest()
        self.assertEqual(approval["candidateJsonlSha256"], digest)
        self.assertEqual(approval["records"], 234)
        self.assertEqual(approval["scope"], "local-P2-training")
        self.assertFalse(approval["publicLicenseGranted"])

    def test_promoted_texts_match_the_review_copy(self):
        draft = {path.relative_to(promotion.candidate.OUTPUT / "sources"): path.read_bytes()
                 for path in (promotion.candidate.OUTPUT / "sources").rglob("*.txt")}
        approved = {path.relative_to(promotion.OUTPUT / "sources"): path.read_bytes()
                    for path in (promotion.OUTPUT / "sources").rglob("*.txt")}
        self.assertEqual(len(approved), 234)
        self.assertEqual(approved, draft)
        catalog = json.loads((promotion.OUTPUT / "dataset-sources.approved.json").read_text(encoding="utf-8"))
        self.assertTrue(all(source["rightsReviewStatus"] == "approved" for source in catalog["sources"]))

    def test_wrong_digest_is_rejected_before_promotion(self):
        with tempfile.TemporaryDirectory() as temporary:
            approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
            approval["candidateJsonlSha256"] = "0" * 64
            path = Path(temporary) / "approval.json"
            path.write_text(json.dumps(approval), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact 234 records"):
                promotion.promote(promotion.OUTPUT, path)


if __name__ == "__main__":
    unittest.main()
