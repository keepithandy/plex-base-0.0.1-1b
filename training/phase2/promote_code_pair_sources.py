"""Promote the exact owner-approved candidate without changing its draft snapshot."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from prepare_code_pair_candidate import (
    DEV_SET, INPUT, LANGUAGES, OUTPUT, PHASE2, _digest, load_records, source_text, validate_records,
)

APPROVAL = PHASE2 / "approvals" / "p2-02-code-pairs-v2.json"
APPROVED_OUTPUT = PHASE2 / "data" / "authored" / "p2-02-code-pairs-v2"


def promote(output: Path = APPROVED_OUTPUT, approval_path: Path = APPROVAL) -> dict:
    if approval_path.is_symlink() or not approval_path.is_file() or approval_path.stat().st_size > 1_048_576:
        raise ValueError("Approval evidence must be a bounded regular JSON file")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    digest = _digest(INPUT.read_bytes())
    if (approval.get("schemaVersion") != 1 or approval.get("approvalStatus") != "approved"
            or approval.get("candidate") != "p2-02-code-pairs-v2"
            or approval.get("candidateJsonlSha256") != digest or approval.get("records") != 36
            or approval.get("scope") != "local-P2-training"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("approvalStatement") != "Approve the 36 examples for local training."):
        raise ValueError("Approval must identify these exact 36 records and local training scope")
    recorded = datetime.fromisoformat(approval["approvalRecordedAtUtc"].replace("Z", "+00:00"))
    if recorded.utcoffset() != timedelta(0):
        raise ValueError("Approval record must carry a UTC timestamp")
    rows = load_records()
    tasks = json.loads(DEV_SET.read_text(encoding="utf-8"))
    report = validate_records(rows, tasks)
    output = output.resolve()
    allowed_root = (PHASE2 / "data" / "authored").resolve()
    output.relative_to(allowed_root)
    if output == allowed_root or output.exists():
        raise FileExistsError("Approved sources already exist; never overwrite their version")
    catalog = json.loads((OUTPUT / "dataset-sources.candidate.json").read_text(encoding="utf-8"))
    if any(row["revision"] != digest for row in catalog["sources"]):
        raise ValueError("Preview source revision does not match approval")
    for row in rows:
        path = OUTPUT / "sources" / row["language"] / row["splitGroupId"] / (row["id"] + ".txt")
        if path.is_symlink() or path.read_bytes() != source_text(row, tasks["outputContracts"]).encode("utf-8"):
            raise ValueError("Preview sources differ from the approved records")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / (".plex-approved-pairs-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        shutil.copytree(OUTPUT / "sources", staging / "sources")
        for language in LANGUAGES:
            (staging / "sources" / language / "NOTICE.md").write_text(
                "# Local training approval\n\nOriginal Codex-authored request/code examples for Plex. "
                "The repository owner approved these exact 36 records for local training: "
                '"Approve the 36 examples for local training."\n\n'
                f"Canonical candidate JSONL SHA-256: `{digest}`.\n\n"
                f"Approval recorded at {approval['approvalRecordedAtUtc']}. "
                "Approval evidence is copied into approval.json. No external source text is included. "
                "This records local P2 use only; no public license grant is asserted. "
                "This notice is excluded from training text.\n", encoding="utf-8", newline="\n",
            )
        for source in catalog["sources"]:
            source["rightsReviewStatus"] = "approved"
            source["rightsReviewedAtUtc"] = approval["approvalRecordedAtUtc"]
            source["licenseId"] = "Owner-approved-local-P2-use"
        for name, value in {"dataset-sources.approved.json": catalog, "approval.json": approval}.items():
            (staging / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.rename(staging, output)
    except Exception:
        if staging.exists() and staging.resolve().parent == output.parent and staging.name.startswith(".plex-approved-pairs-"):
            shutil.rmtree(staging)
        raise
    return {"approvedSources": str(output), "catalog": str(output / "dataset-sources.approved.json"),
            "candidateJsonlSha256": digest, "records": 36, "staticChecksPassed": report["staticChecksPassed"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=APPROVED_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(promote(args.output_dir), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"promote-code-pairs: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
