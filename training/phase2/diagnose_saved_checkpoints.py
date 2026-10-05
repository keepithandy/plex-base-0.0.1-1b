"""Inspect approved v3 prompt completions from saved checkpoints; never train.

This is an in-distribution diagnostic, not the owner-authored coding benchmark.
It writes outputs only to a new local directory and never runs generated code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.checkpoint import read_checkpoint
from plex_training.benchmark import _check_task
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.telemetry import select_device
from plex_training.tokenizer import CODEC, sha256_file

from prepare_code_pair_candidate import prompt_text

MAX_CANDIDATE_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
LANGUAGES = ("html", "css", "javascript")
SPLITS = ("train", "validation")


def load_approved(candidate_path: Path, approval_path: Path) -> tuple[list[dict], str]:
    for path in (candidate_path, approval_path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CANDIDATE_BYTES:
            raise ValueError(f"Missing, linked, or oversized input: {path}")
    raw = candidate_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    if (approval.get("approvalStatus") != "approved"
            or approval.get("scope") != "local-P2-training"
            or approval.get("candidateJsonlSha256") != digest
            or approval.get("records") != len(rows)):
        raise ValueError("Candidate does not match its local-training approval")
    ids: set[str] = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or row["id"] in ids or row.get("candidateSplit") not in SPLITS
                or row.get("language") not in LANGUAGES
                or not isinstance(row.get("request"), str)
                or not isinstance(row.get("solution"), str)
                or not row["solution"]):
            raise ValueError("Candidate has invalid diagnostic rows")
        ids.add(row["id"])
    if Counter(row["candidateSplit"] for row in rows) != {"train": 156, "validation": 78}:
        raise ValueError("Approved v3 split is not the expected 156/78")
    return rows, digest


def aggregate(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["split"]].append(record)
        groups[f"{record['split']}/{record['language']}"].append(record)
    return {
        group: {
            "count": len(items),
            "exactTarget": sum(item["exactTarget"] for item in items),
            "codeOnlyExact": sum(item["codeOnlyExact"] for item in items),
            "empty": sum(item["empty"] for item in items),
            "truncated": sum(item["truncated"] for item in items),
            "meanGeneratedTokens": round(sum(item["generatedTokenCount"] for item in items) / len(items), 2),
            "meanReferenceTokens": round(sum(item["referenceTokenCount"] for item in items) / len(items), 2),
            "referenceOverCap": sum(item["referenceOverCap"] for item in items),
            "staticPass": sum(item["staticPass"] for item in items),
            "syntaxPass": sum(item["parseStatus"] == "pass" for item in items),
            "staticChecksPassed": sum(item["staticChecksPassed"] for item in items),
            "staticChecksTotal": sum(item["staticChecksTotal"] for item in items),
        }
        for group, items in sorted(groups.items())
    }


def diagnose(*, candidate: Path, approval: Path, task_set: Path, bundle: Path,
             checkpoints: list[Path], output: Path, device_name: str) -> dict:
    rows, candidate_sha = load_approved(candidate, approval)
    if task_set.is_symlink() or not task_set.is_file() or task_set.stat().st_size > MAX_CANDIDATE_BYTES:
        raise ValueError("Development task set is missing, linked, or oversized")
    task_set_raw = task_set.read_bytes()
    settings = json.loads(task_set_raw)
    if (settings.get("kind") != "development"
            or settings.get("inferenceDefaults", {}).get("temperature") != 0.0
            or settings["inferenceDefaults"].get("promptTemplateVersion") != "plex-coding-task-v1"):
        raise ValueError("Expected the fixed greedy development prompt settings")
    contracts = settings["outputContracts"]
    caps = settings["inferenceDefaults"]["maxNewTokens"]
    seed = settings["inferenceDefaults"]["seed"]
    vocabulary, tokenizer_record = _completion_tokenizer(bundle)
    bundle_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    dataset_manifest_path = ROOT / "training" / "artifacts" / "datasets" / "p2-request-following-v3" / "manifest.json"
    dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    dataset_sha = sha256_file(dataset_manifest_path)
    if (bundle_manifest.get("sourceDatasetManifestSha256") != dataset_sha
            or dataset_manifest.get("sourceCatalogSha256") is None
            or any(source.get("revision") != candidate_sha for source in dataset_manifest["sources"])):
        raise ValueError("Tokenizer dataset does not match the approved v3 candidate")
    device = select_device(device_name)
    node = shutil.which("node")
    if output.exists():
        raise FileExistsError("Diagnostic output directory already exists; choose a fresh path")
    if not checkpoints or len({path.resolve() for path in checkpoints}) != len(checkpoints):
        raise ValueError("Provide distinct saved checkpoints")

    all_results: list[dict] = []
    for checkpoint in checkpoints:
        if checkpoint.is_symlink() or not checkpoint.is_file():
            raise ValueError(f"Checkpoint is missing or linked: {checkpoint}")
        model, payload = read_checkpoint(checkpoint, device)
        initialization = payload.get("initializationRecord")
        if (payload.get("codec") != CODEC or payload.get("tokenizerRecord") != tokenizer_record
                or payload.get("datasetRecord", {}).get("sourceDatasetManifestSha256") != dataset_sha
                or type(payload.get("step")) is not int or payload["step"] <= 0
                or not isinstance(initialization, dict)
                or initialization.get("pretrainedCheckpointLoaded") is not False
                or initialization.get("pretrainedModelWeightsLoaded") is not False):
            raise ValueError("Checkpoint must match the scratch-initialized tokenizer")
        records = []
        for row in rows:
            prompt = prompt_text(row, contracts)
            prompt_ids = vocabulary.encode(prompt)
            if len(prompt_ids) >= model.config.context_length:
                raise ValueError(f"Prompt exceeds model context: {row['id']}")
            reference = "\n" + row["solution"]
            reference_tokens = len(vocabulary.encode(prompt + reference)) - len(prompt_ids) + 1  # EOS
            cap = caps[row["language"]]
            generated_ids, eos = _generate_token_ids(
                model, prompt_ids, actual_vocab=vocabulary.vocabulary_size,
                max_new_tokens=cap, temperature=0.0, seed=seed, device=device,
            )
            completion = vocabulary.decode(generated_ids)
            static = _check_task({"id": row["id"], "language": row["language"],
                                  "difficulty": "basic", "checks": row["checks"]},
                                 completion, node, 5.0)
            records.append({
                "id": row["id"], "split": row["candidateSplit"], "language": row["language"],
                "completion": completion, "exactTarget": completion == reference and eos,
                "codeOnlyExact": completion.strip() == row["solution"].strip() and eos,
                "empty": not completion.strip(), "truncated": not eos,
                "generatedTokenCount": len(generated_ids),
                "referenceTokenCount": reference_tokens,
                "referenceOverCap": reference_tokens > cap,
                "staticPass": static["passed"], "parseStatus": static["parseStatus"],
                "staticChecksPassed": static["checksPassed"],
                "staticChecksTotal": static["checksTotal"],
            })
        all_results.append({
            "checkpoint": str(checkpoint.resolve()),
            "checkpointSha256": sha256_file(checkpoint),
            "step": payload["step"],
            "groups": aggregate(records),
            "records": records,
        })

    report = {
        "schemaVersion": 1,
        "kind": "approved-v3-in-distribution-completion-diagnostic",
        "candidateSha256": candidate_sha,
        "developmentSettingsSha256": hashlib.sha256(task_set_raw).hexdigest(),
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "datasetManifestSha256": dataset_sha,
        "nodeAvailableForSyntaxCheck": node is not None,
        "device": str(device),
        "decoding": {"temperature": 0.0, "seed": seed, "maxNewTokens": caps},
        "checkpoints": all_results,
        "caveat": "In-distribution text matching only; no code execution or final-holdout evaluation.",
    }
    encoded = (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError("Diagnostic report exceeds the 4 MiB output bound")
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_bytes(encoded)
    return {"output": str(output / "report.json"), "candidateSha256": candidate_sha,
            "checkpoints": [{key: result[key] for key in ("checkpointSha256", "step", "groups")}
                            for result in all_results]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--task-set", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()
    print(json.dumps(diagnose(candidate=args.candidate, approval=args.approval,
                              task_set=args.task_set, bundle=args.bundle,
                              checkpoints=args.checkpoint, output=args.output,
                              device_name=args.device), indent=2))


if __name__ == "__main__":
    main()
