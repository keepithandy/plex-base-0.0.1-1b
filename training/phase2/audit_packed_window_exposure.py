"""Read-only audit of the approved v3 corpus under the production random-window sampler."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / "training" / "artifacts"
DATASET = ARTIFACT_ROOT / "datasets" / "p2-request-following-v3"
TOKEN_BUNDLE = ARTIFACT_ROOT / "tokenizers" / "p2-request-following-v3"
MAX_INPUT_BYTES = 64 * 1024 * 1024
CONTEXT_LENGTH = 512
WINDOWS_PER_STEP = 16
REFERENCE_STEPS = 100
SEED = 1337

import sys
sys.path.insert(0, str(ROOT / "training" / "src"))
sys.path.insert(0, str(ROOT / "training" / "phase2"))

from plex_training.completion import _completion_tokenizer
from plex_training.tokenizer import sha256_file
from plex_training.artifacts import path_within_root
from prepare_code_pair_candidate import prompt_text
from diagnose_saved_checkpoints import load_approved


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError(f"Missing, linked, or oversized local input: {path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Expected JSON objects in {path}")
    return rows


def _overlap(start: int, length: int, lo: int, hi: int) -> int:
    """Count integer token positions shared by [start, start+length) and [lo, hi)."""
    return max(0, min(start + length, hi) - max(start, lo))


def audit(*, candidate_path: Path, approval_path: Path, task_set_path: Path,
          output: Path, steps: int = REFERENCE_STEPS, seed: int = SEED) -> dict:
    if type(steps) is not int or not 1 <= steps <= 100_000:
        raise ValueError("steps must be from 1 through 100000")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    candidate_rows, candidate_sha = load_approved(candidate_path, approval_path)
    task_set = json.loads(task_set_path.read_text(encoding="utf-8"))
    if task_set.get("kind") != "development":
        raise ValueError("Expected the development prompt contracts")
    tokenizer, tokenizer_record = _completion_tokenizer(TOKEN_BUNDLE)

    dataset_manifest_path = DATASET / "manifest.json"
    train_path = DATASET / "train.jsonl"
    index_path = TOKEN_BUNDLE / "train.index.json"
    token_path = TOKEN_BUNDLE / "train.tokens.u16le"
    for path in (dataset_manifest_path, train_path, index_path, token_path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(f"Missing, linked, or oversized corpus artifact: {path}")
    manifest_sha = sha256_file(dataset_manifest_path)
    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    bundle = json.loads((TOKEN_BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    if (bundle.get("sourceDatasetManifestSha256") != manifest_sha
            or bundle.get("tokenizerSha256") != tokenizer_record["tokenizerSha256"]
            or manifest["summary"].get("trainJsonlSha256") != sha256_file(train_path)
            or manifest["summary"].get("trainRecords") != 156
            or manifest["summary"].get("trainTokensSha256") != sha256_file(token_path)
            or any(source.get("revision") != candidate_sha for source in manifest["sources"])):
        raise ValueError("Built corpus, tokenizer, and approved candidate provenance do not match")

    data_rows = _read_jsonl(train_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if len(data_rows) != 156 or len(index) != len(data_rows):
        raise ValueError("Expected 156 training rows and matching token index entries")
    candidate_by_group = {
        row["splitGroupId"]: row for row in candidate_rows if row["candidateSplit"] == "train"
    }
    contracts = task_set["outputContracts"]
    parsed: list[dict[str, Any]] = []
    expected_offset = 0
    packed_tokens = token_path.read_bytes()
    if len(packed_tokens) % 2:
        raise ValueError("Packed uint16 token file has an odd byte count")
    if len(packed_tokens) // 2 <= CONTEXT_LENGTH + 1:
        raise ValueError("Packed corpus is shorter than one training window")
    for row, entry in zip(data_rows, index):
        group = row["splitGroupId"] if "splitGroupId" in row else row["groupId"]
        source = candidate_by_group.get(row.get("candidateId", ""))
        if source is None:
            source = next((item for item in candidate_rows
                           if item["candidateSplit"] == "train"
                           and item["id"].split("-")[-1] == row.get("path", "").rsplit("/", 1)[-1].removesuffix(".txt")), None)
        if source is None or entry.get("recordId") != row.get("recordId"):
            # Resolve robustly by exact approved prompt text; split groups remain provenance data.
            text_matches = [item for item in candidate_rows
                            if item["candidateSplit"] == "train"
                            and prompt_text(item, contracts) + "\n" + item["solution"] == row.get("text")]
            if len(text_matches) != 1:
                raise ValueError("Packed record does not map uniquely to an approved training example")
            source = text_matches[0]
        if row.get("text") != prompt_text(source, contracts) + "\n" + source["solution"]:
            raise ValueError(f"Packed text differs from the approved candidate: {source['id']}")
        text = row["text"]
        prompt = prompt_text(source, contracts)
        if not text.startswith(prompt + "\n"):
            raise ValueError(f"Prompt prefix does not match inference text: {source['id']}")
        prompt_tokens = tokenizer.encode(prompt)
        text_tokens = tokenizer.encode(text)
        start = entry.get("startToken")
        count = entry.get("tokenCount")
        tokens = text_tokens + [3]
        if (start != expected_offset or count != len(tokens)
                or packed_tokens[start * 2:(start + count) * 2]
                != b"".join(int(token).to_bytes(2, "little") for token in tokens)):
            raise ValueError(f"Token index does not match packed data: {source['id']}")
        if text_tokens[:len(prompt_tokens)] != prompt_tokens:
            raise ValueError(f"Prompt tokenization is not a prefix of record tokenization: {source['id']}")
        rec_start = start
        rec_end = start + count  # exclusive; includes EOS
        prompt_end = start + len(prompt_tokens)
        parsed.append({"id": source["id"], "language": source["language"],
                       "recordStart": rec_start, "promptEnd": prompt_end, "recordEnd": rec_end,
                       "promptTokens": len(prompt_tokens),
                       "answerAndEosTokens": rec_end - prompt_end,
                       "recordTokens": count})
        expected_offset = rec_end
    total_tokens = len(packed_tokens) // 2
    if expected_offset != total_tokens:
        raise ValueError("Token index does not cover the complete packed corpus")

    max_start = total_tokens - CONTEXT_LENGTH - 1
    starts = [rng.randint(0, max_start)
              for rng in [random.Random(seed)]
              for _ in range(steps * WINDOWS_PER_STEP)]
    by_id: dict[str, list[int]] = {record["id"]: [0, 0, 0, 0] for record in parsed}
    # Counters per record: full prompt+answer, any answer target, prompt at position zero,
    # and total answer-target positions seen over the replayed production sampling stream.
    alignment_positions: dict[str, list[int]] = defaultdict(list)
    for sample_start in starts:
        for record in parsed:
            r0, prompt_end, rend = record["recordStart"], record["promptEnd"], record["recordEnd"]
            full_prompt = sample_start <= r0 and sample_start + CONTEXT_LENGTH >= prompt_end
            all_answer_targets = sample_start + 1 <= prompt_end and sample_start + CONTEXT_LENGTH + 1 >= rend
            if full_prompt and all_answer_targets:
                by_id[record["id"]][0] += 1
                alignment_positions[record["id"]].append(r0 - sample_start)
            overlap = _overlap(sample_start + 1, CONTEXT_LENGTH, prompt_end, rend)
            if overlap:
                by_id[record["id"]][1] += 1
                by_id[record["id"]][3] += overlap
            if sample_start == r0:
                by_id[record["id"]][2] += 1

    record_results = []
    lang_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in parsed:
        counts = by_id[record["id"]]
        summary = {**record,
                   "completePromptAndAnswerWindows": counts[0],
                   "windowsWithAnyAnswerTarget": counts[1],
                   "promptAtInferencePositionZeroWindows": counts[2],
                   "answerTargetTokenPresentations": counts[3],
                   "completeWindowPromptPositionMin": min(alignment_positions[record["id"]])
                   if alignment_positions[record["id"]] else None,
                   "completeWindowPromptPositionMax": max(alignment_positions[record["id"]])
                   if alignment_positions[record["id"]] else None}
        record_results.append(summary)
        lang_results[record["language"]].append(summary)
    language_summary = {}
    for language, group in sorted(lang_results.items()):
        aligned = [record["promptAtInferencePositionZeroWindows"] for record in group]
        complete = [record["completePromptAndAnswerWindows"] for record in group]
        language_summary[language] = {
            "records": len(group),
            "recordTokensMin": min(row["recordTokens"] for row in group),
            "recordTokensMedian": statistics.median(row["recordTokens"] for row in group),
            "recordTokensMax": max(row["recordTokens"] for row in group),
            "meanCompletePromptAndAnswerWindowsPerRecord": round(statistics.mean(complete), 3),
            "recordsWithZeroCompleteWindows": sum(count == 0 for count in complete),
            "meanPromptAtPositionZeroWindowsPerRecord": round(statistics.mean(aligned), 3),
            "totalAnswerTargetTokenPresentations": sum(row["answerTargetTokenPresentations"] for row in group),
        }
    report = {
        "schemaVersion": 1,
        "kind": "read-only-production-packed-window-exposure-audit",
        "candidateSha256": candidate_sha,
        "datasetManifestSha256": manifest_sha,
        "trainJsonlSha256": sha256_file(train_path),
        "packedTokensSha256": sha256_file(token_path),
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "records": len(parsed), "packedTokenCount": total_tokens,
        "contextLength": CONTEXT_LENGTH,
        "sampler": {"algorithm": "Python random.Random(seed).randint(0, N-context-1)",
                    "seed": seed, "microBatch": 1, "gradientAccumulation": WINDOWS_PER_STEP,
                    "referenceSteps": steps, "windowsReplayed": len(starts),
                    "possibleWindowStarts": max_start + 1,
                    "checkpointCount": "not simulated; sample starts replay the production Python RNG sequence"},
        "summary": {
            "meanRecordTokens": round(statistics.mean(row["recordTokens"] for row in parsed), 3),
            "meanPromptTokens": round(statistics.mean(row["promptTokens"] for row in parsed), 3),
            "meanAnswerAndEosTokens": round(statistics.mean(row["answerAndEosTokens"] for row in parsed), 3),
            "completePromptAndAnswerWindowEvents": sum(row["completePromptAndAnswerWindows"] for row in record_results),
            "recordsWithZeroCompletePromptAndAnswerWindows": sum(not row["completePromptAndAnswerWindows"] for row in record_results),
            "promptAtInferencePositionZeroEvents": sum(row["promptAtInferencePositionZeroWindows"] for row in record_results),
            "meanPromptPositionWhenPromptAndAnswerFit": round(statistics.mean(
                pos for positions in alignment_positions.values() for pos in positions), 3)
                if any(alignment_positions.values()) else None,
            "meanAnswerTargetTokenPresentationsPerRecord": round(statistics.mean(
                row["answerTargetTokenPresentations"] for row in record_results), 3),
        },
        "byLanguage": language_summary,
        "perRecord": record_results,
        "interpretation": "The replay audits random start positions only. It does not simulate model updates, dropout, loss gradients, or prove why earlier checkpoints missed answers.",
    }
    output = path_within_root(output, ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Audit output already exists; choose a fresh directory")
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--task-set", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=REFERENCE_STEPS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    report = audit(candidate_path=args.candidate, approval_path=args.approval,
                   task_set_path=args.task_set, output=args.output,
                   steps=args.steps, seed=args.seed)
    print(json.dumps({"output": str(args.output / "report.json"),
                      "candidateSha256": report["candidateSha256"],
                      "windowsReplayed": report["sampler"]["windowsReplayed"],
                      "summary": report["summary"],
                      "byLanguage": report["byLanguage"]}, indent=2))


if __name__ == "__main__":
    main()
