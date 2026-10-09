"""Contamination checks for Plex Web corpus promotion."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

TRAINING_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = TRAINING_ROOT.parent
DEFAULT_PROTECTED_CONFIG = TRAINING_ROOT / "pretraining" / "protected-eval-paths.json"
MAX_PROTECTED_FILE_BYTES = 2 * 1024 * 1024


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


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} is unavailable: {path}") from exc
    if not resolved.is_file() or resolved.stat().st_size > MAX_PROTECTED_FILE_BYTES:
        raise ValueError(f"{label} must be a regular file no larger than 2 MiB")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _strings(value: Any, output: list[str]) -> None:
    if isinstance(value, str):
        output.append(value)
    elif isinstance(value, list):
        for item in value:
            _strings(item, output)
    elif isinstance(value, dict):
        for item in value.values():
            _strings(item, output)


def _protected_segments(path: Path, minimum: int) -> tuple[list[str], str | None]:
    try:
        if path.is_symlink() or not path.is_file():
            return [], "not-regular-file"
        if path.stat().st_size > MAX_PROTECTED_FILE_BYTES:
            return [], "oversized"
    except OSError:
        return [], "unreadable"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return [], "unreadable"
    except UnicodeDecodeError:
        return [], "invalid-utf8"
    values: list[str] = []
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            _strings(json.loads(raw), values)
        except json.JSONDecodeError:
            values.append(raw)
    elif suffix == ".jsonl":
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                _strings(json.loads(line), values)
            except json.JSONDecodeError:
                values.append(line)
    else:
        values.append(raw)
    normalised = {_normalise(value) for value in values}
    return sorted(value for value in normalised if len(value) >= minimum), None


def _resolve_protected_files(config: dict[str, Any]) -> list[Path]:
    raw_paths = config.get("protectedPaths")
    if not isinstance(raw_paths, list) or not raw_paths or not all(isinstance(v, str) for v in raw_paths):
        raise ValueError("Protected-eval config must list protectedPaths")
    files: set[Path] = set()
    for value in raw_paths:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Protected paths must stay beneath the repository root")
        candidate = (REPO_ROOT / relative).resolve(strict=False)
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ValueError("Protected paths must stay beneath the repository root") from exc
        if not candidate.exists():
            raise ValueError(f"Protected path is unavailable: {value}")
        if candidate.is_file():
            files.add(candidate)
        else:
            for path in candidate.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    files.add(path.resolve())
    return sorted(files)


def _read_dataset_records(dataset_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for split in ("train", "validation"):
        path = dataset_dir / f"{split}.jsonl"
        if not path.is_file():
            raise ValueError(f"Dataset is missing {path.name}")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{line_number} is not valid JSON") from exc
            text = row.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError(f"{path.name}:{line_number} is missing text")
            records.append(
                {
                    "split": split,
                    "sourceId": str(row.get("sourceId", "")),
                    "path": str(row.get("path", "")),
                    "text": _normalise(text),
                }
            )
    if not records:
        raise ValueError("Dataset contains no records")
    return records


def check_contamination(
    dataset_dir: Path,
    *,
    protected_config: Path = DEFAULT_PROTECTED_CONFIG,
    report_path: Path | None = None,
) -> dict[str, Any]:
    dataset_dir = dataset_dir.resolve(strict=True)
    if not dataset_dir.is_dir():
        raise ValueError("Dataset path must be a directory")

    config = _read_json(protected_config, "Protected-eval config")
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
    manifest = _read_json(manifest_path, "Dataset manifest")
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
        file_segments, failure = _protected_segments(path, minimum)
        result: dict[str, Any] = {"path": display}
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

    records = _read_dataset_records(dataset_dir)
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

    passed = (
        protection_coverage_passed
        and not blocked_origin_matches
        and not exact_matches
        and not substring_matches
    )
    report = {
        "schemaVersion": 1,
        "kind": "plex-web-contamination-report-v1",
        "passed": passed,
        "datasetDirectory": dataset_dir.name,
        "datasetManifestSha256": _sha256(manifest_path.read_bytes()),
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
