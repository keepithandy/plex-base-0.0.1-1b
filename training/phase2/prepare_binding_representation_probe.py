"""Prepare the pending P2-06 binding-representation ladder; never train or approve."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, prompt_text, sha256_file, source_text
from prepare_compositional_experiment import TOKENIZER_BUNDLE, TOKENIZER_SHA, DEV_SHA
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
SELECTORS = (".actions", ".filters", ".controls")
GAPS = ("6px", "14px", "28px")
TRAIN_PAIRS = (
    (".actions", "6px"),
    (".actions", "14px"),
    (".filters", "14px"),
    (".filters", "28px"),
    (".controls", "6px"),
    (".controls", "28px"),
)
HELDOUT_PAIRS = (
    (".actions", "28px"),
    (".filters", "6px"),
    (".controls", "14px"),
)
LEVELS = ("single-copy", "dual-binding", "css-composition")
PROVENANCE = "codex-authored-p2-06-binding-representation-probe"


def single_row(kind: str, value: str, index: int, evaluation: bool) -> dict:
    if kind == "selector":
        train_request = f"Return this selector exactly: {value}"
        eval_request = f"Copy this selector without changes: {value}"
    else:
        train_request = f"Return this gap exactly: {value}"
        eval_request = f"Copy this gap value without changes: {value}"
    return {
        "schemaVersion": 1,
        "id": f"p2-06-single-{kind}-{index}-{'eval' if evaluation else 'train'}",
        "level": "single-copy",
        "language": "css",
        "request": eval_request if evaluation else train_request,
        "solution": value,
        "contract": "Return exactly the requested token and nothing else.",
        "checks": [{"kind": "exact_text", "value": value}],
        "bindings": {kind: value},
        "splitGroupId": f"p2-06-single-{kind}",
        "sourceId": "p2-06-binding-representation",
        "use": "evaluation-only-never-train" if evaluation else "training-candidate",
        "approvalStatus": "evaluation-only" if evaluation else "pending-owner-review",
        "provenance": PROVENANCE,
    }


def dual_row(selector: str, gap: str, index: int, evaluation: bool) -> dict:
    request = (
        f"Selector: {selector}\n"
        f"Gap: {gap}\n"
        "Return exactly two lines: selector=<selector> then gap=<gap>."
    )
    solution = f"selector={selector}\ngap={gap}"
    return {
        "schemaVersion": 1,
        "id": f"p2-06-dual-{index}-{'eval' if evaluation else 'train'}",
        "level": "dual-binding",
        "language": "css",
        "request": request,
        "solution": solution,
        "contract": "Return exactly two lines: selector=<selector> then gap=<gap>.",
        "checks": [{"kind": "exact_text", "value": solution}],
        "bindings": {"selector": selector, "gap": gap},
        "splitGroupId": "p2-06-dual-binding",
        "sourceId": "p2-06-binding-representation",
        "use": "evaluation-only-never-train" if evaluation else "training-candidate",
        "approvalStatus": "evaluation-only" if evaluation else "pending-owner-review",
        "provenance": PROVENANCE,
    }


def css_row(selector: str, gap: str, index: int, evaluation: bool) -> dict:
    request = (
        f"Selector: {selector}\n"
        f"Gap: {gap}\n"
        "Write one flex-row rule with centered items using exactly that selector and gap."
    )
    solution = f"{selector} {{ display: flex; gap: {gap}; align-items: center; }}"
    return {
        "schemaVersion": 1,
        "id": f"p2-06-css-{index}-{'eval' if evaluation else 'train'}",
        "level": "css-composition",
        "language": "css",
        "request": request,
        "solution": solution,
        "checks": [
            {"kind": "css_declaration", "selector": selector, "property": "display", "value": "flex"},
            {"kind": "css_declaration", "selector": selector, "property": "gap", "value": gap},
            {"kind": "css_declaration", "selector": selector, "property": "align-items", "value": "center"},
        ],
        "bindings": {"selector": selector, "gap": gap},
        "splitGroupId": "p2-06-css-composition",
        "sourceId": "p2-06-binding-representation",
        "use": "evaluation-only-never-train" if evaluation else "training-candidate",
        "approvalStatus": "evaluation-only" if evaluation else "pending-owner-review",
        "provenance": PROVENANCE,
    }


def build() -> dict[str, dict[str, list[dict]]]:
    single_train = [single_row("selector", value, index, False)
                    for index, value in enumerate(SELECTORS)]
    single_train += [single_row("gap", value, index, False)
                     for index, value in enumerate(GAPS)]
    single_eval = [single_row("selector", value, index, True)
                   for index, value in enumerate(SELECTORS)]
    single_eval += [single_row("gap", value, index, True)
                    for index, value in enumerate(GAPS)]
    dual_train = [dual_row(selector, gap, index, False)
                  for index, (selector, gap) in enumerate(TRAIN_PAIRS)]
    dual_eval = [dual_row(selector, gap, index, True)
                 for index, (selector, gap) in enumerate(HELDOUT_PAIRS)]
    css_train = [css_row(selector, gap, index, False)
                 for index, (selector, gap) in enumerate(TRAIN_PAIRS)]
    css_eval = [css_row(selector, gap, index, True)
                for index, (selector, gap) in enumerate(HELDOUT_PAIRS)]
    return {
        "single-copy": {"train": single_train, "evaluation": single_eval},
        "dual-binding": {"train": dual_train, "evaluation": dual_eval},
        "css-composition": {"train": css_train, "evaluation": css_eval},
    }


def pair(row: dict) -> tuple[str, str]:
    bindings = row["bindings"]
    return bindings["selector"], bindings["gap"]


def validate(levels: dict[str, dict[str, list[dict]]]) -> None:
    if set(levels) != set(LEVELS):
        raise ValueError("P2-06 level list changed")
    single = levels["single-copy"]
    if len(single["train"]) != 6 or len(single["evaluation"]) != 6:
        raise ValueError("Single-copy level requires six train and six evaluation records")
    for kind, expected in (("selector", set(SELECTORS)), ("gap", set(GAPS))):
        train_values = {row["bindings"][kind] for row in single["train"] if kind in row["bindings"]}
        eval_values = {row["bindings"][kind] for row in single["evaluation"] if kind in row["bindings"]}
        if train_values != expected or eval_values != expected:
            raise ValueError(f"Single-copy {kind} values changed")
    if any(row["request"] == other["request"]
           for row, other in zip(single["train"], single["evaluation"])):
        raise ValueError("Single-copy evaluation wording must differ from training wording")

    expected_train, expected_eval = set(TRAIN_PAIRS), set(HELDOUT_PAIRS)
    if expected_train & expected_eval or expected_train | expected_eval != {
        (selector, gap) for selector in SELECTORS for gap in GAPS
    }:
        raise ValueError("P2-06 matrix must partition the complete 3x3 space")
    for level in ("dual-binding", "css-composition"):
        train, evaluation = levels[level]["train"], levels[level]["evaluation"]
        if len(train) != 6 or len(evaluation) != 3:
            raise ValueError(f"{level} requires six train and three held-out records")
        if {pair(row) for row in train} != expected_train or {pair(row) for row in evaluation} != expected_eval:
            raise ValueError(f"{level} pair split changed")
        selector_counts = Counter(row["bindings"]["selector"] for row in train)
        gap_counts = Counter(row["bindings"]["gap"] for row in train)
        if set(selector_counts.values()) != {2} or set(gap_counts.values()) != {2}:
            raise ValueError(f"{level} training must show every selector and gap exactly twice")
    if [row["bindings"] for row in levels["dual-binding"]["train"]] != [
            row["bindings"] for row in levels["css-composition"]["train"]]:
        raise ValueError("Dual-binding and CSS levels must use identical training bindings")
    if [row["bindings"] for row in levels["dual-binding"]["evaluation"]] != [
            row["bindings"] for row in levels["css-composition"]["evaluation"]]:
        raise ValueError("Dual-binding and CSS levels must use identical held-out bindings")

    seen_ids, seen_requests = set(), set()
    for level in LEVELS:
        for row in levels[level]["train"] + levels[level]["evaluation"]:
            if row["id"] in seen_ids or row["request"] in seen_requests:
                raise ValueError("P2-06 contains a duplicate id or request")
            seen_ids.add(row["id"])
            seen_requests.add(row["request"])
            if row["language"] != "css" or row["sourceId"] != "p2-06-binding-representation":
                raise ValueError("P2-06 row identity changed")
            if row["use"] == "training-candidate" and row["approvalStatus"] != "pending-owner-review":
                raise ValueError("Training candidates must remain pending owner review")
            if row["use"] != "training-candidate" and row["approvalStatus"] != "evaluation-only":
                raise ValueError("Evaluation rows must remain evaluation-only")


def write_rows(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return sha256_file(path)


def prepare(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError("P2-06 candidate directory exists; choose a fresh path")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen reference tokenizer changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    levels = build()
    validate(levels)
    output.mkdir(parents=True, exist_ok=False)
    identities, maxima = {}, {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for level in LEVELS:
        root = output / level
        root.mkdir()
        train_path, eval_path = root / "candidate.jsonl", root / "evaluation-only.jsonl"
        identities[level] = {
            "candidateJsonlSha256": write_rows(train_path, levels[level]["train"]),
            "evaluationJsonlSha256": write_rows(eval_path, levels[level]["evaluation"]),
            "trainingRecords": len(levels[level]["train"]),
            "evaluationOnlyRecords": len(levels[level]["evaluation"]),
        }
        for row in levels[level]["train"] + levels[level]["evaluation"]:
            prefix = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            whole = tokenizer.encode(source_text(row, settings["outputContracts"]))
            answer = len(whole) - len(prefix) + 1
            if whole[:len(prefix)] != prefix or len(whole) + 1 > 512:
                raise ValueError(f"P2-06 token budget failed for {row['id']}")
            if answer > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
                raise ValueError(f"P2-06 answer budget failed for {row['id']}")
            maxima["prompt"] = max(maxima["prompt"], len(prefix))
            maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(whole) + 1)
            maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], answer)
    review = {
        "schemaVersion": 1,
        "candidate": "p2-06-binding-representation-probe-v1",
        "approvalStatus": "pending-owner-review",
        "levels": identities,
        "selectors": list(SELECTORS),
        "gaps": list(GAPS),
        "trainingPairs": [list(pair) for pair in TRAIN_PAIRS],
        "heldOutPairs": [list(pair) for pair in HELDOUT_PAIRS],
        "singleCopyEvaluationUsesSeenValuesWithNewWording": True,
        "dualAndCssUseIdenticalBindingSplits": True,
        "freshModelPerLevelPlanned": True,
        "trainingObjectivePlanned": "answer-eos-only-complete-record-v1",
        "referenceTokenizerSha256": TOKENIZER_SHA,
        "referenceTokenizerRefitted": False,
        "tokenMaxima": maxima,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    (output / "review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sections = [
        "# P2-06 binding-representation probe\n",
        "Status: **pending owner review**. No model has been trained on these records.\n",
        "P2-06 separates three questions with independent fresh-model arms: can Plex preserve one requested binding, "
        "can it preserve two bindings simultaneously, and can it compose the same two bindings into CSS?\n",
        "## Level 1 — single-copy\n",
        "Six training examples expose each selector and gap once. Six evaluation examples use the same values with alternate request wording. "
        "This is deliberately a representation/instruction test, not a novel-value holdout.\n",
        "## Level 2 — dual-binding\n",
        "Six selector-gap pairs are trained and three pairings are held out. The output is only two labeled lines, so CSS generation is removed.\n",
        "## Level 3 — CSS composition\n",
        "Uses the exact same six training pairs and three held-out pairs as Level 2, but requires the full CSS rule. "
        "A Level-2 pass with a Level-3 failure would isolate code composition from multi-binding preservation.\n",
        "## Decision ladder\n",
        "- If Level 1 fails, investigate basic prompt-bound copying/token representation before composition.\n"
        "- If Level 1 passes but Level 2 fails, the bottleneck is simultaneous independent binding.\n"
        "- If Level 2 passes but Level 3 fails, the bottleneck is composing preserved bindings into code.\n"
        "- If all three pass, revisit P2-05 distribution effects rather than representation capacity alone.\n",
        "## Approval boundary\n",
        "The preparer writes review artifacts only. Training remains unauthorized until the exact JSONL hashes are reviewed and approved. "
        "The final project holdout stays closed.\n",
    ]
    for level in LEVELS:
        sections.append(f"## {level}\n")
        for split, label in (("train", "Training candidate"), ("evaluation", "Evaluation only")):
            sections.append(f"### {label}\n")
            for row in levels[level][split]:
                sections.append(
                    f"**{row['id']}**\n\nRequest:\n\n```text\n{row['request']}\n```\n\nExpected:\n\n```text\n{row['solution']}\n```\n"
                )
    sections.append("## Identities\n\n```json\n" + json.dumps(identities, indent=2, sort_keys=True) + "\n```\n")
    (output / "REVIEW.md").write_text("\n".join(sections), encoding="utf-8")
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-06-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
