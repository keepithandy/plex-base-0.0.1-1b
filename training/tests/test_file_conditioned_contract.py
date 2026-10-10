"""Contract, identity, preservation, and read-only boundary regressions for P3-01."""

from __future__ import annotations

import json
import os
import hashlib
import shutil
import tempfile
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

from plex_training.cli import main, build_parser

from plex_training.file_conditioned_contract import (
    EXPECTED_TOKENIZER_SHA256,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_CANDIDATE_BYTES,
    _contract,
    score_file_edit,
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
        self.assertEqual(row["expectedFile"], "<button>Save Changes</button>")
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
            self.assertEqual(first["candidateSha256"], EXPECTED_CANDIDATE_SHA256)
            self.assertEqual(first["byteCount"], EXPECTED_CANDIDATE_BYTES)
            self.assertEqual(candidate.read_bytes(), (ROOT / "training/phase3/drafts/p3-01-file-edit-contract-v1.jsonl").read_bytes())
            self.assertEqual(first["candidateSha256"], hashlib.sha256(candidate.read_bytes()).hexdigest())
            self.assertEqual(first["byteCount"], len(candidate.read_bytes()))
            self.assertFalse(json.loads(CONTRACT.read_text(encoding="utf-8"))["modelTrainingAuthorized"])
            self.assertEqual(json.loads(CONTRACT.read_text(encoding="utf-8"))["researchOptimizerUpdates"], 0)
            self.assertFalse(json.loads(CONTRACT.read_text(encoding="utf-8"))["finalHoldoutOpened"])
        finally:
            shutil.rmtree(root)

    def test_generation_second_stage_failure_preserves_existing_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            candidate.write_bytes(b"old-candidate")
            review.write_bytes(b"old-review")
            real_stage = __import__(
                "plex_training.file_conditioned_contract",
                fromlist=["_write_staged_p3_file"],
            )._write_staged_p3_file
            review_stage = review.with_name(review.name + ".p3tmp")

            def fail_second_stage(path, data):
                if path == review_stage:
                    raise OSError("synthetic second-stage failure")
                return real_stage(path, data)

            with patch(
                "plex_training.file_conditioned_contract._write_staged_p3_file",
                side_effect=fail_second_stage,
            ):
                with self.assertRaisesRegex(OSError, "second-stage failure"):
                    generate_file_edit_candidate(
                        candidate_path=candidate,
                        review_path=review,
                        contract_path=CONTRACT,
                    )

            self.assertEqual(candidate.read_bytes(), b"old-candidate")
            self.assertEqual(review.read_bytes(), b"old-review")
            for suffix in (".p3tmp", ".p3bak", ".p3txn"):
                self.assertFalse(candidate.with_name(candidate.name + suffix).exists())
            self.assertFalse(review_stage.exists())

    def test_generation_second_publish_failure_rolls_back_existing_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            candidate.write_bytes(b"old-candidate")
            review.write_bytes(b"old-review")
            review_stage = review.with_name(review.name + ".p3tmp")
            real_replace = os.replace

            def fail_review_publish(source, destination):
                if Path(source) == review_stage and Path(destination) == review:
                    raise OSError("synthetic second-publish failure")
                return real_replace(source, destination)

            with patch(
                "plex_training.file_conditioned_contract.os.replace",
                side_effect=fail_review_publish,
            ):
                with self.assertRaisesRegex(OSError, "second-publish failure"):
                    generate_file_edit_candidate(
                        candidate_path=candidate,
                        review_path=review,
                        contract_path=CONTRACT,
                    )

            self.assertEqual(candidate.read_bytes(), b"old-candidate")
            self.assertEqual(review.read_bytes(), b"old-review")
            for path in (
                candidate.with_name(candidate.name + ".p3tmp"),
                review_stage,
                candidate.with_name(candidate.name + ".p3bak"),
                candidate.with_name(candidate.name + ".p3txn"),
            ):
                self.assertFalse(path.exists())

    def test_generation_rollback_failure_leaves_explicit_recovery_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            candidate.write_bytes(b"old-candidate")
            review.write_bytes(b"old-review")
            review_stage = review.with_name(review.name + ".p3tmp")
            backup = candidate.with_name(candidate.name + ".p3bak")
            marker = candidate.with_name(candidate.name + ".p3txn")
            real_replace = os.replace

            def fail_publish_and_rollback(source, destination):
                source, destination = Path(source), Path(destination)
                if source == review_stage and destination == review:
                    raise OSError("synthetic second-publish failure")
                if source == backup and destination == candidate:
                    raise OSError("synthetic rollback failure")
                return real_replace(source, destination)

            with patch(
                "plex_training.file_conditioned_contract.os.replace",
                side_effect=fail_publish_and_rollback,
            ):
                with self.assertRaisesRegex(RuntimeError, "recovery marker remains"):
                    generate_file_edit_candidate(
                        candidate_path=candidate,
                        review_path=review,
                        contract_path=CONTRACT,
                    )

            self.assertTrue(marker.is_file())
            marker_value = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(marker_value["kind"], "plex-p3-paired-publication-v1")
            self.assertEqual(marker_value["candidate"], str(candidate.resolve()))
            self.assertEqual(marker_value["review"], str(review.resolve()))
            self.assertTrue(marker_value["candidateExisted"])
            self.assertTrue(backup.is_file())
            self.assertEqual(backup.read_bytes(), b"old-candidate")
            self.assertEqual(review.read_bytes(), b"old-review")

    def test_generation_interruptions_restore_both_outputs(self) -> None:
        # Exercise syscall failure and successful replacement followed immediately
        # by interruption, with all combinations of pre-existing output files.
        for candidate_exists in (False, True):
            for review_exists in (False, True):
                for target in ("candidate.jsonl", "review.json"):
                    for after_replace in (False, True):
                        with self.subTest(candidate_exists=candidate_exists,
                                          review_exists=review_exists,
                                          target=target, after_replace=after_replace):
                            with tempfile.TemporaryDirectory() as temporary:
                                root = Path(temporary)
                                candidate = root / "candidate.jsonl"
                                review = root / "review.json"
                                if candidate_exists:
                                    candidate.write_bytes(b"old-candidate")
                                if review_exists:
                                    review.write_bytes(b"old-review")
                                real_replace = os.replace

                                def interrupt(source, destination):
                                    if Path(source).name == target + ".p3tmp":
                                        if after_replace:
                                            real_replace(source, destination)
                                        raise KeyboardInterrupt("publication interruption")
                                    return real_replace(source, destination)

                                with patch("plex_training.file_conditioned_contract.os.replace",
                                           side_effect=interrupt):
                                    with self.assertRaises(KeyboardInterrupt):
                                        generate_file_edit_candidate(candidate_path=candidate,
                                                                     review_path=review,
                                                                     contract_path=CONTRACT)
                                self.assertEqual(candidate.exists(), candidate_exists)
                                self.assertEqual(review.exists(), review_exists)
                                if candidate_exists:
                                    self.assertEqual(candidate.read_bytes(), b"old-candidate")
                                if review_exists:
                                    self.assertEqual(review.read_bytes(), b"old-review")
                                self.assertEqual(set(root.iterdir()),
                                                 {p for p in (candidate, review) if p.exists()})

    def test_generation_review_rollback_failure_preserves_recovery_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate, review = root / "candidate.jsonl", root / "review.json"
            candidate.write_bytes(b"old-candidate")
            review.write_bytes(b"old-review")
            backup = review.with_name(review.name + ".p3bak")
            real_replace = os.replace

            def interrupt_then_fail_recovery(source, destination):
                if Path(source) == backup:
                    raise OSError("review recovery failed")
                real_replace(source, destination)
                if Path(source) == review.with_name(review.name + ".p3tmp"):
                    raise KeyboardInterrupt("after review replacement")

            with patch("plex_training.file_conditioned_contract.os.replace",
                       side_effect=interrupt_then_fail_recovery):
                with self.assertRaisesRegex(RuntimeError, "recovery marker remains"):
                    generate_file_edit_candidate(candidate_path=candidate, review_path=review,
                                                 contract_path=CONTRACT)
            self.assertEqual(candidate.read_bytes(), b"old-candidate")
            self.assertEqual(backup.read_bytes(), b"old-review")
            marker = candidate.with_name(candidate.name + ".p3txn")
            self.assertTrue(json.loads(marker.read_text())["reviewExisted"])
            with self.assertRaises(FileExistsError):
                generate_file_edit_candidate(candidate_path=candidate, review_path=review,
                                             contract_path=CONTRACT)
            self.assertEqual(backup.read_bytes(), b"old-review")

    def test_generation_stale_review_backup_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate, review = root / "candidate.jsonl", root / "review.json"
            backup = review.with_name(review.name + ".p3bak")
            backup.write_bytes(b"protected-recovery")
            with self.assertRaises(FileExistsError):
                generate_file_edit_candidate(candidate_path=candidate, review_path=review,
                                             contract_path=CONTRACT)
            self.assertEqual(backup.read_bytes(), b"protected-recovery")
            self.assertFalse(candidate.exists())
            self.assertFalse(review.exists())

    def test_generation_stale_transaction_marker_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            marker = candidate.with_name(candidate.name + ".p3txn")
            candidate.write_bytes(b"old-candidate")
            review.write_bytes(b"old-review")
            marker.write_text(
                '{"kind":"plex-p3-paired-publication-v1","recovery":"inspect"}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(FileExistsError, "stale transaction artifact"):
                generate_file_edit_candidate(
                    candidate_path=candidate,
                    review_path=review,
                    contract_path=CONTRACT,
                )

            self.assertEqual(candidate.read_bytes(), b"old-candidate")
            self.assertEqual(review.read_bytes(), b"old-review")
            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                '{"kind":"plex-p3-paired-publication-v1","recovery":"inspect"}\n',
            )
            self.assertFalse(candidate.with_name(candidate.name + ".p3tmp").exists())
            self.assertFalse(review.with_name(review.name + ".p3tmp").exists())

    def test_generation_rejects_contract_output_and_canonical_alias_before_contract_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = root / "contract.json"
            contract.write_bytes(b"protected-contract")
            review = root / "review.json"
            for candidate in (
                contract,
                root / "nested" / ".." / "contract.json",
            ):
                with self.subTest(candidate=candidate), patch(
                    "plex_training.file_conditioned_contract._contract"
                ) as contract_check:
                    with self.assertRaisesRegex(
                        ValueError,
                        "must not overwrite protected input",
                    ):
                        generate_file_edit_candidate(
                            candidate_path=candidate,
                            review_path=review,
                            contract_path=contract,
                        )
                    contract_check.assert_not_called()
                    self.assertEqual(contract.read_bytes(), b"protected-contract")
                    self.assertFalse(review.exists())

    def test_generation_rejects_existing_candidate_review_filesystem_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            candidate.write_bytes(b"existing-output")
            review = root / "review-alias.json"
            review.hardlink_to(candidate)
            contract = root / "contract.json"
            contract.write_bytes(b"contract")
            with patch(
                "plex_training.file_conditioned_contract._contract"
            ) as contract_check:
                with self.assertRaisesRegex(
                    ValueError,
                    "output paths must differ",
                ):
                    generate_file_edit_candidate(
                        candidate_path=candidate,
                        review_path=review,
                        contract_path=contract,
                    )
            contract_check.assert_not_called()
            self.assertEqual(candidate.read_bytes(), b"existing-output")
            self.assertEqual(review.read_bytes(), b"existing-output")

    def test_review_report_rejects_candidate_and_tokenizer_aliases_before_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            candidate.write_bytes(b"candidate")
            review = root / "review.json"
            review.write_bytes(b"review")
            contract = root / "contract.json"
            contract.write_bytes(b"contract")
            bundle = root / "tokenizer"
            bundle.mkdir()
            for name in ("manifest.json", "tokenizer-config.json", "tokenizer.json"):
                (bundle / name).write_bytes(name.encode("ascii"))

            cases = [
                ("candidate", candidate),
                ("tokenizer-hardlink", root / "report-tokenizer-alias.json"),
            ]
            cases[1][1].hardlink_to(bundle / "tokenizer.json")

            for name, report in cases:
                with self.subTest(name=name), patch(
                    "plex_training.file_conditioned_contract._contract"
                ) as contract_check:
                    with self.assertRaisesRegex(
                        ValueError,
                        "must not overwrite protected input",
                    ):
                        review_file_edit_candidate(
                            candidate_path=candidate,
                            review_path=review,
                            contract_path=contract,
                            tokenizer_bundle=bundle,
                            report_path=report,
                        )
                    contract_check.assert_not_called()
                    self.assertEqual(candidate.read_bytes(), b"candidate")
                    self.assertEqual(review.read_bytes(), b"review")
                    self.assertEqual(contract.read_bytes(), b"contract")
                    self.assertEqual(
                        (bundle / "tokenizer.json").read_bytes(),
                        b"tokenizer.json",
                    )

    @unittest.skipUnless(os.name == "nt", "Win32 output aliases require Windows")
    def test_generation_rejects_fresh_windows_output_aliases_before_input_read(self) -> None:
        for spelling in ("output.", "output ", "nested./output", "output:stream"):
            for alias_is_candidate in (False, True):
                with self.subTest(spelling=spelling, candidate=alias_is_candidate), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    first, second = root / "output", root / spelling
                    with patch("plex_training.file_conditioned_contract._contract") as contract_check:
                        with self.assertRaisesRegex(ValueError, "Windows"):
                            generate_file_edit_candidate(
                                candidate_path=second if alias_is_candidate else first,
                                review_path=first if alias_is_candidate else second,
                                contract_path=root / "contract.json",
                            )
                    contract_check.assert_not_called()
                    self.assertEqual(list(root.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Win32 output aliases require Windows")
    def test_review_rejects_windows_report_spellings_before_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.jsonl"
            candidate.write_bytes(b"preserve")
            for report in (root / "candidate.jsonl.", root / "candidate.jsonl ", root / "candidate.jsonl:stream"):
                with self.subTest(report=report), patch("plex_training.file_conditioned_contract._contract") as contract_check:
                    with self.assertRaisesRegex(ValueError, "Windows"):
                        review_file_edit_candidate(
                            candidate_path=candidate, review_path=root / "review.json",
                            contract_path=root / "contract.json", report_path=report,
                        )
                    contract_check.assert_not_called()
                    self.assertEqual(candidate.read_bytes(), b"preserve")
                    self.assertEqual(list(root.iterdir()), [candidate])

    @unittest.skipUnless(os.name == "nt", "Win32 output aliases require Windows")
    def test_generation_checks_resolved_windows_output_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            link = root / "link"
            original = Path.resolve

            def resolved(path, *args, **kwargs):
                return root / "output." if path == link else original(path, *args, **kwargs)

            with patch.object(Path, "resolve", resolved), patch("plex_training.file_conditioned_contract._contract") as contract_check:
                with self.assertRaisesRegex(ValueError, "Windows"):
                    generate_file_edit_candidate(
                        candidate_path=root / "output", review_path=link, contract_path=root / "contract.json",
                    )
            contract_check.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])

    def test_review_fails_closed_when_bundle_is_missing(self) -> None:
        root = Path(".test-tmp") / str(uuid.uuid4())
        root.mkdir(parents=True)
        try:
            candidate, draft = root / "candidate.jsonl", root / "review.json"
            generate_file_edit_candidate(candidate_path=candidate, review_path=draft)
            with self.assertRaisesRegex(ValueError, "inaccessible|tokenizer bundle"):
                review_file_edit_candidate(candidate_path=candidate, review_path=draft,
                    contract_path=CONTRACT, tokenizer_bundle=root / "missing-tokenizer")
        finally:
            shutil.rmtree(root)

    def test_all_targets_match_reviewed_requested_values(self):
        # Independently listed requested results, not derived from generator targets.
        expected = ["Save Changes", "Welcome", 'href="/account"', 'type="email"',
                    'alt="a blue sky"', "Submit", "gap: 16px", "color: navy",
                    "border-radius: 4px", "display: flex", "margin-top: 20px",
                    "font-size: 18px", "retryLimit = 5", 'greeting = "Welcome"',
                    "delay = 250", 'querySelector(".save-button")', "size = 20", 'return "Saved"']
        for row, text in zip(build_candidate_rows(), expected):
            with self.subTest(row=row["id"]):
                self.assertIn(text, row["expectedFile"])
                self.assertTrue(score_file_edit(row, row["expectedFile"])["exactMatch"])

    def test_wrong_answer_and_unrelated_edit_are_rejected(self):
        for target in ("<button>Store</button>", "<button class=\"extra\">Save Changes</button>"):
            rows = build_candidate_rows()
            rows[0]["expectedFile"] = target
            with self.assertRaises(ValueError):
                _validate_rows(rows)

    def test_scoring_distinguishes_correctness_and_preservation(self):
        row = build_candidate_rows()[0]
        wrong = score_file_edit(row, "<button>Wrong</button>")
        self.assertFalse(wrong["exactMatch"])
        self.assertTrue(wrong["unrelatedCodePreserved"])
        self.assertEqual(wrong["syntaxCheckability"], "not-checked")
        unrelated = score_file_edit(row, '<button class="extra">Save Changes</button>')
        self.assertTrue(unrelated["unnecessaryEdits"])
        self.assertFalse(score_file_edit(row, row["expectedFile"] + "\n")["exactMatch"])
        css = build_candidate_rows()[6]
        self.assertTrue(score_file_edit(css, css["expectedFile"].replace("\n", "\r\n"))["exactMatch"])

    def test_candidate_and_metadata_tampering_cannot_refreeze(self):
        rows = build_candidate_rows()
        rows[0]["expectedFile"] = "<button>Wrong</button>"
        raw = _canonical_bytes(rows)
        from types import SimpleNamespace
        candidate = SimpleNamespace(read_bytes=lambda: raw)
        review = SimpleNamespace(read_text=lambda **kw: json.dumps({
            "candidateSha256": hashlib.sha256(raw).hexdigest(), "byteCount": len(raw)}))
        with self.assertRaisesRegex(ValueError, "frozen candidate identity"):
            review_file_edit_candidate(candidate_path=candidate, review_path=review,
                                       contract_path=CONTRACT, tokenizer_bundle=BUNDLE)

    def test_authorization_types_and_identity_fail_closed(self):
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for key, bad in [("modelTrainingAuthorized", True), ("modelTrainingAuthorized", 0),
                         ("researchOptimizerUpdates", False), ("finalHoldoutOpened", True),
                         ("dataPreparationAuthorized", False), ("candidateIdentity", {}),
                         ("tokenizer", {})]:
            with self.subTest(key=key, bad=bad), patch(
                "plex_training.file_conditioned_contract._read_json", return_value={**value, key: bad}
            ):
                with self.assertRaises(ValueError):
                    _contract(CONTRACT)
                with self.assertRaises(ValueError):
                    generate_file_edit_candidate(candidate_path=Path("unused"), review_path=Path("unused-review"))

    def test_cli_defaults_are_absolute_and_rooted_at_repository(self):
        for command in ("file-edit-contract-generate", "file-edit-contract-review"):
            args = build_parser().parse_args([command])
            self.assertEqual(args.candidate, ROOT / "training/phase3/drafts/p3-01-file-edit-contract-v1.jsonl")

    @unittest.skipUnless((BUNDLE / "tokenizer.json").is_file(), "Local frozen tokenizer not installed")
    def test_real_frozen_tokenizer_review_and_cli(self):
        output = StringIO()
        with redirect_stdout(output):
            status = main(["file-edit-contract-review"])
        self.assertEqual(status, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["candidateSha256"], EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(result["tokenizerPreflight"]["tokenizerSha256"], EXPECTED_TOKENIZER_SHA256)
        self.assertTrue(result["tokenizerPreflight"]["allFit512Tokens"])
        self.assertEqual(result["tokenizerPreflight"]["maximumTokensIncludingEos"], 77)
        self.assertFalse(result["trainingPerformed"])
        self.assertEqual(result["researchOptimizerUpdates"], 0)
        self.assertFalse(result["finalHoldoutOpened"])

    @unittest.skipUnless((BUNDLE / "tokenizer.json").is_file(), "Local frozen tokenizer not installed")
    def test_changed_tokenizer_manifest_is_rejected(self):
        with patch("plex_training.file_conditioned_contract.sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                review_file_edit_candidate(
                    candidate_path=ROOT / "training/phase3/drafts/p3-01-file-edit-contract-v1.jsonl",
                    review_path=ROOT / "training/phase3/drafts/p3-01-file-edit-contract-v1.review.json",
                    contract_path=CONTRACT, tokenizer_bundle=BUNDLE)


if __name__ == "__main__":
    unittest.main()
