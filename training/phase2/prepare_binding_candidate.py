"""Prepare a pending 24-record local diagnostic candidate and separate evaluation bindings."""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from diagnose_transfer import ROOT, CANDIDATE_SHA, replace_strings, check_completion, sha256_file
from diagnose_saved_checkpoints import load_approved
from prepare_code_pair_candidate import prompt_text, source_text

PLAN = (
    ("gap-html-bidi-02", "Kyoto", ("Lisbon", "Seoul", "Nairobi"), ("Riga", "Tallinn")),
    ("gap-html-progress-01", "35", ("18", "47", "83"), ("27", "74")),
    ("gap-css-logical-border-03", ".top-edge", (".card-edge", ".banner-edge", ".notice-edge"),
     (".summary-edge", ".widget-edge")),
    ("gap-css-layout-01", "12px", ("6px", "14px", "28px"), ("10px", "22px")),
    ("gap-javascript-division-01", "quotientTowardZero",
     ("integerQuotient", "quotientTruncated", "divideTowardZero"), ("truncatedDivide", "wholeQuotient")),
    ("gap-javascript-array-copy-01", "copyItems", ("copyValues", "shallowClone", "copyList"),
     ("cloneList", "duplicateArray")),
)


def normalized(text):
    return " ".join(text.casefold().split())


def build(rows):
    sources = {r["id"]: r for r in rows}
    train, evaluation = [], []
    for source_id, before, training_values, evaluation_values in PLAN:
        source = sources[source_id]
        if source["candidateSplit"] != "train":
            raise ValueError("Anchor must be an approved training record")
        for split, values in (("train", (None, *training_values)), ("evaluation-only", evaluation_values)):
            for index, after in enumerate(values):
                case = {key: copy.deepcopy(source[key]) for key in ("language", "request", "solution", "checks")}
                if after is not None:
                    if before not in case["request"] or before not in case["solution"]:
                        raise ValueError("Binding must occur in both request and solution")
                    case = replace_strings(case, before, after)
                case.update(schemaVersion=1, id=f"binding-{source_id}-{split}-{index}",
                            sourceId=source_id, splitGroupId=source["splitGroupId"],
                            kind="original" if after is None else "variation", before=before if after else None,
                            after=after, originalSolution=source["solution"],
                            use="training-candidate" if split == "train" else "evaluation-only-never-train",
                            approvalStatus="pending-owner-review" if split == "train" else "evaluation-only",
                            provenance="codex-authored-binding-variation-of-approved-v3")
                (train if split == "train" else evaluation).append(case)
    return train, evaluation


def validate(train, evaluation, approved, reserved, development, node):
    if Counter(r["language"] for r in train) != {"html": 8, "css": 8, "javascript": 8}:
        raise ValueError("Candidate must contain eight records per language")
    if Counter(r["language"] for r in evaluation) != {"html": 4, "css": 4, "javascript": 4}:
        raise ValueError("Evaluation must contain four records per language")
    requests, solutions = set(), set()
    forbidden_requests = {normalized(r["request"]) for r in reserved + development["tasks"]}
    approved_requests = {normalized(r["request"]) for r in approved}
    approved_solutions = {normalized(r["solution"]) for r in approved}
    for row in train + evaluation:
        req, sol = normalized(row["request"]), normalized(row["solution"])
        if req in requests or sol in solutions or req in forbidden_requests:
            raise ValueError("Duplicate or reserved request/reference")
        if row["kind"] != "original" and (req in approved_requests or sol in approved_solutions):
            raise ValueError("New variation duplicates an approved record")
        requests.add(req)
        solutions.add(sol)
        if not check_completion(row, "\n" + row["solution"], True, node)["staticPass"]:
            raise ValueError("Reference failed syntax/static/binding checks")
        if row["kind"] == "variation" and check_completion(
                row, "\n" + row["originalSolution"], True, node)["staticPass"]:
            raise ValueError("Unchanged source answer passes changed request")
    # No proposed training binding is one of the reserved transfer replacements.
    # Evaluation names/values must also stay out of proposed training text.
    train_text = "\n".join(r["request"] + "\n" + r["solution"] for r in train)
    for case in reserved + evaluation:
        if case["kind"] != "variation":
            continue
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(case["after"]) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, train_text):
            raise ValueError("Reserved evaluation binding occurs in candidate training text")


def prepare(output):
    if output.exists():
        raise FileExistsError("Candidate directory exists; choose a fresh path")
    phase2 = ROOT / "training/phase2"
    artifacts = ROOT / "training/artifacts"
    approved, digest = load_approved(phase2 / "drafts/p2-02-request-following-v3/candidate.jsonl",
                                   phase2 / "approvals/p2-02-request-following-v3.json")
    if digest != CANDIDATE_SHA:
        raise ValueError("Approved source differs from pinned v3")
    dev_path = phase2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != "e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4":
        raise ValueError("Development settings changed")
    development = json.loads(dev_path.read_text())
    reserved_path = artifacts / "diagnostics/p2-transfer-v1/cases.json"
    if sha256_file(reserved_path) != "c70af62e3f954066a24dae36c613b6efb51a2a34580326d0d9400afff53e88a3":
        raise ValueError("Reserved transfer cases changed")
    reserved = json.loads(reserved_path.read_text())["cases"]
    # Original controls deliberately overlap approved training; reserve the twelve changes only.
    reserved = [r for r in reserved if r["kind"] == "variation"]
    train, evaluation = build(approved)
    node = shutil.which("node")
    if node is None:
        raise ValueError("Installed Node is required for syntax-only validation")
    validate(train, evaluation, approved, reserved, development, node)
    from plex_training.tokenizer import PlexTokenizer
    bundle = artifacts / "tokenizers/p2-request-following-v3"
    tokenizer = PlexTokenizer.load(bundle)
    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prefix = tokenizer.encode(prompt_text(row, development["outputContracts"]))
        whole = tokenizer.encode(source_text(row, development["outputContracts"]))
        answer = len(whole) - len(prefix) + 1
        if (whole[:len(prefix)] != prefix or len(whole) + 1 > 512 or
                answer > development["inferenceDefaults"]["maxNewTokens"][row["language"]]):
            raise ValueError("Record or decoding budget exceeded")
        maxima["prompt"] = max(maxima["prompt"], len(prefix))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(whole) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], answer)
    output.mkdir(parents=True, exist_ok=False)
    def write_rows(filename, records):
        path = output / filename
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
        return sha256_file(path)
    candidate_sha = write_rows("candidate.jsonl", train)
    evaluation_sha = write_rows("evaluation-only.jsonl", evaluation)
    report = {"schemaVersion": 1, "candidate": "p2-03-binding-diversity-v1",
              "approvalStatus": "pending-owner-review", "sourceCandidateSha256": digest,
              "candidateJsonlSha256": candidate_sha, "evaluationJsonlSha256": evaluation_sha,
              "trainingCandidateRecords": 24, "originalRecords": 6, "newTrainingVariations": 18,
              "evaluationOnlyRecords": 12, "referencesPassed": 36, "staleAnswersRejected": 30,
              "trainingLanguageCounts": dict(Counter(r["language"] for r in train)),
              "evaluationLanguageCounts": dict(Counter(r["language"] for r in evaluation)),
              "tokenizerSha256": sha256_file(bundle / "tokenizer.json"), "tokenMaxima": maxima,
              "reusesExistingTrainingFittedTokenizer": True, "modelTrained": False,
              "externalSourceTextIncluded": False, "javascriptBehaviorExecuted": False,
              "finalHoldoutOpened": False, "productionDatasetCatalogCreated": False}
    (output / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sections = ["# Exact binding-diversity candidate\n\nStatus: pending owner review. "
                "24 proposed training examples: six approved originals plus eighteen new variations. "
                "Twelve separate same-family bindings are evaluation-only. No model was trained.\n",
                "## Proposed training examples\n"]
    for row in train:
        sections.append(f"### {row['id']}\n\nRequest: {row['request']}\n\n```{row['language']}\n{row['solution']}\n```\n")
    sections.append("## Evaluation-only examples\n\nThese requests/references will not enter training or tokenizer data.\n")
    for row in evaluation:
        sections.append(f"### {row['id']}\n\nRequest: {row['request']}\n\n```{row['language']}\n{row['solution']}\n```\n")
    sections.append(f"## Identities\n\nCandidate SHA-256: `{candidate_sha}`\n\nEvaluation SHA-256: `{evaluation_sha}`\n")
    (output / "REVIEW.md").write_text("\n".join(sections), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
