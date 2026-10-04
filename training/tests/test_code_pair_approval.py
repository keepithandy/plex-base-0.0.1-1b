"""Verify the approved corpus is exactly the reviewed local-use candidate."""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
spec = importlib.util.spec_from_file_location("pair_promotion", PHASE2 / "promote_code_pair_sources.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)


class CodePairApprovalTests(unittest.TestCase):
    def test_approval_binds_exact_candidate_and_local_scope(self):
        approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
        self.assertEqual(approval["candidateJsonlSha256"], hashlib.sha256(promotion.INPUT.read_bytes()).hexdigest())
        self.assertEqual(approval["approvalStatement"], "Approve the 36 examples for local training.")
        self.assertEqual(approval["scope"], "local-P2-training")
        self.assertFalse(approval["publicLicenseGranted"])

    def test_promoted_text_matches_review_and_notices_are_separate(self):
        preview = {p.relative_to(promotion.OUTPUT / "sources"): p.read_bytes()
                   for p in (promotion.OUTPUT / "sources").rglob("*.txt")}
        approved = {p.relative_to(promotion.APPROVED_OUTPUT / "sources"): p.read_bytes()
                    for p in (promotion.APPROVED_OUTPUT / "sources").rglob("*.txt")}
        self.assertEqual(len(approved), 36)
        self.assertEqual(approved, preview)
        catalog = json.loads((promotion.APPROVED_OUTPUT / "dataset-sources.approved.json").read_text(encoding="utf-8"))
        self.assertTrue(all(s["rightsReviewStatus"] == "approved" for s in catalog["sources"]))
        self.assertEqual(json.loads((promotion.APPROVED_OUTPUT / "approval.json").read_text(encoding="utf-8")),
                         json.loads(promotion.APPROVAL.read_text(encoding="utf-8")))

    def test_changed_candidate_digest_is_rejected_before_creating_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
            approval["candidateJsonlSha256"] = "0" * 64
            path = Path(directory) / "approval.json"
            path.write_text(json.dumps(approval), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact 36 records"):
                promotion.promote(promotion.APPROVED_OUTPUT, path)


if __name__ == "__main__":
    unittest.main()
