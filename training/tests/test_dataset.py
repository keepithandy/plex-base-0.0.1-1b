import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from plex_training.cli import main
from plex_training.dataset import _validate_syntax, build_dataset


class DatasetPipelineTests(unittest.TestCase):
    def _write_catalog(self, root: Path, source_rows: list[dict[str, str]]) -> Path:
        catalog = root / "sources.json"
        catalog.write_text(
            json.dumps({"schemaVersion": 1, "sources": source_rows}, indent=2),
            encoding="utf-8",
        )
        return catalog

    def _source(self, root: Path, source_id: str, group_id: str) -> dict[str, str]:
        source_path = root / "raw" / source_id
        source_path.mkdir(parents=True)
        (source_path / "LICENSE").write_bytes(b"Fixture permission notice retained with copies.\n")
        return {
            "id": source_id,
            "localPath": f"raw/{source_id}",
            "origin": f"https://example.invalid/{source_id}",
            "revision": "fixture-commit-1",
            "licenseId": "MIT",
            "licenseEvidence": "LICENSE",
            "rightsReviewStatus": "approved",
            "rightsReviewedAtUtc": "2026-10-03T00:00:00Z",
            "groupId": group_id,
            "includeExtensions": [".py", ".md", ".json"],
        }

    def test_build_is_reproducible_filters_bad_files_and_splits_source_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_a = self._source(root, "alpha", "project-family")
            source_b = self._source(root, "alpha-related", "project-family")
            source_c = self._source(root, "bravo", "project-bravo")
            source_d = self._source(root, "charlie", "project-charlie")

            (root / "raw/alpha/add.py").write_text(
                "def add(left, right):\n    return left + right\n", encoding="utf-8"
            )
            (root / "raw/alpha/README.md").write_text(
                "This explanation describes a small addition function.\n", encoding="utf-8"
            )
            (root / "raw/alpha/broken.py").write_text("def broken(:\n", encoding="utf-8")
            (root / "raw/alpha/secret.py").write_text(
                'TOKEN = "ghp_123456789012345678901234567890123456"\n', encoding="utf-8"
            )
            (root / "raw/alpha/broken.json").write_text("{broken json", encoding="utf-8")
            (root / "raw/alpha/vendor").mkdir()
            (root / "raw/alpha/vendor/dependency.py").write_text(
                "def vendor(value):\n    return value\n", encoding="utf-8"
            )
            (root / "raw/alpha-related/duplicate.py").write_text(
                "def add(left, right):\n    return left + right\n", encoding="utf-8"
            )
            (root / "raw/alpha-related/README.md").write_text(
                "This related project explains a slightly different operation.\n", encoding="utf-8"
            )
            (root / "raw/bravo/compute.py").write_text(
                "def multiply(left, right):\n    return left * right\n", encoding="utf-8"
            )
            (root / "raw/bravo/README.md").write_text(
                "This project explains multiplying two integer values.\n", encoding="utf-8"
            )
            (root / "raw/charlie/compute.py").write_text(
                "def subtract(left, right):\n    return left - right\n", encoding="utf-8"
            )
            (root / "raw/charlie/README.md").write_text(
                "This project explains subtracting one value from another.\n", encoding="utf-8"
            )
            catalog = self._write_catalog(root, [source_a, source_b, source_c, source_d])

            first = build_dataset(
                catalog, root / "output-one", validation_percent=20, seed=99,
                storage_limit_bytes=1024 * 1024,
            )
            second = build_dataset(
                catalog, root / "output-two", validation_percent=20, seed=99,
                storage_limit_bytes=1024 * 1024,
            )

            self.assertEqual(first["records"], 7)
            self.assertEqual(first["skippedCounts"]["duplicate_content"], 1)
            self.assertEqual(first["skippedCounts"]["secret_pattern"], 1)
            self.assertEqual(first["skippedCounts"]["invalid_python_syntax"], 1)
            self.assertEqual(first["skippedCounts"]["invalid_json_syntax"], 1)
            for filename in ("train.jsonl", "validation.jsonl", "manifest.json"):
                self.assertEqual(
                    (root / "output-one" / filename).read_bytes(),
                    (root / "output-two" / filename).read_bytes(),
                )

            train_rows = [
                json.loads(line)
                for line in (root / "output-one/train.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            validation_rows = [
                json.loads(line)
                for line in (root / "output-one/validation.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            train_groups = {row["groupId"] for row in train_rows}
            validation_groups = {row["groupId"] for row in validation_rows}
            self.assertTrue(train_groups.isdisjoint(validation_groups))
            self.assertEqual(len(train_rows) + len(validation_rows), first["records"])
            all_rows = train_rows + validation_rows
            self.assertFalse(any(Path(row["path"]).is_absolute() for row in all_rows))
            self.assertNotIn("localPath", json.loads((root / "output-one/manifest.json").read_text())["sources"][0])
            manifest = json.loads((root / "output-one/manifest.json").read_text())
            for source in manifest["sources"]:
                original_notice = (root / "raw" / source["id"] / "LICENSE").read_bytes()
                copied_notice = (root / "output-one" / source["licenseNoticeFile"]).read_bytes()
                self.assertEqual(original_notice, copied_notice)
                self.assertEqual(hashlib.sha256(copied_notice).hexdigest(), source["licenseNoticeSha256"])

    def test_unreviewed_source_is_rejected_before_output_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._source(root, "not-reviewed", "pending-group")
            source["rightsReviewStatus"] = "pending"
            catalog = self._write_catalog(root, [source])
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "not approved"):
                build_dataset(catalog, output, storage_limit_bytes=1024)
            self.assertFalse(output.exists())

    def test_missing_local_license_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._source(root, "missing-license", "group")
            (root / "raw/missing-license/LICENSE").unlink()
            catalog = self._write_catalog(root, [source])
            with self.assertRaisesRegex(ValueError, "local license evidence"):
                build_dataset(catalog, root / "output", storage_limit_bytes=1024**2)
            self.assertFalse((root / "output").exists())

    def test_one_group_cannot_be_split_into_train_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._source(root, "only", "one-project")
            (root / "raw/only/example.py").write_text(
                "def example(value):\n    return value + 1\n", encoding="utf-8"
            )
            catalog = self._write_catalog(root, [source])
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "At least two distinct source groups"):
                build_dataset(catalog, output, storage_limit_bytes=1024 * 1024)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".output.staging-*")), [])

    def test_cli_writes_dataset_beneath_artifact_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha", "group-alpha")
            bravo = self._source(root, "bravo", "group-bravo")
            (root / "raw/alpha/example.py").write_text(
                "def alpha(value):\n    return value + 2\n", encoding="utf-8"
            )
            (root / "raw/bravo/example.py").write_text(
                "def bravo(value):\n    return value * 3\n", encoding="utf-8"
            )
            catalog = self._write_catalog(root, [alpha, bravo])
            artifact_root = root / "artifacts"
            output = StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "dataset-build",
                        "--source-manifest",
                        str(catalog),
                        "--artifact-root",
                        str(artifact_root),
                        "--output-dir",
                        "curated",
                        "--validation-percent",
                        "50",
                    ]
                )

            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["outputDirectory"], "curated")
            self.assertEqual(report["records"], 2)
            self.assertTrue((artifact_root / "curated/train.jsonl").is_file())
            self.assertTrue((artifact_root / "curated/validation.jsonl").is_file())

    def test_storage_limit_failure_leaves_no_partial_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alpha = self._source(root, "alpha", "group-alpha")
            bravo = self._source(root, "bravo", "group-bravo")
            (root / "raw/alpha/example.py").write_text(
                "def alpha(value):\n    return value + 2\n", encoding="utf-8"
            )
            (root / "raw/bravo/example.py").write_text(
                "def bravo(value):\n    return value * 3\n", encoding="utf-8"
            )
            catalog = self._write_catalog(root, [alpha, bravo])
            output = root / "output"
            with self.assertRaisesRegex(ValueError, "storage allocation"):
                build_dataset(
                    catalog, output, validation_percent=50, storage_limit_bytes=1
                )
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".output.staging-*")), [])

    def test_javascript_syntax_filter_uses_node_check_without_running_source(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.mjs"
            invalid = root / "invalid.mjs"
            valid.write_text("export const answer = 42;\n", encoding="utf-8")
            invalid.write_text("export const = 42;\n", encoding="utf-8")
            self.assertIsNone(_validate_syntax(valid, valid.read_text(encoding="utf-8"), node))
            self.assertEqual(
                _validate_syntax(invalid, invalid.read_text(encoding="utf-8"), node),
                "invalid_javascript_syntax",
            )

    def test_cjs_extension_is_accepted_by_catalog_and_syntax_filter(self) -> None:
        if shutil.which("node") is None:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = [self._source(root, name, name) for name in ("alpha", "bravo")]
            for source, number in zip(sources, (1, 2)):
                source["includeExtensions"] = [".cjs"]
                (root / source["localPath"] / "example.cjs").write_text(
                    f"module.exports = {number};\n", encoding="utf-8"
                )
            catalog = self._write_catalog(root, sources)
            result = build_dataset(catalog, root / "output", storage_limit_bytes=1024**2)
            self.assertEqual(result["records"], 2)

    def test_family_stratified_split_keeps_projects_whole_and_families_in_both_splits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for source_id, family_id, prefix in (
                ("microsoft", "microsoft-family", "ms"),
                ("mdn", "mdn-family", "mdn"),
            ):
                source = self._source(root, source_id, family_id)
                source["sourceFamilyId"] = family_id
                source["splitGroupRules"] = [
                    {"id": f"{prefix}-project-{index}", "pathPrefixes": [f"project-{index}/"]}
                    for index in range(3)
                ]
                for index in range(3):
                    project = root / "raw" / source_id / f"project-{index}"
                    project.mkdir()
                    (project / "example.py").write_text(
                        f"def {prefix}_example_{index}(value):\n    return value + {index + 1}\n",
                        encoding="utf-8",
                    )
                sources.append(source)
            catalog = root / "sources.json"
            catalog.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "splitStrategy": "family-stratified-groups-v1",
                    "sources": sources,
                }, indent=2),
                encoding="utf-8",
            )

            first = build_dataset(
                catalog, root / "output-one", validation_percent=30, seed=73,
                storage_limit_bytes=1024 * 1024,
            )
            second = build_dataset(
                catalog, root / "output-two", validation_percent=30, seed=73,
                storage_limit_bytes=1024 * 1024,
            )

            self.assertEqual(first["records"], 6)
            self.assertEqual(first["trainRecords"], 4)
            self.assertEqual(first["validationRecords"], 2)
            manifest = json.loads((root / "output-one" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["split"]["families"], {
                "mdn-family": {"trainGroups": 2, "validationGroups": 1},
                "microsoft-family": {"trainGroups": 2, "validationGroups": 1},
            })
            for filename in ("train.jsonl", "validation.jsonl", "manifest.json"):
                self.assertEqual(
                    (root / "output-one" / filename).read_bytes(),
                    (root / "output-two" / filename).read_bytes(),
                )
            split_groups = {}
            for split in ("train", "validation"):
                rows = [
                    json.loads(line)
                    for line in (root / "output-one" / f"{split}.jsonl")
                    .read_text(encoding="utf-8").splitlines()
                ]
                split_groups[split] = {
                    (row["sourceFamilyId"], row["splitGroupId"]) for row in rows
                }
                self.assertEqual({row["sourceFamilyId"] for row in rows},
                                 {"mdn-family", "microsoft-family"})
            self.assertTrue(split_groups["train"].isdisjoint(split_groups["validation"]))

    def test_family_stratified_split_rejects_families_with_only_one_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for source_id in ("alpha", "bravo"):
                source = self._source(root, source_id, source_id)
                source["sourceFamilyId"] = source_id
                source["splitGroupRules"] = [
                    {"id": "only-project", "pathPrefixes": ["project/"]}
                ]
                project = root / "raw" / source_id / "project"
                project.mkdir()
                (project / "example.py").write_text(
                    f"def {source_id}_example(value):\n    return value + 1\n",
                    encoding="utf-8",
                )
                sources.append(source)
            catalog = root / "sources.json"
            catalog.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "splitStrategy": "family-stratified-groups-v1",
                    "sources": sources,
                }, indent=2),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "at least two independent split groups"):
                build_dataset(catalog, root / "output", storage_limit_bytes=1024**2)
            self.assertFalse((root / "output").exists())

    def test_family_stratified_split_rejects_duplicate_content_crossing_splits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for source_id, family_id, prefix in (
                ("alpha", "alpha-family", "a"),
                ("bravo", "bravo-family", "b"),
            ):
                source = self._source(root, source_id, family_id)
                source["sourceFamilyId"] = family_id
                source["splitGroupRules"] = [
                    {"id": f"{prefix}-project-{index}", "pathPrefixes": [f"project-{index}/"]}
                    for index in range(2)
                ]
                for index in range(2):
                    project = root / "raw" / source_id / f"project-{index}"
                    project.mkdir()
                    (project / "duplicate.py").write_text(
                        "def shared(value):\n    return value + 4\n", encoding="utf-8"
                    )
                    (project / "unique.py").write_text(
                        f"def {prefix}_unique_{index}(value):\n    return value * {index + 2}\n",
                        encoding="utf-8",
                    )
                sources.append(source)
            catalog = root / "sources.json"
            catalog.write_text(
                json.dumps({
                    "schemaVersion": 1,
                    "splitStrategy": "family-stratified-groups-v1",
                    "sources": sources,
                }, indent=2),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Exact normalized content crosses"):
                build_dataset(
                    catalog, root / "output", validation_percent=50, seed=19,
                    storage_limit_bytes=1024**2,
                )
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
