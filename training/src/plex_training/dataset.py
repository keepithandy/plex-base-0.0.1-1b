"""Offline, license-gated corpus curation and reproducible grouped splits."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PIPELINE_VERSION = "p1-14.2"
FAMILY_SPLIT_PIPELINE_VERSION = "p2-02.0"
MAX_SOURCE_MANIFEST_BYTES = 1024 * 1024
MAX_SAMPLE_BYTES = 1024 * 1024
DEFAULT_VALIDATION_PERCENT = 10
DEFAULT_SEED = 1337

SUPPORTED_EXTENSIONS = frozenset(
    {
        ".c", ".cc", ".cjs", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
        ".java", ".js", ".json", ".jsx", ".kt", ".md", ".mjs", ".php",
        ".ps1", ".py", ".rb", ".rs", ".sh", ".sql", ".swift", ".toml",
        ".ts", ".tsx", ".txt", ".yaml", ".yml",
    }
)
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git", ".hg", ".svn", ".venv", ".uv-cache", "venv", "node_modules",
        "vendor", "third_party", "dist", "build", "coverage", "target", "artifacts",
        "__pycache__", ".mypy_cache", ".pytest_cache", "site-packages",
    }
)

_SECRET_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{30,})\b",
        r"\bglpat-[A-Za-z0-9_-]{20,}\b",
        r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
        r"\bAIza[0-9A-Za-z_-]{30,}\b",
        r"\bhttps?://[^/\s:@]+:[^/\s@]+@",
        r"(?im)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*"
        r"([\"'])(?!(?:example|sample|changeme|change-me|placeholder|your[_-].*?|<[^>]+>)\1)"
        r"[^\"'\r\n]{8,}\1",
    )
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_WINDOWS_PROMOTION_RETRY_DELAYS = (0.05, 0.10, 0.20, 0.40, 0.80, 1.20, 1.60)
_WINDOWS_TRANSIENT_PROMOTION_ERRORS = frozenset({5, 32})


def _promote_staging_directory(staging: Path, output_dir: Path) -> None:
    """Atomically promote a completed dataset, retrying transient Windows locks."""
    attempts = 1 + len(_WINDOWS_PROMOTION_RETRY_DELAYS)
    for attempt in range(attempts):
        try:
            os.replace(staging, output_dir)
            return
        except PermissionError as exc:
            winerror = getattr(exc, "winerror", None)
            if winerror not in _WINDOWS_TRANSIENT_PROMOTION_ERRORS:
                raise
            if output_dir.exists():
                raise FileExistsError(
                    "Dataset output appeared while retrying staged dataset promotion"
                ) from exc
            if attempt >= len(_WINDOWS_PROMOTION_RETRY_DELAYS):
                raise
            time.sleep(_WINDOWS_PROMOTION_RETRY_DELAYS[attempt])


def _text(value: object, field: str, source_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Source {source_id!r} must provide {field}")
    result = value.strip()
    if result.lower() in {"unknown", "pending", "replace-me", "todo"}:
        raise ValueError(f"Source {source_id!r} must replace the {field} placeholder")
    return result


def _parse_catalog(path: Path) -> tuple[list[dict[str, Any]], bytes, str]:
    if path.is_symlink():
        raise ValueError("Source catalog must not be a symbolic link")
    try:
        catalog_path = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Source catalog is unavailable: {path}") from exc
    if not catalog_path.is_file() or catalog_path.stat().st_size > MAX_SOURCE_MANIFEST_BYTES:
        raise ValueError("Source catalog must be a regular JSON file no larger than 1 MiB")
    raw_catalog = catalog_path.read_bytes()
    try:
        catalog = json.loads(raw_catalog.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Source catalog must be valid UTF-8 JSON") from exc
    if not isinstance(catalog, dict) or catalog.get("schemaVersion") != 1:
        raise ValueError("Source catalog schemaVersion must be 1")
    raw_sources = catalog.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("Source catalog must contain at least one reviewed source")
    split_strategy = catalog.get("splitStrategy", "source-groups-v1")
    if split_strategy not in {"source-groups-v1", "family-stratified-groups-v1"}:
        raise ValueError("Source catalog has an unsupported splitStrategy")

    catalog_root = catalog_path.parent.resolve()
    sources: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in raw_sources:
        if not isinstance(item, dict):
            raise ValueError("Every source catalog entry must be an object")
        source_id = _text(item.get("id"), "id", "catalog entry")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", source_id):
            raise ValueError(f"Source id {source_id!r} must use letters, digits, dot, underscore, or hyphen")
        if source_id in seen_ids:
            raise ValueError(f"Duplicate source id: {source_id}")
        seen_ids.add(source_id)
        if item.get("rightsReviewStatus") != "approved":
            raise ValueError(
                f"Source {source_id!r} is not approved; review its license and permissions before inclusion"
            )
        relative_root_value = _text(item.get("localPath"), "localPath", source_id)
        relative_root = Path(relative_root_value)
        if relative_root.is_absolute() or ".." in relative_root.parts:
            raise ValueError(f"Source {source_id!r} localPath must stay beneath the source catalog")
        if (catalog_root / relative_root).is_symlink():
            raise ValueError(f"Source {source_id!r} root must not be a symbolic link")
        try:
            source_root = (catalog_root / relative_root).resolve(strict=True)
            source_root.relative_to(catalog_root)
        except (OSError, ValueError) as exc:
            raise ValueError(f"Source {source_id!r} localPath is unavailable or outside the catalog directory") from exc
        if not source_root.is_dir():
            raise ValueError(f"Source {source_id!r} localPath must be a directory")

        origin = _text(item.get("origin"), "origin", source_id)
        parsed_origin = urlparse(origin)
        if parsed_origin.username or parsed_origin.password or parsed_origin.query:
            raise ValueError(f"Source {source_id!r} origin must not contain credentials or query parameters")
        license_evidence = _text(item.get("licenseEvidence"), "licenseEvidence", source_id)
        parsed_evidence = urlparse(license_evidence)
        if parsed_evidence.username or parsed_evidence.password:
            raise ValueError(f"Source {source_id!r} licenseEvidence must not contain embedded credentials")
        license_notice = None
        if parsed_evidence.scheme not in {"http", "https"}:
            evidence_path = Path(license_evidence)
            if evidence_path.is_absolute() or ".." in evidence_path.parts:
                raise ValueError(f"Source {source_id!r} licenseEvidence must be a safe relative path or URL")
            notice_path = source_root / evidence_path
            try:
                if notice_path.is_symlink():
                    raise ValueError("License evidence must not be a symbolic link")
                notice_path = notice_path.resolve(strict=True)
                notice_path.relative_to(source_root)
                if not notice_path.is_file() or not 0 < notice_path.stat().st_size <= MAX_SAMPLE_BYTES:
                    raise ValueError("License evidence must be a nonempty file no larger than 1 MiB")
                with notice_path.open("rb") as notice_stream:
                    license_notice = notice_stream.read(MAX_SAMPLE_BYTES + 1)
                if len(license_notice) > MAX_SAMPLE_BYTES:
                    raise ValueError("License evidence exceeds 1 MiB")
            except (OSError, ValueError) as exc:
                raise ValueError(f"Source {source_id!r} local license evidence is unavailable or unsafe") from exc
        extensions_value = item.get("includeExtensions")
        if extensions_value is None:
            extensions = SUPPORTED_EXTENSIONS
        elif (
            isinstance(extensions_value, list)
            and all(isinstance(value, str) for value in extensions_value)
        ):
            extensions = frozenset(value.lower() for value in extensions_value)
            unknown_extensions = extensions - SUPPORTED_EXTENSIONS
            if unknown_extensions:
                raise ValueError(
                    f"Source {source_id!r} includes unsupported extensions: "
                    + ", ".join(sorted(unknown_extensions))
                )
        else:
            raise ValueError(f"Source {source_id!r} includeExtensions must be an array of extensions")

        review_date = _text(item.get("rightsReviewedAtUtc"), "rightsReviewedAtUtc", source_id)
        try:
            reviewed_at = datetime.fromisoformat(review_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Source {source_id!r} rightsReviewedAtUtc must be an ISO-8601 UTC timestamp") from exc
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() != timedelta(0):
            raise ValueError(f"Source {source_id!r} rightsReviewedAtUtc must include the UTC offset")
        group_id = _text(item.get("groupId"), "groupId", source_id)
        family_id = _text(item.get("sourceFamilyId", group_id), "sourceFamilyId", source_id)
        raw_split_rules = item.get("splitGroupRules", [])
        if not isinstance(raw_split_rules, list):
            raise ValueError(f"Source {source_id!r} splitGroupRules must be an array")
        split_group_rules: list[dict[str, Any]] = []
        seen_rule_ids: set[str] = set()
        seen_prefixes: set[str] = set()
        for rule in raw_split_rules:
            if not isinstance(rule, dict):
                raise ValueError(f"Source {source_id!r} split-group rules must be objects")
            rule_id = _text(rule.get("id"), "splitGroupRules.id", source_id)
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", rule_id) or rule_id in seen_rule_ids:
                raise ValueError(f"Source {source_id!r} has an invalid or duplicate split-group id")
            seen_rule_ids.add(rule_id)
            prefixes = rule.get("pathPrefixes")
            if not isinstance(prefixes, list) or not prefixes or not all(isinstance(value, str) for value in prefixes):
                raise ValueError(f"Source {source_id!r} split-group pathPrefixes must be a nonempty string array")
            clean_prefixes: list[str] = []
            for prefix in prefixes:
                if (not prefix or prefix.startswith("/") or "\\" in prefix
                        or any(part in {"", ".", ".."} for part in prefix.rstrip("/").split("/"))
                        or not prefix.endswith("/")):
                    raise ValueError(f"Source {source_id!r} has an unsafe split-group path prefix")
                if prefix in seen_prefixes:
                    raise ValueError(f"Source {source_id!r} has duplicate split-group path prefixes")
                seen_prefixes.add(prefix)
                clean_prefixes.append(prefix)
            split_group_rules.append({"id": rule_id, "pathPrefixes": clean_prefixes})

        sources.append(
            {
                "id": source_id,
                "root": source_root,
                "origin": origin,
                "revision": _text(item.get("revision"), "revision", source_id),
                "licenseId": _text(item.get("licenseId"), "licenseId", source_id),
                "licenseEvidence": license_evidence,
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": review_date,
                "groupId": group_id,
                "sourceFamilyId": family_id,
                "splitGroupRules": split_group_rules,
                "includeExtensions": extensions,
                "_licenseNotice": license_notice,
            }
        )
    if split_strategy == "family-stratified-groups-v1" and any(
        not source["splitGroupRules"] for source in sources
    ):
        raise ValueError("Family-stratified splitting requires path rules for every source")
    return sorted(sources, key=lambda source: source["id"]), raw_catalog, split_strategy


def _split_group_for_path(source: dict[str, Any], relative_path: str) -> str:
    rules = source["splitGroupRules"]
    if not rules:
        return source["groupId"]
    matches = [
        rule["id"]
        for rule in rules
        if any(relative_path.startswith(prefix) for prefix in rule["pathPrefixes"])
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Source {source['id']!r} file {relative_path!r} must match exactly one split-group rule"
        )
    return matches[0]


def _iter_source_files(source: dict[str, Any]):
    root: Path = source["root"]
    extensions: frozenset[str] = source["includeExtensions"]
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if name.lower() not in EXCLUDED_DIRECTORIES
            and not (current_path / name).is_symlink()
        )
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink() or path.suffix.lower() not in extensions:
                continue
            yield path, path.relative_to(root).as_posix()


def _has_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)


def _normalise_text(raw: bytes) -> tuple[str | None, str | None]:
    if len(raw) > MAX_SAMPLE_BYTES:
        return None, "sample_too_large"
    try:
        text = raw.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return None, "invalid_utf8"
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    if not text.strip():
        return None, "empty"
    if "\x00" in text:
        return None, "binary_content"
    controls = sum(ord(char) < 32 and char not in "\n\r\t\f" for char in text)
    if controls / max(len(text), 1) > 0.01:
        return None, "binary_content"
    if len(text.encode("utf-8")) < 8:
        return None, "too_short"
    if _has_secret(text):
        return None, "secret_pattern"
    return text, None


def _validate_syntax(path: Path, text: str, node: str | None) -> str | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".py":
            ast.parse(text, filename=path.name)
        elif suffix == ".json":
            json.loads(text)
        elif suffix in {".js", ".mjs", ".cjs"}:
            if node is None:
                return "javascript_validator_unavailable"
            checked = subprocess.run(
                [node, "--check", str(path)],
                capture_output=True,
                timeout=15,
                check=False,
            )
            if checked.returncode != 0:
                return "invalid_javascript_syntax"
    except SyntaxError:
        return "invalid_python_syntax"
    except json.JSONDecodeError:
        return "invalid_json_syntax"
    except RecursionError:
        return "source_syntax_too_deep"
    except (OSError, subprocess.TimeoutExpired):
        return "syntax_validator_failed"
    return None


def _node_info() -> tuple[str | None, str | None]:
    node = shutil.which("node")
    if node is None:
        return None, None
    try:
        result = subprocess.run(
            [node, "--version"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    version = result.stdout.strip() if result.returncode == 0 else None
    return (node, version) if version else (None, None)


def _group_split(groups: set[str], validation_percent: int, seed: int) -> set[str]:
    if not 1 <= validation_percent <= 50:
        raise ValueError("validation-percent must be an integer from 1 to 50")
    if len(groups) < 2:
        raise ValueError("At least two distinct source groups are needed for a leak-resistant split")
    ranked = sorted(
        groups,
        key=lambda group: hashlib.sha256(f"{seed}\0{group}".encode("utf-8")).digest(),
    )
    validation_count = min(len(groups) - 1, max(1, (len(groups) * validation_percent + 50) // 100))
    return set(ranked[:validation_count])


def _family_stratified_group_split(
    groups_by_family: dict[str, set[str]], validation_percent: int, seed: int,
) -> set[tuple[str, str]]:
    """Choose complete groups within each family so every family appears in both splits."""
    if not 1 <= validation_percent <= 50:
        raise ValueError("validation-percent must be an integer from 1 to 50")
    if len(groups_by_family) < 2:
        raise ValueError("Family-stratified splitting requires at least two source families")
    validation: set[tuple[str, str]] = set()
    for family, groups in sorted(groups_by_family.items()):
        if len(groups) < 2:
            raise ValueError(
                f"Source family {family!r} needs at least two independent split groups"
            )
        ranked = sorted(
            groups,
            key=lambda group: hashlib.sha256(
                f"{seed}\0{family}\0{group}".encode("utf-8")
            ).digest(),
        )
        validation_count = min(
            len(groups) - 1,
            max(1, (len(groups) * validation_percent + 50) // 100),
        )
        validation.update((family, group) for group in ranked[:validation_count])
    return validation


def build_dataset(
    source_manifest: Path,
    output_dir: Path,
    *,
    validation_percent: int = DEFAULT_VALIDATION_PERCENT,
    seed: int = DEFAULT_SEED,
    storage_limit_bytes: int,
) -> dict[str, Any]:
    """Build local JSONL splits from reviewed, pinned sources without network access."""
    if storage_limit_bytes <= 0:
        raise ValueError("No storage remains in the configured artifact allocation")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(validation_percent, int) or isinstance(validation_percent, bool) or not 1 <= validation_percent <= 50:
        raise ValueError("validation-percent must be an integer from 1 to 50")
    sources, raw_catalog, split_strategy = _parse_catalog(source_manifest)
    output_dir = output_dir.resolve(strict=False)
    if output_dir.exists():
        raise FileExistsError("Dataset output already exists; select a new output directory")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # tempfile.mkdtemp applies a private Windows ACL that can block later
    # tokenizer/training processes. A unique child created with mkdir inherits
    # the destination parent's permissions while preserving atomic promotion.
    staging = output_dir.parent / f".{output_dir.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    node, node_version = _node_info()
    hash_occurrences: dict[str, set[tuple[str, str]]] = {}
    first_content_hashes: set[str] = set()
    records: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    skipped_files: list[dict[str, str]] = []
    source_summaries: list[dict[str, Any]] = []
    license_notice_bytes = 0
    try:
        for source in sources:
            notice_info = {}
            if source["_licenseNotice"] is not None:
                notice = source["_licenseNotice"]
                license_notice_bytes += len(notice)
                if license_notice_bytes > storage_limit_bytes:
                    raise ValueError("License notices exceed the remaining artifact storage allocation")
                notice_relative = f"licenses/{source['id']}.txt"
                notice_output = staging / notice_relative
                notice_output.parent.mkdir(exist_ok=True)
                notice_output.write_bytes(notice)
                notice_info = {
                    "licenseNoticeFile": notice_relative,
                    "licenseNoticeSha256": _sha256(notice),
                }
            source_counts = {"accepted": 0, "duplicates": 0, "skipped": 0}
            source_split_groups: set[str] = set()
            for path, relative_path in _iter_source_files(source):
                text = None
                try:
                    size = path.stat().st_size
                    if size > MAX_SAMPLE_BYTES:
                        reason = "sample_too_large"
                    else:
                        with path.open("rb") as source_stream:
                            raw = source_stream.read(MAX_SAMPLE_BYTES + 1)
                        text, reason = _normalise_text(raw)
                        if text is not None:
                            reason = _validate_syntax(path, text, node)
                except OSError:
                    text, reason = None, "unreadable_file"
                    raw = b""
                if reason is not None or text is None:
                    key = reason or "invalid_content"
                    skipped[key] = skipped.get(key, 0) + 1
                    skipped_files.append(
                        {"sourceId": source["id"], "path": relative_path, "reason": key}
                    )
                    source_counts["skipped"] += 1
                    continue
                content_bytes = text.encode("utf-8")
                content_hash = _sha256(content_bytes)
                split_group_id = _split_group_for_path(source, relative_path)
                family_id = source["sourceFamilyId"]
                hash_occurrences.setdefault(content_hash, set()).add((family_id, split_group_id))
                if content_hash in first_content_hashes:
                    skipped["duplicate_content"] = skipped.get("duplicate_content", 0) + 1
                    skipped_files.append(
                        {"sourceId": source["id"], "path": relative_path, "reason": "duplicate_content"}
                    )
                    source_counts["duplicates"] += 1
                    continue
                first_content_hashes.add(content_hash)
                record_id = _sha256(
                    f"{source['id']}\0{relative_path}\0{content_hash}".encode("utf-8")
                )
                records.append(
                    {
                        "recordId": record_id,
                        "sourceId": source["id"],
                        "groupId": source["groupId"],
                        "sourceFamilyId": family_id,
                        "splitGroupId": split_group_id,
                        "path": relative_path,
                        "contentSha256": content_hash,
                        "_sourcePath": path,
                        "_sourceRoot": source["root"],
                    }
                )
                source_counts["accepted"] += 1
                source_split_groups.add(split_group_id)
            source_summaries.append(
                {
                    "id": source["id"],
                    "origin": source["origin"],
                    "revision": source["revision"],
                    "licenseId": source["licenseId"],
                    "licenseEvidence": source["licenseEvidence"],
                    "rightsReviewStatus": source["rightsReviewStatus"],
                    "rightsReviewedAtUtc": source["rightsReviewedAtUtc"],
                    "groupId": source["groupId"],
                    "acceptedFiles": source_counts["accepted"],
                    "duplicateFiles": source_counts["duplicates"],
                    "skippedFiles": source_counts["skipped"],
                    **({"sourceFamilyId": source["sourceFamilyId"],
                       "splitGroupIds": sorted(source_split_groups)}
                       if split_strategy == "family-stratified-groups-v1" else {}),
                    **notice_info,
                }
            )
        if not records:
            raise ValueError("No source files passed the configured quality and secret filters")
        if split_strategy == "family-stratified-groups-v1":
            groups_by_family: dict[str, set[str]] = {}
            for record in records:
                groups_by_family.setdefault(record["sourceFamilyId"], set()).add(record["splitGroupId"])
            validation_groups = _family_stratified_group_split(groups_by_family, validation_percent, seed)
        else:
            validation_groups = _group_split(
                {record["groupId"] for record in records}, validation_percent, seed
            )

        def record_is_validation(record: dict[str, Any]) -> bool:
            if split_strategy == "family-stratified-groups-v1":
                return (record["sourceFamilyId"], record["splitGroupId"]) in validation_groups
            return record["groupId"] in validation_groups

        if split_strategy == "family-stratified-groups-v1":
            for occurrences in hash_occurrences.values():
                if len({(family, group) for family, group in occurrences}) <= 1:
                    continue
                occurrence_splits = {
                    "validation" if (family, group) in validation_groups else "train"
                    for family, group in occurrences
                }
                if len(occurrence_splits) > 1:
                    raise ValueError("Exact normalized content crosses the train/development split")
        records.sort(key=lambda record: (record["sourceId"], record["path"], record["recordId"]))

        train_path = staging / "train.jsonl"
        validation_path = staging / "validation.jsonl"
        split_counts = {"train": 0, "validation": 0}
        split_group_ids = {"train": set(), "validation": set()}
        split_hashes = {"train": hashlib.sha256(), "validation": hashlib.sha256()}
        bytes_written = 0
        with train_path.open("xb") as train_stream, validation_path.open("xb") as validation_stream:
            for record in records:
                split = "validation" if record_is_validation(record) else "train"
                source_path: Path = record["_sourcePath"]
                if source_path.is_symlink():
                    raise ValueError("A source file changed to a symbolic link during dataset creation")
                try:
                    resolved_source = source_path.resolve(strict=True)
                    resolved_source.relative_to(record["_sourceRoot"])
                    with resolved_source.open("rb") as source_stream:
                        current_raw = source_stream.read(MAX_SAMPLE_BYTES + 1)
                    current_text, reason = _normalise_text(current_raw)
                except (OSError, ValueError) as exc:
                    raise ValueError("A source file changed or became unavailable during dataset creation") from exc
                if reason is not None or current_text is None:
                    raise ValueError("A source file failed its curation checks during dataset creation")
                if _sha256(current_text.encode("utf-8")) != record["contentSha256"]:
                    raise ValueError("A source file changed during dataset creation; rerun from a stable revision")
                output_record = {
                    key: value
                    for key, value in record.items()
                    if not key.startswith("_")
                }
                if split_strategy != "family-stratified-groups-v1":
                    output_record.pop("sourceFamilyId", None)
                    output_record.pop("splitGroupId", None)
                output_record["text"] = current_text
                line = (
                    json.dumps(
                        output_record,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                bytes_written += len(line)
                if bytes_written + license_notice_bytes > storage_limit_bytes:
                    raise ValueError("Curated dataset exceeds the remaining artifact storage allocation")
                stream = validation_stream if split == "validation" else train_stream
                stream.write(line)
                split_hashes[split].update(line)
                split_counts[split] += 1
                split_group_ids[split].add(
                    f"{record['sourceFamilyId']}:{record['splitGroupId']}"
                    if split_strategy == "family-stratified-groups-v1" else record["groupId"]
                )

        pipeline_version = (
            FAMILY_SPLIT_PIPELINE_VERSION
            if split_strategy == "family-stratified-groups-v1" else PIPELINE_VERSION
        )
        split_info: dict[str, Any] = {
            "method": (
                "family-stratified-split-groups-sha256-v1"
                if split_strategy == "family-stratified-groups-v1" else "grouped-sha256-v1"
            ),
            "seed": seed,
            "validationPercentOfGroups": validation_percent,
            "trainGroups": len(split_group_ids["train"]),
            "validationGroups": len(split_group_ids["validation"]),
        }
        if split_strategy == "family-stratified-groups-v1":
            family_counts: dict[str, dict[str, set[str]]] = {}
            for record in records:
                split = "validation" if record_is_validation(record) else "train"
                family_groups = family_counts.setdefault(
                    record["sourceFamilyId"], {"train": set(), "validation": set()}
                )
                family_groups[split].add(record["splitGroupId"])
            split_info["families"] = {
                family: {
                    "trainGroups": len(groups["train"]),
                    "validationGroups": len(groups["validation"]),
                }
                for family, groups in sorted(family_counts.items())
            }

        manifest: dict[str, Any] = {
            "schemaVersion": 1,
            "pipelineVersion": pipeline_version,
            "recordFormat": "jsonl; one reviewed source file per record",
            "normalization": "UTF-8 strict, BOM stripped, CRLF/CR mapped to LF, Unicode NFC",
            "sourceCatalogSha256": _sha256(raw_catalog),
            "split": split_info,
            "filters": {
                "allowedExtensions": sorted(SUPPORTED_EXTENSIONS),
                "excludedDirectories": sorted(EXCLUDED_DIRECTORIES),
                "maximumSampleBytes": MAX_SAMPLE_BYTES,
                "checks": [
                    "strict UTF-8 and non-binary text",
                    "known credential and secret patterns",
                    "Python AST syntax when extension is .py",
                    "JSON syntax when extension is .json",
                    "Node --check syntax for .js/.mjs/.cjs; excluded if Node is unavailable",
                ],
                "skippedCounts": dict(sorted(skipped.items())),
                "skippedFiles": skipped_files,
            },
            "validators": {"python": "ast.parse", "json": "json.loads", "nodeVersion": node_version},
            "sources": source_summaries,
            "summary": {
                "records": len(records),
                "trainRecords": split_counts["train"],
                "validationRecords": split_counts["validation"],
                "trainJsonlSha256": split_hashes["train"].hexdigest(),
                "validationJsonlSha256": split_hashes["validation"].hexdigest(),
                "jsonlBytes": bytes_written,
                "licenseNoticeBytes": license_notice_bytes,
            },
        }
        manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        total_bytes = bytes_written + license_notice_bytes + len(manifest_bytes)
        if total_bytes > storage_limit_bytes:
            raise ValueError("Curated dataset and manifest exceed the remaining artifact storage allocation")
        (staging / "manifest.json").write_bytes(manifest_bytes)
        _promote_staging_directory(staging, output_dir)
        return {
            "directory": output_dir.name,
            "manifest": "manifest.json",
            "records": len(records),
            "trainRecords": split_counts["train"],
            "validationRecords": split_counts["validation"],
            "skippedCounts": dict(sorted(skipped.items())),
            "bytes": total_bytes,
        }
    except Exception:
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except OSError:
                # Preserve the original preparation error if a transient Windows/OneDrive
                # handle also delays cleanup of the private staging directory.
                pass
        raise
