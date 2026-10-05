"""Build and hash-pin a fresh evaluation-only set for the P2-12 step-200 checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT
from prepare_explicit_answer_start_candidate import OUTPUT_CONTRACT, build as build_p210
from prepare_p2_10_wider_evaluation import _build as build_p210_wider
from prepare_p2_11_balanced_wording_candidate import _jsonl as jsonl_bytes, build as build_p211
from prepare_p2_12_answer_start_candidate_v2 import build as build_p212
from prepare_selector_format_probe import SELECTORS, TRAINING_PHRASES, build as build_p208

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-13-step200-evaluation-v1"
EXPERIMENT = "p2-13-step200-wording-evaluation-v1"
EXPECTED_EVALUATION_SHA256 = "d185156b0126cecd1de7b21a6d9a5de23eda67bf14a7192dd904c654449b03c2"
PHRASES = (
    ("ask-exact-selector-text", "What is the exact text of this selector? {value}"),
    ("report-selector-unchanged", "Report the selector shown here unchanged: {value}"),
    ("selector-entire-output", "Use this selector as the entire output: {value}"),
    ("echo-selector-unmodified", "Echo the selector displayed below without alteration: {value}"),
    ("give-selector-as-written", "Give the selector exactly as it appears here: {value}"),
    ("return-css-selector-punctuation", "Return the CSS selector with its punctuation intact: {value}"),
)
LAYOUTS = ("colon-space", "colon-newline")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def request(template: str, selector: str, layout: str) -> str:
    text = template.format(value=selector)
    if layout == "colon-newline":
        text = text[:-len(selector)] + "\n" + selector
    return text


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def build() -> list[dict]:
    p210_train, p210_eval, _ = build_p210()
    p210_wide, _ = build_p210_wider()
    p211_train, p211_eval = build_p211()
    p212_train, p212_eval = build_p212()
    p208_train, p208_eval = build_p208()
    base = {(row["layoutId"], row["value"]): row for row in p210_train}
    if len(base) != 16 or set(SELECTORS) != {row["value"] for row in p210_train}:
        raise ValueError("Pinned selector/layout source matrix changed")

    rows: list[dict] = []
    for phrase_id, template in PHRASES:
        for layout in LAYOUTS:
            for selector in SELECTORS:
                row = dict(base[(layout, selector)])
                row.update({
                    "id": f"{EXPERIMENT}-{phrase_id}-{layout}-{selector.removeprefix('.')}",
                    "request": request(template, selector, layout),
                    "phrasingId": phrase_id,
                    "phrasingGroup": "held-out-development",
                    "sourceId": EXPERIMENT,
                    "splitGroupId": EXPERIMENT,
                    "provenance": "codex-authored-fresh-step200-wording-development-evaluation",
                    "approvalStatus": "evaluation-only",
                    "use": "evaluation-only-never-train",
                })
                rows.append(row)

    historical = (p208_train + p208_eval + p210_train + p210_eval + p210_wide
                  + p211_train + p211_eval + p212_train + p212_eval)
    historical_exact = {row["request"] for row in historical}
    historical_normalized = {normalized(row["request"]) for row in historical}
    exact = [row["request"] for row in rows]
    norm = [normalized(value) for value in exact]
    if (len(rows) != 96 or len(set(exact)) != 96
            or set(exact) & historical_exact or set(norm) & historical_normalized):
        raise ValueError("Fresh P2-13 development evaluation overlaps prior or duplicated requests")
    expected_cells = {(phrase, layout, selector) for phrase, _ in PHRASES
                      for layout in LAYOUTS for selector in SELECTORS}
    actual_cells = {(row["phrasingId"], row["layoutId"], row["value"]) for row in rows}
    if actual_cells != expected_cells:
        raise ValueError("P2-13 phrase/layout/selector matrix is incomplete")
    if any(row["contract"] != OUTPUT_CONTRACT or row["solution"] != row["value"]
           or row["bindings"] != {"selector": row["value"]}
           or row["checks"] != [{"kind": "exact_text", "value": row["value"]}]
           or row["use"] != "evaluation-only-never-train" for row in rows):
        raise ValueError("P2-13 changed the exact-selector task or evaluation-only boundary")
    return rows


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare(output: Path, *, verify_only: bool = False) -> dict:
    output = output.resolve()
    # Keep the reviewable source files under the phase2 draft tree.
    output.relative_to((PHASE2 / "drafts").resolve())
    candidate = build()
    encoded = jsonl_bytes(candidate)
    digest = sha256(encoded)
    if digest != EXPECTED_EVALUATION_SHA256:
        raise ValueError("P2-13 evaluation-only rows differ from their pinned SHA-256")
    if verify_only:
        path = output / "evaluation-only.jsonl"
        if not path.is_file() or path.read_bytes() != encoded:
            raise ValueError("Saved P2-13 evaluation set differs from deterministic reconstruction")
        return {"evaluationOnlyRecords": len(candidate), "evaluationJsonlSha256": digest,
                "verified": True, "finalHoldoutOpened": False}
    if output.exists():
        raise FileExistsError("P2-13 evaluation draft already exists")
    output.mkdir(parents=True)
    (output / "evaluation-only.jsonl").write_bytes(encoded)
    review = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "status": "evaluation-only-development-set-hash-pinned",
        "evaluationOnlyRecords": len(candidate),
        "phrases": [{"id": phrase_id, "template": template} for phrase_id, template in PHRASES],
        "layouts": list(LAYOUTS),
        "selectors": list(SELECTORS),
        "evaluationJsonlSha256": digest,
        "checkpointSha256": "e1e6821eaf5af2bfb9ddb0de7031790dc96e6d0e8f706bb4521d005219736065",
        "trainingUsed": False,
        "runtimeValidationLossUsed": False,
        "independentFinalHoldout": False,
        "finalHoldoutOpened": False,
        "overlapPolicy": "Exact and whitespace/case-normalized requests checked against P2-08, P2-10, P2-10 wider evaluation, P2-11, and P2-12 training/evaluation requests.",
    }
    write_json(output / "review.json", review)
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output, verify_only=args.verify_only), indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-13-evaluation-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
