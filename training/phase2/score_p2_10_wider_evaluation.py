"""Greedy-score the P2-10 wider evaluation set on its pinned frozen checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from prepare_binding_candidate import sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import TOKENIZER_BUNDLE, read_rows, write_json
from prepare_explicit_answer_start_candidate import DEFAULT_OUTPUT as P210_DRAFT
from prepare_p2_10_wider_evaluation import (
    CHECKPOINT, CHECKPOINT_SHA, DEFAULT_OUTPUT, PHRASES, _build,
)
from prepare_selector_format_probe import SELECTORS
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.telemetry import select_device

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/wider-evaluation-score-v1.json"
WIDER_EVALUATION_SHA = "da084655484ec4cb64c77a9a852dbb8ffb7be6d7cbd02c172c19373ec6529b4a"


def _classify(value: str, completion: str, eos: bool) -> str:
    stripped = completion.strip()
    if stripped == value and eos:
        return "exact_selector"
    if stripped in SELECTORS and eos:
        return "wrong_known_selector"
    if value in stripped and eos:
        return "expected_selector_with_extra_text"
    return "other_or_no_eos"


def _summarize(records: list[dict]) -> dict:
    return {
        "count": len(records),
        "exact": sum(r["category"] == "exact_selector" for r in records),
        "wrongKnownSelector": sum(r["category"] == "wrong_known_selector" for r in records),
        "expectedSelectorWithExtraText": sum(
            r["category"] == "expected_selector_with_extra_text" for r in records
        ),
        "otherOrNoEos": sum(r["category"] == "other_or_no_eos" for r in records),
        "eos": sum(r["eos"] for r in records),
        "beginsWithNewline": sum(r["beginsWithNewline"] for r in records),
        "generatedTokenCount": sum(r["generatedTokenCount"] for r in records),
    }


def _load_review(directory: Path) -> tuple[list[dict], dict]:
    directory = directory.resolve()
    directory.relative_to((ROOT / "training/phase2/drafts").resolve())
    eval_path, markdown_path, review_path = (
        directory / "evaluation-only.jsonl", directory / "REVIEW.md", directory / "review.json"
    )
    for path in (eval_path, markdown_path, review_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or linked wider evaluation file: {path.name}")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected = {
        "evaluationSet": "p2-10-wider-heldout-eval-v1",
        "reviewStatus": "reviewed-for-read-only-existing-checkpoint-score",
        "evaluationOnlyRecords": 64,
        "trainingRecords": 0,
        "evaluationJsonlSha256": WIDER_EVALUATION_SHA,
        "checkpointSha256": CHECKPOINT_SHA,
        "tokenizerSha256": "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573",
        "tokenizerRefitted": False,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "weightUpdate": False,
        "trainingRunStarted": False,
        "scoreMode": "deterministic-greedy-inference",
        "finalHoldoutOpened": False,
    }
    if any(review.get(key) != value for key, value in expected.items()):
        raise ValueError("Wider evaluation review does not match its approved read-only scope")
    if review.get("phrases") != [{"id": k, "template": v} for k, v in PHRASES]:
        raise ValueError("Wider evaluation phrasing matrix changed")
    if review.get("selectors") != list(SELECTORS):
        raise ValueError("Wider evaluation selector set changed")
    if sha256_file(eval_path) != WIDER_EVALUATION_SHA:
        raise ValueError("Wider evaluation rows differ from the reviewed hash")
    if sha256_file(markdown_path) != review.get("reviewMarkdownSha256"):
        raise ValueError("Wider evaluation review Markdown changed")
    rows = read_rows(eval_path)
    expected_rows, _ = _build()
    if rows != expected_rows:
        raise ValueError("Wider evaluation rows differ from deterministic reviewed generation")
    if sha256_file(CHECKPOINT) != CHECKPOINT_SHA:
        raise ValueError("Pinned P2-10 checkpoint changed")
    return rows, review


def score(directory: Path = DEFAULT_OUTPUT, output: Path = OUTPUT) -> dict:
    rows, review = _load_review(directory)
    output = output.resolve()
    output.relative_to((ROOT / "training/artifacts/experiments").resolve())
    if output.exists():
        raise FileExistsError("Wider evaluation score output exists; choose a fresh path")
    settings = json.loads((ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    if tokenizer_record["tokenizerSha256"] != review["tokenizerSha256"]:
        raise ValueError("Frozen tokenizer differs from the reviewed hash")
    device = select_device("cuda")
    checkpoint_before = sha256_file(CHECKPOINT)
    model, payload = read_checkpoint(CHECKPOINT, device)
    if payload.get("tokenizerRecord") != tokenizer_record or payload.get("step") != 100:
        raise ValueError("Pinned P2-10 checkpoint metadata does not match the review")
    model.eval()
    results = []
    for row in rows:
        ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        tokens, eos = _generate_token_ids(
            model, ids, actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=settings["inferenceDefaults"]["maxNewTokens"]["css"],
            temperature=0.0, seed=1337, device=device,
        )
        completion = tokenizer.decode(tokens)
        results.append({
            "id": row["id"], "phrasingId": row["phrasingId"],
            "layoutId": row["layoutId"], "value": row["value"],
            "request": row["request"], "completion": completion,
            "beginsWithNewline": completion.startswith("\n"),
            "generatedTokenIds": tokens,
            "generatedTokenPieces": [tokenizer.decode([token_id]) for token_id in tokens],
            "generatedTokenCount": len(tokens), "eos": eos,
            "category": _classify(row["value"], completion, eos),
        })
    cells = {}
    for phrase_id, _ in PHRASES:
        cells[phrase_id] = {}
        for layout_id in ("colon-space", "colon-newline"):
            cells[phrase_id][layout_id] = _summarize([
                r for r in results if r["phrasingId"] == phrase_id and r["layoutId"] == layout_id
            ])
    summary = _summarize(results)
    if sha256_file(CHECKPOINT) != checkpoint_before or checkpoint_before != CHECKPOINT_SHA:
        raise ValueError("Pinned checkpoint changed during read-only scoring")
    result = {
        "schemaVersion": 1,
        "evaluationSet": review["evaluationSet"],
        "mode": "read-only-greedy-score-existing-checkpoint",
        "checkpointSha256Before": checkpoint_before,
        "checkpointSha256After": sha256_file(CHECKPOINT),
        "evaluationJsonlSha256": review["evaluationJsonlSha256"],
        "reviewJsonSha256": sha256_file(directory.resolve() / "review.json"),
        "reviewMarkdownSha256": review["reviewMarkdownSha256"],
        "tokenizerSha256": review["tokenizerSha256"],
        "evaluation": summary,
        "conditionCells": cells,
        "records": results,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "weightUpdate": False,
        "trainingRunStarted": False,
        "greedyCompletionsScored": True,
        "stochasticSampling": False,
        "finalHoldoutOpened": False,
    }
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        result = score(args.evaluation_dir, args.output)
        print(json.dumps({
            "report": str(args.output), "evaluation": result["evaluation"],
            "conditionCells": result["conditionCells"],
            "finalHoldoutOpened": result["finalHoldoutOpened"],
        }, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"p2-10-wider-eval-score: {exc}", file=sys.stderr)
        raise SystemExit(2)
