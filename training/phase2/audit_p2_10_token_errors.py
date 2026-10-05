"""Read-only teacher-forced and greedy-path token audit for the P2-10 checkpoint."""
from __future__ import annotations

import json
from pathlib import Path

import torch

from prepare_binding_candidate import sha256_file
from prepare_code_pair_candidate import prompt_text
from prepare_compositional_experiment import TOKENIZER_BUNDLE, read_rows, write_json
from prepare_explicit_answer_start_experiment import PHASE2
from plex_training.checkpoint import read_checkpoint
from plex_training.completion import _completion_tokenizer
from plex_training.telemetry import select_device

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "training/artifacts/experiments/p2-10-explicit-answer-start-run-v1"
CHECKPOINT = ARTIFACT / "pilot/pilot-checkpoint.pt"
RESULT = ARTIFACT / "result.json"
SCORES = ARTIFACT / "completion-score.json"
EVALUATION = PHASE2 / "drafts/p2-10-explicit-answer-start-v1/evaluation-only.jsonl"
SETTINGS = PHASE2 / "evaluation/p2-01b-dev-v1.json"
OUTPUT = ARTIFACT / "token-error-audit-v1.json"


def _ranked(logits: torch.Tensor, expected_id: int, tokenizer, actual_vocab: int) -> dict:
    scores = logits[:actual_vocab].float().clone()
    scores[:3] = -torch.inf
    log_probs = torch.log_softmax(scores, dim=-1)
    value = scores[expected_id]
    rank = int((scores > value).sum().item()) + 1
    best = torch.topk(scores, k=5).indices.tolist()
    return {
        "tokenId": expected_id,
        "piece": tokenizer.decode([expected_id]) if expected_id != 3 else "<|eos|>",
        "rank": rank,
        "logProbability": float(log_probs[expected_id].item()),
        "top5": [{
            "tokenId": token,
            "piece": tokenizer.decode([token]) if token != 3 else "<|eos|>",
            "logProbability": float(log_probs[token].item()),
        } for token in best],
    }


def _next_logits(model, prefix: list[int], device: torch.device) -> torch.Tensor:
    if not prefix:
        raise ValueError("Cannot score a token after an empty prompt")
    context = torch.tensor(prefix[-model.config.context_length:], dtype=torch.long,
                           device=device).unsqueeze(0)
    logits, _ = model(context)
    return logits[0, -1]


def audit() -> dict:
    before = sha256_file(CHECKPOINT)
    run = json.loads(RESULT.read_text(encoding="utf-8"))
    score_file = json.loads(SCORES.read_text(encoding="utf-8"))
    if (before != score_file["checkpointSha256"]
            or run["experiment"] != "p2-10-explicit-answer-start-v1"
            or run["finalHoldoutOpened"] is not False
            or run["evaluationUsedForTraining"] is not False
            or run["evaluationUsedForRuntimeValidationLoss"] is not False):
        raise ValueError("P2-10 checkpoint or evaluation boundary does not match the saved run")
    if run["evaluationJsonlSha256"] != "632838a43cc6faef06bea2bad5fd321c17e0f7d328a425f11ef443d66c5457a9":
        raise ValueError("P2-10 evaluation identity changed")

    tokenizer, tokenizer_record = _completion_tokenizer(TOKENIZER_BUNDLE)
    if tokenizer_record["tokenizerSha256"] != run["tokenizerSha256"]:
        raise ValueError("P2-10 tokenizer identity changed")
    device = select_device("cuda")
    model, payload = read_checkpoint(CHECKPOINT, device)
    if payload.get("tokenizerRecord") != tokenizer_record or payload.get("step") != 100:
        raise ValueError("P2-10 checkpoint metadata is inconsistent")
    model.eval()

    rows = read_rows(EVALUATION)
    recorded = {record["id"]: record for record in score_file["records"]
                if record["group"] == "evaluation"}
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    audit_records = []
    with torch.no_grad():
        for row in rows:
            prior = recorded[row["id"]]
            prompt_ids = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
            expected_ids = tokenizer.encode("\n" + row["value"])
            full_target_ids = expected_ids + [3]
            if expected_ids[:2] != [202, 17]:
                raise ValueError(f"Unexpected answer-start tokenization for {row['id']}")

            expected_positions = []
            prefix = prompt_ids.copy()
            for index, token_id in enumerate(full_target_ids):
                item = _ranked(_next_logits(model, prefix, device), token_id,
                               tokenizer, tokenizer.vocabulary_size)
                item["position"] = (
                    "answerNewline" if index == 0 else
                    "selectorPeriod" if index == 1 else
                    "eos" if token_id == 3 else
                    f"selectorBodyToken{index - 1}"
                )
                expected_positions.append(item)
                if token_id != 3:
                    prefix.append(token_id)

            generated_ids = prior["generatedTokenIds"]
            divergence = 0
            while (divergence < min(len(generated_ids), len(expected_ids))
                   and generated_ids[divergence] == expected_ids[divergence]):
                divergence += 1
            actual_path = None
            if divergence < len(expected_ids):
                actual_prefix = prompt_ids + generated_ids[:divergence]
                actual_logits = _next_logits(model, actual_prefix, device)
                expected_at_divergence = expected_ids[divergence]
                actual_path = {
                    "divergenceIndex": divergence,
                    "generatedTokenId": (generated_ids[divergence]
                                         if divergence < len(generated_ids) else None),
                    "generatedPiece": (tokenizer.decode([generated_ids[divergence]])
                                       if divergence < len(generated_ids) else "<|eos|>"),
                    "expectedNext": _ranked(actual_logits, expected_at_divergence,
                                            tokenizer, tokenizer.vocabulary_size),
                    "greedyTopTokenId": int(actual_logits[:tokenizer.vocabulary_size].argmax().item()),
                    "greedyTopPiece": tokenizer.decode([
                        int(actual_logits[:tokenizer.vocabulary_size].argmax().item())
                    ]),
                }

            audit_records.append({
                "id": row["id"], "layoutId": row["layoutId"],
                "value": row["value"], "completion": prior["completion"],
                "category": prior["category"], "eos": prior["eos"],
                "beginsWithNewline": prior["beginsWithNewline"],
                "generatedTokenIds": generated_ids,
                "generatedTokenPieces": prior["generatedTokenPieces"],
                "expectedTokenIds": full_target_ids,
                "expectedTokenPieces": [tokenizer.decode([t]) for t in expected_ids] + ["<|eos|>"],
                "expectedPositions": expected_positions,
                "firstDivergence": actual_path,
            })

    if sha256_file(CHECKPOINT) != before:
        raise ValueError("P2-10 checkpoint changed during read-only audit")
    misses = [r for r in audit_records if r["category"] != "exact_selector"]
    counts = {
        "evaluationRecords": len(audit_records),
        "exactGreedyOutputs": len(audit_records) - len(misses),
        "misses": len(misses),
        "newlineTopRanked": sum(r["expectedPositions"][0]["rank"] == 1 for r in audit_records),
        "periodTopRankedAfterExpectedNewline": sum(r["expectedPositions"][1]["rank"] == 1
                                                    for r in audit_records),
        "bodyFirstTokenTopRankedAfterExpectedPrefix": sum(
            r["expectedPositions"][2]["rank"] == 1 for r in audit_records),
        "eosTopRankedAfterExpectedAnswer": sum(r["expectedPositions"][-1]["rank"] == 1
                                                for r in audit_records),
        "actualFirstDivergenceAtAnswerToken0": sum(
            r["firstDivergence"] is not None and r["firstDivergence"]["divergenceIndex"] == 0
            for r in misses),
        "actualFirstDivergenceAfterExpectedNewlinePeriod": sum(
            r["firstDivergence"] is not None and r["firstDivergence"]["divergenceIndex"] == 2
            for r in misses),
    }
    result = {
        "schemaVersion": 1,
        "experiment": "p2-10-explicit-answer-start-v1",
        "mode": "read-only-teacher-forced-and-greedy-path-token-audit",
        "checkpointSha256Before": before,
        "checkpointSha256After": sha256_file(CHECKPOINT),
        "candidateJsonlSha256": run["candidateJsonlSha256"],
        "evaluationJsonlSha256": run["evaluationJsonlSha256"],
        "tokenizerSha256": run["tokenizerSha256"],
        "records": audit_records,
        "summaries": counts,
        "weightUpdate": False,
        "newSamplesGenerated": False,
        "evaluationUsedForTraining": False,
        "evaluationUsedForRuntimeValidationLoss": False,
        "finalHoldoutOpened": False,
    }
    write_json(OUTPUT, result)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
