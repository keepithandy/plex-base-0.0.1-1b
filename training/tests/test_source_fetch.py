import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.source_fetch import fetch_sources, git_blob_sha1, read_plan


class PublicGitHubResponse(io.BytesIO):
    def geturl(self):
        return "https://raw.githubusercontent.com/example/repository/pinned/file"


class SourceFetchTests(unittest.TestCase):
    def _plan(self, root):
        blobs = {"LICENSE": b"Fixture permission notice.\n", "example.js": b"const answer = 42;\n"}
        plan = {
            "schemaVersion": 1,
            "sources": [{
                "id": "fixture",
                "repo": "example/repository",
                "revision": "a" * 40,
                "files": [
                    {"path": path, "bytes": len(raw), "gitBlobSha1": git_blob_sha1(raw)}
                    for path, raw in blobs.items()
                ],
            }],
        }
        path = root / "lock.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return path, blobs, plan

    def _response(self, blobs):
        def respond(request, **kwargs):
            filename = request.full_url.rsplit("/", 1)[1]
            return PublicGitHubResponse(blobs[filename])
        return respond

    def test_fetch_verifies_pinned_blobs_and_reuses_exact_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, blobs, _ = self._plan(root)
            with patch("plex_training.source_fetch.urlopen", side_effect=self._response(blobs)):
                result = fetch_sources(plan_path)
            self.assertEqual(result["totalBytes"], sum(map(len, blobs.values())))
            self.assertEqual((root / "data/raw/fixture/LICENSE").read_bytes(), blobs["LICENSE"])
            with patch("plex_training.source_fetch.urlopen") as network:
                second = fetch_sources(plan_path)
                network.assert_not_called()
            self.assertTrue(second["sources"][0]["alreadyVerified"])

    def test_hash_mismatch_cleans_staging_and_leaves_no_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, blobs, _ = self._plan(root)
            blobs["example.js"] = b"const answer = 99;\n"
            with patch("plex_training.source_fetch.urlopen", side_effect=self._response(blobs)):
                with self.assertRaisesRegex(ValueError, "differs from the source lock"):
                    fetch_sources(plan_path)
            self.assertFalse((root / "data/raw/fixture").exists())
            self.assertEqual(list((root / "data/raw").glob(".*.fetch-*")), [])

    def test_changed_existing_snapshot_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, blobs, _ = self._plan(root)
            with patch("plex_training.source_fetch.urlopen", side_effect=self._response(blobs)):
                fetch_sources(plan_path)
            changed = root / "data/raw/fixture/example.js"
            changed.write_bytes(b"const answer = 99;\n")
            with self.assertRaisesRegex(ValueError, "differs from the source lock"):
                fetch_sources(plan_path)
            self.assertEqual(changed.read_bytes(), b"const answer = 99;\n")

    def test_path_escape_and_mutable_revision_are_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path, _, plan = self._plan(root)
            plan["sources"][0]["files"][1]["path"] = "../escaped.js"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escape"):
                read_plan(plan_path)
            plan["sources"][0]["files"][1]["path"] = "example.js"
            plan["sources"][0]["revision"] = "main"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "immutable"):
                read_plan(plan_path)
