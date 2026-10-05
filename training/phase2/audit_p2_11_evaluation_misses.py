"""Read-only token-rank and greedy-divergence audit for the P2-11 evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import torch

from prepare_binding_candidate import sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import TOKENIZER_BUNDLE, read_rows, write_json
from prepare_p2_11_balanced_wording_candidate import HELD_OUT_PHRASES, EXPERIMENT
from prepare_p2_11_experiment import EXPECTED, PHASE2, canonical_sha256
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer
from plex_training.telemetry import select_device

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "training/artifacts/experiments/p2-11-balanced-wording-transfer-v1-run-100step-v1"
PREPARED = ROOT / "training/artifacts/experiments/p2-11-balanced-wording-transfer-v1-inputs"
CHECKPOINT = RUN / "pilot/pilot-checkpoint.pt"
SCORE = RUN / "completion-score.json"
RUN_REPORT = RUN / "result.json"
EVALUATION = PREPARED / "evaluation-only/evaluation-only.jsonl"
OUTPUT = RUN / "token-error-audit-v1.json"


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


def _divergence_group(record: dict) -> str:
    divergence = record["firstDivergence"]
    if divergence is None:
        return "no_divergence"
    index = divergence["index"]
    return {0: "answer_newline", 1: "selector_leading_period"}.get(index, "selector_body")


def _summarize(records: list[dict]) -> dict:
    misses = [r for r in records if r["category"] != "exact_selector"]
    divergence_groups = {name: 0 for name in (
        "answer_newline", "selector_leading_period", "selector_body", "no_divergence"
    )}
    for row in misses:
        divergence_groups[_divergence_group(row)] += 1
    return {
        "count": len(records),
        "exact": len(records) - len(misses),
        "answerNewlineTopRanked": sum(r["expectedRanks"][0]["rank"] == 1 for r in records),
        "periodTopRankedAfterExpectedNewline": sum(
            r["expectedRanks"][1]["rank"] == 1 for r in records
        ),
        "selectorBodyFirstTokenTopRankedAfterExpectedPrefix": sum(
            r["expectedRanks"][2]["rank"] == 1 for r in records
        ),
        "eosTopRankedAfterExpectedAnswer": sum(r["expectedRanks"][-1]["rank"] == 1 for r in records),
        "eosPresent": sum(r["eos"] for r in records),
        "misses": len(misses),
        "missFirstDivergence": divergence_groups,
    }


def audit(output: Path = OUTPUT) -> dict:
    plan = json.loads((PREPARED / "experiment.json").read_text(encoding="utf-8"))
    report = json.loads(RUN_REPORT.read_text(encoding="utf-8"))
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    checkpoint_before = sha256_file(CHECKPOINT)
    if (checkpoint_before != score.get("checkpointSha256")
            or plan.get("candidateJsonlSha256") != EXPECTED["candidate"]
            or plan.get("evaluationJsonlSha256") != EXPECTED["evaluation"]
            or report.get("experiment") != EXPERIMENT
            or report.get("scoringComplete") is not True):
        raise ValueError("P2-11 run, checkpoint, or approved input identity changed")
    if (plan.get("evaluationUsedForTraining") is not False
            or plan.get("evaluationUsedForRuntimeValidationLoss") is not False
            or report.get("evaluationUsedForTraining") is not False
            or report.get("evaluationUsedForRuntimeValidationLoss") is not False
            or report.get("trainingConverged") is not True
            or report.get("finalHoldoutOpened") is not False
            or canonical_sha256(EVALUATION) != EXPECTED["evaluation"]):
        raise ValueError("P2-11 evaluation scope or convergence gate changed")
    rows = read_rows(EVALUATION)
    scored = {r["id"]: r for r in score["records"] if r["group"] == "evaluation"}
    if len(rows) != 64 or len(scored) != 64:
        raise ValueError("Expected exactly 64 prepared and scored P2-11 evaluation rows")

    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    if tokenizer_record["tokenizerSha256"] != plan["tokenizerSha256"]:
        raise ValueError("P2-11 tokenizer differs from the approved frozen tokenizer")
    device = select_device("cuda")
    model, payload = read_checkpoint(CHECKPOINT, device)
    if payload.get("tokenizerRecord") != tokenizer_record or payload.get("step") != 100:
        raise ValueError("Frozen P2-11 checkpoint metadata changed")
    model.eval()
    settings = json.loads((PHASE2 / "evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    records = []
    with torch.no_grad():
        for row in rows:
            saved = scored[row["id"]]
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            answer_ids = tokenizer.encode("\n" + row["value"])
            expected_ids = answer_ids + [3]
            if answer_ids[:2] != [202, 17]:
                raise ValueError(f"Unexpected answer-boundary tokenization: {row['id']}")
            expected_ranks = []
            prefix = list(prompt_ids)
            for index, target_id in enumerate(expected_ids):
                ranked = _rank(_logits(model, prefix, device), target_id,
                               tokenizer, tokenizer.vocabulary_size)
                ranked["position"] = (
                    "answerNewline" if index == 0 else
                    "selectorLeadingPeriod" if index == 1 else
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
                scores = logits[:tokenizer.vocabulary_size].clone()
                scores[:3] = -torch.inf
                chosen_rank = int((scores > scores[actual]).sum().item()) + 1
                divergence = {
                    "index": index,
                    "actualTokenId": actual,
                    "actualPiece": "<|eos|>" if actual == 3 else tokenizer.decode([actual]),
                    "expectedNext": _rank(logits, answer_ids[index], tokenizer,
                                          tokenizer.vocabulary_size),
                    "greedyTop5": _top5(logits, tokenizer, tokenizer.vocabulary_size),
                    "actualChosenTokenRank": chosen_rank,
                }
            records.append({
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
    for phrase_id, template in HELD_OUT_PHRASES:
        group = [r for r in records if r["phrasingId"] == phrase_id]
        by_phrase[phrase_id] = {"template": template, "overall": _summarize(group), "layouts": {}}
        for layout in ("colon-space", "colon-newline"):
            by_phrase[phrase_id]["layouts"][layout] = _summarize(
                [r for r in group if r["layoutId"] == layout]
            )

    checkpoint_after = sha256_file(CHECKPOINT)
    if checkpoint_before != checkpoint_after:
        raise ValueError("P2-11 checkpoint changed during read-only audit")
    output = output.resolve()
    output.relative_to((ROOT / "training/artifacts/experiments").resolve())
    if output.exists():
        raise FileExistsError("P2-11 token audit artifact exists; choose a fresh path")
    result = {
        "schemaVersion": 1,
        "evaluationSet": EXPERIMENT,
        "mode": "read-only-teacher-forced-and-saved-greedy-divergence-audit",
        "checkpointSha256Before": checkpoint_before,
        "checkpointSha256After": checkpoint_after,
        "candidateJsonlSha256": plan["candidateJsonlSha256"],
        "evaluationJsonlSha256": plan["evaluationJsonlSha256"],
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "overall": _summarize(records),
        "byPhrase": by_phrase,
        "records": records,
        "weightUpdate": False,
        "trainingStartedDuringAudit": False,
        "greedyCompletionsResampled": False,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "finalHoldoutOpened": False,
    }
    write_json(output, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        result = audit(args.output)
        print(json.dumps({"report": str(args.output), "overall": result["overall"],
                          "byPhrase": result["byPhrase"],
                          "finalHoldoutOpened": result["finalHoldoutOpened"]}, indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"p2-11-token-audit: {exc}", file=sys.stderr)
        raise SystemExit(2)
