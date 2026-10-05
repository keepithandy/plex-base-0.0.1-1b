"""Prepare a tiny pending compositional-binding probe for the failed CSS operation."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys

from diagnose_saved_checkpoints import _check_task
from diagnose_transfer import ROOT, sha256_file

PHASE2 = ROOT / "training/phase2"
SOURCE_CANDIDATE = PHASE2 / "drafts/p2-03-binding-diversity-v1/candidate.jsonl"
SOURCE_CANDIDATE_SHA = "8f3fc7dfc21c4ebb5ce5b40391e9b123521d13df50b2d349e5d6b7c3faf37c2f"
TRAIN_PAIRS = ((0, 0), (0, 1), (1, 1), (1, 2), (2, 0), (2, 2))
EVAL_PAIRS = ((0, 2), (1, 0), (2, 1))
SUPPORTED = ("gap-css-logical-border-03", "gap-css-layout-01")


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def border_case(selector: str, width: str) -> tuple[str, str, list[dict]]:
    value = f"{width} dashed #334155"
    request = (f"For {selector}: Add a {value} border on the block start edge only. "
               "Return one rule with only the requested declarations.")
    solution = f"{selector} {{\n  border-block-start: {value};\n}}"
    checks = [{"kind": "css_declaration", "selector": selector,
               "property": "border-block-start", "value": value}]
    return request, solution, checks


def layout_case(selector: str, gap: str) -> tuple[str, str, list[dict]]:
    request = f"Make {selector} a flex row with a {gap} gap and centered items. Return code only."
    solution = f"{selector} {{ display: flex; gap: {gap}; align-items: center; }}"
    checks = [
        {"kind": "css_declaration", "selector": selector, "property": "display", "value": "flex"},
        {"kind": "css_declaration", "selector": selector, "property": "gap", "value": gap},
        {"kind": "css_declaration", "selector": selector, "property": "align-items", "value": "center"},
    ]
    return request, solution, checks


def matrix(source_id: str):
    if source_id == "gap-css-logical-border-03":
        return ("selector", (".card-edge", ".banner-edge", ".notice-edge"),
                "width", ("1px", "3px", "5px"), border_case)
    if source_id == "gap-css-layout-01":
        return ("selector", (".actions", ".filters", ".controls"),
                "gap", ("6px", "14px", "28px"), layout_case)
    raise ValueError(f"Unsupported source id: {source_id}; choose one of {', '.join(SUPPORTED)}")


def build(source_id: str) -> tuple[list[dict], list[dict], dict]:
    slot_a, values_a, slot_b, values_b, render = matrix(source_id)
    train, evaluation = [], []
    for split, pairs in (("train", TRAIN_PAIRS), ("evaluation-only", EVAL_PAIRS)):
        for index, (a_index, b_index) in enumerate(pairs):
            a, b = values_a[a_index], values_b[b_index]
            request, solution, checks = render(a, b)
            row = {
                "schemaVersion": 1,
                "id": f"compositional-{source_id}-{split}-{index}",
                "sourceId": source_id,
                "splitGroupId": f"compositional-{source_id}",
                "kind": "compositional-variation",
                "language": "css",
                "request": request,
                "solution": solution,
                "checks": checks,
                "bindings": {slot_a: a, slot_b: b},
                "use": "training-candidate" if split == "train" else "evaluation-only-never-train",
                "approvalStatus": "pending-owner-review" if split == "train" else "evaluation-only",
                "provenance": "codex-authored-compositional-binding-probe",
            }
            (train if split == "train" else evaluation).append(row)
    design = {"slotA": slot_a, "slotAValues": list(values_a),
              "slotB": slot_b, "slotBValues": list(values_b),
              "trainingPairs": [list(pair) for pair in TRAIN_PAIRS],
              "evaluationPairs": [list(pair) for pair in EVAL_PAIRS]}
    return train, evaluation, design


def validate(train: list[dict], evaluation: list[dict], design: dict) -> None:
    if len(train) != 6 or len(evaluation) != 3:
        raise ValueError("Compositional probe must contain exactly six train and three evaluation records")
    if set(map(tuple, design["trainingPairs"])) & set(map(tuple, design["evaluationPairs"])):
        raise ValueError("Training and evaluation pairings overlap")
    for slot, values in ((design["slotA"], design["slotAValues"]),
                         (design["slotB"], design["slotBValues"])):
        counts = Counter(row["bindings"][slot] for row in train)
        if set(counts) != set(values) or any(counts[value] < 2 for value in values):
            raise ValueError(f"Every {slot} value must appear at least twice in training")
        if set(row["bindings"][slot] for row in evaluation) != set(values):
            raise ValueError(f"Every {slot} value must appear in held-out recombinations")
    train_pairs = {tuple(sorted(row["bindings"].items())) for row in train}
    if any(tuple(sorted(row["bindings"].items())) in train_pairs for row in evaluation):
        raise ValueError("Evaluation contains a seen binding pair")

    known_requests = set()
    for filename in (SOURCE_CANDIDATE, PHASE2 / "drafts/p2-03-binding-diversity-v1/evaluation-only.jsonl"):
        for line in filename.read_text(encoding="utf-8").splitlines():
            known_requests.add(normalized(json.loads(line)["request"]))
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for CSS syntax/static validation")
    for row in train + evaluation:
        if normalized(row["request"]) in known_requests:
            raise ValueError("Probe duplicates an existing P2-03 request")
        static = _check_task(
            {"id": row["id"], "language": row["language"], "difficulty": "basic", "checks": row["checks"]},
            "\n" + row["solution"], node, 5.0,
        )
        if not static["passed"] or static["parseStatus"] != "pass":
            raise ValueError(f"Reference failed probe checks: {row['id']}")


def write_rows(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return sha256_file(path)


def prepare(output: Path, source_id: str) -> dict:
    if source_id not in SUPPORTED:
        raise ValueError(f"Source id must be one of {', '.join(SUPPORTED)}")
    if sha256_file(SOURCE_CANDIDATE) != SOURCE_CANDIDATE_SHA:
        raise ValueError("Pinned P2-03 source candidate changed")
    if output.exists():
        raise FileExistsError("Candidate directory already exists; choose a fresh path")
    train, evaluation, design = build(source_id)
    validate(train, evaluation, design)
    output.mkdir(parents=True, exist_ok=False)
    train_sha = write_rows(output / "candidate.jsonl", train)
    eval_sha = write_rows(output / "evaluation-only.jsonl", evaluation)
    review = {
        "schemaVersion": 1,
        "candidate": "p2-04-compositional-binding-probe-v1",
        "approvalStatus": "pending-owner-review",
        "sourceId": source_id,
        "sourceCandidateSha256": SOURCE_CANDIDATE_SHA,
        "candidateJsonlSha256": train_sha,
        "evaluationJsonlSha256": eval_sha,
        "trainingCandidateRecords": len(train),
        "evaluationOnlyRecords": len(evaluation),
        "languageCounts": dict(Counter(row["language"] for row in train)),
        "design": design,
        "allSlotValuesSeenInTraining": True,
        "allEvaluationPairsUnseen": True,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    (output / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    sections = [
        "# P2-04 compositional-binding probe candidate\n",
        "Status: **pending owner review**. No model has been trained on these records.\n",
        f"Failed-operation source: `{source_id}`.\n",
        "The probe uses two independently varied binding slots. Every individual slot value appears in training, "
        "while each evaluation example is a pairing never shown during training.\n",
        "## Training candidate\n",
    ]
    for row in train:
        sections.append(f"### {row['id']}\n\nBindings: `{json.dumps(row['bindings'], sort_keys=True)}`\n\n"
                        f"Request: {row['request']}\n\n```css\n{row['solution']}\n```\n")
    sections.append("## Evaluation only — never train\n")
    for row in evaluation:
        sections.append(f"### {row['id']}\n\nBindings: `{json.dumps(row['bindings'], sort_keys=True)}`\n\n"
                        f"Request: {row['request']}\n\n```css\n{row['solution']}\n```\n")
    sections.append(f"## Identities\n\nCandidate SHA-256: `{train_sha}`\n\nEvaluation SHA-256: `{eval_sha}`\n")
    (output / "REVIEW.md").write_text("\n".join(sections), encoding="utf-8")
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", choices=SUPPORTED, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output, args.source_id), indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"plex-compositional-candidate: {exc}", file=sys.stderr)
        sys.exit(2)
