"""Verify approved pair identities, grouped splits, packed EOS, and token budgets."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from prepare_code_pair_candidate import DEV_SET, INPUT, LANGUAGES, _digest, load_records, prompt_text, source_text
from plex_training.benchmark import render_task_prompt
from plex_training.config import DEFAULT_CONFIG
from plex_training.pilot import inspect_pilot_bundle
from plex_training.tokenizer import PlexTokenizer, sha256_file


def inspect(dataset: Path, bundle: Path) -> dict:
    inspected = inspect_pilot_bundle(bundle)
    tokenizer = PlexTokenizer.load(bundle)
    tasks = json.loads(DEV_SET.read_text(encoding="utf-8"))
    canonical = {source_text(row, tasks["outputContracts"]): row for row in load_records()}
    if sha256_file(dataset / "manifest.json") != inspected["dataset"]["sourceDatasetManifestSha256"]:
        raise ValueError("Dataset is not the tokenizer's recorded input")
    report = {"candidateJsonlSha256": _digest(INPUT.read_bytes()), "dataset": inspected["dataset"],
              "tokenizer": inspected["tokenizer"], "contextLength": DEFAULT_CONFIG.context_length,
              "promptTemplateVersion": "plex-coding-task-v1", "splits": {}, "allBudgetsPassed": True}
    seen = set()
    for split in ("train", "validation"):
        path = dataset / (split + ".jsonl")
        if sha256_file(path) != inspected["dataset"][split + "JsonlSha256"]:
            raise ValueError("Dataset JSONL digest differs from the tokenizer input")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        index = json.loads((bundle / (split + ".index.json")).read_text(encoding="utf-8"))
        if len(index) != len(rows) or len(rows) != (24 if split == "train" else 12):
            raise ValueError("Wrong record/index counts")
        raw = (bundle / (split + ".tokens.u16le")).read_bytes()
        packed = struct.unpack(f"<{len(raw)//2}H", raw)
        max_prompt = max_record = prompt_tokens = answer_tokens = offset = 0
        maxima = {language: 0 for language in LANGUAGES}
        for row, entry in zip(rows, index):
            original = canonical.get(row["text"])
            if (original is None or original["id"] in seen or original["candidateSplit"] != split
                    or row["sourceFamilyId"] != original["sourceFamilyId"]
                    or row["splitGroupId"] != original["splitGroupId"]):
                raise ValueError("Record text, family, or split differs from the approved candidate")
            seen.add(original["id"])
            prefix = tokenizer.encode(prompt_text(original, tasks["outputContracts"]))
            whole = tokenizer.encode(row["text"])
            if whole[:len(prefix)] != prefix:
                raise ValueError("Inference prefix is not a training-token prefix")
            expected = tuple(whole + [3])
            if (entry["recordId"] != row["recordId"] or entry["startToken"] != offset
                    or entry["tokenCount"] != len(expected) or tuple(packed[offset:offset+len(expected)]) != expected):
                raise ValueError("Packed record lacks its exact token/EOS boundary")
            answer = len(whole) - len(prefix)
            if len(expected) > DEFAULT_CONFIG.context_length or answer + 1 > tasks["inferenceDefaults"]["maxNewTokens"][original["language"]]:
                raise ValueError("Candidate record exceeds its context or answer cap")
            prompt_tokens += len(prefix)
            answer_tokens += answer
            max_prompt = max(max_prompt, len(prefix))
            max_record = max(max_record, len(expected))
            maxima[original["language"]] = max(maxima[original["language"]], answer + 1)
            offset += len(expected)
        if offset != len(packed):
            raise ValueError("Packed corpus contains unindexed tokens")
        report["splits"][split] = {
            "records": len(rows), "tokens": len(packed), "promptTokens": prompt_tokens,
            "answerTokensIncludingLeadingNewline": answer_tokens, "eosMarkers": len(rows),
            "maximumPromptTokens": max_prompt, "maximumRecordTokensIncludingEos": max_record,
            "maximumAnswerTokensIncludingEosByLanguage": maxima,
            "answerShareOfTokenPositions": round(answer_tokens / len(packed), 6),
        }
    if len(seen) != 36:
        raise ValueError("Not all approved examples were encoded exactly once")
    prompts = [len(tokenizer.encode(render_task_prompt(tasks, task))) for task in tasks["tasks"]]
    if max(prompts) >= DEFAULT_CONFIG.context_length:
        raise ValueError("A development prompt exceeds context capacity")
    report["maximumDevelopmentPromptTokens"] = max(prompts)
    report["tokenizerFitSplit"] = "train"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.dataset_dir, args.bundle_dir)
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"check-code-pairs: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
