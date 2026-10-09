import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.web_contamination import check_contamination


class PlexWebContaminationTests(unittest.TestCase):
    def _dataset(self, root: Path, train_text: str, validation_text: str, origin: str = "https://example.invalid/source") -> Path:
        dataset = root / "dataset"
        dataset.mkdir()
        (dataset / "train.jsonl").write_text(
            json.dumps({"sourceId": "train-source", "path": "index.html", "text": train_text}) + "\n",
            encoding="utf-8",
        )
        (dataset / "validation.jsonl").write_text(
            json.dumps({"sourceId": "validation-source", "path": "app.js", "text": validation_text}) + "\n",
            encoding="utf-8",
        )
        (dataset / "manifest.json").write_text(
            json.dumps({"schemaVersion": 1, "sources": [{"id": "source", "origin": origin}]}, indent=2),
            encoding="utf-8",
        )
        return dataset

    def _config(
        self,
        root: Path,
        protected_relative: str,
        blocked: list[str] | None = None,
        minimum: int = 80,
    ) -> Path:
        path = root / "protected.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "protectedPaths": [protected_relative],
                    "blockedSourceOrigins": blocked or [],
                    "minimumSubstringCharacters": minimum,
                    "minimumProtectedFiles": 1,
                    "minimumProtectedSegments": 1,
                    "finalHoldout": "closed-not-addressable",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def test_clean_dataset_passes_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            (protected / "eval.json").write_text(
                json.dumps({"prompt": "A" * 100, "answer": "B" * 100}),
                encoding="utf-8",
            )
            dataset = self._dataset(root, "<main>independent markup</main>", "const answer = 42;")
            config = self._config(root, "protected")
            report_path = root / "report.json"
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=report_path)
            self.assertTrue(report["passed"])
            self.assertTrue(report["protectionCoveragePassed"])
            self.assertEqual(report["protectedFilesDiscovered"], 1)
            self.assertEqual(report["protectedFilesScanned"], 1)
            self.assertEqual(report["protectedFilesSkipped"], 0)
            self.assertEqual(report["exactMatches"], [])
            self.assertEqual(report["substringMatches"], [])
            self.assertTrue(report_path.is_file())

    def test_long_protected_string_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            secret_eval = "function protectedEvaluationExample() { return 'never pretrain this exact evaluation sample'; }"
            (protected / "eval.json").write_text(json.dumps({"code": secret_eval}), encoding="utf-8")
            dataset = self._dataset(root, f"<script>{secret_eval}</script>", "const other = true;")
            config = self._config(root, "protected")
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(len(report["substringMatches"]), 1)

    def test_interior_shared_substring_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            shared = "shared-interior-" * 8
            protected_text = "protected-prefix-" + shared + "-protected-suffix"
            corpus_text = "corpus-prefix-" + shared + "-corpus-suffix"
            (protected / "eval.txt").write_text(protected_text, encoding="utf-8")
            dataset = self._dataset(root, corpus_text, "const other = true;")
            config = self._config(root, "protected", minimum=80)
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(len(report["substringMatches"]), 1)
            self.assertGreaterEqual(report["substringMatches"][0]["overlapAtLeastCharacters"], 80)

    def test_shared_substring_at_exact_threshold_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            shared = "S" * 80
            (protected / "eval.txt").write_text("P" * 40 + shared + "Q" * 40, encoding="utf-8")
            dataset = self._dataset(root, "R" * 40 + shared + "T" * 40, "const other = true;")
            config = self._config(root, "protected", minimum=80)
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(report["substringMatches"][0]["overlapAtLeastCharacters"], 80)

    def test_shared_substring_below_threshold_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            shared = "S" * 79
            (protected / "eval.txt").write_text("P" * 40 + shared + "Q" * 40, encoding="utf-8")
            dataset = self._dataset(root, "R" * 40 + shared + "T" * 40, "const other = true;")
            config = self._config(root, "protected", minimum=80)
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertTrue(report["passed"])
            self.assertEqual(report["substringMatches"], [])

    def test_blocked_source_origin_fails_even_without_text_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            (protected / "eval.json").write_text(json.dumps({"prompt": "Z" * 100}), encoding="utf-8")
            origin = "https://github.com/keepithandy/plex-nano-27m-v0.0.1-p2-24"
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;", origin=origin)
            config = self._config(root, "protected", [origin])
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(len(report["blockedOriginMatches"]), 1)

    def test_empty_protected_directory_fails_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "protected").mkdir()
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;")
            config = self._config(root, "protected")
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertFalse(report["protectionCoveragePassed"])
            self.assertEqual(report["protectedFilesDiscovered"], 0)
            self.assertEqual(report["protectedFilesScanned"], 0)
            self.assertEqual(report["protectedSegmentsScanned"], 0)
            self.assertIn("minimum-protected-files-not-met", report["protectionCoverageFailures"])
            self.assertIn("minimum-protected-segments-not-met", report["protectionCoverageFailures"])

    def test_invalid_utf8_protected_file_fails_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            (protected / "eval.txt").write_bytes(b"\xff\xfe\xfd")
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;")
            config = self._config(root, "protected")
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(report["protectedFilesDiscovered"], 1)
            self.assertEqual(report["protectedFilesScanned"], 0)
            self.assertEqual(report["protectedFilesSkipped"], 1)
            self.assertEqual(report["protectedFileResults"][0]["reason"], "invalid-utf8")
            self.assertIn("protected-files-skipped", report["protectionCoverageFailures"])

    def test_oversized_protected_file_fails_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            (protected / "eval.txt").write_bytes(b"A" * (2 * 1024 * 1024 + 1))
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;")
            config = self._config(root, "protected")
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(report["protectedFilesScanned"], 0)
            self.assertEqual(report["protectedFilesSkipped"], 1)
            self.assertEqual(report["protectedFileResults"][0]["reason"], "oversized")

    def test_mixed_successful_and_unreadable_protected_files_fail_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            good = protected / "good.txt"
            bad = protected / "bad.txt"
            good.write_text("G" * 100, encoding="utf-8")
            bad.write_text("B" * 100, encoding="utf-8")
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;")
            config = self._config(root, "protected")
            original_read_text = Path.read_text

            def selective_read_text(path: Path, *args, **kwargs):
                if path == bad:
                    raise OSError("synthetic unreadable file")
                return original_read_text(path, *args, **kwargs)

            with patch("plex_training.web_contamination.REPO_ROOT", root), patch.object(
                Path, "read_text", selective_read_text
            ):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(report["protectedFilesDiscovered"], 2)
            self.assertEqual(report["protectedFilesScanned"], 1)
            self.assertEqual(report["protectedFilesSkipped"], 1)
            results = {entry["path"]: entry for entry in report["protectedFileResults"]}
            self.assertEqual(results["protected/good.txt"]["status"], "scanned")
            self.assertEqual(results["protected/bad.txt"]["reason"], "unreadable")
            self.assertIn("protected-files-skipped", report["protectionCoverageFailures"])

    def test_short_only_protection_fails_minimum_segment_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protected = root / "protected"
            protected.mkdir()
            (protected / "eval.json").write_text(json.dumps({"prompt": "short"}), encoding="utf-8")
            dataset = self._dataset(root, "<div>clean</div>", "const clean = true;")
            config = self._config(root, "protected")
            with patch("plex_training.web_contamination.REPO_ROOT", root):
                report = check_contamination(dataset, protected_config=config, report_path=root / "report.json")
            self.assertFalse(report["passed"])
            self.assertEqual(report["protectedFilesScanned"], 1)
            self.assertEqual(report["protectedSegmentsScanned"], 0)
            self.assertIn("minimum-protected-segments-not-met", report["protectionCoverageFailures"])


if __name__ == "__main__":
    unittest.main()
