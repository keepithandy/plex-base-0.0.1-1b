import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from plex_training.tokenizer_review import review_tokenizers


class TokenizerReviewTests(unittest.TestCase):
    def _dataset(self, root: Path) -> Path:
        dataset = root / "dataset"
        dataset.mkdir()
        licenses = dataset / "licenses"
        licenses.mkdir()
        notice = b"MIT fixture license\n"
        (licenses / "alpha.txt").write_bytes(notice)
        (licenses / "bravo.txt").write_bytes(notice)

        rows = {
            "train": [
                {
                    "recordId": "train-a",
                    "sourceId": "alpha",
                    "groupId": "alpha",
                    "path": "index.html",
                    "text": '<main class="card">Hello Plex</main>\n' * 20,
                }
            ],
            "validation": [
                {
                    "recordId": "validation-b",
                    "sourceId": "bravo",
                    "groupId": "bravo",
                    "path": "app.js",
                    "text": "function greet(name) { return name + '!'; }\n",
                }
            ],
        }
        summary = {}
        for split, split_rows in rows.items():
            raw_lines = []
            for row in split_rows:
                text = row["text"]
                row["contentSha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                raw_lines.append(
                    json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                )
            raw = "".join(raw_lines).encode("utf-8")
            (dataset / f"{split}.jsonl").write_bytes(raw)
            summary[f"{split}Records"] = len(split_rows)
            summary[f"{split}JsonlSha256"] = hashlib.sha256(raw).hexdigest()

        manifest = {
            "schemaVersion": 1,
            "pipelineVersion": "p1-14.2",
            "sources": [
                {
                    "id": "alpha",
                    "groupId": "alpha",
                    "rightsReviewStatus": "approved",
                    "licenseNoticeFile": "licenses/alpha.txt",
                    "licenseNoticeSha256": hashlib.sha256(notice).hexdigest(),
                },
                {
                    "id": "bravo",
                    "groupId": "bravo",
                    "rightsReviewStatus": "approved",
                    "licenseNoticeFile": "licenses/bravo.txt",
                    "licenseNoticeSha256": hashlib.sha256(notice).hexdigest(),
                },
            ],
            "summary": summary,
        }
        (dataset / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return dataset

    def test_review_fits_multiple_fresh_candidates_without_model_training(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = self._dataset(root)
            output = root / "review"

            result = review_tokenizers(
                dataset,
                output,
                vocab_sizes=[300, 320],
                min_frequency=2,
                storage_limit_bytes=64 * 1024 * 1024,
            )

            self.assertEqual(result["candidateCount"], 2)
            self.assertFalse(result["automaticPromotion"])
            self.assertFalse(result["modelTrainingPerformed"])
            report = json.loads((output / "review.json").read_text(encoding="utf-8"))
            self.assertFalse(report["validationUsedForFitting"])
            self.assertFalse(report["scratchTrainingBoundary"]["pretrainedModelWeightsLoaded"])
            self.assertFalse(report["scratchTrainingBoundary"]["modelTrainingPerformed"])
            self.assertEqual(
                [row["requestedVocabularySize"] for row in report["candidates"]],
                [300, 320],
            )
            for row in report["candidates"]:
                self.assertTrue(row["reviewSamples"]["allRoundtripsExact"])
                self.assertEqual(row["train"]["roundtripRecords"], 1)
                self.assertEqual(row["validation"]["roundtripRecords"], 1)

    def test_duplicate_or_unsorted_vocab_sizes_are_canonicalized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = review_tokenizers(
                self._dataset(root),
                root / "review",
                vocab_sizes=[320, 300, 320],
                storage_limit_bytes=64 * 1024 * 1024,
            )
            self.assertEqual(
                [row["requestedVocabularySize"] for row in result["candidates"]],
                [300, 320],
            )


if __name__ == "__main__":
    unittest.main()
