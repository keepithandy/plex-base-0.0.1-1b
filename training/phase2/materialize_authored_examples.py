"""Materialize the owner-approved, first-party P2 examples as grouped Markdown sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE2_ROOT = REPO_ROOT / "training" / "phase2"
INPUT_PATH = PHASE2_ROOT / "drafts" / "p2-02-authored-examples-v1.jsonl"
DEFAULT_OUTPUT = PHASE2_ROOT / "data" / "authored" / "p2-02-examples-v1"
EXPECTED_PROVENANCE = "owner-approved-codex-authored-for-p2-training"
LANGUAGES = ("html", "css", "javascript")
GROUP_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _load_records(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Approved example file must be a regular file no larger than 1 MiB")
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_requests: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid example JSON on line {line_number}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Example line {line_number} must contain an object")
        identifier, language = record.get("id"), record.get("language")
        if (not isinstance(identifier, str) or identifier in seen_ids
                or not isinstance(language, str) or language not in LANGUAGES):
            raise ValueError(f"Example line {line_number} has an invalid id or language")
        if record.get("provenance") != EXPECTED_PROVENANCE:
            raise ValueError("Every example must carry the owner's P2 training approval provenance")
        if record.get("sourceFamilyId") != f"plex-authored-{language}-v1":
            raise ValueError(f"Example {identifier} has an unexpected source family")
        group_id = record.get("splitGroupId")
        if not isinstance(group_id, str) or not GROUP_PATTERN.fullmatch(group_id):
            raise ValueError(f"Example {identifier} has an unsafe split-group id")
        if record.get("candidateSplit") not in {"training", "validation"}:
            raise ValueError(f"Example {identifier} has no proposed split")
        request, solution = record.get("request"), record.get("solution")
        if (not isinstance(request, str) or not request.strip()
                or not isinstance(solution, str) or not solution.strip()
                or "```" in request or "```" in solution):
            raise ValueError(f"Example {identifier} must have plain request and solution text")
        normalized_request = " ".join(request.casefold().split())
        if normalized_request in seen_requests:
            raise ValueError("Duplicate authored requests are not allowed")
        seen_ids.add(identifier)
        seen_requests.add(normalized_request)
        records.append(record)

    if len(records) != 9 or Counter(record["language"] for record in records) != {
        "html": 3, "css": 3, "javascript": 3,
    }:
        raise ValueError("This version requires exactly three approved examples per language")

    for language in LANGUAGES:
        family = f"plex-authored-{language}-v1"
        groups = {record["splitGroupId"] for record in records if record["sourceFamilyId"] == family}
        if len(groups) != 3:
            raise ValueError(f"{family} must have three independent example groups")
        ranked = sorted(
            groups,
            key=lambda group: hashlib.sha256(f"51\0{family}\0{group}".encode("utf-8")).digest(),
        )
        validation_groups = set(ranked[:1])
        for record in records:
            if record["sourceFamilyId"] != family:
                continue
            expected = "validation" if record["splitGroupId"] in validation_groups else "training"
            if record["candidateSplit"] != expected:
                raise ValueError(f"Example {record['id']} does not match the seed-51 group split")
    return records


def _source_text(record: dict[str, Any]) -> str:
    language = record["language"]
    return (
        f"# Plex P2 example {record['id']}\n\n"
        f"## Request\n\n{record['request']}\n\n"
        f"## Solution\n\n```{language}\n{record['solution']}\n```\n"
    )


def materialize(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    records = _load_records(INPUT_PATH)
    allowed_root = (PHASE2_ROOT / "data" / "authored").resolve()
    output_dir = output_dir.resolve(strict=False)
    try:
        output_dir.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("Authored sources must stay beneath training/phase2/data/authored") from exc
    if output_dir.exists():
        raise FileExistsError("Authored source output already exists; choose a fresh versioned path")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".p2-authored-staging-", dir=output_dir.parent))
    notice = (
        "# Authored data provenance and permission\n\n"
        "These original HTML, CSS, and JavaScript examples were drafted with Codex for Plex. "
        "The repository owner approved these nine records for inclusion in a new local Plex P2 "
        "training corpus on 2026-10-04. This records approval for that use only; it is not a "
        "public license grant or a claim about other uses. No external source text is included.\n"
    )
    try:
        for language in LANGUAGES:
            language_root = staging / language
            language_root.mkdir()
            (language_root / "AUTHORED-DATA-NOTICE.txt").write_text(
                notice, encoding="utf-8", newline="\n"
            )
        for record in records:
            destination = (
                staging / record["language"] / record["splitGroupId"] / "example.md"
            )
            destination.parent.mkdir()
            destination.write_text(_source_text(record), encoding="utf-8", newline="\n")
        os.rename(staging, output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    return {
        "outputDirectory": str(output_dir.relative_to(REPO_ROOT)),
        "records": len(records),
        "recordsByLanguage": dict(sorted(Counter(row["language"] for row in records).items())),
        "approvedForLocalP2Training": True,
        "externalSourceTextIncluded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(materialize(args.output_dir), indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"materialize-authored-examples: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
