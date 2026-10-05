"""Read-only expected-token and first-divergence audit for P2-10 wider scoring."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import torch

from prepare_binding_candidate import sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import TOKENIZER_BUNDLE, read_rows, write_json
from prepare_p2_10_wider_evaluation import CHECKPOINT, CHECKPOINT_SHA, DEFAULT_OUTPUT
from prepare_p2_10_wider_evaluation import PHRASES
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer
from plex_training.telemetry import select_device

ROOT = Path(__file__).resolve().parents[2]
SCORE = ROOT / "training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/wider-evaluation-score-v1.json"
OUTPUT = ROOT / "training/artifacts/experiments/p2-10-explicit-answer-start-run-v1/wider-token-audit-v1.json"


def _top5(logits: torch.Tensor, tokenizer, vocab: int) -> list[dict]:
    scores = logits[:vocab].float().clone()
    scores[:3] = -torch.inf
    log_probs = torch.log_softmax(scores, dim=-1)
    ids = torch.topk(scores, 5).indices.tolist()
    return [{
        "tokenId": token_id,
        "piece": "<|eos|>" if token_id == 3 else tokenizer.decode([token_id]),
        "logProbability": float(log_probs[token_id].item()),
    } for token_id in ids]


def _rank(logits: torch.Tensor, expected: int, tokenizer, vocab: int) -> dict:
    scores = logits[:vocab].float().clone()
    scores[:3] = -torch.inf
    log_probs = torch.log_softmax(scores, dim=-1)
    return {
        "tokenId": expected,
        "piece": "<|eos|>" if expected == 3 else tokenizer.decode([expected]),
        "rank": int((scores > scores[expected]).sum().item()) + 1,
        "logProbability": float(log_probs[expected].item()),
        "top5": _top5(logits, tokenizer, vocab),
    }


def _logits(model, prefix: list[int], device: torch.device) -> torch.Tensor:
    tensor = torch.tensor(prefix[-model.config.context_length:], dtype=torch.long,
                          device=device).unsqueeze(0)
    logits, _ = model(tensor)
    return logits[0, -1]


def _category_for_divergence(record: dict) -> str:
    divergence = record["firstDivergence"]
    if divergence is None:
        return "no_divergence"
    index = divergence["index"]
    return {0: "answer_start", 1: "period", 2: "selector_body_start"}.get(index, "later_selector_body")


def _summarize(records: list[dict]) -> dict:
    misses = [r for r in records if r["category"] != "exact_selector"]
    divergence_groups = {name: 0 for name in (
        "answer_start", "period", "selector_body_start", "later_selector_body", "no_divergence"
    )}
    for row in misses:
        divergence_groups[_category_for_divergence(row)] += 1
    return {
        "count": len(records),
        "exact": len(records) - len(misses),
        "newlineTopRanked": sum(r["expectedRanks"][0]["rank"] == 1 for r in records),
        "periodTopRankedAfterExpectedNewline": sum(r["expectedRanks"][1]["rank"] == 1 for r in records),
        "bodyFirstTokenTopRankedAfterExpectedPrefix": sum(r["expectedRanks"][2]["rank"] == 1 for r in records),
        "eosTopRankedAfterExpectedAnswer": sum(r["expectedRanks"][-1]["rank"] == 1 for r in records),
        "eosPresent": sum(r["eos"] for r in records),
        "misses": len(misses),
        "missFirstDivergence": divergence_groups,
    }


def audit(evaluation_dir: Path = DEFAULT_OUTPUT, output: Path = OUTPUT) -> dict:
    evaluation_dir = evaluation_dir.resolve()
    evaluation_dir.relative_to((ROOT / "training/phase2/drafts").resolve())
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    review = json.loads((evaluation_dir / "review.json").read_text(encoding="utf-8"))
    checkpoint_before = sha256_file(CHECKPOINT)
    if (checkpoint_before != CHECKPOINT_SHA
            or score["checkpointSha256Before"] != CHECKPOINT_SHA
            or score["checkpointSha256After"] != CHECKPOINT_SHA
            or score["evaluationJsonlSha256"] != review["evaluationJsonlSha256"]
            or review["trainingRecords"] != 0
            or score["evaluationUsedForTraining"] is not False
            or score["evaluationUsedForRuntimeValidationLoss"] is not False
            or score["weightUpdate"] is not False
            or score["stochasticSampling"] is not False
            or score["finalHoldoutOpened"] is not False):
        raise ValueError("Wider evaluation or checkpoint identity/scope changed")
    if sha256_file(evaluation_dir / "evaluation-only.jsonl") != review["evaluationJsonlSha256"]:
        raise ValueError("Wider evaluation-only rows changed")
    rows = read_rows(evaluation_dir / "evaluation-only.jsonl")
    scored = {r["id"]: r for r in score["records"]}
    if len(rows) != 64 or len(scored) != 64:
        raise ValueError("Expected exactly 64 reviewed and scored evaluation rows")

    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    if tokenizer_record["tokenizerSha256"] != review["tokenizerSha256"]:
        raise ValueError("Tokenizer does not match the reviewed evaluation")
    device = select_device("cuda")
    model, payload = read_checkpoint(CHECKPOINT, device)
    if payload.get("tokenizerRecord") != tokenizer_record or payload.get("step") != 100:
        raise ValueError("Frozen P2-10 checkpoint metadata changed")
    model.eval()
    settings = json.loads((ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    audits = []
    with torch.no_grad():
        for row in rows:
            saved = scored[row["id"]]
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            answer_ids = tokenizer.encode("\n" + row["value"])
            expected_ids = answer_ids + [3]
            if answer_ids[:2] != [202, 17]:
                raise ValueError(f"Unexpected boundary tokenization: {row['id']}")
            expected_ranks = []
            prefix = list(prompt_ids)
            for index, target_id in enumerate(expected_ids):
                ranked = _rank(_logits(model, prefix, device), target_id,
                               tokenizer, tokenizer.vocabulary_size)
                ranked["position"] = (
                    "answerNewline" if index == 0 else
                    "selectorPeriod" if index == 1 else
                    "eos" if target_id == 3 else
                    f"selectorBodyToken{index - 1}"
                )
                expected_ranks.append(ranked)
                if target_id != 3:
                    prefix.append(target_id)
            generated = saved["generatedTokenIds"]
            index = 0
            while index < min(len(generated), len(answer_ids)) and generated[index] == answer_ids[index]:
                index += 1
            divergence = None
            if index < len(answer_ids):
                logits = _logits(model, prompt_ids + generated[:index], device)
                actual = generated[index] if index < len(generated) else 3
                allowed = logits[:tokenizer.vocabulary_size].clone()
                allowed[:3] = -torch.inf
                chosen_rank = int((allowed > allowed[actual]).sum().item()) + 1
                divergence = {
                    "index": index,
                    "actualTokenId": actual,
                    "actualPiece": "<|eos|>" if actual == 3 else tokenizer.decode([actual]),
                    "expectedNext": _rank(logits, answer_ids[index], tokenizer, tokenizer.vocabulary_size),
                    "greedyTop5": _top5(logits, tokenizer, tokenizer.vocabulary_size),
                    "actualChosenTokenRank": chosen_rank,
                }
            audits.append({
                "id": row["id"], "phrasingId": row["phrasingId"],
                "layoutId": row["layoutId"], "value": row["value"],
                "request": row["request"], "completion": saved["completion"],
                "category": saved["category"], "eos": saved["eos"],
                "generatedTokenIds": generated,
                "generatedTokenPieces": saved["generatedTokenPieces"],
                "expectedTokenIds": expected_ids,
                "expectedTokenPieces": [tokenizer.decode([i]) for i in answer_ids] + ["<|eos|>"],
                "expectedRanks": expected_ranks,
                "firstDivergence": divergence,
            })

    by_phrase = {}
    for phrase_id, template in PHRASES:
        group = [r for r in audits if r["phrasingId"] == phrase_id]
        by_phrase[phrase_id] = {"template": template, "overall": _summarize(group), "layouts": {}}
        for layout in ("colon-space", "colon-newline"):
            by_phrase[phrase_id]["layouts"][layout] = _summarize(
                [r for r in group if r["layoutId"] == layout]
            )
    checkpoint_after = sha256_file(CHECKPOINT)
    if checkpoint_before != checkpoint_after:
        raise ValueError("Checkpoint changed during read-only token audit")
    output = output.resolve()
    output.relative_to((ROOT / "training/artifacts/experiments").resolve())
    if output.exists():
        raise FileExistsError("Wider token audit artifact exists; choose a fresh path")
    result = {
        "schemaVersion": 1,
        "evaluationSet": review["evaluationSet"],
        "mode": "read-only-teacher-forced-and-greedy-divergence-audit",
        "checkpointSha256Before": checkpoint_before,
        "checkpointSha256After": checkpoint_after,
        "evaluationJsonlSha256": review["evaluationJsonlSha256"],
        "reviewJsonSha256": score["reviewJsonSha256"],
        "reviewMarkdownSha256": review["reviewMarkdownSha256"],
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "overall": _summarize(audits),
        "byPhrase": by_phrase,
        "records": audits,
        "weightUpdate": False,
        "trainingRunStarted": False,
        "greedyCompletionsResampled": False,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
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
        result = audit(args.evaluation_dir, args.output)
        print(json.dumps({"report": str(args.output), "overall": result["overall"],
                          "byPhrase": result["byPhrase"],
                          "finalHoldoutOpened": result["finalHoldoutOpened"]}, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"p2-10-wider-token-audit: {exc}", file=sys.stderr)
        raise SystemExit(2)
