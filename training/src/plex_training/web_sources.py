"""Plex Web local-source preflight for license, provenance, and web-code quality gates."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .dataset import MAX_SAMPLE_BYTES, _normalise_text

DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "pretraining" / "source-policy.json"
MAX_JSON_BYTES = 1024 * 1024
_GENERATED_MARKERS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bdo not edit\b",
        r"\bauto(?:matically)?[- ]generated\b",
        r"\bgenerated file\b",
        r"@generated\b",
    )
)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} is unavailable: {path}") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"{label} must be a regular JSON file no larger than 1 MiB")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def load_source_policy(path: Path | None = None) -> dict[str, Any]:
    policy = _read_json(DEFAULT_POLICY if path is None else path, "Plex Web source policy")
    if policy.get("schemaVersion") != 1:
        raise ValueError("Plex Web source policy schemaVersion must be 1")
    if policy.get("defaultLicenseDecision") != "reject":
        raise ValueError("Plex Web source policy must reject licenses by default")
    if policy.get("requireLicenseEvidence") is not True:
        raise ValueError("Plex Web source policy must require license evidence")
    if policy.get("requireSourceProvenance") is not True:
        raise ValueError("Plex Web source policy must require source provenance")

    raw_languages = policy.get("languages")
    if not isinstance(raw_languages, dict) or not raw_languages:
        raise ValueError("Plex Web source policy must define languages")
    extension_languages: dict[str, str] = {}
    for language, values in raw_languages.items():
        if not isinstance(language, str) or not language:
            raise ValueError("Plex Web language names must be nonempty strings")
        if not isinstance(values, list) or not values:
            raise ValueError(f"Plex Web language {language!r} must list extensions")
        for value in values:
            if not isinstance(value, str) or not re.fullmatch(r"\.[a-z0-9]+", value):
                raise ValueError("Plex Web extensions must be lowercase dot-prefixed suffixes")
            if value in extension_languages:
                raise ValueError(f"Plex Web extension appears in multiple languages: {value}")
            extension_languages[value] = language

    allowed = policy.get("allowedSpdx")
    if not isinstance(allowed, list) or not allowed or len(set(allowed)) != len(allowed):
        raise ValueError("Plex Web source policy must define unique allowed SPDX identifiers")
    if not all(isinstance(value, str) and value for value in allowed):
        raise ValueError("Plex Web allowed SPDX identifiers must be nonempty strings")

    segments = policy.get("disallowedPathSegments", [])
    suffixes = policy.get("disallowedSuffixes", [])
    if not isinstance(segments, list) or not all(isinstance(v, str) and v for v in segments):
        raise ValueError("disallowedPathSegments must be an array of nonempty strings")
    if not isinstance(suffixes, list) or not all(isinstance(v, str) and v for v in suffixes):
        raise ValueError("disallowedSuffixes must be an array of nonempty strings")

    return {
        **policy,
        "_extensionLanguages": extension_languages,
        "_allowedSpdxSet": frozenset(allowed),
        "_disallowedPathSegmentsSet": frozenset(v.casefold() for v in segments),
        "_disallowedSuffixesTuple": tuple(v.casefold() for v in suffixes),
    }


def _required_text(item: dict[str, Any], field: str, source_id: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Source {source_id!r} must provide {field}")
    return value.strip()


def _source_root(catalog_root: Path, item: dict[str, Any], source_id: str) -> Path:
    relative = Path(_required_text(item, "localPath", source_id))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Source {source_id!r} localPath must stay beneath the source catalog")
    candidate = catalog_root / relative
    if candidate.is_symlink():
        raise ValueError(f"Source {source_id!r} root must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(catalog_root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Source {source_id!r} localPath is unavailable or outside the catalog") from exc
    if not resolved.is_dir():
        raise ValueError(f"Source {source_id!r} localPath must be a directory")
    return resolved


def _verify_license_evidence(root: Path, value: str, source_id: str) -> None:
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise ValueError(f"Source {source_id!r} license evidence must not contain credentials")
    if parsed.scheme in {"http", "https"}:
        return
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Source {source_id!r} licenseEvidence must be a safe relative path or URL")
    path = root / relative
    if path.is_symlink():
        raise ValueError(f"Source {source_id!r} license evidence must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Source {source_id!r} license evidence is unavailable or unsafe") from exc
    if not resolved.is_file() or not 0 < resolved.stat().st_size <= MAX_SAMPLE_BYTES:
        raise ValueError(f"Source {source_id!r} license evidence must be a nonempty file <= 1 MiB")


def _path_filter(relative_path: str, policy: dict[str, Any]) -> str | None:
    lower = relative_path.casefold()
    parts = [part.casefold() for part in Path(relative_path).parts]
    if any(part in policy["_disallowedPathSegmentsSet"] for part in parts):
        return "disallowed_path_segment"
    if lower.endswith(policy["_disallowedSuffixesTuple"]):
        return "disallowed_suffix"
    return None


def _looks_generated(text: str) -> bool:
    return any(pattern.search(text[:8192]) for pattern in _GENERATED_MARKERS)


def _looks_minified(text: str) -> bool:
    if len(text) < 2048:
        return False
    lines = text.splitlines()
    if not lines:
        return False
    longest = max(len(line) for line in lines)
    return longest >= 8000 or (len(lines) <= 3 and longest >= 2000)


def verify_web_sources(source_manifest: Path, policy_path: Path | None = None) -> dict[str, Any]:
    """Verify reviewed local sources without copying or training on them."""
    policy = load_source_policy(policy_path)
    manifest = _read_json(source_manifest, "Plex Web source manifest")
    if manifest.get("schemaVersion") != 1:
        raise ValueError("Plex Web source manifest schemaVersion must be 1")
    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("Plex Web source manifest must list at least one source")

    catalog_root = source_manifest.resolve(strict=True).parent
    seen_source_ids: set[str] = set()
    seen_hashes: set[str] = set()
    skipped: dict[str, int] = {}
    accepted_by_language: dict[str, int] = {}
    source_reports: list[dict[str, Any]] = []
    total_accepted_bytes = 0
    groups: set[str] = set()

    for item in raw_sources:
        if not isinstance(item, dict):
            raise ValueError("Every Plex Web source must be an object")
        source_id = _required_text(item, "id", "catalog-entry")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", source_id):
            raise ValueError(f"Invalid Plex Web source id: {source_id!r}")
        if source_id in seen_source_ids:
            raise ValueError(f"Duplicate Plex Web source id: {source_id}")
        seen_source_ids.add(source_id)

        if item.get("rightsReviewStatus") != "approved":
            raise ValueError(f"Source {source_id!r} is not rights-review approved")
        license_id = _required_text(item, "licenseId", source_id)
        if license_id not in policy["_allowedSpdxSet"]:
            raise ValueError(f"Source {source_id!r} license {license_id!r} is not allowed by Plex Web policy")

        origin = _required_text(item, "origin", source_id)
        parsed_origin = urlparse(origin)
        if parsed_origin.username or parsed_origin.password or parsed_origin.query:
            raise ValueError(f"Source {source_id!r} origin must not contain credentials or query parameters")
        _required_text(item, "revision", source_id)
        group_id = _required_text(item, "groupId", source_id)
        groups.add(group_id)

        root = _source_root(catalog_root, item, source_id)
        evidence = _required_text(item, "licenseEvidence", source_id)
        _verify_license_evidence(root, evidence, source_id)

        raw_extensions = item.get("includeExtensions")
        if raw_extensions is None:
            extensions = frozenset(policy["_extensionLanguages"])
        elif isinstance(raw_extensions, list) and raw_extensions and all(isinstance(v, str) for v in raw_extensions):
            extensions = frozenset(v.casefold() for v in raw_extensions)
        else:
            raise ValueError(f"Source {source_id!r} includeExtensions must be a nonempty string array")
        unsupported = extensions - set(policy["_extensionLanguages"])
        if unsupported:
            raise ValueError(
                f"Source {source_id!r} requests extensions outside Plex Web v1: "
                + ", ".join(sorted(unsupported))
            )

        counts = {"accepted": 0, "skipped": 0, "duplicates": 0}
        accepted_paths: list[str] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                if path.is_file():
                    skipped["symlink"] = skipped.get("symlink", 0) + 1
                    counts["skipped"] += 1
                continue
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            suffix = path.suffix.casefold()
            if suffix not in extensions:
                continue

            reason = _path_filter(relative, policy)
            text: str | None = None
            if reason is None:
                try:
                    raw = path.read_bytes()
                except OSError:
                    reason = "unreadable_file"
                else:
                    text, reason = _normalise_text(raw)
            if reason is None and text is not None and policy.get("rejectGenerated") is True and _looks_generated(text):
                reason = "generated_content"
            if reason is None and text is not None and policy.get("rejectMinified") is True and _looks_minified(text):
                reason = "minified_content"

            if reason is not None or text is None:
                key = reason or "invalid_content"
                skipped[key] = skipped.get(key, 0) + 1
                counts["skipped"] += 1
                continue

            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                skipped["duplicate_content"] = skipped.get("duplicate_content", 0) + 1
                counts["duplicates"] += 1
                continue
            seen_hashes.add(content_hash)

            language = policy["_extensionLanguages"][suffix]
            accepted_by_language[language] = accepted_by_language.get(language, 0) + 1
            total_accepted_bytes += len(text.encode("utf-8"))
            counts["accepted"] += 1
            accepted_paths.append(relative)

        if counts["accepted"] == 0:
            raise ValueError(f"Source {source_id!r} has no accepted Plex Web files after filtering")
        source_reports.append(
            {
                "id": source_id,
                "licenseId": license_id,
                "groupId": group_id,
                "acceptedFiles": counts["accepted"],
                "duplicateFiles": counts["duplicates"],
                "skippedFiles": counts["skipped"],
                "acceptedPaths": accepted_paths,
            }
        )

    if len(groups) < 2:
        raise ValueError("Plex Web preflight requires at least two repository/source groups")

    return {
        "schemaVersion": 1,
        "policy": policy["policy"],
        "sources": source_reports,
        "sourceGroups": len(groups),
        "acceptedFiles": sum(row["acceptedFiles"] for row in source_reports),
        "acceptedBytes": total_accepted_bytes,
        "acceptedByLanguage": dict(sorted(accepted_by_language.items())),
        "skippedCounts": dict(sorted(skipped.items())),
        "exactDuplicateHashesRemoved": skipped.get("duplicate_content", 0),
        "readyForDeterministicBuild": True,
    }
