"""Promote the exact owner-approved 234-record v3 review snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import check_failure_gap_candidate as checker
import prepare_failure_gap_candidate as candidate

PHASE2 = Path(__file__).resolve().parent
APPROVAL = PHASE2 / "approvals/p2-02-request-following-v3.json"
OUTPUT = PHASE2 / "data/authored/p2-02-request-following-v3"


def promote(output: Path = OUTPUT, approval_path: Path = APPROVAL) -> dict:
    if approval_path.is_symlink() or not approval_path.is_file() or approval_path.stat().st_size > 1_048_576:
        raise ValueError("Approval must be a bounded regular JSON file")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    raw = (candidate.OUTPUT / "candidate.jsonl").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if (approval.get("schemaVersion") != 1 or approval.get("approvalStatus") != "approved"
            or approval.get("candidate") != "p2-02-request-following-v3"
            or approval.get("candidateJsonlSha256") != digest or approval.get("records") != 234
            or approval.get("scope") != "local-P2-training"
            or approval.get("approvedBy") != "repository-owner"
            or approval.get("approvalStatement") != "Approve the 234-example v3 candidate for local training."
            or approval.get("externalSourceTextIncluded") is not False
            or approval.get("publicLicenseGranted") is not False):
        raise ValueError("Approval must bind these exact 234 records and local training scope")
    recorded = datetime.fromisoformat(approval["approvalRecordedAtUtc"].replace("Z", "+00:00"))
    if recorded.utcoffset() != timedelta(0): raise ValueError("Approval must carry a UTC timestamp")
    if checker.check()["sha256"] != digest:
        raise ValueError("Candidate or review files differ from the owner-approved snapshot")
    draft_catalog = json.loads((candidate.OUTPUT / "dataset-sources.candidate.json").read_text(encoding="utf-8"))
    if len(draft_catalog["sources"]) != 3 or any(
        source["revision"] != digest or source["rightsReviewStatus"] != "pending-owner-review"
        for source in draft_catalog["sources"]
    ):
        raise ValueError("Draft catalog does not match approved candidate")
    output = output.resolve()
    allowed = (PHASE2 / "data/authored").resolve()
    if output.parent != allowed or output.exists():
        raise ValueError("Approved source output must be a fresh directory under data/authored")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent / (".plex-gap-approved-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        shutil.copytree(candidate.OUTPUT / "sources", staging / "sources")
        for language in candidate.LANGUAGES:
            (staging / "sources" / language / "NOTICE.md").write_text(
                "# Local training approval\n\nOriginal Codex-authored request/code examples. "
                'The repository owner approved these exact 234 records for local training: '
                '"Approve the 234-example v3 candidate for local training."\n\n'
                f"Canonical JSONL SHA-256: `{digest}`.\n"
                f"Approval recorded at {approval['approvalRecordedAtUtc']}. "
                "The approval record is copied into approval.json. No external source text is included. "
                "This covers local P2 training only, not a public license grant. "
                "This notice is excluded from training text.\n", encoding="utf-8", newline="\n")
        for source in draft_catalog["sources"]:
            source["rightsReviewStatus"] = "approved"
            source["rightsReviewedAtUtc"] = approval["approvalRecordedAtUtc"]
            source["licenseId"] = "Owner-approved-local-P2-use"
        for name, value in {"dataset-sources.approved.json": draft_catalog, "approval.json": approval}.items():
            (staging / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.rename(staging, output)
    except Exception:
        if staging.exists() and staging.resolve().parent == output.parent and staging.name.startswith(".plex-gap-approved-"):
            shutil.rmtree(staging)
        raise
    return {"approvedSources": str(output), "records": 234, "candidateJsonlSha256": digest}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(promote(args.output_dir), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"promote-gap: {exc}\n")


if __name__ == "__main__":
    main()
