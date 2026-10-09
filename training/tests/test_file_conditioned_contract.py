"""Contract, identity, preservation, and read-only boundary regressions for P3-01."""

from __future__ import annotations

import json
import hashlib
import shutil
import uuid
import unittest
from pathlib import Path

from plex_training.file_conditioned_contract import (
    EXPECTED_TOKENIZER_SHA256,
    PROMPT_TEMPLATE,
    _canonical_bytes,
    _validate_rows,
    build_candidate_rows,
    generate_file_edit_candidate,
    review_file_edit_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "training/pretraining/p3-01-file-request-contract.json"
BUNDLE = ROOT / "training/artifacts/request-grounded/p2-48-training-bundle"


class FileConditionedContractTests(unittest.TestCase):
    def test_fixture_set_is_balanced_strict_and_deterministic(self) -> None:
        rows = build_candidate_rows()
        self.assertEqual(_canonical_bytes(rows), _canonical_bytes(build_candidate_rows()))
        self.assertEqual(_validate_rows(rows), {
            "fixtures": 18, "perLanguage": {"css": 6, "html": 6, "javascript": 6}
        })
        self.assertEqual(len({row["id"] for row in rows}), 18)
        self.assertEqual(len({row["request"] for row in rows}), 18)

    def test_prompt_and_raw_target_contract(self) -> None:
        row = build_candidate_rows()[0]
        prompt = PROMPT_TEMPLATE.format(language=row["language"], request=row["request"], input_file=row["inputFile"])
        self.assertEqual(prompt, "Edit the supplied file to satisfy the request.\nLanguage: html\nRequest: Change the button text to Save Changes.\nFile:\n<button>Apply</button>\nEdited file:")
        self.assertEqual(row["expectedFile"], "<button>Store</button>")
        self.assertNotIn("```", row["expectedFile"])
        self.assertFalse(row["expectedFile"].startswith("{"))

    def test_preservation_rejects_unrelated_expected_edit(self) -> None:
        rows = build_candidate_rows()
        rows[0]["inputFile"] = '<button class="primary">Submit</button>'
        rows[0]["expectedFile"] = '<button>Save</button>'
        with self.assertRaisesRegex(ValueError, "preserve all text"):
            _validate_rows(rows)

    def test_malformed_fixture_fields_fail_closed(self) -> None:
        rows = build_candidate_rows()
        rows[0]["repositoryPath"] = "secret/path"
        with self.assertRaisesRegex(ValueError, "fields are invalid"):
            _validate_rows(rows)

    def test_generation_identity_is_deterministic(self) -> None:
        root = Path(".test-tmp") / str(uuid.uuid4())
        root.mkdir(parents=True)
        try:
            candidate, draft = root / "candidate.jsonl", root / "review.json"
            first = generate_file_edit_candidate(candidate_path=candidate, review_path=draft)
            second = generate_file_edit_candidate(candidate_path=candidate, review_path=draft)
            self.assertEqual(first, second)
            self.assertEqual(first["candidateSha256"], hashlib.sha256(candidate.read_bytes()).hexdigest())
            self.assertEqual(first["byteCount"], len(candidate.read_bytes()))
            self.assertFalse(json.loads(CONTRACT.read_text(encoding="utf-8"))["modelTrainingAuthorized"])
            self.assertEqual(json.loads(CONTRACT.read_text(encoding="utf-8"))["researchOptimizerUpdates"], 0)
            self.assertFalse(json.loads(CONTRACT.read_text(encoding="utf-8"))["finalHoldoutOpened"])
        finally:
            shutil.rmtree(root)

    def test_review_fails_closed_when_bundle_is_inaccessible(self) -> None:
        root = Path(".test-tmp") / str(uuid.uuid4())
        root.mkdir(parents=True)
        try:
            candidate, draft = root / "candidate.jsonl", root / "review.json"
            generate_file_edit_candidate(candidate_path=candidate, review_path=draft)
            with self.assertRaisesRegex(ValueError, "inaccessible|tokenizer bundle"):
                review_file_edit_candidate(candidate_path=candidate, review_path=draft,
                    contract_path=CONTRACT, tokenizer_bundle=BUNDLE)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
