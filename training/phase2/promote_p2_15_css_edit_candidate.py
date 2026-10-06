"""Promote the owner-approved P2-15 candidate without editing its review draft."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from prepare_p2_15_css_edit_candidate import (
    CANDIDATE_JSONL_SHA256, INPUT, OUT, PENDING, _encoded_rows, rows,
)

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "training" / "phase2"
APPROVAL = PHASE2 / "approvals" / "p2-15-css-edit-candidate-v1.json"
OUTPUT = PHASE2 / "data" / "authored" / "p2-15-css-edit-v1"


def promote() -> dict:
    raw = INPUT.read_bytes()
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    expected = {
        "schemaVersion": 1,
        "candidate": "p2-15-css-edit-candidate-v1",
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "records": 36,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training",
        "maxUpdates": 100,
        "maxDurationMinutes": 10,
        "freshInitialization": True,
        "seed": 1337,
        "matchedStepZeroEvaluation": True,
        "finalHoldoutOpened": False,
    }
    if hashlib.sha256(raw).hexdigest() != CANDIDATE_JSONL_SHA256:
        raise ValueError("Candidate JSONL differs from the approved hash")
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("Owner approval does not authorize this exact candidate and bounded run")
    if (not isinstance(approval.get("ownerMessage"), str)
            or "continue" not in approval["ownerMessage"].casefold()):
        raise ValueError("Approval must retain the owner's authorizing message")
    approved_at = datetime.fromisoformat(approval["approvedAtUtc"].replace("Z", "+00:00"))
    if approved_at.utcoffset() != timedelta(0):
        raise ValueError("Approval timestamp must be UTC")
    if OUTPUT.exists():
        raise FileExistsError("Approved data already exists; refusing to overwrite")

    records = rows()
    stage = OUTPUT.parent / (".p2-15-css-approved-" + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    try:
        grouped: dict[str, list[dict]] = {}
        for row in records:
            grouped.setdefault(row["splitGroupId"], []).append(row)
        sources = []
        for group, members in sorted(grouped.items()):
            root = stage / "sources" / group
            root.mkdir(parents=True)
            (root / "NOTICE.md").write_text(
                "# Local Plex training approval\n\n"
                "Original Codex-authored CSS request/edit examples, approved by the repository owner "
                f"for local P2 training under candidate SHA-256 `{CANDIDATE_JSONL_SHA256}`. "
                "No external source text is included; this does not assert a public license grant. "
                "This notice is excluded from training text.\n",
                encoding="utf-8", newline="\n",
            )
            for row in members:
                original = (OUT / "records" / row["candidateSplit"] / group / f"{row['id']}.txt").read_bytes()
                prefix = (f"Write a small CSS coding solution.\nRequest: {row['request']}\n"
                          "Output contract: Return CSS rules only. Do not include HTML, Markdown fences, or explanations.\n"
                          "Return code only. Do not include Markdown fences or explanations.\n")
                expected_text = (prefix + row["solution"]).encode("utf-8")
                if original != expected_text:
                    raise ValueError(f"Candidate source changed for {row['id']}")
                (root / f"{row['id']}.txt").write_bytes(original)
            sources.append({
                "id": f"p2-15-{group}",
                "groupId": group,
                "sourceFamilyId": "p2-15-css-edits-v1",
                "localPath": f"sources/{group}",
                "origin": "urn:plex:codex-authored:p2-15-css-edit-candidate-v1",
                "revision": CANDIDATE_JSONL_SHA256,
                "licenseId": "Owner-approved-local-P2-use",
                "licenseEvidence": "NOTICE.md",
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": approval["approvedAtUtc"],
                "includeExtensions": [".txt"],
            })
        catalog = {"schemaVersion": 1, "splitStrategy": "source-groups-v1", "sources": sources}
        (stage / "dataset-sources.approved.json").write_text(
            json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (stage / "approval.json").write_text(
            json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        os.rename(stage, OUTPUT)
    except Exception:
        if stage.exists() and stage.parent == OUTPUT.parent and stage.name.startswith(".p2-15-css-approved-"):
            shutil.rmtree(stage)
        raise
    return {"approvedSources": str(OUTPUT), "sourceCatalog": str(OUTPUT / "dataset-sources.approved.json"),
            "candidateJsonlSha256": CANDIDATE_JSONL_SHA256, "sourceGroups": len(sources),
            "records": len(records), "approvalStatus": "approved"}


if __name__ == "__main__":
    try:
        print(json.dumps(promote(), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"promote-p2-15-css-edit: {exc}", file=sys.stderr)
        raise SystemExit(2)
