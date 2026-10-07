"""Portable tests for P2-32 structured-plan curriculum preparation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.structured_plan import canonical_text_sha256
from plex_training.structured_plan_curriculum import review_structured_plan_curriculum


ROOT = Path(__file__).parents[2]
CANDIDATE = ROOT / "phase2" / "drafts" / "p2-32-structured-plan-candidate-v1.jsonl"
REVIEW = ROOT / "phase2" / "drafts" / "p2-32-structured-plan-candidate-v1.review.json"
DEV = ROOT / "phase2" / "evaluation" / "p2-31-plan-dev-v1.json"
CONTRACT = ROOT / "pretraining" / "p2-32-structured-plan-preparation-contract.json"


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_variant(root: Path, rows: list[dict]) -> tuple[Path, Path, Path, Path, str]:
    candidate = root / "candidate.jsonl"
    candidate.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
                         encoding="utf-8", newline="\n")
    sha = canonical_text_sha256(candidate.read_bytes())

    review_value = json.loads(REVIEW.read_text(encoding="utf-8"))
    review_value["candidateSha256"] = sha
    review = root / "review.json"
    review.write_text(json.dumps(review_value), encoding="utf-8")

    contract_value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract_value["curriculum"]["candidateSha256"] = sha
    contract = root / "contract.json"
    contract.write_text(json.dumps(contract_value), encoding="utf-8")

    dev = root / "dev.json"
    dev.write_bytes(DEV.read_bytes())
    return candidate, review, dev, contract, sha


class P232CurriculumTests(unittest.TestCase):
    def test_shipped_candidate_passes_static_review(self) -> None:
        report = review_structured_plan_curriculum(
            candidate_path=CANDIDATE,
            review_path=REVIEW,
            development_task_set_path=DEV,
            contract_path=CONTRACT,
        )
        self.assertEqual(
            report["candidateSha256"],
            "608cf988b96e8578fa2c7948a12e298c4ed25c640098a2bf3710f3b3cc6802d3",
        )
        self.assertEqual(report["records"], 96)
        self.assertEqual(report["trainRecords"], 72)
        self.assertEqual(report["validationRecords"], 24)
        self.assertEqual(report["groups"], 24)
        self.assertEqual(report["trainGroups"], 18)
        self.assertEqual(report["validationGroups"], 6)
        self.assertEqual(report["solutionsSchemaValid"], 96)
        self.assertEqual(report["developmentTargetRoleOverlap"], 0)
        self.assertEqual(report["developmentExactRequestOverlap"], 0)
        self.assertFalse(report["tokenizerPreflight"]["checked"])
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])

    def test_candidate_has_expected_language_balance_and_group_levels(self) -> None:
        rows = _rows(CANDIDATE)
        counts = {}
        groups = {}
        for row in rows:
            counts[(row["candidateSplit"], row["language"])] = (
                counts.get((row["candidateSplit"], row["language"]), 0) + 1
            )
            groups.setdefault(row["splitGroupId"], []).append(row)
        self.assertEqual(counts, {
            ("train", "html"): 24,
            ("validation", "html"): 8,
            ("train", "css"): 24,
            ("validation", "css"): 8,
            ("train", "javascript"): 24,
            ("validation", "javascript"): 8,
        })
        self.assertEqual(len(groups), 24)
        for entries in groups.values():
            self.assertEqual(len(entries), 4)
            self.assertEqual(
                {level: sum(row["level"] == level for row in entries) for level in ("A", "B", "C")},
                {"A": 1, "B": 1, "C": 2},
            )
            self.assertEqual(len({row["candidateSplit"] for row in entries}), 1)

    def test_review_rejects_semantic_group_crossing_splits(self) -> None:
        rows = _rows(CANDIDATE)
        group = rows[0]["splitGroupId"]
        changed = False
        for row in rows:
            if row["splitGroupId"] == group and row["level"] == "C" and not changed:
                row["candidateSplit"] = "validation"
                changed = True
        with tempfile.TemporaryDirectory() as temporary:
            candidate, review, dev, contract, sha = _write_variant(Path(temporary), rows)
            with patch(
                "plex_training.structured_plan_curriculum.EXPECTED_CANDIDATE_SHA256", sha
            ), self.assertRaisesRegex(ValueError, "split/language counts|may not cross"):
                review_structured_plan_curriculum(
                    candidate_path=candidate,
                    review_path=review,
                    development_task_set_path=dev,
                    contract_path=contract,
                )

    def test_review_rejects_p231_target_role_leakage(self) -> None:
        rows = _rows(CANDIDATE)
        group = rows[0]["splitGroupId"]
        for row in rows:
            if row["splitGroupId"] == group:
                row["targetRole"] = "primary-navigation"
                plan = json.loads(row["solution"])
                plan["targetRole"] = "primary-navigation"
                row["solution"] = json.dumps(plan, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as temporary:
            candidate, review, dev, contract, sha = _write_variant(Path(temporary), rows)
            with patch(
                "plex_training.structured_plan_curriculum.EXPECTED_CANDIDATE_SHA256", sha
            ), self.assertRaisesRegex(ValueError, "overlaps P2-31"):
                review_structured_plan_curriculum(
                    candidate_path=candidate,
                    review_path=review,
                    development_task_set_path=dev,
                    contract_path=contract,
                )

    def test_review_rejects_invalid_solution_schema(self) -> None:
        rows = _rows(CANDIDATE)
        plan = json.loads(rows[0]["solution"])
        plan["filePath"] = "index.html"
        rows[0]["solution"] = json.dumps(plan, separators=(",", ":"))
        with tempfile.TemporaryDirectory() as temporary:
            candidate, review, dev, contract, sha = _write_variant(Path(temporary), rows)
            with patch(
                "plex_training.structured_plan_curriculum.EXPECTED_CANDIDATE_SHA256", sha
            ), self.assertRaisesRegex(ValueError, "fields"):
                review_structured_plan_curriculum(
                    candidate_path=candidate,
                    review_path=review,
                    development_task_set_path=dev,
                    contract_path=contract,
                )

    def test_optional_tokenizer_preflight_uses_frozen_identity_and_context(self) -> None:
        class FakeTokenizer:
            vocabulary_size = 16384

            def __init__(self):
                self.last_text = None
                self.last_ids = None

            def encode(self, text):
                self.last_text = text
                count = max(1, len(text.encode("utf-8")) // 16)
                self.last_ids = list(range(10, 10 + count))
                return self.last_ids

            def decode(self, ids):
                return self.last_text if list(ids) == self.last_ids else ""

        fake = FakeTokenizer()
        record = {
            "tokenizerSha256":
                "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
            "bundleManifestSha256":
                "7753b1518b737e7f6b8e0b64f4f829b027ed3aad5b33a7613b3715481448eec5",
            "actualVocabularySize": 16384,
        }
        with patch(
            "plex_training.structured_plan_curriculum._completion_tokenizer",
            return_value=(fake, record),
        ):
            report = review_structured_plan_curriculum(
                candidate_path=CANDIDATE,
                review_path=REVIEW,
                development_task_set_path=DEV,
                contract_path=CONTRACT,
                bundle_dir=Path("synthetic-tokenizer"),
            )
        self.assertTrue(report["tokenizerPreflight"]["checked"])
        self.assertEqual(report["tokenizerPreflight"]["tokenizerSha256"], record["tokenizerSha256"])
        self.assertGreater(report["tokenizerPreflight"]["trainTokenCount"], 0)
        self.assertGreater(report["tokenizerPreflight"]["validationTokenCount"], 0)
        self.assertLessEqual(report["tokenizerPreflight"]["maximumRecordTokensIncludingEos"], 513)


if __name__ == "__main__":
    unittest.main()
