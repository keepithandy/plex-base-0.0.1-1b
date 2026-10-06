"""Create a hash-pinned CSS edit development set; never train or open final data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-14-css-edit-step200-v1"
TASK_SET_SHA256 = "0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e"
TASKS = (
    ("gap", "basic", ".notice-list { display: flex; gap: 0.5rem; }",
     "Change only the gap from 0.5rem to 1rem; preserve the display setting.",
     {"display": "flex", "gap": "1rem"}),
    ("banner-color", "basic", ".promo-banner { background-color: #f3f4f6; color: #111827; }",
     "Change only the background color to #dbeafe; preserve the text color.",
     {"background-color": "#dbeafe", "color": "#111827"}),
    ("flex-direction", "basic", ".action-row { display: flex; flex-direction: column; align-items: flex-start; }",
     "Change the flex direction from column to row; preserve display and alignment.",
     {"display": "flex", "flex-direction": "row", "align-items": "flex-start"}),
    ("object-fit", "basic", ".product-thumb { width: 6rem; height: 6rem; object-fit: contain; }",
     "Change object-fit from contain to cover; preserve width and height.",
     {"width": "6rem", "height": "6rem", "object-fit": "cover"}),
    ("logical-margin", "edge", ".content-pane { margin-left: 1rem; margin-top: 0.5rem; }",
     "Replace the physical left margin with an equivalent inline-start margin; preserve its 1rem value and the top margin.",
     {"margin-inline-start": "1rem", "margin-top": "0.5rem"}),
    ("sticky-banner", "edge", ".site-banner { position: relative; z-index: 2; }",
     "Make the banner sticky at the top (top: 0); preserve its z-index.",
     {"position": "sticky", "top": "0", "z-index": "2"}),
    ("line-height", "basic", ".field-hint { font-size: 0.875rem; line-height: 1.4; color: #4b5563; }",
     "Change line-height to 1.6; preserve font size and color.",
     {"font-size": "0.875rem", "line-height": "1.6", "color": "#4b5563"}),
    ("font-weight", "basic", ".card-title { margin: 0 0 0.75rem; font-weight: 500; }",
     "Increase font-weight to 600; preserve the margin.",
     {"margin": "0 0 0.75rem", "font-weight": "600"}),
    ("remove-decoration", "edge", ".secondary-link { color: #2563eb; text-decoration: underline; }",
     "Remove the text decoration while preserving the link color.",
     {"color": "#2563eb"}),
    ("show-menu", "basic", ".menu-panel { display: none; padding: 1rem; }",
     "Show the menu panel by changing display to block; preserve its padding.",
     {"display": "block", "padding": "1rem"}),
    ("two-column-grid", "edge", ".form-grid { display: grid; grid-template-columns: 1fr; gap: 1rem; }",
     "Change the grid to two equal minmax(0, 1fr) columns; preserve display and gap.",
     {"display": "grid", "grid-template-columns": "repeat(2, minmax(0, 1fr))", "gap": "1rem"}),
    ("toast-layer", "edge", ".toast { position: fixed; inset-inline-end: 1rem; bottom: 1rem; }",
     "Add z-index 1000; preserve the fixed position and both offsets.",
     {"position": "fixed", "inset-inline-end": "1rem", "bottom": "1rem", "z-index": "1000"}),
)


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def task_request(source: str, instruction: str) -> str:
    return ("Starting CSS:\n" + source + "\n\n" + instruction
            + " Return the complete updated stylesheet with no unrelated rules.")


def build() -> dict:
    baseline = json.loads((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    old_requests = {normalized(task["request"]) for task in baseline["tasks"]}
    tasks = []
    for slug, difficulty, source, instruction, declarations in TASKS:
        selector = source.split("{", 1)[0].strip()
        request = task_request(source, instruction)
        checks = [
            {"kind": "css_declaration", "selector": selector,
             "property": name, "value": value}
            for name, value in declarations.items()
        ]
        checks.append({"kind": "css_stylesheet_exact", "rules": {selector: declarations}})
        tasks.append({
            "id": f"p2-14-css-edit-{slug}",
            "language": "css",
            "difficulty": difficulty,
            "request": request,
            "provenance": "codex-authored",
            "checks": checks,
        })
    requests = [normalized(task["request"]) for task in tasks]
    if (len(tasks) != 12 or len(set(requests)) != len(requests)
            or set(requests) & old_requests):
        raise ValueError("P2-14 task count, uniqueness, or development-prompt separation failed")
    return {
        "schemaVersion": 1,
        "setId": "p2-14-css-edit-development-v1",
        "kind": "development",
        "provenance": "codex-authored",
        "outputContracts": baseline["outputContracts"],
        "inferenceDefaults": baseline["inferenceDefaults"],
        "tasks": tasks,
    }


def encoded(task_set: dict) -> bytes:
    return (json.dumps(task_set, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def prepare(output: Path, *, verify_only: bool = False) -> dict:
    output = output.resolve()
    output.relative_to((PHASE2 / "drafts").resolve())
    task_set = build()
    raw = encoded(task_set)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != TASK_SET_SHA256:
        raise ValueError("P2-14 task set differs from the source-pinned SHA-256")
    path = output / "task-set.json"
    if verify_only:
        if not path.is_file() or path.read_bytes() != raw:
            raise ValueError("Saved P2-14 task set differs from deterministic reconstruction")
        review = json.loads((output / "review.json").read_text(encoding="utf-8"))
        if review.get("taskSetSha256") != digest or review.get("finalHoldoutOpened") is not False:
            raise ValueError("P2-14 review metadata does not match pinned development set")
        return {"taskCount": len(task_set["tasks"]), "taskSetSha256": digest,
                "verified": True, "finalHoldoutOpened": False}
    if output.exists():
        raise FileExistsError("P2-14 development draft exists; choose a fresh directory")
    output.mkdir(parents=True)
    path.write_bytes(raw)
    review = {
        "schemaVersion": 1,
        "setId": task_set["setId"],
        "taskSetSha256": digest,
        "tasks": len(task_set["tasks"]),
        "taskFamily": "single-rule CSS edits with whole-stylesheet exact-map checks",
        "sourceSnippetAndEditTargetsAreInRequest": True,
        "completeExpectedRuleMapsAreNotInRenderedPrompt": True,
        "overlapCheckedAgainst": "P2-01b development requests, exact and whitespace/case-normalized",
        "trainingUsed": False,
        "runtimeValidationLossUsed": False,
        "finalHoldoutOpened": False,
    }
    (output / "review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output, verify_only=args.verify_only), indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-14-css-edit-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
