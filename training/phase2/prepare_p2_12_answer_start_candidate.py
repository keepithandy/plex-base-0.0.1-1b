"""Prepare a review-only P2-12 answer-start candidate; never train here."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text, source_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA
from prepare_explicit_answer_start_candidate import OUTPUT_CONTRACT, build as build_p210
from prepare_p2_10_wider_evaluation import _build as build_p210_wider
from prepare_p2_11_balanced_wording_candidate import (
    P210_CANDIDATE_SHA, P210_EVALUATION_SHA, P210_WIDER_EVALUATION_SHA,
    _jsonl, build as build_p211,
)
from prepare_selector_format_probe import SELECTORS, TRAINING_PHRASES
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-12-answer-start-transfer-v1"
EXPERIMENT = "p2-12-answer-start-transfer-v1"
P211_CANDIDATE_SHA = "baaa056835f50120e55d93f6f74622c77e9a178e4c8801396ba3575b785001ab"
P211_EVALUATION_SHA = "f189dfbeb0d7595740f4f06399c420bd0f0bdb4a181dd23484d4c58a59260322"
P211_CHECKPOINT_SHA = "6c4de918e3aa270cc0e94273ff803390facd351b1b9f3ce2889c77d234a4205e"
P210_WIDER_AUDIT_SHA = "28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb"

# Preserve the four baseline training phrasings and replace two P2-11 weak
# evaluation phrasings with balanced training rows. Their 32 exact requests
# are no longer held out for P2-12.
PROMOTED_TRAINING_PHRASES = (
    ("give-literal-selector-after-label", "Give only the literal selector shown after this label: {value}"),
    ("preserve-spelling-and-punctuation",
     "Please preserve the spelling and punctuation of the selector: {value}"),
)
FRESH_EVALUATION_PHRASES = (
    ("copy-selector-starting-next-line", "Copy the selector below exactly, starting on the next line: {value}"),
    ("following-line-only-selector", "On the following line, output only this selector: {value}"),
    ("selector-exactly-on-own-line", "Put the selector exactly as written on its own line: {value}"),
    ("literal-selector-on-new-line", "Return the literal selector unchanged on a new line: {value}"),
)
PROPOSED_LIMITS = {
    "freshSeed": 1337,
    "maximumSteps": 100,
    "maximumMinutes": 10,
    "maximumTotalSteps": 100,
    "maximumTotalMinutes": 10,
    "microBatch": 1,
    "gradientAccumulation": 16,
    "device": "cuda",
    "automaticExtension": False,
}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _request(template: str, selector: str, layout: str) -> str:
    request = template.format(value=selector)
    if layout == "colon-newline":
        request = request[:-len(selector)] + "\n" + selector
    return request


def _row(old: dict, phrase_id: str, template: str, layout: str,
         selector: str, split: str) -> dict:
    training = split == "train"
    row = dict(old)
    row.update({
        "id": f"{EXPERIMENT}-{phrase_id}-{layout}-{selector.removeprefix('.')}-{split}",
        "request": _request(template, selector, layout),
        "phrasingId": phrase_id,
        "phrasingGroup": "training" if training else "held-out",
        "sourceId": EXPERIMENT,
        "splitGroupId": EXPERIMENT,
        "provenance": "codex-authored-answer-start-transfer-diagnostic" if training
        else "codex-authored-fresh-heldout-answer-start-evaluation",
        "approvalStatus": "pending-owner-review" if training else "evaluation-only",
        "use": "training-candidate" if training else "evaluation-only-never-train",
    })
    return row


def build() -> tuple[list[dict], list[dict]]:
    p210_train, p210_evaluation, _ = build_p210()
    p210_wider, _ = build_p210_wider()
    p211_train, p211_evaluation = build_p211()
    if _sha(_jsonl(p210_train)) != P210_CANDIDATE_SHA or _sha(_jsonl(p210_evaluation)) != P210_EVALUATION_SHA:
        raise ValueError("Pinned P2-10 inputs changed")
    if _sha(_jsonl(p211_train)) != P211_CANDIDATE_SHA or _sha(_jsonl(p211_evaluation)) != P211_EVALUATION_SHA:
        raise ValueError("Pinned P2-11 inputs changed")

    base_lookup = {(row["layoutId"], row["value"]): row for row in p210_train}
    if len(base_lookup) != 16:
        raise ValueError("P2-10 source training matrix changed")
    training_specs = list(TRAINING_PHRASES) + list(PROMOTED_TRAINING_PHRASES)
    train = [
        _row(base_lookup[(layout, selector)], phrase_id, template, layout, selector, "train")
        for phrase_id, template in training_specs
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    ]
    evaluation = [
        _row(base_lookup[(layout, selector)], phrase_id, template, layout, selector, "evaluation")
        for phrase_id, template in FRESH_EVALUATION_PHRASES
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    ]
    _validate(train, evaluation)

    previous_rows = p210_train + p210_evaluation + p210_wider + p211_train + p211_evaluation
    previous_requests = {row["request"] for row in previous_rows}
    train_requests = {row["request"] for row in train}
    eval_requests = {row["request"] for row in evaluation}
    promoted_phrase_ids = {phrase_id for phrase_id, _ in PROMOTED_TRAINING_PHRASES}
    promoted = {row["request"] for row in train if row["phrasingId"] in {p for p, _ in PROMOTED_TRAINING_PHRASES}}
    expected_promoted = {
        _request(template, selector, layout)
        for _phrase_id, template in PROMOTED_TRAINING_PHRASES
        for layout in ("colon-space", "colon-newline")
        for selector in SELECTORS
    }
    p211_eval_requests = {row["request"] for row in p211_evaluation}
    if promoted != expected_promoted:
        raise ValueError("P2-12 promoted training matrix changed")
    if promoted & p211_eval_requests != expected_promoted or len(expected_promoted) != 32:
        raise ValueError("P2-12 must promote exactly 32 P2-11 evaluation requests")
    if eval_requests & previous_requests or eval_requests & train_requests:
        raise ValueError("P2-12 fresh evaluation overlaps a prior request or training request")
    if {row["phrasingId"] for row in evaluation} & promoted_phrase_ids:
        raise ValueError("P2-12 evaluation wording leaked into training wording")
    return train, evaluation


def _validate(train: list[dict], evaluation: list[dict]) -> None:
    if len(train) != 96 or len(evaluation) != 64:
        raise ValueError("P2-12 requires 96 training and 64 evaluation-only records")
    for rows, phrases, split, group, status, use in (
        (train, training_specs_for_validation(), "train", "training", "pending-owner-review", "training-candidate"),
        (evaluation, FRESH_EVALUATION_PHRASES, "evaluation", "held-out", "evaluation-only", "evaluation-only-never-train"),
    ):
        expected = {(phrase, layout, selector) for phrase, _ in phrases
                    for layout in ("colon-space", "colon-newline") for selector in SELECTORS}
        actual = {(row["phrasingId"], row["layoutId"], row["value"]) for row in rows}
        if actual != expected:
            raise ValueError(f"P2-12 {split} phrase/layout/selector cells changed")
        ids = [row["id"] for row in rows]
        requests = [row["request"] for row in rows]
        if len(ids) != len(set(ids)) or len(requests) != len(set(requests)):
            raise ValueError(f"P2-12 {split} IDs and requests must be unique")
        if any(row["phrasingGroup"] != group or row["approvalStatus"] != status or row["use"] != use
               for row in rows):
            raise ValueError(f"P2-12 {split} review metadata changed")
        if any(row["contract"] != OUTPUT_CONTRACT or row["solution"] != row["value"]
               or row["bindings"] != {"selector": row["value"]}
               or row["checks"] != [{"kind": "exact_text", "value": row["value"]}]
               for row in rows):
            raise ValueError("P2-12 altered output contract or selector target")
    if {row["request"] for row in train} & {row["request"] for row in evaluation}:
        raise ValueError("P2-12 training and evaluation requests overlap")


def training_specs_for_validation() -> list[tuple[str, str]]:
    return list(TRAINING_PHRASES) + list(PROMOTED_TRAINING_PHRASES)


def _markdown(review: dict) -> str:
    train = "\n".join(f"| `{p['id']}` | `{p['template']}` |" for p in review["trainingPhrases"])
    evaluation = "\n".join(f"| `{p['id']}` | `{p['template']}` |" for p in review["evaluationPhrases"])
    limits = review["proposedRunLimits"]
    return f"""# P2-12: answer-start transfer candidate

Status: **review-only candidate; no training approval exists and no run has started**.

## Question

Does balanced exposure to the two P2-11 phrasings with answer-start misses improve exact copying on four fresh phrasings, under the unchanged explicit answer-start contract?

The P2-11 read-only audit found 9 of 11 greedy misses first diverged at the answer newline. In those cases, the body token was selected immediately and the expected newline ranked second through fourth. Given the expected newline, the expected period ranked first on all 64 prompts, and EOS ranked first on all 64 expected complete answers. Two further misses occurred in selector-body choice. This points to the prompt-conditioned answer start as the main observed failure location; it does not establish a causal explanation for the model's choice.

## Controlled design

- Training: {review['trainingRecords']} rows; six phrasings × two layouts × eight fixed selectors. The four original P2-10 training phrasings remain; the two P2-11 lower-scoring evaluation phrasings replace the two P2-11 added training phrasings, keeping row count and selector/layout coverage fixed.
- Evaluation-only: {review['evaluationOnlyRecords']} rows; four entirely fresh phrasings × two layouts × eight selectors. Requests are disjoint from P2-10 training, original and wider evaluation, P2-11 training and evaluation, and P2-12 training.
- Historical holdout transition: {review['p211EvaluationRequestsPromotedToTraining']} exact requests from the weak P2-11 evaluation templates are now training data; their old scores are historical evidence, not clean P2-12 holdout evidence.
- All rows retain the P2-10 output contract: `{OUTPUT_CONTRACT}`. The eight selector targets, two colon layouts, model, architecture, objective, and frozen tokenizer remain fixed.
- Fresh-from-scratch seed {limits['freshSeed']} only; do not continue the P2-11 checkpoint. Require **96/96 exact supplied outputs** before interpreting evaluation. Otherwise evaluation is inconclusive.
- Proposed ceiling is {limits['maximumSteps']} updates or {limits['maximumMinutes']} minutes, whichever comes first. Expected uniform record exposure is about {limits['maximumSteps']} × {limits['gradientAccumulation']} / 96 ≈ {limits['maximumSteps'] * limits['gradientAccumulation'] / 96:.1f} presentations per record. The ceiling is a proposal, not run authorization; the shared complete-record framework caps at 100 updates.

## Training phrasings

| Phrase ID | Template |
|---|---|
{train}

## Fresh evaluation-only phrasings

| Phrase ID | Template |
|---|---|
{evaluation}

Each phrase is crossed with inline (`: {{value}}`) and next-line (`:\n{{value}}`) layouts and all eight known selectors.

## Hashes and run boundary

- Training candidate SHA-256: `{review['candidateJsonlSha256']}`
- Evaluation-only SHA-256: `{review['evaluationJsonlSha256']}`
- Frozen tokenizer SHA-256: `{review['tokenizerSha256']}`; refitting is false.
- Prior evidence: P2-10 candidate `{P210_CANDIDATE_SHA}`, original evaluation `{P210_EVALUATION_SHA}`, wider evaluation `{P210_WIDER_EVALUATION_SHA}`, P2-10 checkpoint `{P210_WIDER_AUDIT_SHA}`; P2-11 candidate `{P211_CANDIDATE_SHA}`, evaluation `{P211_EVALUATION_SHA}`, checkpoint `{P211_CHECKPOINT_SHA}`.
- Proposed limits: {limits['maximumSteps']} updates / {limits['maximumMinutes']} minutes, seed {limits['freshSeed']}, microbatch {limits['microBatch']}, accumulation {limits['gradientAccumulation']}, CUDA, no automatic extension.
- Evaluation approved for training: false. Evaluation approved for runtime validation loss: false. `finalHoldoutOpened`: false.
- No approval artifact exists. Training requires owner approval of these exact hashes and limits. Do not extend a prior run.

## Limits

This is a single-arm diagnostic. It changes the training wording mix and promotes 32 previously evaluated requests, so it cannot isolate phrase effects causally. Small repeated-selector cells are descriptive, not evidence of general instruction understanding or coding ability.
"""


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    output.relative_to((PHASE2 / "drafts").resolve())
    if output.exists():
        raise FileExistsError("P2-12 candidate directory exists; choose a fresh path")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development prompt settings changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    train, evaluation = build()
    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        record_ids = tokenizer.encode(source_text(row, settings["outputContracts"]))
        answer_ids = tokenizer.encode("\n" + row["solution"]) + [3]
        if len(record_ids) + 1 > 512 or len(answer_ids) > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"P2-12 context or generation budget failed: {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prompt_ids))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(record_ids) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], len(answer_ids))

    output.mkdir(parents=True, exist_ok=False)
    train_path, eval_path = output / "candidate.jsonl", output / "evaluation-only.jsonl"
    train_path.write_bytes(_jsonl(train))
    eval_path.write_bytes(_jsonl(evaluation))
    summary = {
        "schemaVersion": 1, "candidate": EXPERIMENT, "reviewStatus": "pending-owner-review",
        "trainingRecords": len(train), "evaluationOnlyRecords": len(evaluation),
        "trainingPhrases": [{"id": k, "template": v} for k, v in training_specs_for_validation()],
        "evaluationPhrases": [{"id": k, "template": v} for k, v in FRESH_EVALUATION_PHRASES],
        "selectors": list(SELECTORS), "layouts": ["colon-space", "colon-newline"],
        "outputContract": OUTPUT_CONTRACT,
        "candidateJsonlSha256": sha256_file(train_path), "evaluationJsonlSha256": sha256_file(eval_path),
        "reviewMarkdownSha256": None,
        "sourceP210CandidateSha256": P210_CANDIDATE_SHA,
        "sourceP210EvaluationSha256": P210_EVALUATION_SHA,
        "sourceP210WiderEvaluationSha256": P210_WIDER_EVALUATION_SHA,
        "sourceP210CheckpointSha256": P210_WIDER_AUDIT_SHA,
        "sourceP211CandidateSha256": P211_CANDIDATE_SHA,
        "sourceP211EvaluationSha256": P211_EVALUATION_SHA,
        "sourceP211CheckpointSha256": P211_CHECKPOINT_SHA,
        "tokenizerSha256": TOKENIZER_SHA, "tokenizerRefitted": False,
        "tokenMaxima": maxima, "proposedRunLimits": PROPOSED_LIMITS,
        "evaluationWordingDisjointFromTraining": True,
        "p211EvaluationRequestsPromotedToTraining": 32,
        "p211PromotedRequestIntersectionVerified": True,
        "freshEvaluationRequestsDisjointFromAllP210AndP211Requests": True,
        "modelTrained": False, "trainingApprovalCreated": False,
        "evaluationApprovedForTraining": False,
        "evaluationApprovedForRuntimeValidationLoss": False,
        "finalHoldoutOpened": False,
    }
    review_md = output / "REVIEW.md"
    review_md.write_text(_markdown(summary), encoding="utf-8", newline="\n")
    summary["reviewMarkdownSha256"] = sha256_file(review_md)
    (output / "review.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                         encoding="utf-8", newline="\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"p2-12-prepare: {exc}", file=sys.stderr)
        raise SystemExit(1)
