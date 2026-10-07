import json
import tempfile
import unittest
from pathlib import Path

from plex_training.web_sources import verify_web_sources


class PlexWebSourcePreflightTests(unittest.TestCase):
    def _policy(self, root: Path) -> Path:
        path = root / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "policy": "test-web-policy-v1",
                    "languages": {
                        "HTML": [".html", ".htm"],
                        "CSS": [".css"],
                        "JavaScript": [".js", ".mjs", ".cjs"],
                    },
                    "allowedSpdx": ["MIT", "Apache-2.0"],
                    "defaultLicenseDecision": "reject",
                    "requireLicenseEvidence": True,
                    "requireSourceProvenance": True,
                    "disallowedPathSegments": ["node_modules", "vendor", "dist", "build"],
                    "disallowedSuffixes": [".map", ".min.js", ".min.css"],
                    "rejectGenerated": True,
                    "rejectMinified": True,
                    "rejectSecrets": True,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def _source(self, root: Path, source_id: str, license_id: str = "MIT") -> dict:
        source = root / "raw" / source_id
        source.mkdir(parents=True)
        (source / "LICENSE").write_text("fixture license evidence\n", encoding="utf-8")
        return {
            "id": source_id,
            "localPath": f"raw/{source_id}",
            "origin": f"https://example.invalid/{source_id}",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "licenseId": license_id,
            "licenseEvidence": "LICENSE",
            "rightsReviewStatus": "approved",
            "rightsReviewedAtUtc": "2026-10-06T00:00:00Z",
            "groupId": f"repo-{source_id}",
            "includeExtensions": [".html", ".css", ".js"],
        }

    def _manifest(self, root: Path, sources: list[dict]) -> Path:
        path = root / "sources.json"
        path.write_text(
            json.dumps({"schemaVersion": 1, "sources": sources}, indent=2),
            encoding="utf-8",
        )
        return path

    def test_accepts_reviewed_web_files_and_reports_languages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha")
            bravo = self._source(root, "bravo", "Apache-2.0")

            (root / "raw/alpha/index.html").write_text(
                "<!doctype html>\n<html><body>Hello</body></html>\n",
                encoding="utf-8",
            )
            (root / "raw/alpha/styles.css").write_text(
                "body { color: navy; }\n",
                encoding="utf-8",
            )
            (root / "raw/bravo/app.js").write_text(
                "export function greet(name) { return `Hello ${name}`; }\n",
                encoding="utf-8",
            )

            result = verify_web_sources(
                self._manifest(root, [alpha, bravo]),
                self._policy(root),
            )

            self.assertEqual(result["acceptedFiles"], 3)
            self.assertEqual(
                result["acceptedByLanguage"],
                {"CSS": 1, "HTML": 1, "JavaScript": 1},
            )
            self.assertEqual(result["sourceGroups"], 2)
            self.assertTrue(result["readyForDeterministicBuild"])

    def test_rejects_license_outside_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha", "GPL-3.0-only")
            bravo = self._source(root, "bravo")
            (root / "raw/alpha/index.html").write_text("<p>alpha</p>\n", encoding="utf-8")
            (root / "raw/bravo/index.html").write_text("<p>bravo</p>\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "not allowed"):
                verify_web_sources(
                    self._manifest(root, [alpha, bravo]),
                    self._policy(root),
                )

    def test_filters_bad_web_artifacts_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha")
            bravo = self._source(root, "bravo")

            good = "<main>Useful human-authored markup</main>\n"
            (root / "raw/alpha/index.html").write_text(good, encoding="utf-8")
            (root / "raw/alpha/bundle.min.js").write_text(
                "const x=" + "1+" * 2000 + "1;\n",
                encoding="utf-8",
            )
            (root / "raw/alpha/generated.css").write_text(
                "/* generated file - do not edit */\nbody { color: red; }\n",
                encoding="utf-8",
            )
            (root / "raw/alpha/secret.js").write_text(
                'const token = "ghp_123456789012345678901234567890123456";\n',
                encoding="utf-8",
            )
            (root / "raw/alpha/vendor").mkdir()
            (root / "raw/alpha/vendor/library.js").write_text(
                "export const vendored = true;\n",
                encoding="utf-8",
            )
            (root / "raw/bravo/copy.html").write_text(good, encoding="utf-8")
            (root / "raw/bravo/app.js").write_text(
                "export const answer = 42;\n",
                encoding="utf-8",
            )

            result = verify_web_sources(
                self._manifest(root, [alpha, bravo]),
                self._policy(root),
            )

            self.assertEqual(result["acceptedFiles"], 2)
            self.assertEqual(result["exactDuplicateHashesRemoved"], 1)
            self.assertEqual(result["skippedCounts"]["disallowed_suffix"], 1)
            self.assertEqual(result["skippedCounts"]["generated_content"], 1)
            self.assertEqual(result["skippedCounts"]["secret_pattern"], 1)
            self.assertEqual(result["skippedCounts"]["disallowed_path_segment"], 1)


if __name__ == "__main__":
    unittest.main()
