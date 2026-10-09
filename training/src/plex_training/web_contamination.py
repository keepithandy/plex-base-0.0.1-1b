"""Contamination checks for Plex Web corpus promotion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

TRAINING_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = TRAINING_ROOT.parent
DEFAULT_PROTECTED_CONFIG = TRAINING_ROOT / "pretraining" / "protected-eval-paths.json"
MAX_PROTECTED_FILE_BYTES = 2 * 1024 * 1024
SCANNER_VERSION = "plex-web-contamination-v2"
SCANNER_NORMALIZATION = "crlf-cr-to-lf-collapse-whitespace-strip-v1"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _longest_shared_substring_length(left: str, right: str) -> int:
    if not left or not right:
        return 0
    if left in right:
        return len(left)
    if right in left:
        return len(right)
    if len(left) > len(right):
        left, right = right, left

    transitions: list[dict[str, int]] = [{}]
    links = [-1]
    lengths = [0]
    last = 0

    for char in left:
        current = len(transitions)
        transitions.append({})
        links.append(0)
        lengths.append(lengths[last] + 1)

        state = last
        while state >= 0 and char not in transitions[state]:
            transitions[state][char] = current
            state = links[state]

        if state >= 0:
            target = transitions[state][char]
            if lengths[state] + 1 == lengths[target]:
                links[current] = target
            else:
                clone = len(transitions)
                transitions.append(transitions[target].copy())
                links.append(links[target])
                lengths.append(lengths[state] + 1)
                while state >= 0 and transitions[state].get(char) == target:
                    transitions[state][char] = clone
                    state = links[state]
                links[target] = clone
                links[current] = clone
        last = current

    state = 0
    matched = 0
    longest = 0
    for char in right:
        if char in transitions[state]:
            state = transitions[state][char]
            matched += 1
        else:
            while state >= 0 and char not in transitions[state]:
                state = links[state]
            if state < 0:
                state = 0
                matched = 0
                continue
            matched = lengths[state] + 1
            state = transitions[state][char]
        longest = max(longest, matched)

    return longest


def _read_json_with_bytes(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} is unavailable: {path}") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_PROTECTED_FILE_BYTES:
        raise ValueError(f"{label} must be a regular file no larger than 2 MiB")
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise ValueError(f"{label} is unavailable: {path}") from exc
    if len(raw) > MAX_PROTECTED_FILE_BYTES:
        raise ValueError(f"{label} must be a regular file no larger than 2 MiB")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value, raw


def _read_json(path: Path, label: str) -> dict[str, Any]:
    return _read_json_with_bytes(path, label)[0]

def _strings(value: Any, output: list[str]) -> None:
    if isinstance(value, str):
        output.append(value)
    elif isinstance(value, list):
        for item in value:
            _strings(item, output)
    elif isinstance(value, dict):
        for item in value.values():
            _strings(item, output)


def _protected_segments(
    path: Path,
    minimum: int,
) -> tuple[list[str], str | None, str | None, int | None]:
    try:
        if path.is_symlink() or not path.is_file():
            return [], "not-regular-file", None, None
        metadata = path.stat()
        if metadata.st_size > MAX_PROTECTED_FILE_BYTES:
            return [], "oversized", None, metadata.st_size
        with path.open("rb") as stream:
            raw = stream.read(MAX_PROTECTED_FILE_BYTES + 1)
    except OSError:
        return [], "unreadable", None, None
    if len(raw) > MAX_PROTECTED_FILE_BYTES:
        return [], "oversized", None, len(raw)
    digest = _sha256(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [], "invalid-utf8", digest, len(raw)
    values: list[str] = []
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            _strings(json.loads(text), values)
        except json.JSONDecodeError:
            values.append(text)
    elif suffix == ".jsonl":
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                _strings(json.loads(line), values)
            except json.JSONDecodeError:
                values.append(line)
    else:
        values.append(text)
    normalised = {_normalise(value) for value in values}
    return (
        sorted(value for value in normalised if len(value) >= minimum),
        None,
        digest,
        len(raw),
    )

def _resolve_protected_files(config: dict[str, Any]) -> list[Path]:
    raw_paths = config.get("protectedPaths")
    if not isinstance(raw_paths, list) or not raw_paths or not all(isinstance(v, str) for v in raw_paths):
        raise ValueError("Protected-eval config must list protectedPaths")
    files: set[Path] = set()
    for value in raw_paths:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Protected paths must stay beneath the repository root")
        candidate = REPO_ROOT / relative
        try:
            pending = [candidate]
            while pending:
                path = pending.pop()
                metadata = path.lstat()
                if (stat.S_ISLNK(metadata.st_mode)
                        or getattr(metadata, "st_file_attributes", 0)
                        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                    raise ValueError(f"Protected path must not be a link or reparse point: {path}")
                resolved = path.resolve(strict=True)
                resolved.relative_to(REPO_ROOT.resolve())
                if stat.S_ISREG(metadata.st_mode):
                    files.add(resolved)
                elif stat.S_ISDIR(metadata.st_mode):
                    # Unlike Path.rglob, scandir propagates traversal failures.
                    with os.scandir(path) as entries:
                        pending.extend(Path(entry.path) for entry in entries)
                else:
                    raise ValueError(f"Protected path must be a regular file or directory: {path}")
        except OSError as exc:
            raise ValueError(f"Protected path discovery failed: {value}: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"Protected path discovery rejected {value}: {exc}") from exc
    return sorted(files)


def _read_dataset_records(
    dataset_dir: Path,
    manifest: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    records: list[dict[str, str]] = []
    inputs: list[dict[str, Any]] = []
    summary = manifest.get("summary")
    if summary is not None and not isinstance(summary, dict):
        raise ValueError("Dataset manifest summary must be an object when present")
    for split in ("train", "validation"):
        path = dataset_dir / f"{split}.jsonl"
        if not path.is_file():
            raise ValueError(f"Dataset is missing {path.name}")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"Dataset split is unavailable: {path.name}") from exc
        digest = _sha256(raw)
        declared_field = f"{split}JsonlSha256"
        declared = None if summary is None else summary.get(declared_field)
        if declared is not None:
            if not isinstance(declared, str) or re.fullmatch(r"[a-f0-9]{64}", declared) is None:
                raise ValueError(
                    f"Dataset manifest {declared_field} must be a lowercase SHA-256 digest"
                )
            if declared != digest:
                raise ValueError(
                    f"Dataset manifest {declared_field} does not match {path.name}"
                )
        try:
            text_content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{path.name} is not valid UTF-8") from exc
        split_records = 0
        for line_number, line in enumerate(text_content.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_number} is not valid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path.name}:{line_number} must contain a JSON object")
            text_value = row.get("text")
            if not isinstance(text_value, str) or not text_value:
                raise ValueError(f"{path.name}:{line_number} is missing text")
            records.append(
                {
                    "split": split,
                    "sourceId": str(row.get("sourceId", "")),
                    "path": str(row.get("path", "")),
                    "text": _normalise(text_value),
                }
            )
            split_records += 1
        inputs.append(
            {
                "path": path.name,
                "bytes": len(raw),
                "sha256": digest,
                "manifestDeclaredSha256": declared,
                "manifestHashVerified": declared is not None,
                "records": split_records,
            }
        )
    if not records:
        raise ValueError("Dataset contains no records")
    return records, inputs

def check_contamination(
    dataset_dir: Path,
    *,
    protected_config: Path = DEFAULT_PROTECTED_CONFIG,
    report_path: Path | None = None,
) -> dict[str, Any]:
    dataset_dir = dataset_dir.resolve(strict=True)
    if not dataset_dir.is_dir():
        raise ValueError("Dataset path must be a directory")

    config, config_raw = _read_json_with_bytes(protected_config, "Protected-eval config")
    if config.get("schemaVersion") != 1:
        raise ValueError("Protected-eval config schemaVersion must be 1")
    minimum = config.get("minimumSubstringCharacters", 120)
    if type(minimum) is not int or not 80 <= minimum <= 4096:
        raise ValueError("minimumSubstringCharacters must be an integer from 80 to 4096")
    minimum_protected_files = config.get("minimumProtectedFiles")
    if type(minimum_protected_files) is not int or minimum_protected_files < 1:
        raise ValueError("minimumProtectedFiles must be a positive integer")
    minimum_protected_segments = config.get("minimumProtectedSegments")
    if type(minimum_protected_segments) is not int or minimum_protected_segments < 1:
        raise ValueError("minimumProtectedSegments must be a positive integer")

    manifest_path = dataset_dir / "manifest.json"
    manifest, manifest_raw = _read_json_with_bytes(manifest_path, "Dataset manifest")
    blocked_origins = config.get("blockedSourceOrigins", [])
    if not isinstance(blocked_origins, list) or not all(isinstance(v, str) and v for v in blocked_origins):
        raise ValueError("blockedSourceOrigins must be an array of nonempty strings")
    blocked = {value.rstrip("/").casefold() for value in blocked_origins}
    blocked_origin_matches = []
    for source in manifest.get("sources", []):
        if not isinstance(source, dict):
            continue
        origin = source.get("origin")
        if isinstance(origin, str) and origin.rstrip("/").casefold() in blocked:
            blocked_origin_matches.append(
                {"sourceId": str(source.get("id", "")), "origin": origin}
            )

    protected_files = _resolve_protected_files(config)
    segments: list[tuple[str, str]] = []
    protected_file_results: list[dict[str, Any]] = []
    for path in protected_files:
        display = path.relative_to(REPO_ROOT).as_posix()
        file_segments, failure, content_sha256, content_bytes = _protected_segments(path, minimum)
        result: dict[str, Any] = {"path": display}
        if content_sha256 is not None:
            result["sha256"] = content_sha256
        if content_bytes is not None:
            result["bytes"] = content_bytes
        if failure is None:
            result.update({"status": "scanned", "segments": len(file_segments)})
            for segment in file_segments:
                segments.append((display, segment))
        else:
            result.update({"status": "skipped", "reason": failure, "segments": 0})
        protected_file_results.append(result)

    protected_files_scanned = sum(result["status"] == "scanned" for result in protected_file_results)
    protected_files_skipped = len(protected_file_results) - protected_files_scanned
    protection_coverage_failures: list[str] = []
    usable_files = {
        path for path, result in zip(protected_files, protected_file_results)
        if result["status"] == "scanned" and result["segments"] > 0
    }
    for value in config["protectedPaths"]:
        configured_path = (REPO_ROOT / value).resolve(strict=False)
        if not any(
            path == configured_path or configured_path in path.parents
            for path in usable_files
        ):
            protection_coverage_failures.append(
                f"protected-path-without-usable-segments:{value}"
            )
    if len(protected_files) < minimum_protected_files:
        protection_coverage_failures.append("minimum-protected-files-not-met")
    if len(segments) < minimum_protected_segments:
        protection_coverage_failures.append("minimum-protected-segments-not-met")
    if protected_files_skipped:
        protection_coverage_failures.append("protected-files-skipped")
    protection_coverage_passed = not protection_coverage_failures

    records, dataset_inputs = _read_dataset_records(dataset_dir, manifest)
    exact_matches: list[dict[str, Any]] = []
    substring_matches: list[dict[str, Any]] = []
    for record in records:
        text = record["text"]
        for protected_path, segment in segments:
            if text == segment:
                exact_matches.append(
                    {
                        "split": record["split"],
                        "sourceId": record["sourceId"],
                        "path": record["path"],
                        "protectedPath": protected_path,
                        "characters": len(segment),
                    }
                )
            else:
                overlap = _longest_shared_substring_length(text, segment)
                if overlap >= minimum:
                    substring_matches.append(
                        {
                            "split": record["split"],
                            "sourceId": record["sourceId"],
                            "path": record["path"],
                            "protectedPath": protected_path,
                            "overlapAtLeastCharacters": overlap,
                        }
                    )

    scanner = {
        "version": SCANNER_VERSION,
        "normalization": SCANNER_NORMALIZATION,
        "minimumSubstringCharacters": minimum,
        "minimumProtectedFiles": minimum_protected_files,
        "minimumProtectedSegments": minimum_protected_segments,
        "maximumProtectedFileBytes": MAX_PROTECTED_FILE_BYTES,
        "blockedSourceOrigins": sorted(blocked),
    }
    dataset_manifest_sha256 = _sha256(manifest_raw)
    protected_config_sha256 = _sha256(config_raw)
    assessment_inputs = {
        "scanner": scanner,
        "datasetManifest": {
            "bytes": len(manifest_raw),
            "sha256": dataset_manifest_sha256,
        },
        "datasetFiles": dataset_inputs,
        "protectedConfig": {
            "bytes": len(config_raw),
            "sha256": protected_config_sha256,
        },
        "protectedFiles": protected_file_results,
    }
    assessment_sha256 = _sha256(
        json.dumps(
            assessment_inputs,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    passed = (
        protection_coverage_passed
        and not blocked_origin_matches
        and not exact_matches
        and not substring_matches
    )
    report = {
        "schemaVersion": 2,
        "kind": "plex-web-contamination-report-v2",
        "passed": passed,
        "datasetDirectory": dataset_dir.name,
        "scanner": scanner,
        "assessmentSha256": assessment_sha256,
        "datasetManifestSha256": dataset_manifest_sha256,
        "datasetManifestBytes": len(manifest_raw),
        "datasetFiles": dataset_inputs,
        "protectedConfigSha256": protected_config_sha256,
        "protectedConfigBytes": len(config_raw),
        "recordsScanned": len(records),
        "protectedFilesDiscovered": len(protected_files),
        "protectedFilesScanned": protected_files_scanned,
        "protectedFilesSkipped": protected_files_skipped,
        "protectedFileResults": protected_file_results,
        "protectedSegmentsScanned": len(segments),
        "minimumProtectedFiles": minimum_protected_files,
        "minimumProtectedSegments": minimum_protected_segments,
        "protectionCoveragePassed": protection_coverage_passed,
        "protectionCoverageFailures": protection_coverage_failures,
        "minimumSubstringCharacters": minimum,
        "blockedOriginMatches": blocked_origin_matches,
        "exactMatches": exact_matches,
        "substringMatches": substring_matches,
        "finalHoldout": config.get("finalHoldout", "closed-not-addressable"),
    }

    target = report_path or dataset_dir / "contamination-report.json"
    if target.exists():
        raise FileExistsError(f"Contamination report already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return {**report, "report": str(target)}


def require_clean_contamination(
    dataset_dir: Path,
    *,
    protected_config: Path = DEFAULT_PROTECTED_CONFIG,
    report_path: Path | None = None,
) -> dict[str, Any]:
    report = check_contamination(
        dataset_dir,
        protected_config=protected_config,
        report_path=report_path,
    )
    if not report["passed"]:
        raise ValueError(
            "Plex Web contamination check failed; corpus promotion is blocked. "
            f"See {report['report']}"
        )
    return report
