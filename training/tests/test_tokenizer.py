import hashlib
import json
import sys
import tempfile
import unittest
from array import array
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from plex_training.cli import main
from plex_training.config import DEFAULT_CONFIG
from plex_training.data import TokenCorpus
from plex_training.dataset import build_dataset
from plex_training.tokenizer import PlexTokenizer, ROUNDTRIP_SAMPLES, train_tokenizer


class TokenizerTests(unittest.TestCase):
    def dataset(self, root: Path, validation: str = "Withheld text 🐱\n") -> Path:
        dataset = root / "dataset"
        dataset.mkdir(exist_ok=True)
        (dataset / "licenses").mkdir(exist_ok=True)
        notice = b"Fixture permission notice.\n"
        (dataset / "licenses/fixture.txt").write_bytes(notice)
        sources = []
        summary = {}
        for split, text in (("train", "function add(a, b) {\n\treturn a + b;\n}\n" * 30),
                            ("validation", validation)):
            digest = hashlib.sha256(text.encode()).hexdigest()
            row = {"recordId": split, "sourceId": split, "groupId": split,
                   "contentSha256": digest, "text": text, "path": "fixture.js"}
            raw = (json.dumps(row, ensure_ascii=False) + "\n").encode()
            (dataset / (split + ".jsonl")).write_bytes(raw)
            summary[split + "Records"] = 1
            summary[split + "JsonlSha256"] = hashlib.sha256(raw).hexdigest()
            sources.append({"id": split, "groupId": split, "rightsReviewStatus": "approved",
                            "licenseNoticeFile": "licenses/fixture.txt",
                            "licenseNoticeSha256": hashlib.sha256(notice).hexdigest()})
        (dataset / "manifest.json").write_text(json.dumps({"schemaVersion": 1,
            "pipelineVersion": "p1-14.2", "sources": sources, "summary": summary}), encoding="utf-8")
        return dataset

    def test_saved_tokenizer_preserves_code_unicode_whitespace_and_literal_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = train_tokenizer(self.dataset(root), root / "bundle", vocab_size=300)
            tokenizer = PlexTokenizer.load(root / "bundle")
            for text in ROUNDTRIP_SAMPLES + ["Unseen bytes: 🦕 🫠 ภาษาไทย кириллица\r\n"]:
                ids = tokenizer.encode(text)
                self.assertTrue(all(4 <= value < result["actualVocabularySize"] for value in ids))
                self.assertEqual(tokenizer.decode(ids), text)
            self.assertEqual(json.loads((root / "bundle/model-config.json").read_text()),
                             DEFAULT_CONFIG.to_dict())
            self.assertEqual((root / "bundle/licenses/fixture.txt").read_bytes(),
                             b"Fixture permission notice.\n")

    def test_fit_is_deterministic_and_validation_text_never_changes_vocabulary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            first = train_tokenizer(dataset, root / "one", vocab_size=400)
            second = train_tokenizer(dataset, root / "two", vocab_size=400)
            for path in (root / "one").rglob("*"):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (root / "two" / path.relative_to(root / "one")).read_bytes())
            self.dataset(root, "Entirely different validation vocabulary Ω 🚀 never fitted!\n")
            changed = train_tokenizer(dataset, root / "three", vocab_size=400)
            self.assertEqual(first["tokenizerSha256"], changed["tokenizerSha256"])
            self.assertEqual(first["train"]["sha256"], second["train"]["sha256"])
            self.assertNotEqual(first["validation"]["sha256"], changed["validation"]["sha256"])

    def test_packed_records_have_eos_offsets_valid_ids_and_exact_roundtrips(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            result = train_tokenizer(dataset, root / "bundle", vocab_size=300)
            tokenizer = PlexTokenizer.load(root / "bundle")
            for split in ("train", "validation"):
                values = array("H")
                values.frombytes((root / "bundle" / (split + ".tokens.u16le")).read_bytes())
                if sys.byteorder != "little":
                    values.byteswap()
                row = json.loads((dataset / (split + ".jsonl")).read_text(encoding="utf-8"))
                index = json.loads((root / "bundle" / (split + ".index.json")).read_text())
                self.assertEqual(index, [{"recordId": split, "startToken": 0, "tokenCount": len(values)}])
                self.assertEqual(values[-1], 3)
                self.assertEqual(tokenizer.decode(list(values[:-1])), row["text"])
                self.assertEqual(len(values), result[split]["tokenCount"])
                with TokenCorpus(root / "bundle" / (split + ".tokens.u16le")) as corpus:
                    self.assertEqual(corpus.token_count, len(values))
                    with self.assertRaisesRegex(ValueError, "Bootstrap runner requires byte-v1"):
                        corpus.require_byte_codec()

    def test_corrupt_split_and_unapproved_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            with (dataset / "train.jsonl").open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaises(ValueError):
                train_tokenizer(dataset, root / "bad")
            self.assertFalse((root / "bad").exists())
            self.dataset(root)
            manifest = json.loads((dataset / "manifest.json").read_text())
            manifest["sources"][0]["rightsReviewStatus"] = "pending"
            (dataset / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "owner-approved"):
                train_tokenizer(dataset, root / "bad")

    def test_storage_failure_leaves_no_partial_bundle_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            with self.assertRaisesRegex(ValueError, "storage allocation"):
                train_tokenizer(dataset, root / "bad", storage_limit_bytes=100)
            self.assertFalse((root / "bad").exists())
            self.assertEqual(list(root.glob(".plex-tokenizer-*")), [])
            (root / "exists").mkdir()
            (root / "exists/keep.txt").write_text("keep")
            with self.assertRaises(FileExistsError):
                train_tokenizer(dataset, root / "exists")
            self.assertEqual((root / "exists/keep.txt").read_text(), "keep")

    def test_license_hash_and_notice_path_are_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            (dataset / "licenses/fixture.txt").write_bytes(b"Changed notice")
            with self.assertRaisesRegex(ValueError, "notice hash"):
                train_tokenizer(dataset, root / "bad")
            self.dataset(root)
            manifest = json.loads((dataset / "manifest.json").read_text())
            manifest["sources"][0]["licenseNoticeFile"] = "licenses/../manifest.json"
            (dataset / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "license notice"):
                train_tokenizer(dataset, root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_cross_split_group_leakage_is_rejected_even_with_valid_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            manifest = json.loads((dataset / "manifest.json").read_text())
            manifest["sources"][1]["groupId"] = "train"
            row = json.loads((dataset / "validation.jsonl").read_text(encoding="utf-8"))
            row["groupId"] = "train"
            raw = (json.dumps(row, ensure_ascii=False) + "\n").encode()
            (dataset / "validation.jsonl").write_bytes(raw)
            manifest["summary"]["validationJsonlSha256"] = hashlib.sha256(raw).hexdigest()
            (dataset / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "disjoint"):
                train_tokenizer(dataset, root / "bad")

    def test_cli_bounds_and_vocabulary_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self.dataset(root)
            common = ["tokenizer-train", "--dataset-dir", str(dataset), "--artifact-root", str(root / "artifacts")]
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(common + ["--output-dir", "../escape"]), 2)
                self.assertEqual(main(common + ["--storage-limit-gib", "201"]), 2)
                self.assertEqual(main(common + ["--vocab-size", "259"]), 2)
                self.assertEqual(main(common + ["--vocab-size", "16385"]), 2)
                self.assertEqual(main(common + ["--vocab-size", "300"]), 0)

    def test_saved_tokenizer_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train_tokenizer(self.dataset(root), root / "bundle", vocab_size=300)
            with (root / "bundle/tokenizer.json").open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(ValueError, "hash"):
                PlexTokenizer.load(root / "bundle")

    def test_renamed_nonbyte_corpus_cannot_be_mislabeled_by_bootstrap_runner(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "renamed.tokens.u16le"
            path.write_bytes(b"\x00\x01")  # 256, even when a manifest is absent
            with TokenCorpus(path) as corpus:
                with self.assertRaisesRegex(ValueError, "out-of-range"):
                    corpus.require_byte_codec()

    def test_family_stratified_p2_dataset_is_accepted_and_fits_train_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for source_id, family_id, prefix in (
                ("microsoft", "microsoft-family", "ms"),
                ("mdn", "mdn-family", "mdn"),
            ):
                source_root = root / "raw" / source_id
                source_root.mkdir(parents=True)
                (source_root / "LICENSE").write_text("Fixture permission notice.\n", encoding="utf-8")
                source = {
                    "id": source_id,
                    "localPath": f"raw/{source_id}",
                    "origin": f"https://example.invalid/{source_id}",
                    "revision": "fixture-commit-1",
                    "licenseId": "MIT",
                    "licenseEvidence": "LICENSE",
                    "rightsReviewStatus": "approved",
                    "rightsReviewedAtUtc": "2026-10-03T00:00:00Z",
                    "groupId": family_id,
                    "sourceFamilyId": family_id,
                    "includeExtensions": [".py"],
                    "splitGroupRules": [
                        {"id": f"{prefix}-project-{index}", "pathPrefixes": [f"project-{index}/"]}
                        for index in range(3)
                    ],
                }
                for index in range(3):
                    project = source_root / f"project-{index}"
                    project.mkdir()
                    (project / "example.py").write_text(
                        f"def {prefix}_function_{index}(value):\n    return value + {index + 1}\n",
                        encoding="utf-8",
                    )
                sources.append(source)
            catalog = root / "sources.json"
            catalog.write_text(json.dumps({
                "schemaVersion": 1,
                "splitStrategy": "family-stratified-groups-v1",
                "sources": sources,
            }), encoding="utf-8")
            dataset = root / "dataset"
            build_dataset(
                catalog, dataset, validation_percent=30, seed=91,
                storage_limit_bytes=1024 * 1024,
            )

            result = train_tokenizer(dataset, root / "bundle", vocab_size=300)

            tokenizer = PlexTokenizer.load(root / "bundle")
            self.assertEqual(result["codec"], "plex-byte-bpe-v1")
            for text in ("def learned(value):\n    return value + 7\n", "plain Ω text\n"):
                self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)


if __name__ == "__main__":
    unittest.main()
