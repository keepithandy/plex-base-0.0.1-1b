"""Check exact approval binding and promoted source bytes."""
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PHASE2 = Path(__file__).resolve().parents[1] / "phase2"
sys.path.insert(0, str(PHASE2))
spec = importlib.util.spec_from_file_location("curated_promotion", PHASE2 / "promote_curated_request_sources.py")
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)


class CuratedApprovalTests(unittest.TestCase):
    def test_approval_is_for_this_exact_local_use_version(self):
        approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
        digest = hashlib.sha256((promotion.candidate.OUTPUT / "candidate.jsonl").read_bytes()).hexdigest()
        self.assertEqual(approval["candidateJsonlSha256"], digest)
        self.assertEqual(approval["scope"], "local-P2-training")
        self.assertEqual(approval["records"], 180)
        self.assertFalse(approval["publicLicenseGranted"])

    def test_all_approved_texts_match_the_reviewed_snapshot(self):
        draft = {p.relative_to(promotion.candidate.OUTPUT / "sources"): p.read_bytes()
                 for p in (promotion.candidate.OUTPUT / "sources").rglob("*.txt")}
        approved = {p.relative_to(promotion.OUTPUT / "sources"): p.read_bytes()
                    for p in (promotion.OUTPUT / "sources").rglob("*.txt")}
        self.assertEqual(len(approved), 180)
        self.assertEqual(approved, draft)
        catalog = json.loads((promotion.OUTPUT / "dataset-sources.approved.json").read_text(encoding="utf-8"))
        self.assertTrue(all(s["rightsReviewStatus"] == "approved" for s in catalog["sources"]))

    def test_wrong_digest_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            approval = json.loads(promotion.APPROVAL.read_text(encoding="utf-8"))
            approval["candidateJsonlSha256"] = "0" * 64
            path = Path(directory) / "approval.json"
            path.write_text(json.dumps(approval), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact 180 records"):
                promotion.promote(promotion.OUTPUT, path)


if __name__ == "__main__":
    unittest.main()
