import json
import tempfile
import unittest
from pathlib import Path

from plex_training.web_dataset import build_web_dataset


class PlexWebDatasetBuildTests(unittest.TestCase):
    def _policy(self, root: Path) -> Path:
        path = root / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "policy": "test-web-policy-v1",
                    "languages": {
                        "HTML": [".html"],
                        "CSS": [".css"],
                        "JavaScript": [".js"],
                    },
                    "allowedSpdx": ["MIT"],
                    "defaultLicenseDecision": "reject",
                    "requireLicenseEvidence": True,
                    "requireSourceProvenance": True,
                    "disallowedPathSegments": ["vendor", "dist", "build"],
                    "disallowedSuffixes": [".min.js", ".min.css"],
                    "rejectGenerated": True,
                    "rejectMinified": True,
                    "rejectSecrets": True,
                }
            ),
            encoding="utf-8",
        )
        return path

    def _source(self, root: Path, source_id: str) -> dict:
        source = root / "raw" / source_id
        source.mkdir(parents=True)
        (source / "LICENSE").write_text("MIT fixture\n", encoding="utf-8")
        return {
            "id": source_id,
            "localPath": f"raw/{source_id}",
            "origin": f"https://example.invalid/{source_id}",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "licenseId": "MIT",
            "licenseEvidence": "LICENSE",
            "rightsReviewStatus": "approved",
            "rightsReviewedAtUtc": "2026-10-07T00:00:00Z",
            "groupId": f"group-{source_id}",
            "includeExtensions": [".html", ".css", ".js"],
        }

    def test_builder_never_reintroduces_files_rejected_by_web_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha")
            bravo = self._source(root, "bravo")

            (root / "raw/alpha/index.html").write_text(
                "<main>Human authored HTML content for Plex Web.</main>\n",
                encoding="utf-8",
            )
            (root / "raw/alpha/bundle.min.js").write_text(
                "const bundled = true;" * 300,
                encoding="utf-8",
            )
            (root / "raw/bravo/site.css").write_text(
                "body { display: grid; gap: 1rem; }\n",
                encoding="utf-8",
            )

            manifest = root / "sources.json"
            manifest.write_text(
                json.dumps({"schemaVersion": 1, "sources": [alpha, bravo]}),
                encoding="utf-8",
            )
            output = root / "dataset"

            result = build_web_dataset(
                manifest,
                output,
                validation_percent=50,
                seed=1337,
                storage_limit_bytes=10 * 1024 * 1024,
                policy_path=self._policy(root),
            )

            self.assertEqual(result["preflightAcceptedFiles"], 2)
            self.assertEqual(result["records"], 2)
            self.assertTrue(result["verifiedPathSetApplied"])
            rows = []
            for split in ("train.jsonl", "validation.jsonl"):
                rows.extend(
                    json.loads(line)
                    for line in (output / split).read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            self.assertEqual({row["path"] for row in rows}, {"index.html", "site.css"})
            self.assertNotIn("bundle.min.js", {row["path"] for row in rows})


if __name__ == "__main__":
    unittest.main()
