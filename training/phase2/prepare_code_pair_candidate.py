"""Validate and materialize an unapproved, original request-to-code candidate.

No training, downloads, generated-code execution, or approval changes occur here.
JavaScript solutions are parsed with Node --check only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "training" / "src"))
from plex_training.benchmark import _check_task, render_task_prompt, validate_task_set
from plex_training.dataset import _family_stratified_group_split

PHASE2 = REPO_ROOT / "training" / "phase2"
INPUT = PHASE2 / "drafts" / "p2-02-code-pairs-v2.jsonl"
DEV_SET = PHASE2 / "evaluation" / "p2-01b-dev-v1.json"
OUTPUT = PHASE2 / "drafts" / "p2-02-code-pairs-v2"
LANGUAGES = ("html", "css", "javascript")
PROVENANCE = "codex-authored-local-training-candidate"
PENDING = "pending-owner-review"
SAFE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_records(path: Path = INPUT) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
        raise ValueError("Candidate must be a regular JSONL file of at most 1 MiB")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Candidate lines must contain JSON objects")
    return rows


def prompt_text(row: dict[str, Any], contracts: dict[str, str]) -> str:
    """Byte-for-byte v1 format; validated against the real development renderer."""
    language = {"html": "HTML", "css": "CSS", "javascript": "JavaScript"}[row["language"]]
    return (
        f"Write a small {language} coding solution.\n"
        f"Request: {row['request']}\n"
        f"Output contract: {row.get('contract', contracts[row['language']])}\n"
        "Return code only. Do not include Markdown fences or explanations."
    )


def source_text(row: dict[str, Any], contracts: dict[str, str]) -> str:
    # The unchanged inference prefix predicts the newline, then the code answer.
    # tokenizer-train appends the real EOS id 3; never put its spelling in text.
    return prompt_text(row, contracts) + "\n" + row["solution"]


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold()))


def validate_records(rows: list[dict[str, Any]], task_set: dict[str, Any]) -> dict[str, Any]:
    task_set = validate_task_set(task_set)
    if task_set["kind"] != "development":
        raise ValueError("Candidate review must not open a final holdout")
    contracts = task_set["outputContracts"]
    if any(prompt_text(task, contracts) != render_task_prompt(task_set, task)
           for task in task_set["tasks"]):
        raise ValueError("Candidate prompt format drifted from plex-coding-task-v1")
    if len(rows) != 36 or Counter(row.get("language") for row in rows) != {
        language: 12 for language in LANGUAGES
    }:
        raise ValueError("Candidate requires exactly twelve examples per language")

    ids: set[str] = set()
    requests: set[str] = set()
    solutions: set[str] = set()
    groups: dict[str, set[str]] = {}
    dev_requests = {_normalized(task["request"]) for task in task_set["tasks"]}
    highest_overlap = 0.0
    checks_passed = checks_total = 0
    for row in rows:
        identifier, group, language = row.get("id"), row.get("splitGroupId"), row["language"]
        if (row.get("schemaVersion") != 1 or not isinstance(identifier, str)
                or not SAFE_NAME.fullmatch(identifier) or identifier in ids
                or not isinstance(group, str) or not SAFE_NAME.fullmatch(group)
                or not group.startswith(language + "-")):
            raise ValueError("Candidate has an invalid/duplicate identifier or group")
        family = f"plex-code-pairs-{language}-v2"
        if (row.get("sourceFamilyId") != family or row.get("provenance") != PROVENANCE
                or row.get("approvalStatus") != PENDING):
            raise ValueError("Candidate provenance must remain pending owner review")
        request, solution = row.get("request"), row.get("solution")
        if any(not isinstance(text, str) or not text.strip() or "```" in text
               or "<|" in text or len(text.encode("utf-8")) > 2_000
               for text in (request, solution)):
            raise ValueError(f"{identifier} needs bounded plain request and code text")
        if not isinstance(row.get("checks"), list) or not row["checks"]:
            raise ValueError(f"{identifier} needs static solution checks")
        if not isinstance(row.get("behaviorReviewCases"), list):
            raise ValueError(f"{identifier} needs explicit behavior-review notes")
        request_key, solution_key = _normalized(request), _normalized(solution)
        if request_key in requests or request_key in dev_requests or solution_key in solutions:
            raise ValueError("Exact normalized candidate/development duplicates are not allowed")
        for task in task_set["tasks"]:
            if task["language"] != language:
                continue
            a, b = _words(request), _words(task["request"])
            overlap = len(a & b) / len(a | b)
            highest_overlap = max(highest_overlap, overlap)
            if overlap >= 0.70:
                raise ValueError(f"{identifier} needs review for development-request overlap")
        ids.add(identifier)
        requests.add(request_key)
        solutions.add(solution_key)
        groups.setdefault(family, set()).add(group)
        result = _check_task({"id": identifier, "language": language, "difficulty": "basic", "checks": row["checks"]},
                             solution, None, 5.0)
        if not result["passed"]:
            raise ValueError(f"Static solution review failed for {identifier}: {result}")
        checks_passed += result["checksPassed"]
        checks_total += result["checksTotal"]

    if any(len(value) != 6 for value in groups.values()):
        raise ValueError("Each language must have six semantic groups")
    counts = Counter((row["sourceFamilyId"], row["splitGroupId"]) for row in rows)
    if any(value != 2 for value in counts.values()):
        raise ValueError("Each semantic group must contain two related variants")
    validation = _family_stratified_group_split(groups, 30, 51)
    split_counts: Counter[str] = Counter()
    code_bytes: Counter[str] = Counter()
    total_bytes: Counter[str] = Counter()
    language_splits: Counter[str] = Counter()
    for row in rows:
        split = "validation" if (row["sourceFamilyId"], row["splitGroupId"]) in validation else "train"
        if row.get("candidateSplit") != split:
            raise ValueError("Candidate split disagrees with the existing seed-51 group algorithm")
        split_counts[split] += 1
        language_splits[f"{split}/{row['language']}"] += 1
        code_bytes[split] += len(row["solution"].encode("utf-8"))
        total_bytes[split] += len(source_text(row, contracts).encode("utf-8"))
    return {
        "schemaVersion": 1, "candidate": "p2-02-code-pairs-v2", "approvalStatus": PENDING,
        "records": len(rows), "splitSeed": 51, "validationPercentOfGroups": 30,
        "recordsBySplit": dict(split_counts), "recordsBySplitAndLanguage": dict(language_splits),
        "staticSolutionsPassed": len(rows), "staticChecksPassed": checks_passed,
        "staticChecksTotal": checks_total, "javascriptBehaviorExecuted": False,
        "exactRequestDuplicatesWithDevelopment": 0,
        "highestDevelopmentRequestWordJaccard": round(highest_overlap, 6),
        "semanticLeakageNotProvenAbsent": True, "finalHoldoutOpened": False,
        "promptTemplateVersion": "plex-coding-task-v1", "promptRendererParityChecked": True,
        "codeAnswerBytesBySplit": dict(code_bytes), "serializedTextBytesBySplit": dict(total_bytes),
        "modelTrained": False, "externalSourceTextIncluded": False,
    }


def reference_tokenizer_review(rows: list[dict[str, Any]], task_set: dict[str, Any], directory: Path) -> dict[str, Any]:
    from plex_training.tokenizer import PlexTokenizer, sha256_file
    tokenizer = PlexTokenizer.load(directory)
    contracts = task_set["outputContracts"]
    max_prompt = max_record = 0
    answer_maxima = {language: 0 for language in LANGUAGES}
    for row in rows:
        prefix = tokenizer.encode(prompt_text(row, contracts))
        whole = tokenizer.encode(source_text(row, contracts))
        if whole[:len(prefix)] != prefix:
            raise ValueError("Tokenized inference prefix is not an exact training-record prefix")
        max_prompt = max(max_prompt, len(prefix))
        max_record = max(max_record, len(whole) + 1)
        answer_maxima[row["language"]] = max(answer_maxima[row["language"]], len(whole) - len(prefix) + 1)
        if len(whole) + 1 > 512 or len(whole) - len(prefix) + 1 > task_set["inferenceDefaults"]["maxNewTokens"][row["language"]]:
            raise ValueError(f"Reference token budget exceeded for {row['id']}")
    return {
        "referenceTokenizerOnly": True, "tokenizerSha256": sha256_file(directory / "tokenizer.json"),
        "maximumPromptTokens": max_prompt, "maximumRecordTokensIncludingEos": max_record,
        "maximumAnswerTokensIncludingEosByLanguage": answer_maxima,
        "newCandidateTokenizerMustBeFittedOnTrainingOnlyAfterApproval": True,
    }


def review_markdown(rows: list[dict[str, Any]], report: dict[str, Any], contracts: dict[str, str]) -> str:
    sections = [
        "# P2-02 request-to-code candidate v2\n",
        "**Status: draft for owner review; not approved for training.**\n",
        "This original, Codex-authored set contains 36 request/answer pairs: 12 each for HTML, CSS, and JavaScript. "
        "Two related variants stay in each semantic group. Seed 51 selects whole groups: 24 training records and "
        "12 validation records (8/4 per language). No external source text was copied.\n",
        "## Why a separate candidate\n",
        "The v3 training split was 76.3% Markdown, with its six authored examples supplying 0.7% of token positions. "
        "The ten-minute model passed 0/30 development tasks and emitted Markdown/Mermaid text. This candidate isolates "
        "request-to-code formatting; it is deliberately tiny and cannot establish broad coding ability. "
        "It is proposed as a separate diagnostic corpus, not appended to the existing tutorial corpus.\n",
        "## Exact training format\n",
        "Every source `.txt` file is the unchanged `plex-coding-task-v1` prompt, one newline, and a code-only answer. "
        "There are no Markdown headings, fences, review checks, or behavior notes in training text. "
        "The existing tokenizer pipeline appends EOS id 3 after each record; the literal marker is never source text. "
        "The existing causal objective trains on both prompt and answer tokens; answer-only loss masking is not introduced.\n",
        "```text\n" + source_text(rows[0], contracts) + "\n```\n",
        "## Review and verification\n",
        f"All {report['staticSolutionsPassed']} authored solutions passed {report['staticChecksPassed']}/{report['staticChecksTotal']} "
        "static checks. HTML structure and declared attributes/text were checked; CSS uses the evaluator's flat-rule parser. "
        "JavaScript was syntax-checked with Node `--check`, never executed. The listed behavior cases are review expectations, "
        "not measured behavioral results. These checks validate supplied examples, not Plex outputs.\n",
        "Exact normalized requests were checked against the 30 development prompts. A request-word Jaccard screen "
        f"had maximum overlap {report['highestDevelopmentRequestWordJaccard']}; it is a heuristic, not proof against semantic leakage. "
        "The semantic families below differ from the development tasks; broad language skills necessarily overlap. "
        "No final holdout was opened. Variants are grouped so parameter changes never create train/validation leakage.\n",
        "The candidate catalog keeps `rightsReviewStatus: pending-owner-review`, so the production dataset builder refuses it. "
        "Owner approval is still needed for these exact records because the agreed next step was to review new examples before use. "
        "The previous nine-record approval covers only that earlier set. Approval would authorize local P2 training, "
        "not assert an external license or approve a public release.\n",
        "## Proposed experiment after review\n",
        "1. Approve or revise these exact examples and their whole-group split.\n"
        "2. Build a separate corpus and fit a fresh tokenizer on its training split only. Record token mix and verify "
        "prompt/answer/EOS budgets with that new tokenizer before training. Preserve v3 artifacts.\n"
        "3. Initialize fresh random Plex weights, seed 1337, and score the same 30 development tasks at step zero.\n"
        "4. Run a ten-minute CUDA check with the existing model and training settings; score the same tasks again. "
        "Compare complete-task passes, syntax, fences, EOS/truncation, held-out loss, and resource use separately.\n"
        "5. A two-hour run is a later decision based on those results; this draft schedules no training. "
        "Keep the $0 paid-service and 200 GiB limits. Qwen weights are never initialization weights.\n",
        "This is not yet the 70–80% code base-corpus target: serialized prompts occupy part of each record. "
        "Code-answer and total text bytes are recorded in `review.json`; a code-token share must be measured "
        "with the candidate's own training-fitted tokenizer after approval.\n",
        "## All examples\n",
    ]
    for language in LANGUAGES:
        sections.append(f"### {language.upper() if language != 'javascript' else 'JavaScript'}\n")
        for row in rows:
            if row["language"] != language:
                continue
            sections.append(f"#### {row['id']} — {row['candidateSplit']}\n\n"
                            f"Group: `{row['splitGroupId']}`\n\n{row['request']}\n\n"
                            f"```{language}\n{row['solution']}\n```\n")
            if row["behaviorReviewCases"]:
                sections.append("Review cases (not executed): `" + json.dumps(row["behaviorReviewCases"]) + "`\n")
    return "\n".join(sections)


def prepare(rows: list[dict[str, Any]], task_set: dict[str, Any], report: dict[str, Any], output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Candidate preview already exists; choose a fresh path")
    output.parent.mkdir(parents=True, exist_ok=True)
    # mkdir inherits parent permissions on Windows; avoid tempfile's private ACL.
    staging = output.parent / (".plex-code-pairs-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        sources = []
        for language in LANGUAGES:
            root = staging / "sources" / language
            root.mkdir(parents=True)
            (root / "NOTICE.md").write_text(
                "# Draft data provenance\n\nOriginal Codex-authored examples prepared for Plex owner review. "
                "No external source text is included. Pending owner approval for local P2 training; "
                "no public license grant is asserted. This notice is excluded from training text.\n",
                encoding="utf-8", newline="\n",
            )
            language_rows = [row for row in rows if row["language"] == language]
            groups = sorted({row["splitGroupId"] for row in language_rows})
            sources.append({
                "id": f"plex-code-pairs-{language}-v2", "groupId": f"plex-code-pairs-{language}-v2",
                "sourceFamilyId": f"plex-code-pairs-{language}-v2", "localPath": f"sources/{language}",
                "origin": "urn:plex:codex-authored:p2-02-code-pairs-v2", "revision": report["candidateJsonlSha256"],
                "licenseId": "Local-use-review-pending", "licenseEvidence": "NOTICE.md",
                "rightsReviewStatus": PENDING, "rightsReviewedAtUtc": None, "includeExtensions": [".txt"],
                "splitGroupRules": [{"id": group, "pathPrefixes": [group + "/"]} for group in groups],
            })
            for row in language_rows:
                path = root / row["splitGroupId"] / (row["id"] + ".txt")
                path.parent.mkdir(exist_ok=True)
                path.write_text(source_text(row, task_set["outputContracts"]), encoding="utf-8", newline="\n")
        for name, content in {
            "dataset-sources.candidate.json": {"schemaVersion": 1, "splitStrategy": "family-stratified-groups-v1", "sources": sources},
            "review.json": report,
        }.items():
            (staging / name).write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (staging / "REVIEW.md").write_text(review_markdown(rows, report, task_set["outputContracts"]), encoding="utf-8", newline="\n")
        os.rename(staging, output)
    except Exception:
        if staging.exists() and staging.resolve().parent == output.parent and staging.name.startswith(".plex-code-pairs-"):
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-dir", type=Path, help="New directory for review-only sources and pending catalog")
    parser.add_argument("--tokenizer-dir", type=Path, help="Optional existing tokenizer for reference-only budget checks")
    args = parser.parse_args()
    try:
        rows = load_records()
        task_set = json.loads(DEV_SET.read_text(encoding="utf-8"))
        report = validate_records(rows, task_set)
        report["candidateJsonlSha256"] = _digest(INPUT.read_bytes())
        report["developmentTaskSetSha256"] = _digest(DEV_SET.read_bytes())
        if args.tokenizer_dir:
            report["referenceTokenizerReview"] = reference_tokenizer_review(rows, task_set, args.tokenizer_dir)
        if args.prepare_dir:
            prepare(rows, task_set, report, args.prepare_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"prepare-code-pairs: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
