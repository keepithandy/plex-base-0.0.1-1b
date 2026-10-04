"""Read-only integrity check for the pending P2 failure-gap candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prepare_code_pair_candidate import prompt_text
from prepare_failure_gap_candidate import DEV, LANGUAGES, OUTPUT, records, validate


def check() -> dict:
    rows = records()
    report = validate(rows)
    raw = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    actual = (OUTPUT / "candidate.jsonl").read_bytes()
    if actual != raw: raise ValueError("Candidate JSONL differs from checked records")
    recorded = json.loads((OUTPUT / "review.json").read_text(encoding="utf-8"))
    expected = {**report, "candidateJsonlSha256": hashlib.sha256(raw).hexdigest()}
    if recorded != expected: raise ValueError("Recorded candidate report differs")
    tasks = json.loads(DEV.read_text(encoding="utf-8"))
    expected_paths = set()
    for row in rows:
        path = OUTPUT / "sources" / row["language"] / row["splitGroupId"] / (row["id"] + ".txt")
        expected_paths.add(path)
        expected_text = prompt_text(row, tasks["outputContracts"]) + "\n" + row["solution"]
        if path.read_text(encoding="utf-8") != expected_text:
            raise ValueError(f"Source text differs: {path}")
    actual_paths = {path for path in (OUTPUT / "sources").rglob("*.txt")}
    if actual_paths != expected_paths: raise ValueError("Missing or extra candidate source file")
    catalog = json.loads((OUTPUT / "dataset-sources.candidate.json").read_text(encoding="utf-8"))
    if len(catalog["sources"]) != 3 or catalog["splitStrategy"] != "family-stratified-groups-v1":
        raise ValueError("Candidate catalog shape differs")
    for source in catalog["sources"]:
        language = source["id"].removeprefix("plex-request-following-").removesuffix("-v3")
        if language not in LANGUAGES or source["rightsReviewStatus"] != "pending-owner-review":
            raise ValueError("Catalog approval or language differs")
        if source["revision"] != expected["candidateJsonlSha256"]:
            raise ValueError("Catalog identity differs")
        groups = {row["splitGroupId"] for row in rows if row["language"] == language}
        if {rule["id"] for rule in source["splitGroupRules"]} != groups:
            raise ValueError("Catalog split groups differ")
    return {"candidate": expected["candidate"], "recordsChecked": len(rows),
            "sourceFilesChecked": len(expected_paths), "sha256": expected["candidateJsonlSha256"],
            "approvalStatus": "pending-owner-review"}


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
