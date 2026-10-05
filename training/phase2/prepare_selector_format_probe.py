"""Prepare a hashable P2-08 selector-copy candidate with wording/layout controls.

This module creates review files only. It never trains a model or opens the final holdout.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text, source_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-08-selector-format-v1"
PREVIOUS_CANDIDATE = PHASE2 / "drafts/p2-07-instruction-invariance-v1/candidate.jsonl"
PREVIOUS_CANDIDATE_SHA = "ed0bee7c2c7f99ffaa7c349ba4e644d8c26d33266976fbe3fb8e96af1095245f"

BASELINE_SELECTORS = (".actions", ".filters", ".controls")
ADDITIONAL_SELECTORS = (
    ".alpha-panel", ".bravo-item", ".charlie-list", ".delta-card", ".echo-label",
)
SELECTORS = BASELINE_SELECTORS + ADDITIONAL_SELECTORS
TRAINING_PHRASES = (
    ("return-exactly", "Return this selector exactly: {value}"),
    ("copy-unchanged", "Copy this selector unchanged: {value}"),
    ("repeat-as-shown", "Repeat the selector exactly as shown: {value}"),
    ("output-only", "Output only the selector shown here: {value}"),
)
HELD_OUT_PHRASE = ("give-back-no-changes", "Give back this selector with no changes: {value}")
LAYOUTS = ("colon-space", "colon-newline")
CONTRACT = "Return exactly the requested value and nothing else."
EXPERIMENT = "p2-08-selector-format-v1"


def _request(template: str, value: str, layout: str) -> str:
    request = template.format(value=value)
    if layout == "colon-newline":
        marker = ": " + value
        if not request.endswith(marker):
            raise ValueError("Phrase template does not end in the controlled value slot")
        return request[:-len(marker)] + ":\n" + value
    if layout != "colon-space":
        raise ValueError(f"Unknown value layout: {layout}")
    return request


def _canonical_text_sha256(path: Path) -> str:
    text = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(text).hexdigest()


def _row(value: str, phrase_id: str, template: str, layout: str, evaluation: bool) -> dict:
    split = "evaluation" if evaluation else "train"
    safe_value = value.removeprefix(".")
    return {
        "schemaVersion": 1,
        "id": f"p2-08-selector-{phrase_id}-{layout}-{safe_value}-{split}",
        "operationFamily": "selector-copy",
        "language": "css",
        "request": _request(template, value, layout),
        "solution": value,
        "contract": CONTRACT,
        "checks": [{"kind": "exact_text", "value": value}],
        "bindings": {"selector": value},
        "value": value,
        "phrasingId": phrase_id,
        "phrasingGroup": "held-out" if evaluation else "training",
        "layoutId": layout,
        "splitGroupId": EXPERIMENT,
        "sourceId": EXPERIMENT,
        "use": "evaluation-only-never-train" if evaluation else "training-candidate",
        "approvalStatus": "evaluation-only" if evaluation else "pending-owner-review",
        "provenance": "codex-authored-selector-format-diagnostic",
    }


def build() -> tuple[list[dict], list[dict]]:
    train = [
        _row(value, phrase_id, template, layout, False)
        for phrase_id, template in TRAINING_PHRASES
        for layout in LAYOUTS
        for value in SELECTORS
    ]
    held_id, held_template = HELD_OUT_PHRASE
    evaluation = [
        _row(value, held_id, held_template, layout, True)
        for layout in LAYOUTS
        for value in SELECTORS
    ]
    validate(train, evaluation)
    return train, evaluation


def validate(train: list[dict], evaluation: list[dict]) -> None:
    if len(train) != 64 or len(evaluation) != 16:
        raise ValueError("P2-08 requires 64 training and 16 evaluation records")
    if len(SELECTORS) != 8 or len(set(SELECTORS)) != 8:
        raise ValueError("P2-08 requires eight distinct selector values")
    if len(set(BASELINE_SELECTORS)) != 3 or set(BASELINE_SELECTORS) & set(ADDITIONAL_SELECTORS):
        raise ValueError("P2-08 baseline and additional selectors must be distinct")
    if len(set(ADDITIONAL_SELECTORS)) != 5:
        raise ValueError("P2-08 requires five additional selector values")
    if Counter((r["phrasingId"], r["layoutId"]) for r in train) != Counter(
        {(phrase_id, layout): 8 for phrase_id, _ in TRAINING_PHRASES for layout in LAYOUTS}
    ):
        raise ValueError("Training phrase/layout matrix is incomplete")
    expected_train = {
        (phrase_id, layout, value)
        for phrase_id, _ in TRAINING_PHRASES
        for layout in LAYOUTS
        for value in SELECTORS
    }
    expected_eval = {(HELD_OUT_PHRASE[0], layout, value) for layout in LAYOUTS for value in SELECTORS}
    actual_train = {(r["phrasingId"], r["layoutId"], r["value"]) for r in train}
    actual_eval = {(r["phrasingId"], r["layoutId"], r["value"]) for r in evaluation}
    if actual_train != expected_train or actual_eval != expected_eval:
        raise ValueError("P2-08 phrase/layout/value matrix differs from its declared design")
    requests = [r["request"] for r in train + evaluation]
    ids = [r["id"] for r in train + evaluation]
    if len(requests) != len(set(requests)) or len(ids) != len(set(ids)):
        raise ValueError("P2-08 requests and IDs must be unique")
    if {r["request"] for r in train} & {r["request"] for r in evaluation}:
        raise ValueError("Held-out requests leak into training")
    if {r["phrasingId"] for r in train} & {r["phrasingId"] for r in evaluation}:
        raise ValueError("Held-out wording leaks into training")
    if {r["value"] for r in evaluation} != {r["value"] for r in train}:
        raise ValueError("Every evaluation selector must be seen in training")
    pending_ids = {row["id"] for row in train}
    for row in train + evaluation:
        if (row["language"] != "css" or row["operationFamily"] != "selector-copy"
                or row["sourceId"] != EXPERIMENT or row["solution"] != row["value"]
                or row["contract"] != CONTRACT or row["bindings"] != {"selector": row["value"]}
                or row["checks"] != [{"kind": "exact_text", "value": row["value"]}]):
            raise ValueError("P2-08 row content differs from its single-selector copy contract")
        should_be_pending = row["id"] in pending_ids
        if should_be_pending != (row["approvalStatus"] == "pending-owner-review"):
            raise ValueError("P2-08 training approval state is invalid")
        if should_be_pending != (row["use"] == "training-candidate"):
            raise ValueError("P2-08 training/evaluation boundary is invalid")
        if row["phrasingGroup"] != ("training" if should_be_pending else "held-out"):
            raise ValueError("P2-08 phrase split metadata is invalid")
        if not should_be_pending and row["phrasingId"] != HELD_OUT_PHRASE[0]:
            raise ValueError("P2-08 evaluation must use only the declared held-out phrasing")
        if row["layoutId"] == "colon-space" and not row["request"].endswith(": " + row["value"]):
            raise ValueError("Inline layout must keep a single space after the colon")
        if row["layoutId"] == "colon-newline" and not row["request"].endswith(":\n" + row["value"]):
            raise ValueError("Line layout must put the value on the following line")
        template = (dict(TRAINING_PHRASES).get(row["phrasingId"])
                    if should_be_pending else HELD_OUT_PHRASE[1])
        if template is None or row["request"] != _request(template, row["value"], row["layoutId"]):
            raise ValueError("P2-08 request text does not match its declared phrase/layout/value")


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8", newline="\n")
    return _canonical_text_sha256(path)


def _review_markdown(review: dict) -> str:
    phrase_table = "\n".join(
        f"| `{phrase_id}` | `{template}` |" for phrase_id, template in TRAINING_PHRASES
    )
    return f"""# P2-08: selector copying with wording and layout controls

Status: **pending owner review**. This preparation creates a candidate and review metadata only. It does not approve or train a model.

## Question

Does selector copying remain exact across alternate instruction wording and a change in how the selector is placed after the colon, when eight selector values are fully represented in training?

P2-07 used three selector values. The held-out wording scored 1/3, with one selector copied as another known selector and one correct selector preceded by repeated periods. A score-only follow-up also found lower accuracy when the input selector moved to a new line. P2-08 expands the values and crosses wording and layout so those factors can be compared separately.

## Candidate design

- Eight selector values: three P2-07 baseline values (`{', '.join(BASELINE_SELECTORS)}`) and five additional values (`{', '.join(ADDITIONAL_SELECTORS)}`).
- Training: 64 records; four training phrasings × two input layouts × eight selectors.
- Evaluation-only: 16 records; one held-out phrasing × two input layouts × the same eight known selectors.
- Output contract: `{CONTRACT}` for every row; one selector per answer; no CSS rule composition.
- Layout levels: inline (`colon-space`) and value on the next line (`colon-newline`). Both occur in training and evaluation, so layout is not held out.

## Training phrase matrix

| Phrase ID | Request template |
|---|---|
{phrase_table}

Held-out wording: `{HELD_OUT_PHRASE[0]}` — `{HELD_OUT_PHRASE[1]}`

Evaluation compares the held-out wording against the training phrasings at each layout while keeping selector values known. Token IDs, decoded output, exact copy, wrong-known-selector output, and extra punctuation should be recorded after approval. This tiny controlled probe cannot establish broad instruction understanding.

## Safeguards and approval boundary

- Frozen tokenizer SHA-256: `{TOKENIZER_SHA}`; no refit.
- Existing model architecture and configuration are unchanged.
- Candidate rows are pending owner review; evaluation rows are evaluation-only.
- `modelTrained: false`; `finalHoldoutOpened: false`.
- No training is authorized until the owner reviews and explicitly approves the exact training and evaluation hashes.
- If approved later, use one fresh seed-1337 scratch model and the existing bounded limit of 100 updates / 10 minutes. Do not extend automatically.

## Exact files and hashes

- Training: {review['trainingRecords']} records — `{review['candidateJsonlSha256']}`
- Evaluation-only: {review['evaluationOnlyRecords']} records — `{review['evaluationJsonlSha256']}`
- The matching review markdown SHA-256 is pinned in `review.json`.
- Maximum prompt / complete-record-with-EOS / answer-with-EOS token lengths: {review['tokenMaxima']['prompt']} / {review['tokenMaxima']['recordIncludingEos']} / {review['tokenMaxima']['answerIncludingEos']}

Preparation tests:

```powershell
uv run --project training --no-sync python -m unittest discover -s training\\tests -p test_p2_08_selector_format_probe.py -v
```
"""


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    try:
        output.relative_to((PHASE2 / "drafts").resolve())
    except ValueError as exc:
        raise ValueError("P2-08 output must remain under training/phase2/drafts") from exc
    if output.exists():
        raise FileExistsError("P2-08 candidate directory exists; choose a fresh path")
    if _canonical_text_sha256(PREVIOUS_CANDIDATE) != PREVIOUS_CANDIDATE_SHA:
        raise ValueError("P2-07 baseline candidate changed; refusing to reuse its selector set")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen reference tokenizer changed; refusing candidate preparation")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    train, evaluation = build()
    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prefix = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        whole = tokenizer.encode(source_text(row, settings["outputContracts"]))
        answer = len(whole) - len(prefix) + 1
        if whole[:len(prefix)] != prefix or len(whole) + 1 > 512:
            raise ValueError(f"P2-08 token/context budget failed for {row['id']}")
        if answer > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"P2-08 answer budget failed for {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prefix))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(whole) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], answer)
    output.mkdir(parents=True, exist_ok=False)
    candidate_sha = _write_jsonl(output / "candidate.jsonl", train)
    evaluation_sha = _write_jsonl(output / "evaluation-only.jsonl", evaluation)
    review = {
        "schemaVersion": 1,
        "candidate": EXPERIMENT,
        "approvalStatus": "pending-owner-review",
        "trainingRecords": len(train),
        "evaluationOnlyRecords": len(evaluation),
        "selectors": list(SELECTORS),
        "baselineSelectors": list(BASELINE_SELECTORS),
        "additionalSelectors": list(ADDITIONAL_SELECTORS),
        "trainingPhrases": [{"id": pid, "template": template} for pid, template in TRAINING_PHRASES],
        "heldOutPhrase": {"id": HELD_OUT_PHRASE[0], "template": HELD_OUT_PHRASE[1]},
        "layouts": list(LAYOUTS),
        "candidateJsonlSha256": candidate_sha,
        "evaluationJsonlSha256": evaluation_sha,
        "reviewMarkdownSha256": None,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "allEvaluationValuesSeenInTraining": True,
        "evaluationWordingAbsentFromTraining": True,
        "fullyCrossedTrainingMatrix": True,
        "formatFullyCrossedWithWordingAndValues": True,
        "tokenMaxima": maxima,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    markdown_path = output / "REVIEW.md"
    markdown_path.write_text(_review_markdown(review), encoding="utf-8", newline="\n")
    review["reviewMarkdownSha256"] = _canonical_text_sha256(markdown_path)
    json_path = output / "review.json"
    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8", newline="\n")
    review["reviewJsonSha256"] = _canonical_text_sha256(json_path)
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-08-prepare: {exc}", file=sys.stderr)
        raise SystemExit(1)
