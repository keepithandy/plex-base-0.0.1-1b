"""Read-only approved-corpus/transfer audit; optional report writes into a fresh file."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from diagnose_transfer import ROOT, CANDIDATE_SHA, build_cases, sha256_file, summarize
from diagnose_saved_checkpoints import load_approved
from prepare_code_pair_candidate import source_text


def function_shape(solution):
    match = re.search(r"function\s+(\w+)\s*\(", solution)
    if match is None:
        raise ValueError("Expected a named function in approved JavaScript reference")
    shape = re.sub(r"function\s+\w+\s*\(", "function NAME(", solution, count=1)
    return match[1], re.sub(r"\s+", " ", shape).strip()


def selector_shape(solution):
    selector, body = solution.split("{", 1)
    names = re.findall(r"\.[\w-]+", selector)
    shape = re.sub(r"\.[\w-]+", ".SELECTOR", selector) + "{" + body
    return names, re.sub(r"\s+", " ", shape).strip()


def audit():
    phase2 = ROOT / "training/phase2"
    artifacts = ROOT / "training/artifacts"
    candidate = phase2 / "drafts/p2-02-request-following-v3/candidate.jsonl"
    rows, digest = load_approved(candidate, phase2 / "approvals/p2-02-request-following-v3.json")
    if digest != CANDIDATE_SHA:
        raise ValueError("Audit requires pinned approved candidate")
    train = [r for r in rows if r["candidateSplit"] == "train"]
    validation = [r for r in rows if r["candidateSplit"] == "validation"]
    dataset = artifacts / "datasets/p2-request-following-v3"
    if sha256_file(dataset / "manifest.json") != "bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea":
        raise ValueError("Built corpus manifest differs from the recorded v3 dataset")
    contracts = json.loads((phase2 / "evaluation/p2-01b-dev-v1.json").read_text())["outputContracts"]
    actual_files = {}
    for split, expected in (("train", train), ("validation", validation)):
        path = dataset / (split + ".jsonl")
        actual = [json.loads(line) for line in path.read_text().splitlines()]
        # Compare the full rendered text, not just the candidate's split labels.
        if Counter(r["text"] for r in actual) != Counter(source_text(r, contracts) for r in expected):
            raise ValueError("Built corpus text differs from approved candidate rendering")
        actual_files[split] = {"records": len(actual), "sha256": sha256_file(path)}
    by_group = defaultdict(list)
    for row in train:
        by_group[row["splitGroupId"]].append(row)
    overlap = set(by_group) & {r["splitGroupId"] for r in validation}
    if overlap:
        raise ValueError("Unexpected split group overlap")
    names, js_shapes, selectors, css_shapes = set(), defaultdict(list), set(), defaultdict(list)
    for row in train:
        if row["language"] == "javascript":
            name, shape = function_shape(row["solution"])
            names.add(name)
            js_shapes[shape].append({"id": row["id"], "name": name})
        elif row["language"] == "css":
            selected, shape = selector_shape(row["solution"])
            selectors.update(selected)
            css_shapes[shape].append(row["id"])
    plan_path = artifacts / "diagnostics/p2-transfer-v1/cases.json"
    report_path = artifacts / "diagnostics/p2-transfer-v1/report.json"
    plan = json.loads(plan_path.read_text())
    transfer = json.loads(report_path.read_text())
    if plan["cases"] != build_cases(rows) or transfer["casesSha256"] != sha256_file(plan_path):
        raise ValueError("Transfer cases or identity do not match the frozen diagnostic")
    expected_hashes = {100: "0737e617facc7ae9d8e3f1c9c6888cdcc066183d40a711f231933161de7e4e2e",
                       200: "348423a1dcb58639c1384216b67318144658d33e4e37ae48f76a121c851a692b"}
    if {r["step"] for r in transfer["checkpoints"]} != set(expected_hashes):
        raise ValueError("Unexpected transfer checkpoints")
    for checkpoint in transfer["checkpoints"]:
        if (checkpoint["checkpointSha256"] != expected_hashes[checkpoint["step"]]
                or checkpoint["groups"] != summarize(checkpoint["records"])
                or [r["id"] for r in checkpoint["records"]] != [r["id"] for r in plan["cases"]]):
            raise ValueError("Transfer aggregate counts or checkpoint identity differ")
    sources = {row["id"]: row for row in rows}
    bindings = []
    for case in plan["cases"]:
        if case["kind"] != "variation":
            continue
        source = sources[case["sourceId"]]
        pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(case["after"]) + r"(?![A-Za-z0-9_])")
        contains = lambda r: bool(pattern.search(r["request"] + "\n" + r["solution"]))
        bindings.append({"id": case["id"], "group": source["splitGroupId"],
                         "before": case["before"], "after": case["after"],
                         "newDetailInTrainRecords": sum(contains(r) for r in train),
                         "newDetailInSameGroupRecords": sum(contains(r) for r in by_group[source["splitGroupId"]]),
                         "newDetailInValidationRecords": sum(contains(r) for r in validation)})
    selected_groups = sorted({r["group"] for r in bindings})
    group_details = [{"group": group, "records": len(by_group[group]),
                      "requests": [{"id": r["id"], "request": r["request"], "solution": r["solution"]}
                                   for r in by_group[group]]} for group in selected_groups]
    return {"schemaVersion": 1, "kind": "approved-training-binding-variation-audit",
            "candidateSha256": digest, "transferCasesSha256": sha256_file(plan_path),
            "transferReportSha256": sha256_file(report_path),
            "actualCorpusVerified": actual_files, "datasetManifestSha256": sha256_file(dataset / "manifest.json"),
            "counts": dict(sorted(Counter(r["candidateSplit"] + "/" + r["language"] for r in rows).items())),
            "trainGroups": len(by_group), "validationGroups": len({r["splitGroupId"] for r in validation}),
            "splitGroupOverlap": sorted(overlap),
            "javascript": {"uniqueFunctionNames": len(names), "nameMaskedShapes": len(js_shapes),
                           "multipleNamesForIdenticalShape": [items for items in js_shapes.values() if len(items)>1]},
            "css": {"uniqueClassSelectorNames": len(selectors), "selectorMaskedShapes": len(css_shapes),
                    "multipleRecordsForIdenticalShape": [items for items in css_shapes.values() if len(items)>1]},
            "bindings": bindings, "selectedTrainingGroups": group_details,
            "transfer": [{"step": r["step"], "groups": r["groups"]} for r in transfer["checkpoints"]],
            "limits": "Masked signatures preserve the remaining reference source after whitespace collapse; they are not semantic-equivalence proofs. Detail occurrence uses lexical boundaries, not operation relevance. No training or model execution."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(args.report), **{k: report[k] for k in
                     ("counts", "trainGroups", "validationGroups", "javascript", "css", "bindings")}}, indent=2))
