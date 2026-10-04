"""Check approved record identity, whole-group splits, packed EOS, and limits."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import prepare_curated_request_candidate as candidate
from prepare_code_pair_candidate import prompt_text
from plex_training.benchmark import render_task_prompt
from plex_training.config import DEFAULT_CONFIG
from plex_training.pilot import inspect_pilot_bundle
from plex_training.tokenizer import PlexTokenizer, sha256_file


def inspect(dataset: Path, bundle: Path) -> dict:
    record = inspect_pilot_bundle(bundle)
    tokenizer = PlexTokenizer.load(bundle)
    tasks = json.loads(candidate.original.DEV.read_text(encoding="utf-8"))
    raw = (candidate.OUTPUT / "candidate.jsonl").read_bytes()
    originals = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    if originals != candidate.records():
        raise ValueError("Reviewed candidate content changed")
    if sha256_file(dataset / "manifest.json") != record["dataset"]["sourceDatasetManifestSha256"]:
        raise ValueError("Tokenizer was fitted on a different dataset")
    canonical = {prompt_text(row, tasks["outputContracts"]) + "\n" + row["solution"]: row for row in originals}
    report = {"candidateJsonlSha256": hashlib.sha256(raw).hexdigest(), "dataset": record["dataset"],
              "tokenizer": record["tokenizer"], "tokenizerFitSplit": "train",
              "contextLength": DEFAULT_CONFIG.context_length, "splits": {}, "allBudgetsPassed": True}
    seen = set()
    for split in ("train", "validation"):
        split_jsonl = dataset / (split + ".jsonl")
        if sha256_file(split_jsonl) != record["dataset"][split + "JsonlSha256"]:
            raise ValueError("Split text changed after tokenizer fitting")
        rows = [json.loads(line) for line in split_jsonl.read_text(encoding="utf-8").splitlines()]
        index = json.loads((bundle / (split + ".index.json")).read_text(encoding="utf-8"))
        if len(rows) != (120 if split == "train" else 60) or len(index) != len(rows):
            raise ValueError("Wrong split/index size")
        raw_tokens = (bundle / (split + ".tokens.u16le")).read_bytes()
        if len(raw_tokens) % 2: raise ValueError("Odd token byte count")
        tokens = struct.unpack(f"<{len(raw_tokens)//2}H", raw_tokens)
        offset = prompt_tokens = answer_tokens = largest_prompt = largest_record = 0
        maxima = {language: 0 for language in candidate.LANGUAGES}
        by_language = {language: 0 for language in candidate.LANGUAGES}
        for row, entry in zip(rows, index):
            source = canonical.get(row["text"])
            if (source is None or source["id"] in seen or source["candidateSplit"] != split
                    or source["sourceFamilyId"] != row["sourceFamilyId"]
                    or source["splitGroupId"] != row["splitGroupId"]):
                raise ValueError("A dataset record differs from the exact approved candidate")
            seen.add(source["id"])
            prefix = tokenizer.encode(prompt_text(source, tasks["outputContracts"]))
            whole = tokenizer.encode(row["text"])
            if whole[:len(prefix)] != prefix:
                raise ValueError("Inference prompt is not a complete training-token prefix")
            expected = tuple(whole + [3])
            if (entry["recordId"] != row["recordId"] or entry["startToken"] != offset
                    or entry["tokenCount"] != len(expected)
                    or tuple(tokens[offset:offset+len(expected)]) != expected):
                raise ValueError("Packed tokens or EOS boundary differ from exact source")
            answer = len(whole) - len(prefix) + 1
            if len(expected) > DEFAULT_CONFIG.context_length or answer > tasks["inferenceDefaults"]["maxNewTokens"][source["language"]]:
                raise ValueError("Record exceeds context or fixed answer cap")
            offset += len(expected)
            prompt_tokens += len(prefix)
            answer_tokens += answer - 1
            largest_prompt = max(largest_prompt, len(prefix))
            largest_record = max(largest_record, len(expected))
            maxima[source["language"]] = max(maxima[source["language"]], answer)
            by_language[source["language"]] += 1
        if offset != len(tokens): raise ValueError("Packed split contains unindexed tokens")
        report["splits"][split] = {"records": len(rows), "recordsByLanguage": by_language,
                                   "tokens": len(tokens), "promptTokens": prompt_tokens,
                                   "answerTokensIncludingLeadingNewline": answer_tokens, "eosMarkers": len(rows),
                                   "maximumPromptTokens": largest_prompt, "maximumRecordTokensIncludingEos": largest_record,
                                   "maximumAnswerTokensIncludingEosByLanguage": maxima,
                                   "answerShareOfTokenPositions": round(answer_tokens / len(tokens), 6)}
    if len(seen) != 180: raise ValueError("Not every approved example was encoded exactly once")
    prompts = [len(tokenizer.encode(render_task_prompt(tasks, task))) for task in tasks["tasks"]]
    if max(prompts) >= DEFAULT_CONFIG.context_length: raise ValueError("Development prompt exceeds context")
    report["maximumDevelopmentPromptTokens"] = max(prompts)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.dataset_dir, args.bundle_dir)
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True); stream.write("\n")
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"check-curated-bundle: {exc}\n")


if __name__ == "__main__":
    main()
