"""Prepare an unapproved CSS request-to-code training candidate; never train."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))
from plex_training.benchmark import _check_task

PHASE2 = ROOT / "training" / "phase2"
OUT = PHASE2 / "drafts" / "p2-15-css-edit-candidate-v1"
INPUT = PHASE2 / "drafts" / "p2-15-css-edit-candidate-v1.jsonl"
PENDING = "pending-owner-review"
CANDIDATE_JSONL_SHA256 = "e9ca83c92a40abd0575db708bd67d2e4ce6888d97bc31ef4a38938a050dfd6cf"
P2_14_TASK_SET_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"

# group, split, selector, starting rule, instruction, complete edited rule.
EXAMPLES = (
    ("button-radius", "train", ".primary-button", "border-radius: 2px; padding: 0.5rem 1rem;", "Replace the corner radius with 6px and keep the padding.", "border-radius: 6px; padding: 0.5rem 1rem;"),
    ("button-radius", "train", ".submit-button", "border-radius: 4px; background-color: #1d4ed8;", "Set the corner radius to 0.75rem; preserve the background color.", "border-radius: 0.75rem; background-color: #1d4ed8;"),
    ("button-radius", "train", ".quiet-button", "border-radius: 999px; color: #334155;", "Change the radius to 0.25rem and leave the text color as given.", "border-radius: 0.25rem; color: #334155;"),
    ("callout-border", "train", ".warning-callout", "border: 1px solid #94a3b8; padding: 1rem;", "Keep the border width and style, but change its color to #b91c1c. Preserve the padding.", "border: 1px solid #b91c1c; padding: 1rem;"),
    ("callout-border", "train", ".info-callout", "border: 2px dashed #64748b; margin-block: 1rem;", "Change only the border color to #0369a1; keep its width, style, and margin.", "border: 2px dashed #0369a1; margin-block: 1rem;"),
    ("callout-border", "train", ".success-callout", "border: 3px solid #475569; background: #f8fafc;", "Use #15803d for the border color and preserve the other declarations.", "border: 3px solid #15803d; background: #f8fafc;"),
    ("nav-justify", "train", ".main-navigation", "display: flex; justify-content: flex-start; gap: 1rem;", "Align the flex items at the inline end. Keep the gap and display mode.", "display: flex; justify-content: flex-end; gap: 1rem;"),
    ("nav-justify", "train", ".toolbar-links", "display: flex; justify-content: center; align-items: center;", "Distribute the items with space-between; preserve the other declarations.", "display: flex; justify-content: space-between; align-items: center;"),
    ("nav-justify", "train", ".footer-navigation", "display: flex; justify-content: space-around; flex-wrap: wrap;", "Set the main-axis alignment to space-evenly and keep wrapping enabled.", "display: flex; justify-content: space-evenly; flex-wrap: wrap;"),
    ("card-shadow", "train", ".catalog-card", "box-shadow: 0 1px 2px #0002; border-radius: 0.5rem;", "Replace the shadow with 0 4px 12px #0003 and keep the radius.", "box-shadow: 0 4px 12px #0003; border-radius: 0.5rem;"),
    ("card-shadow", "train", ".profile-card", "box-shadow: none; padding: 1.25rem;", "Add a shadow of 0 2px 8px #1e293b33; preserve the padding.", "box-shadow: 0 2px 8px #1e293b33; padding: 1.25rem;"),
    ("card-shadow", "train", ".summary-card", "box-shadow: 0 6px 18px #0004; border: 1px solid #cbd5e1;", "Remove the shadow while leaving the border declaration unchanged.", "box-shadow: none; border: 1px solid #cbd5e1;"),
    ("label-font-style", "train", ".field-label", "font-style: normal; font-weight: 600;", "Make the label italic and retain its font weight.", "font-style: italic; font-weight: 600;"),
    ("label-font-style", "train", ".editorial-note", "font-style: italic; color: #475569;", "Return the text to normal style; keep its color.", "font-style: normal; color: #475569;"),
    ("label-font-style", "train", ".image-caption", "font-style: oblique; font-size: 0.875rem;", "Change the font style to italic and preserve the font size.", "font-style: italic; font-size: 0.875rem;"),
    ("thumbnail-width", "train", ".gallery-thumbnail", "width: 12rem; height: auto;", "Add max-width: 100% so the thumbnail cannot exceed its container; keep both existing declarations.", "width: 12rem; height: auto; max-width: 100%;"),
    ("thumbnail-width", "train", ".avatar-preview", "width: 5rem; object-fit: cover;", "Add a 100% maximum width and preserve the width and object-fit settings.", "width: 5rem; object-fit: cover; max-width: 100%;"),
    ("thumbnail-width", "train", ".article-image", "width: 100%; display: block;", "Add max-width: 42rem; keep the current width and display mode.", "width: 100%; display: block; max-width: 42rem;"),
    ("badge-transform", "train", ".status-badge", "text-transform: none; letter-spacing: 0.02em;", "Display the badge text in uppercase and keep its letter spacing.", "text-transform: uppercase; letter-spacing: 0.02em;"),
    ("badge-transform", "train", ".category-tag", "text-transform: uppercase; padding: 0.25rem;", "Use lowercase text instead; preserve the padding.", "text-transform: lowercase; padding: 0.25rem;"),
    ("badge-transform", "train", ".section-kicker", "text-transform: capitalize; color: #64748b;", "Change the text transformation to uppercase and retain its color.", "text-transform: uppercase; color: #64748b;"),
    ("menu-opacity", "train", ".disabled-menu-item", "opacity: 1; pointer-events: auto;", "Set opacity to 0.45 and keep pointer events enabled.", "opacity: 0.45; pointer-events: auto;"),
    ("menu-opacity", "train", ".loading-menu-item", "opacity: 0.8; cursor: progress;", "Make this item fully opaque; leave the progress cursor in place.", "opacity: 1; cursor: progress;"),
    ("menu-opacity", "train", ".inactive-menu-item", "opacity: 0.5; pointer-events: none;", "Restore opacity to 1 while keeping pointer events disabled.", "opacity: 1; pointer-events: none;"),
    ("list-style", "validation", ".resource-list", "list-style-type: disc; padding-inline-start: 1.25rem;", "Use square markers and retain the current indentation.", "list-style-type: square; padding-inline-start: 1.25rem;"),
    ("list-style", "validation", ".steps-list", "list-style-type: decimal; margin-block: 0;", "Change the markers to lower-alpha and keep the block margins reset.", "list-style-type: lower-alpha; margin-block: 0;"),
    ("list-style", "validation", ".feature-list", "list-style-type: circle; color: #334155;", "Remove the list markers but keep the text color.", "list-style-type: none; color: #334155;"),
    ("white-space", "validation", ".terminal-output", "white-space: normal; overflow-x: auto;", "Preserve whitespace and line breaks without wrapping lines; keep horizontal scrolling.", "white-space: pre; overflow-x: auto;"),
    ("white-space", "validation", ".inline-code-sample", "white-space: pre; background: #f1f5f9;", "Allow normal wrapping and preserve the background.", "white-space: normal; background: #f1f5f9;"),
    ("white-space", "validation", ".message-preview", "white-space: pre-wrap; color: #1e293b;", "Collapse whitespace normally and retain the text color.", "white-space: normal; color: #1e293b;"),
    ("aspect-ratio", "validation", ".video-frame", "aspect-ratio: 4 / 3; width: 100%;", "Change the preferred ratio to 16 / 9 and keep full width.", "aspect-ratio: 16 / 9; width: 100%;"),
    ("aspect-ratio", "validation", ".square-preview", "aspect-ratio: 16 / 9; max-width: 20rem;", "Make the preferred ratio square and preserve the maximum width.", "aspect-ratio: 1 / 1; max-width: 20rem;"),
    ("aspect-ratio", "validation", ".portrait-frame", "aspect-ratio: 1 / 1; width: 9rem;", "Set the ratio to 3 / 4 and leave the width unchanged.", "aspect-ratio: 3 / 4; width: 9rem;"),
    ("outline", "validation", ".keyboard-control", "outline: 2px solid #2563eb; outline-offset: 0;", "Move the outline 3px away from the control; preserve its style and color.", "outline: 2px solid #2563eb; outline-offset: 3px;"),
    ("outline", "validation", ".search-field", "outline: 1px dotted #475569; outline-offset: 2px;", "Set the outline offset to -1px; leave the outline itself unchanged.", "outline: 1px dotted #475569; outline-offset: -1px;"),
    ("outline", "validation", ".dialog-close", "outline: none; color: #334155;", "Add a 2px solid #0f766e outline and retain the text color.", "outline: 2px solid #0f766e; color: #334155;"),
)


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encoded_rows(examples: list[dict]) -> bytes:
    return ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in examples) + "\n").encode("utf-8")


def rows() -> list[dict]:
    result = []
    for index, (group, split, selector, before, instruction, after) in enumerate(EXAMPLES, 1):
        request = (f"Starting CSS:\n{selector} {{ {before} }}\n\n{instruction} "
                   "Return the complete updated CSS rule with no unrelated changes.")
        checks = [{"kind": "css_stylesheet_exact", "rules": {selector: dict(
            (item.split(":", 1)[0].strip(), item.split(":", 1)[1].strip())
            for item in after.split(";") if item.strip())}}]
        result.append({
            "schemaVersion": 1,
            "id": f"p2-15-css-{index:02d}",
            "language": "css",
            "request": request,
            "solution": f"{selector} {{ {after} }}",
            "checks": checks,
            "splitGroupId": f"css-{group}",
            "candidateSplit": split,
            "provenance": "codex-authored-local-training-candidate",
            "approvalStatus": PENDING,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        if not INPUT.is_file() or not (OUT / "REVIEW.md").is_file():
            parser.error("candidate draft files are missing")
        payload = json.loads((OUT / "review.json").read_text(encoding="utf-8"))
        expected = _encoded_rows(rows())
        if (_sha(expected) != CANDIDATE_JSONL_SHA256 or INPUT.read_bytes() != expected
                or payload["candidateJsonlSha256"] != CANDIDATE_JSONL_SHA256
                or payload["developmentTaskSetSha256"] != P2_14_TASK_SET_SHA256):
            parser.error("candidate JSONL hash no longer matches review metadata")
        print(json.dumps({"verified": True, "records": payload["records"],
                          "candidateJsonlSha256": payload["candidateJsonlSha256"],
                          "approvalStatus": payload["approvalStatus"], "modelTrained": False}, indent=2))
        return 0

    if OUT.exists() or INPUT.exists():
        parser.error("candidate files already exist; refusing to overwrite")
    task_set_path = PHASE2 / "drafts/p2-14-css-edit-step200-v1/task-set.json"
    if _sha(task_set_path.read_bytes()) != P2_14_TASK_SET_SHA256:
        parser.error("P2-14 development set does not match its recorded hash")
    task_set = json.loads(task_set_path.read_text(encoding="utf-8"))
    baseline_set = json.loads((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    dev_sets = {
        "P2-01b": baseline_set["tasks"],
        "P2-14": task_set["tasks"],
    }
    dev_requests = {name: {_norm(task["request"]) for task in tasks}
                    for name, tasks in dev_sets.items()}
    examples = rows()
    if len(examples) != 36:
        parser.error("candidate must contain 36 records")
    counts = Counter(row["candidateSplit"] for row in examples)
    group_splits: dict[str, set[str]] = {}
    check_totals = 0
    jaccard_max = {name: 0.0 for name in dev_sets}
    for row in examples:
        group_splits.setdefault(row["splitGroupId"], set()).add(row["candidateSplit"])
        norm_request = _norm(row["request"])
        if any(norm_request in requests for requests in dev_requests.values()):
            parser.error(f"candidate request duplicates an existing development prompt: {row['id']}")
        words = set(re.findall(r"\w+", norm_request))
        for name, old_tasks in dev_sets.items():
            for old in old_tasks:
                other = set(re.findall(r"\w+", _norm(old["request"])))
                jaccard_max[name] = max(jaccard_max[name], len(words & other) / len(words | other))
        checked = _check_task({"id": row["id"], "language": "css", "difficulty": "basic",
                               "checks": row["checks"]}, row["solution"], None, 5.0)
        if not checked["passed"]:
            parser.error(f"invalid authored solution {row['id']}: {checked}")
        check_totals += checked["checksTotal"]
    if counts != Counter({"train": 24, "validation": 12}) or any(len(v) != 1 for v in group_splits.values()):
        parser.error("candidate must have disjoint semantic groups and a 24/12 split")
    if len(group_splits) != 12 or any(value >= 0.70 for value in jaccard_max.values()):
        parser.error("candidate group count or development prompt separation failed")

    raw = _encoded_rows(examples)
    if _sha(raw) != CANDIDATE_JSONL_SHA256:
        parser.error("candidate rows differ from the source-pinned SHA-256")
    INPUT.parent.mkdir(parents=True, exist_ok=True)
    INPUT.write_bytes(raw)
    OUT.mkdir(parents=True)
    records_root = OUT / "records"
    for row in examples:
        path = records_root / row["candidateSplit"] / row["splitGroupId"] / f"{row['id']}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = (f"Write a small CSS coding solution.\nRequest: {row['request']}\n"
                  "Output contract: Return CSS rules only. Do not include HTML, Markdown fences, or explanations.\n"
                  "Return code only. Do not include Markdown fences or explanations.\n")
        path.write_text(prefix + row["solution"], encoding="utf-8", newline="\n")
    report = {
        "candidate": "p2-15-css-edit-candidate-v1", "approvalStatus": PENDING,
        "records": len(examples), "recordsBySplit": dict(counts),
        "semanticGroups": {key: sorted(value) for key, value in sorted(group_splits.items())},
        "candidateJsonlSha256": _sha(raw), "trainingRowsSha256": _sha("\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in examples if row["candidateSplit"] == "train").encode()),
        "validationRowsSha256": _sha("\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in examples if row["candidateSplit"] == "validation").encode()),
        "developmentTaskSetSha256": _sha((PHASE2 / "drafts/p2-14-css-edit-step200-v1/task-set.json").read_bytes()),
        "baselineDevelopmentTaskSetSha256": _sha((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_bytes()),
        "developmentRequestExactOverlap": {name: 0 for name in dev_sets},
        "highestDevelopmentRequestWordJaccard": {name: round(value, 6) for name, value in jaccard_max.items()},
        "staticAuthoredSolutionsPassed": len(examples), "staticChecksPassed": check_totals,
        "externalSourceTextIncluded": False, "tokenizerFitted": False,
        "trainingRunCreated": False, "modelTrained": False, "finalHoldoutOpened": False,
        "proposedExperiment": {"freshInitialization": True, "seed": 1337,
                               "matchedStepZeroEvaluation": True,
                               "maximumDurationMinutes": 10,
                               "maximumUpdates": 100,
                               "requiresSeparateOwnerApproval": True},
    }
    (OUT / "review.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = [
        "# P2-15 CSS request-to-code candidate v1\n",
        "**Status: ready for owner review; not approved for training.**\n",
        "## What this candidate teaches\n",
        "Each prompt supplies one CSS rule and asks for one bounded edit. The target is the complete updated rule, including declarations that should stay unchanged. The candidate contains 36 original examples in 12 semantic groups: 24 training records (8 groups) and 12 validation records (4 different groups). Related variants are kept together so no edit family crosses the split.\n",
        "## Why this follows P2-14\n",
        "P2-14 showed that the existing step-200 model could copy selector strings but did not produce complete CSS edits. This candidate directly teaches that input-rule → instruction → complete-rule format. It is a small diagnostic candidate, not a broad CSS curriculum. Its exact prompts do not overlap P2-14; the split withholds four entire edit families. The P2-14 task set is development-only and already disclosed. The owner-controlled final set remains unopened.\n",
        "## Example training record\n",
        "```text\n" + (records_root / "train/css-button-radius/p2-15-css-01.txt").read_text(encoding="utf-8") + "\n```\n",
        "## Split\n",
        "**Training families:** button radius, callout border color, navigation alignment, card shadow, label font style, thumbnail width, badge text transformation, and menu-item opacity (24 records).\n\n",
        "**Validation-only families:** list marker, whitespace handling, aspect ratio, and outline (12 records). These records are not trained on; the tokenizer must be fitted only on the training partition after approval.\n",
        "## Candidate checks and limits\n",
        f"All {len(examples)} authored outputs passed the static exact-rule checker ({check_totals}/{check_totals} checks). This validates the examples, not model capability or browser rendering. No exact request duplicates were found against P2-01b or P2-14. Maximum word-level Jaccard overlap was {round(jaccard_max['P2-01b'], 6)} with P2-01b and {round(jaccard_max['P2-14'], 6)} with P2-14; these are only lexical screens. No external material was copied.\n",
        "No corpus was built, tokenizer fitted, checkpoint initialized, training run started, or final set opened. Review/approve these exact candidate hashes before any training. After approval, build a separate corpus, fit a fresh tokenizer on training records only, measure token budgets, create a new seed-1337 step-zero checkpoint, then run at most 100 updates or 10 minutes and compare against step zero. This ceiling is a proposal, not run authorization.\n",
        "## Hashes\n",
        f"- Candidate JSONL: `{report['candidateJsonlSha256']}`\n- Training rows: `{report['trainingRowsSha256']}`\n- Validation rows: `{report['validationRowsSha256']}`\n- P2-14 development set: `{report['developmentTaskSetSha256']}`\n- Final holdout opened: **no**\n",
        "## All examples\n",
    ]
    for split in ("train", "validation"):
        md.append(f"### {split.title()}\n")
        for row in examples:
            if row["candidateSplit"] == split:
                md.append(f"#### {row['id']} — {row['splitGroupId']}\n\nRequest: {row['request']}\n\n```css\n{row['solution']}\n```\n")
    (OUT / "REVIEW.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
