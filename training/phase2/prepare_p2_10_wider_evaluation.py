"""Build a separately reviewed, evaluation-only wording set for P2-10 inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA, read_rows
from prepare_explicit_answer_start_candidate import EXPERIMENT as P210, DEFAULT_OUTPUT as P210_DRAFT
from prepare_explicit_answer_start_experiment import EXPERIMENT, PHASE2
from prepare_selector_format_probe import SELECTORS
from plex_training.tokenizer import PlexTokenizer

DEFAULT_OUTPUT = PHASE2 / "drafts/p2-10-wider-heldout-eval-v1"
RUN = ROOT / "training/artifacts/experiments/p2-10-explicit-answer-start-run-v1"
CHECKPOINT = RUN / "pilot/pilot-checkpoint.pt"
CHECKPOINT_SHA = "28c5aa6f7e04c6c48c54636077545d207ee3593b42c26d7fe2da37aae3c3d6bb"
EVALUATION_SHA = "632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9"
PHRASES = (
    ("transcribe-css-selector", "Transcribe this CSS selector: {value}"),
    ("reproduce-selector-verbatim", "Reproduce the selector below verbatim: {value}"),
    ("preserve-selector-spelling", "Preserve every character in this selector: {value}"),
    ("write-selector-character-for-character", "Write this selector again, character for character: {value}"),
)
CONTRACT = "Return exactly the requested value and nothing else. Begin the answer on a new line."


def _canonical(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _build() -> tuple[list[dict], dict]:
    base = read_rows(P210_DRAFT / "evaluation-only.jsonl")
    lookup = {(row["layoutId"], row["value"]): row for row in base}
    if len(lookup) != 16 or {r["value"] for r in base} != set(SELECTORS):
        raise ValueError("P2-10 source evaluation matrix changed")
    rows = []
    phrase_specs = []
    for phrase_id, template in PHRASES:
        phrase_specs.append({"id": phrase_id, "template": template})
        if not template.endswith(": {value}"):
            raise ValueError("P2-10 wider evaluation templates must preserve the colon layout point")
        for layout in ("colon-space", "colon-newline"):
            for selector in SELECTORS:
                old = lookup[(layout, selector)]
                request = template.format(value=selector)
                if layout == "colon-newline":
                    request = request[:-len(selector)] + "\n" + selector
                row = dict(old)
                row.update({
                    "id": f"p2-10-wider-heldout-eval-v1-{phrase_id}-{layout}-{selector.removeprefix('.')}",
                    "request": request,
                    "phrasingId": phrase_id,
                    "phrasingGroup": "held-out-wider-evaluation",
                    "sourceId": "p2-10-wider-heldout-eval-v1",
                    "splitGroupId": "p2-10-wider-heldout-eval-v1",
                    "provenance": "codex-authored-read-only-selector-evaluation",
                    "approvalStatus": "evaluation-only",
                    "use": "evaluation-only-never-train",
                })
                if row["solution"] != selector or row["contract"] != CONTRACT:
                    raise ValueError("Wider evaluation changed P2-10 target or output contract")
                rows.append(row)
    ids, requests = [r["id"] for r in rows], [r["request"] for r in rows]
    if len(rows) != 64 or len(ids) != len(set(ids)) or len(requests) != len(set(requests)):
        raise ValueError("P2-10 wider evaluation requires 64 unique rows")
    previous = read_rows(P210_DRAFT / "candidate.jsonl") + base
    previous_requests = {r["request"] for r in previous}
    if previous_requests & set(requests):
        raise ValueError("Wider evaluation request overlaps an existing P2-10 request")
    return rows, {"phrases": phrase_specs}


def _review_markdown(summary: dict) -> str:
    phrases = "\n".join(f"| `{p['id']}` | `{p['template']}` |" for p in summary["phrases"])
    return f"""# P2-10 wider held-out wording evaluation

Status: **prepared and reviewed for read-only scoring of the frozen P2-10 checkpoint**.

## Purpose and scope

The original P2-10 evaluation crossed one held-out wording with eight selectors and two input layouts (16 prompts). This separate evaluation-only set crosses four additional held-out wording templates with the same selectors and layouts (64 prompts). The output contract, selector targets, frozen tokenizer, checkpoint, and greedy decoding settings are unchanged. No prompts from this set are used for training or runtime validation loss.

This is a narrow selector-copy diagnostic. It does not open the final project holdout and does not authorize or start training. The set is additive: the original 16-row P2-10 evaluation remains separately reported.

## Wording matrix

| Phrase ID | Request template |
|---|---|
{phrases}

Each wording is tested in inline (`: {{value}}`) and next-line (`:\\n{{value}}`) input layouts for the same eight selectors: `{', '.join(summary['selectors'])}`. Each request differs from every P2-10 train/evaluation request.

## Exact identities

- Evaluation-only JSONL SHA-256: `{summary['evaluationJsonlSha256']}`
- Existing P2-10 checkpoint SHA-256: `{summary['checkpointSha256']}`
- Frozen tokenizer SHA-256: `{summary['tokenizerSha256']}`; no refit.
- Evaluation rows: {summary['evaluationOnlyRecords']}; training rows: **0**.
- Maximum prompt / expected completion-plus-EOS length: {summary['tokenMaxima']['prompt']} / {summary['tokenMaxima']['answerIncludingEos']} tokens.
- Evaluation use for training: false. Evaluation use for runtime validation loss: false.
- No training run or weight updates. Scoring uses deterministic greedy inference. Final holdout opened: false.

## Review decision

The four templates ask for the same exact selector-copy operation while varying the verb and wording. The design adds wording coverage without changing the task target, input layout, output contract, or checkpoint. Score this set only against the pinned existing checkpoint and report phrase/layout cells as descriptive small samples.
"""


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    output.relative_to((PHASE2 / "drafts").resolve())
    if output.exists():
        raise FileExistsError("P2-10 wider evaluation directory exists; choose a fresh path")
    if sha256_file(CHECKPOINT) != CHECKPOINT_SHA:
        raise ValueError("Frozen P2-10 checkpoint changed")
    if sha256_file(TOKENIZER_BUNDLE / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Frozen tokenizer changed")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development prompt settings changed")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    rows, design = _build()
    maxima = {"prompt": 0, "answerIncludingEos": 0}
    for row in rows:
        prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        answer_ids = tokenizer.encode("\n" + row["value"]) + [3]
        if len(prompt_ids) >= 512 or len(answer_ids) > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"Wider evaluation token budget failed: {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prompt_ids))
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], len(answer_ids))
    output.mkdir(parents=True, exist_ok=False)
    eval_path = output / "evaluation-only.jsonl"
    eval_path.write_bytes(_canonical(rows))
    summary = {
        "schemaVersion": 1,
        "evaluationSet": "p2-10-wider-heldout-eval-v1",
        "reviewStatus": "reviewed-for-read-only-existing-checkpoint-score",
        "evaluationJsonlSha256": sha256_file(eval_path),
        "evaluationOnlyRecords": len(rows),
        "trainingRecords": 0,
        "phrases": design["phrases"],
        "selectors": list(SELECTORS),
        "layouts": ["colon-space", "colon-newline"],
        "outputContract": CONTRACT,
        "sourceP210CandidateSha256": "ac0b65b623b80a8de89d78c2d038a03f2a5b4f8782097327d46624ea04aaa1e8",
        "sourceP210EvaluationSha256": EVALUATION_SHA,
        "checkpointSha256": CHECKPOINT_SHA,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "tokenMaxima": maxima,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "weightUpdate": False,
        "trainingRunStarted": False,
        "scoreMode": "deterministic-greedy-inference",
        "finalHoldoutOpened": False,
    }
    review_md = output / "REVIEW.md"
    review_md.write_text(_review_markdown(summary),
                         encoding="utf-8", newline="\n")
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
        print(f"p2-10-wider-eval-prepare: {exc}", file=sys.stderr)
        raise SystemExit(1)
