"""Prepare a review-only P2-10 candidate with an explicit answer-start cue.

This script writes deterministic training/evaluation candidates and review
metadata. It does not approve the data, create a training approval, or train.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text, source_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA
from prepare_selector_format_probe import (
    HELD_OUT_PHRASE, SELECTORS, TRAINING_PHRASES, build as build_baseline,
)
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-10-explicit-answer-start-v1"
EXPERIMENT = "p2-10-explicit-answer-start-v1"
BASELINE_TRAIN_SHA = "feb5feb0f7b06dad372e359de3f0958603888da0989ae4982c4f93c3b4622564"
BASELINE_EVALUATION_SHA = "4d9f4051318fcfe9f7941f4a5462b2b97998cb06f0ff0599f0a0cab00c7eb8a3"
OUTPUT_CONTRACT = (
    "Return exactly the requested value and nothing else. "
    "Begin the answer on a new line."
)
PROPOSED_LIMITS = {
    "freshSeed": 1337,
    "maximumSteps": 100,
    "maximumMinutes": 10,
    "microBatch": 1,
    "gradientAccumulation": 16,
    "device": "cuda",
    "automaticExtension": False,
}


def _canonical_jsonl(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build() -> tuple[list[dict], list[dict], dict]:
    baseline_train, baseline_eval = build_baseline()
    if (_sha256(_canonical_jsonl(baseline_train)) != BASELINE_TRAIN_SHA
            or _sha256(_canonical_jsonl(baseline_eval)) != BASELINE_EVALUATION_SHA):
        raise ValueError("P2-08 baseline matrix changed; refusing to derive P2-10")

    def transform(rows: list[dict], evaluation: bool) -> list[dict]:
        result = []
        for old in rows:
            row = dict(old)
            value = row["value"]
            split = "evaluation" if evaluation else "train"
            row["id"] = f"{EXPERIMENT}-{row['phrasingId']}-{row['layoutId']}-{value.removeprefix('.')}" \
                f"-{split}"
            row["splitGroupId"] = EXPERIMENT
            row["sourceId"] = EXPERIMENT
            row["contract"] = OUTPUT_CONTRACT
            result.append(row)
        return result

    train = transform(baseline_train, evaluation=False)
    evaluation = transform(baseline_eval, evaluation=True)
    validate(train, evaluation, baseline_train, baseline_eval)
    baseline = {
        "candidateJsonlSha256": BASELINE_TRAIN_SHA,
        "evaluationJsonlSha256": BASELINE_EVALUATION_SHA,
    }
    return train, evaluation, baseline


def validate(train: list[dict], evaluation: list[dict],
             baseline_train: list[dict] | None = None,
             baseline_eval: list[dict] | None = None) -> None:
    if len(train) != 64 or len(evaluation) != 16:
        raise ValueError("P2-10 requires 64 training and 16 evaluation records")
    ids = [row["id"] for row in train + evaluation]
    requests = [row["request"] for row in train + evaluation]
    if len(ids) != len(set(ids)) or len(requests) != len(set(requests)):
        raise ValueError("P2-10 IDs and requests must be unique")
    if ({row["request"] for row in train} & {row["request"] for row in evaluation}
            or {row["phrasingId"] for row in train} & {row["phrasingId"] for row in evaluation}):
        raise ValueError("P2-10 held-out wording or requests leaked into training")
    if ({row["value"] for row in train} != set(SELECTORS)
            or {row["value"] for row in evaluation} != set(SELECTORS)):
        raise ValueError("P2-10 must retain the same eight known selector values")
    if any(row["contract"] != OUTPUT_CONTRACT for row in train + evaluation):
        raise ValueError("P2-10 output-start contract drifted")
    if any(row["solution"] != row["value"] or row["bindings"] != {"selector": row["value"]}
           or row["checks"] != [{"kind": "exact_text", "value": row["value"]}]
           for row in train + evaluation):
        raise ValueError("P2-10 must keep the exact single-selector copy target")
    if any((row["approvalStatus"] != "pending-owner-review"
            or row["use"] != "training-candidate"
            or row["phrasingGroup"] != "training") for row in train):
        raise ValueError("P2-10 training rows must remain pending owner review")
    if any((row["approvalStatus"] != "evaluation-only"
            or row["use"] != "evaluation-only-never-train"
            or row["phrasingGroup"] != "held-out") for row in evaluation):
        raise ValueError("P2-10 evaluation rows must remain evaluation-only")
    if baseline_train is not None and baseline_eval is not None:
        for new_rows, old_rows in ((train, baseline_train), (evaluation, baseline_eval)):
            if len(new_rows) != len(old_rows):
                raise ValueError("P2-10 baseline row counts changed")
            for new, old in zip(new_rows, old_rows):
                for key in ("request", "solution", "value", "phrasingId", "phrasingGroup", "layoutId"):
                    if new[key] != old[key]:
                        raise ValueError(f"P2-10 changed the P2-08 {key} matrix")
                if new["contract"] == old["contract"]:
                    raise ValueError("P2-10 must differ from P2-08 by its answer-start cue")


def _review_markdown(review: dict) -> str:
    phrases = "\n".join(
        f"| `{item['id']}` | `{item['template']}` |"
        for item in review["trainingPhrases"]
    )
    return f"""# P2-10: explicit answer-start cue

Status: **pending owner review**. This stage prepares deterministic files only. It does not create a training approval or train a model.

## Question

Does explicitly telling Plex to begin its answer on a new line improve selector-copy output under held-out wording, compared with P2-08?

P2-08 learned 63/64 supplied prompts, below the 64/64 convergence gate. Its 4/16 held-out score is formally inconclusive. A read-only teacher-forced audit found the expected newline token ranked first on 6/16 held-out prompts; the period token ranked first on all 16 once the expected newline was supplied. P2-10 changes only the output contract to cue the answer start explicitly.

## Controlled design

- Training: {review['trainingRecords']} rows; four known phrasings × two known input layouts × eight selectors.
- Evaluation-only: {review['evaluationOnlyRecords']} rows; the same held-out wording, layouts, and eight selector values as P2-08.
- Output contract for every row: `{OUTPUT_CONTRACT}`
- Compared with P2-08, selector values, requests, targets, phrase/layout assignments, frozen tokenizer, architecture, and proposed run settings are held fixed. Only the output contract is changed.
- Require 64/64 exact supplied outputs before interpreting the 16 held-out outputs. If training does not converge, report evaluation as inconclusive.
- This remains a tiny selector-copy diagnostic, not evidence of general instruction understanding or coding ability.

## Phrasing matrix

| Phrase ID | Request template |
|---|---|
{phrases}

Each phrase uses both layouts: inline (`: {{value}}`) and the selector on the following line (colon, then a line break, then `{{value}}`).

Held-out wording: `{review['heldOutPhrase']['id']}` — `{review['heldOutPhrase']['template']}`

## Approval and safety boundary

- Candidate SHA-256: `{review['candidateJsonlSha256']}`
- Evaluation-only SHA-256: `{review['evaluationJsonlSha256']}`
- Frozen tokenizer SHA-256: `{review['tokenizerSha256']}`; tokenizer refitting is false.
- Proposed fresh-run limits (not approved): 100 updates / 10 minutes, seed 1337, microbatch 1, accumulation 16, CUDA, no automatic extension.
- Training examples remain `pending-owner-review`; evaluation examples remain `evaluation-only-never-train`.
- No approval artifact exists. No training has run. `finalHoldoutOpened` is false.
- Training may begin only after the owner approves these exact train/evaluation hashes and the proposed bounds.

## Token limits

Maximum prompt / complete-record-with-EOS / answer-with-EOS lengths: {review['tokenMaxima']['prompt']} / {review['tokenMaxima']['recordIncludingEos']} / {review['tokenMaxima']['answerIncludingEos']} tokens.
"""


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    try:
        output.relative_to((PHASE2 / "drafts").resolve())
    except ValueError as exc:
        raise ValueError("P2-10 output must remain under training/phase2/drafts") from exc
    if output.exists():
        raise FileExistsError("P2-10 candidate directory exists; choose a fresh path")

    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed; refusing candidate preparation")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    train, evaluation, baseline = build()

    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        full_ids = tokenizer.encode(source_text(row, settings["outputContracts"]))
        answer_length = len(full_ids) - len(prompt_ids) + 1
        if full_ids[:len(prompt_ids)] != prompt_ids or len(full_ids) + 1 > 512:
            raise ValueError(f"P2-10 token/context budget failed: {row['id']}")
        if answer_length > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"P2-10 answer budget failed: {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prompt_ids))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(full_ids) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], answer_length)

    output.mkdir(parents=True, exist_ok=False)
    train_path = output / "candidate.jsonl"
    eval_path = output / "evaluation-only.jsonl"
    train_path.write_bytes(_canonical_jsonl(train))
    eval_path.write_bytes(_canonical_jsonl(evaluation))
    review = {
        "schemaVersion": 1,
        "candidate": EXPERIMENT,
        "approvalStatus": "pending-owner-review",
        "trainingRecords": len(train),
        "evaluationOnlyRecords": len(evaluation),
        "selectors": list(SELECTORS),
        "trainingPhrases": [
            {"id": phrase_id, "template": template}
            for phrase_id, template in TRAINING_PHRASES
        ],
        "heldOutPhrase": {
            "id": HELD_OUT_PHRASE[0],
            "template": HELD_OUT_PHRASE[1],
        },
        "layouts": sorted({row["layoutId"] for row in train}),
        "outputContract": OUTPUT_CONTRACT,
        "baselineP2_08": baseline,
        "candidateJsonlSha256": sha256_file(train_path),
        "evaluationJsonlSha256": sha256_file(eval_path),
        "reviewMarkdownSha256": None,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "allEvaluationValuesSeenInTraining": True,
        "evaluationWordingAbsentFromTraining": True,
        "fullyCrossedTrainingMatrix": True,
        "onlyPromptContractChangedFromP2_08": True,
        "tokenMaxima": maxima,
        "modelTrained": False,
        "trainingApprovalCreated": False,
        "finalHoldoutOpened": False,
        "proposedRunLimits": PROPOSED_LIMITS,
    }
    review_md = output / "REVIEW.md"
    review_md.write_text(_review_markdown(review), encoding="utf-8", newline="\n")
    review["reviewMarkdownSha256"] = _sha256(review_md.read_bytes())
    review_path = output / "review.json"
    review_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")
    review["reviewJsonSha256"] = sha256_file(review_path)
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-10-prepare: {exc}", file=sys.stderr)
        raise SystemExit(1)
