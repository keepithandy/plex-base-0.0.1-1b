import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.web_materialize import materialize_sources


class PlexWebMaterializeTests(unittest.TestCase):
    def _policy(self, root: Path) -> Path:
        path = root / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "policy": "test",
                    "languages": {"HTML": [".html"], "CSS": [".css"], "JavaScript": [".js"]},
                    "allowedSpdx": ["MIT"],
                    "defaultLicenseDecision": "reject",
                    "requireLicenseEvidence": True,
                    "requireSourceProvenance": True,
                    "disallowedPathSegments": [],
                    "disallowedSuffixes": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def _registry(self, root: Path) -> Path:
        path = root / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "sources": [
                        {
                            "id": "example",
                            "repo": "owner/repo",
                            "origin": "https://github.com/owner/repo",
                            "revision": "a" * 40,
                            "licenseId": "MIT",
                            "licenseEvidence": "LICENSE",
                            "localPath": "data/raw/example",
                            "groupId": "github-owner-repo",
                            "rightsReviewedAtUtc": "2026-10-07T01:45:00Z",
                            "includeExtensions": [".html", ".css", ".js"],
                            "reviewStatus": "license-file-verified",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_materializes_reviewed_sources_and_writes_local_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = self._registry(root)
            policy = self._policy(root)

            def fake_materialize(item, registry_root):
                destination = registry_root / item["localPath"]
                destination.mkdir(parents=True)
                (destination / "LICENSE").write_text("MIT fixture", encoding="utf-8")
                return {"id": item["id"], "revision": item["revision"], "alreadyVerified": False}

            with patch("plex_training.web_materialize._materialize_one", side_effect=fake_materialize):
                result = materialize_sources(registry, policy_path=policy)

            self.assertEqual(result["sourceCount"], 1)
            manifest = json.loads((root / "sources.p2-26.local.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"][0]["rightsReviewStatus"], "approved")
            self.assertEqual(manifest["sources"][0]["licenseId"], "MIT")

    def test_rejects_unreviewed_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = self._registry(root)
            value = json.loads(registry.read_text(encoding="utf-8"))
            value["sources"][0]["reviewStatus"] = "pending"
            registry.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not license-file verified"):
                materialize_sources(registry, policy_path=self._policy(root))


if __name__ == "__main__":
    unittest.main()
