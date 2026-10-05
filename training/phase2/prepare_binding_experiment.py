"""Pack approved control/varied corpora using the existing tokenizer; never fit or train."""
from __future__ import annotations

import argparse
from array import array
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from prepare_binding_candidate import ROOT, sha256_file, source_text, validate
from diagnose_saved_checkpoints import load_approved
from plex_training.tokenizer import PlexTokenizer, CODEC

CANDIDATE_SHA = "8f3fc7dfc21c4ebb5ce5b40391e9b123521d13df50b2d349e5d6b7c3faf37c2f"
EVALUATION_SHA = "ea8699efc997c0b4a5cdeb55c0da1d5be1b0d27a8ae9ad6b5164476c0d82ca7c"
TOKENIZER_SHA = "a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573"
ASSETS = ("tokenizer.json", "tokenizer-config.json", "model-config.json")
ARTIFACT_ROOT = ROOT / "training/artifacts"


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_inputs():
    phase2 = ROOT / "training/phase2"
    draft = phase2 / "drafts/p2-03-binding-diversity-v1"
    approval_path = phase2 / "approvals/p2-03-binding-diversity-v1.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if (approval.get("approvalStatus") != "approved"
            or approval.get("scope") != "local-P2-diagnostic-training"
            or approval.get("candidateJsonlSha256") != CANDIDATE_SHA
            or approval.get("evaluationJsonlSha256") != EVALUATION_SHA
            or approval.get("records") != 24 or approval.get("evaluationApprovedForTraining") is not False):
        raise ValueError("Exact diagnostic training approval is required")
    if (sha256_file(draft / "candidate.jsonl") != CANDIDATE_SHA
            or sha256_file(draft / "evaluation-only.jsonl") != EVALUATION_SHA):
        raise ValueError("Approved candidate or evaluation changed")
    train = [json.loads(line) for line in (draft / "candidate.jsonl").read_text(encoding="utf-8").splitlines()]
    evaluation = [json.loads(line) for line in (draft / "evaluation-only.jsonl").read_text(encoding="utf-8").splitlines()]
    old, _ = load_approved(phase2 / "drafts/p2-02-request-following-v3/candidate.jsonl",
                           phase2 / "approvals/p2-02-request-following-v3.json")
    dev_path = phase2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4":
        raise ValueError("Development settings changed")
    dev = json.loads(dev_path.read_text(encoding="utf-8"))
    reserved_path = ARTIFACT_ROOT / "diagnostics/p2-transfer-v1/cases.json"
    if sha256_file(reserved_path) != "c70af62e3f954066a24dae36c613b6efb51a2a34580326d0d9400afff53e88a3":
        raise ValueError("Reserved transfer cases changed")
    reserved = json.loads(reserved_path.read_text(encoding="utf-8"))["cases"]
    reserved = [r for r in reserved if r["kind"] == "variation"]
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for reference syntax checks")
    validate(train, evaluation, old, reserved, dev, node)
    return train, evaluation, dev, approval_path


def pack_split(rows, dataset, bundle, split, tokenizer, contracts):
    index, packed, texts = [], array("H"), []
    for row in rows:
        text = source_text(row, contracts)
        ids = tokenizer.encode(text)
        if tokenizer.decode(ids) != text or len(ids) + 1 > 512:
            raise ValueError("Reference roundtrip/context check failed")
        ids.append(3)
        index.append({"recordId": row["id"], "startToken": len(packed), "tokenCount": len(ids)})
        packed.extend(ids)
        texts.append({"recordId": row["id"], "splitGroupId": row["splitGroupId"],
                      "sourceId": row["sourceId"], "text": text})
    if len(packed) < 513:
        raise ValueError("Packed split must support the unchanged 512-token validation infrastructure")
    path = dataset / (split + ".jsonl")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(json.dumps(row, sort_keys=True) + "\n" for row in texts))
    if sys.byteorder != "little":
        packed.byteswap()
    token_path = bundle / (split + ".tokens.u16le")
    token_path.write_bytes(packed.tobytes())
    write_json(bundle / (split + ".index.json"), index)
    return {"path": token_path.name, "records": len(rows), "tokenCount": len(packed),
            "sha256": sha256_file(token_path), "jsonlSha256": sha256_file(path),
            "roundtripRecords": len(rows), "textBytes": sum(len(r["text"].encode()) for r in texts)}


def prepare(output):
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared experiment already exists; choose a fresh directory")
    train, evaluation, dev, approval_path = load_inputs()
    original_bundle = ARTIFACT_ROOT / "tokenizers/p2-request-following-v3"
    if sha256_file(original_bundle / "tokenizer.json") != TOKENIZER_SHA:
        raise ValueError("Existing tokenizer changed")
    tokenizer = PlexTokenizer.load(original_bundle)
    # Preparation is under 1 MiB; reserve room for two initializations and checkpoints too.
    used = sum(p.stat().st_size for p in ARTIFACT_ROOT.rglob("*") if p.is_file() and not p.is_symlink())
    if used + 2 * 1024**3 > 200 * 1024**3:
        raise ValueError("Insufficient space in the owner's 200 GiB artifact allocation")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(approval_path, output / "approval.json")
    arms = {}
    for arm, records in (("original-only", [r for r in train if r["kind"] == "original"]), ("varied", train)):
        dataset, bundle = output / arm / "dataset", output / arm / "tokenizer"
        dataset.mkdir(parents=True)
        bundle.mkdir()
        for asset in ASSETS:
            shutil.copyfile(original_bundle / asset, bundle / asset)
        splits = {split: pack_split(rows, dataset, bundle, split, tokenizer, dev["outputContracts"])
                  for split, rows in (("train", records), ("validation", evaluation))}
        manifest = {"schemaVersion": 1, "purpose": "approved-local-binding-diagnostic", "arm": arm,
                    "candidateJsonlSha256": CANDIDATE_SHA, "evaluationJsonlSha256": EVALUATION_SHA,
                    "approvalSha256": sha256_file(approval_path), "sameFamilyEvaluation": True,
                    "splitPolicy": "original-anchors-or-approved-variations;separate-reserved-bindings",
                    "summary": {**{split + "Records": info["records"] for split, info in splits.items()},
                                **{split + "JsonlSha256": info["jsonlSha256"] for split, info in splits.items()}}}
        write_json(dataset / "manifest.json", manifest)
        shutil.copyfile(dataset / "manifest.json", bundle / "source-dataset-manifest.json")
        write_json(bundle / "manifest.json", {"schemaVersion": 1, "codec": CODEC, "storageDtype": "uint16-le",
                   "actualVocabularySize": tokenizer.vocabulary_size, "modelVocabularyCapacity": 16384,
                   "tokenizerSha256": TOKENIZER_SHA, "modelConfigSha256": sha256_file(bundle / "model-config.json"),
                   "sourceDatasetManifestSha256": sha256_file(dataset / "manifest.json"),
                   "tokenizerReuse": {"refitted": False, "fitCorpus": "approved-p2-request-following-v3-train",
                                      "sourceBundleManifestSha256": sha256_file(original_bundle / "manifest.json")},
                   **splits})
        arms[arm] = {"trainRecords": len(records), "operations": 6,
                     "recordsPerOperation": dict(Counter(r["sourceId"] for r in records)),
                     "trainTokens": splits["train"]["tokenCount"], "validationTokens": splits["validation"]["tokenCount"]}
    files = {str(p.relative_to(output)).replace("\\", "/"): sha256_file(p)
             for p in output.rglob("*") if p.is_file()}
    plan = {"schemaVersion": 1, "experiment": "p2-03-binding-diversity-v1", "approvalStatus": "approved",
            "candidateJsonlSha256": CANDIDATE_SHA, "evaluationJsonlSha256": EVALUATION_SHA,
            "tokenizerSha256": TOKENIZER_SHA, "tokenizerRefitted": False, "arms": arms, "files": files,
            "maximumStepsPerArm": 100, "maximumMinutesPerArm": 10, "seed": 1337,
            "samplingPolicy": "complete-record-v1", "modelTrained": False,
            "validationMeaning": "same-family new-binding text loss; not family-separated capability validation"}
    write_json(output / "experiment.json", plan)
    return {"preparedDirectory": str(output), **plan}


def verify_prepared(prepared):
    train, evaluation, dev, approval_path = load_inputs()
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    if (plan.get("candidateJsonlSha256") != CANDIDATE_SHA or plan.get("evaluationJsonlSha256") != EVALUATION_SHA
            or sha256_file(prepared / "approval.json") != sha256_file(approval_path)
            or plan.get("maximumStepsPerArm") != 100 or plan.get("maximumMinutesPerArm") != 10):
        raise ValueError("Prepared experiment approval or bounds differ")
    for relative, digest in plan["files"].items():
        path = prepared / relative
        path.resolve().relative_to(prepared.resolve())
        if path.is_symlink() or sha256_file(path) != digest:
            raise ValueError("Prepared experiment input changed")
    for arm, expected in (("original-only", [r for r in train if r["kind"] == "original"]), ("varied", train)):
        tokenizer = PlexTokenizer.load(prepared / arm / "tokenizer")
        if sha256_file(prepared / arm / "tokenizer/tokenizer.json") != TOKENIZER_SHA:
            raise ValueError("Frozen tokenizer changed")
        for split, rows in (("train", expected), ("validation", evaluation)):
            actual = [json.loads(line) for line in (prepared / arm / "dataset" / (split + ".jsonl")).read_text(encoding="utf-8").splitlines()]
            if [(r["recordId"], r["text"]) for r in actual] != [(r["id"], source_text(r, dev["outputContracts"])) for r in rows]:
                raise ValueError("Prepared text differs from exact approved rows")
            packed = array("H")
            packed.frombytes((prepared / arm / "tokenizer" / (split + ".tokens.u16le")).read_bytes())
            if sys.byteorder != "little":
                packed.byteswap()
            expected_ids = [i for r in rows for i in tokenizer.encode(source_text(r, dev["outputContracts"])) + [3]]
            if packed.tolist() != expected_ids:
                raise ValueError("Prepared token IDs differ from approved text")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "files"}, indent=2))
