"""Prepare a review-only P2-11 candidate for wording transfer; never train here."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text, source_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA
from prepare_explicit_answer_start_candidate import (
    OUTPUT_CONTRACT, build as build_p210,
)
from prepare_p2_10_wider_evaluation import _build as build_p210_wider
from prepare_selector_format_probe import SELECTORS, TRAINING_PHRASES
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-11-balanced-wording-transfer-v1"
EXPERIMENT = "p2-11-balanced-wording-transfer-v1"
P210_CANDIDATE_SHA = "ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8"
P210_EVALUATION_SHA = "632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9"
P210_WIDER_EVALUATION_SHA = "da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a"
P210_WIDER_AUDIT_SHA = "28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb"

# These two phrases were low-scoring P2-10 wider-evaluation conditions and are
# deliberately promoted into training. Their exact 32 request strings lose
# held-out status; P2-11 instead evaluates on four new templates.
ADDED_TRAINING_PHRASES = (
    ("reproduce-selector-verbatim", "Reproduce the selector below verbatim: {value}"),
    ("write-selector-character-for-character",
     "Write this selector again, character for character: {value}"),
)
HELD_OUT_PHRASES = (
    ("repeat-css-selector-as-provided", "Repeat this CSS selector exactly as provided: {value}"),
    ("give-literal-selector-after-label", "Give only the literal selector shown after this label: {value}"),
    ("preserve-spelling-and-punctuation",
     "Please preserve the spelling and punctuation of the selector: {value}"),
    ("write-supplied-selector-unchanged", "Write out the supplied selector unchanged: {value}"),
)
PROPOSED_LIMITS = {
    "freshSeed": 1337,
    "maximumSteps": 150,
    "maximumMinutes": 10,
    "maximumTotalSteps": 150,
    "maximumTotalMinutes": 10,
    "microBatch": 1,
    "gradientAccumulation": 16,
    "device": "cuda",
    "automaticExtension": False,
}


def _jsonl(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _request(template: str, selector: str, layout: str) -> str:
    request = template.format(value=selector)
    if layout == "colon-newline":
        request = request[:-len(selector)] + "\n" + selector
    return request


def build() -> tuple[list[dict], list[dict]]:
    base_train, old_evaluation, _baseline = build_p210()
    p210_wider_evaluation, _wider_metadata = build_p210_wider()
    base_lookup = {(row["phrasingId"], row["layoutId"], row["value"]): row
                   for row in base_train}
    if len(base_train) != 64 or set(TRAINING_PHRASES) != {
        (r["phrasingId"], next(t for i, t in TRAINING_PHRASES if i == r["phrasingId"]))
        for r in base_train
    }:
        raise ValueError("P2-10 training phrase matrix changed")
    train = []
    training_specs = list(TRAINING_PHRASES) + list(ADDED_TRAINING_PHRASES)
    for phrase_id, template in training_specs:
        for layout in ("colon-space", "colon-newline"):
            for selector in SELECTORS:
                old = base_lookup[(TRAINING_PHRASES[0][0], layout, selector)]
                row = dict(old)
                row.update({
                    "id": f"{EXPERIMENT}-{phrase_id}-{layout}-{selector.removeprefix('.')}-train",
                    "request": _request(template, selector, layout),
                    "phrasingId": phrase_id,
                    "phrasingGroup": "training",
                    "sourceId": EXPERIMENT,
                    "splitGroupId": EXPERIMENT,
                    "provenance": "codex-authored-balanced-wording-diagnostic",
                    "approvalStatus": "pending-owner-review",
                    "use": "training-candidate",
                })
                train.append(row)

    evaluation = []
    for phrase_id, template in HELD_OUT_PHRASES:
        for layout in ("colon-space", "colon-newline"):
            for selector in SELECTORS:
                old = base_lookup[(TRAINING_PHRASES[0][0], layout, selector)]
                row = dict(old)
                row.update({
                    "id": f"{EXPERIMENT}-{phrase_id}-{layout}-{selector.removeprefix('.')}-evaluation",
                    "request": _request(template, selector, layout),
                    "phrasingId": phrase_id,
                    "phrasingGroup": "held-out",
                    "sourceId": EXPERIMENT,
                    "splitGroupId": EXPERIMENT,
                    "provenance": "codex-authored-independent-heldout-wording",
                    "approvalStatus": "evaluation-only",
                    "use": "evaluation-only-never-train",
                })
                evaluation.append(row)

    _validate(train, evaluation)
    previous_requests = {r["request"] for r in
                         base_train + old_evaluation + p210_wider_evaluation}
    added_training_requests = {
        r["request"] for r in train
        if r["phrasingId"] in {phrase_id for phrase_id, _ in ADDED_TRAINING_PHRASES}
    }
    held_out_requests = {r["request"] for r in evaluation}
    expected_promoted_requests = {
        _request(template, selector, layout)
        for _phrase_id, template in ADDED_TRAINING_PHRASES
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    }
    if added_training_requests != expected_promoted_requests:
        raise ValueError("P2-11 promoted training request matrix changed")
    if added_training_requests & held_out_requests:
        raise ValueError("P2-11 promoted training requests overlap fresh evaluation")
    if held_out_requests & previous_requests:
        raise ValueError("P2-11 fresh evaluation overlaps any historical P2-10 request")
    if added_training_requests & previous_requests != expected_promoted_requests:
        raise ValueError("P2-11 must promote exactly the 32 weak P2-10 wider-evaluation requests")
    return train, evaluation


def _validate(train: list[dict], evaluation: list[dict]) -> None:
    if len(train) != 96 or len(evaluation) != 64:
        raise ValueError("P2-11 matrix requires 96 training / 64 evaluation-only records")
    if {r["value"] for r in train} != set(SELECTORS) or {r["value"] for r in evaluation} != set(SELECTORS):
        raise ValueError("P2-11 must retain the eight known selectors")
    if {r["layoutId"] for r in train + evaluation} != {"colon-space", "colon-newline"}:
        raise ValueError("P2-11 must retain both crossed input layouts")
    expected_train_cells = {
        (phrase_id, layout, selector)
        for phrase_id, _template in list(TRAINING_PHRASES) + list(ADDED_TRAINING_PHRASES)
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    }
    expected_eval_cells = {
        (phrase_id, layout, selector)
        for phrase_id, _template in HELD_OUT_PHRASES
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    }
    if {(r["phrasingId"], r["layoutId"], r["value"]) for r in train} != expected_train_cells:
        raise ValueError("P2-11 training matrix is missing or duplicating a phrase/layout/selector cell")
    if {(r["phrasingId"], r["layoutId"], r["value"]) for r in evaluation} != expected_eval_cells:
        raise ValueError("P2-11 evaluation matrix is missing or duplicating a phrase/layout/selector cell")
    if {r["phrasingId"] for r in train} & {r["phrasingId"] for r in evaluation}:
        raise ValueError("P2-11 evaluation wording leaked into training")
    for rows, status, use, group in (
        (train, "pending-owner-review", "training-candidate", "training"),
        (evaluation, "evaluation-only", "evaluation-only-never-train", "held-out"),
    ):
        ids, requests = [r["id"] for r in rows], [r["request"] for r in rows]
        if len(ids) != len(set(ids)) or len(requests) != len(set(requests)):
            raise ValueError("P2-11 rows must have unique IDs and requests within each split")
        if any(r["approvalStatus"] != status or r["use"] != use or r["phrasingGroup"] != group
               for r in rows):
            raise ValueError("P2-11 row approval/use metadata is incorrect")
        if any(r["contract"] != OUTPUT_CONTRACT or r["solution"] != r["value"]
               or r["bindings"] != {"selector": r["value"]}
               or r["checks"] != [{"kind": "exact_text", "value": r["value"]}]
               for r in rows):
            raise ValueError("P2-11 changed output contract or selector target")
    if {r["request"] for r in train} & {r["request"] for r in evaluation}:
        raise ValueError("P2-11 train/evaluation requests overlap")


def _markdown(review: dict) -> str:
    train = "\n".join(f"| `{p['id']}` | `{p['template']}` |" for p in review["trainingPhrases"])
    evaluation = "\n".join(f"| `{p['id']}` | `{p['template']}` |" for p in review["evaluationPhrases"])
    limits = review["proposedRunLimits"]
    return f"""# P2-11: balanced wording transfer candidate

Status: **review-only candidate; no training approval exists and no run has started**.

## Question

Does adding balanced exposure to two previously weak request phrasings improve exact selector copying on fresh, independently held-out phrasings, under the unchanged explicit answer-start contract?

P2-10's wider read-only audit found 43/64 exact outputs. “Reproduce the selector below verbatim” scored 6/16, with answer-start skips on next-line inputs and duplicated newlines after the expected prefix. “Write this selector again, character for character” scored 5/16, with ten body-token divergences and frequent attraction to `charlie-list`. “Transcribe” and “Preserve” each scored 16/16. P2-11 deliberately promotes the 32 exact requests from those two weak P2-10 wider-evaluation templates into training. Their historical scores remain in the report, but those requests are no longer held-out for a future run. Four entirely new phrasing templates provide fresh evaluation-only requests.

## Controlled design

- Training: {review['trainingRecords']} rows; six phrasings × two layouts × eight selectors. Four phrases retain the P2-10 training matrix; two phrases add examples for the observed weak wording patterns.
- Evaluation-only: {review['evaluationOnlyRecords']} rows; four new phrasings × two layouts × eight selectors. Their exact requests are disjoint from P2-10 training, original evaluation, and wider evaluation, and from P2-11 training.
- Historical holdout transition: {review['p210WiderEvaluationRequestsPromotedToTraining']} of the P2-10 wider-evaluation requests (the two low-scoring phrasings × two layouts × eight selectors) are reused as P2-11 training requests. Their P2-10 results remain historical evidence, not a clean holdout for this follow-up.
- All rows retain the P2-10 output contract: `{OUTPUT_CONTRACT}`. Selector targets, model, architecture, objective, and frozen tokenizer remain fixed.
- Fresh-from-scratch seed 1337 only. Do not continue the P2-10 checkpoint.
- Require **96/96 exact supplied outputs** before interpreting held-out scores. Otherwise mark evaluation inconclusive.
- The proposed {limits['maximumSteps']}-update cap keeps expected uniform record exposure near P2-10's 100 updates over 64 training rows ({limits['maximumSteps']} × 16 / 96 ≈ 25 selections per record in expectation). The cap is a proposal, not run authorization.

## Training phrasings

| Phrase ID | Template |
|---|---|
{train}

## Fresh evaluation-only phrasings

| Phrase ID | Template |
|---|---|
{evaluation}

Each phrase is crossed with inline (`: {{value}}`) and next-line (`:\\n{{value}}`) layouts and the unchanged eight selectors.

## Hashes and run boundary

- Training candidate SHA-256: `{review['candidateJsonlSha256']}`
- Evaluation-only SHA-256: `{review['evaluationJsonlSha256']}`
- Frozen tokenizer SHA-256: `{review['tokenizerSha256']}`; refitting is false.
- Prior evidence reviewed: P2-10 candidate `{P210_CANDIDATE_SHA}`, original evaluation `{P210_EVALUATION_SHA}`, wider evaluation `{P210_WIDER_EVALUATION_SHA}`, checkpoint `{P210_WIDER_AUDIT_SHA}`.
- Proposed limits: {limits['maximumSteps']} updates / {limits['maximumMinutes']} minutes, seed {limits['freshSeed']}, microbatch {limits['microBatch']}, accumulation {limits['gradientAccumulation']}, CUDA, no automatic extension.
- Evaluation approved for training: false. Evaluation approved for runtime validation loss: false. `finalHoldoutOpened`: false.
- No approval artifact exists. Training may begin only after owner approval of these exact hashes and proposed limits.

## Limits

This single-arm diagnostic is sized to preserve expected record exposure while adding phrase variety. It will not isolate phrase diversity from the larger number of unique training records and must not be described as a causal comparison. It remains a tiny selector-copy test, not evidence of general instruction understanding or coding ability.
"""


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    output.relative_to((PHASE2 / "drafts").resolve())
    if output.exists():
        raise FileExistsError("P2-11 candidate directory exists; choose a fresh path")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    train, evaluation = build()
    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        record_ids = tokenizer.encode(source_text(row, settings["outputContracts"]))
        answer_ids = tokenizer.encode("\n" + row["solution"]) + [3]
        if len(record_ids) + 1 > 512 or len(answer_ids) > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"P2-11 context or generation budget failed: {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prompt_ids))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(record_ids) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], len(answer_ids))

    output.mkdir(parents=True, exist_ok=False)
    train_path, eval_path = output / "candidate.jsonl", output / "evaluation-only.jsonl"
    train_path.write_bytes(_jsonl(train))
    eval_path.write_bytes(_jsonl(evaluation))
    summary = {
        "schemaVersion": 1,
        "candidate": EXPERIMENT,
        "reviewStatus": "pending-owner-review",
        "trainingRecords": len(train),
        "evaluationOnlyRecords": len(evaluation),
        "trainingPhrases": [{"id": k, "template": v}
                            for k, v in list(TRAINING_PHRASES) + list(ADDED_TRAINING_PHRASES)],
        "evaluationPhrases": [{"id": k, "template": v} for k, v in HELD_OUT_PHRASES],
        "selectors": list(SELECTORS),
        "layouts": ["colon-space", "colon-newline"],
        "outputContract": OUTPUT_CONTRACT,
        "candidateJsonlSha256": sha256_file(train_path),
        "evaluationJsonlSha256": sha256_file(eval_path),
        "reviewMarkdownSha256": None,
        "sourceP210CandidateSha256": P210_CANDIDATE_SHA,
        "sourceP210EvaluationSha256": P210_EVALUATION_SHA,
        "sourceP210WiderEvaluationSha256": P210_WIDER_EVALUATION_SHA,
        "sourceP210CheckpointSha256": P210_WIDER_AUDIT_SHA,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "tokenMaxima": maxima,
        "proposedRunLimits": PROPOSED_LIMITS,
        "evaluationWordingDisjointFromTraining": True,
        "p210WiderEvaluationRequestsPromotedToTraining": 32,
        "p210PromotedRequestIntersectionVerified": True,
        "freshEvaluationRequestsDisjointFromAllP210Requests": True,
        "modelTrained": False,
        "trainingApprovalCreated": False,
        "evaluationApprovedForTraining": False,
        "evaluationApprovedForRuntimeValidationLoss": False,
        "finalHoldoutOpened": False,
    }
    review_md = output / "REVIEW.md"
    review_md.write_text(_markdown(summary), encoding="utf-8", newline="\n")
    summary["reviewMarkdownSha256"] = sha256_file(review_md)
    review_json = output / "review.json"
    review_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"p2-11-prepare: {exc}", file=sys.stderr)
        raise SystemExit(1)
