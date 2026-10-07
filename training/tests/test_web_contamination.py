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

    def _config(self, root: Path, protected_relative: str, blocked: list[str] | None = None) -> Path:
        path = root / "protected.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "protectedPaths": [protected_relative],
                    "blockedSourceOrigins": blocked or [],
                    "minimumSubstringCharacters": 80,
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


if __name__ == "__main__":
    unittest.main()
