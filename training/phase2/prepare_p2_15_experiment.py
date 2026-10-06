"""Prepare the exact owner-approved P2-15 CSS edit experiment; never train."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.config import DEFAULT_CONFIG
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.tokenizer import PlexTokenizer, sha256_file, train_tokenizer

from prepare_code_pair_candidate import prompt_text, source_text
from prepare_p2_15_css_edit_candidate import (
    CANDIDATE_JSONL_SHA256,
    INPUT,
    P2_14_TASK_SET_SHA256,
    PHASE2,
)
from verify_p2_15_css_edit_candidate import verify as verify_candidate

EXPERIMENT = "p2-15-css-edit-candidate-v1"
OBJECTIVE = "answer-eos-only-complete-record-v1"
APPROVAL = PHASE2 / "approvals/p2-15-css-edit-candidate-v1.json"
TASK_SET = PHASE2 / "drafts/p2-14-css-edit-step200-v1/task-set.json"
ARTIFACT_ROOT = ROOT / "training" / "artifacts"

TRAIN_SHA = "db29a222896c732fc0b7b43452d6100c281065a99ee22c911f184e458554d19c"
VALIDATION_SHA = "d49333860bb73d1e941588e070d9cda24bc4d17f75fd9c7546b1d7bbdc2e5cd8"
NOTICE_TEXT = (
    "P2-15 local diagnostic data. Original repository-owner-approved Plex examples; "
    "no external source text is included. Authorized for this bounded local training "
    "diagnostic only. This notice is not training text.\n"
)


def _canonical_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _rows() -> list[dict]:
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines()]
    if len(rows) != 36 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("P2-15 candidate rows are incomplete")
    return rows


def _split_sha(rows: list[dict], split: str) -> str:
    raw = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True)
        for row in rows
        if row["candidateSplit"] == split
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _limits() -> dict:
    return {
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "maximumTotalSteps": 100,
        "maximumTotalMinutes": 10,
        "seed": 1337,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "automaticExtension": False,
    }


def _tokenizer_policy() -> dict:
    return {
        "fitSplit": "train",
        "validationTextUsedForFit": False,
        "algorithm": "plex-byte-bpe-v1",
        "requestedVocabularySize": 16384,
        "minFrequency": 2,
    }


def _load_approval(rows: list[dict]) -> dict:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8-sig"))
    expected = {
        "candidate": EXPERIMENT,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-diagnostic-training",
        "objective": OBJECTIVE,
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "trainingRowsSha256": TRAIN_SHA,
        "validationRowsSha256": VALIDATION_SHA,
        "developmentTaskSetSha256": P2_14_TASK_SET_SHA256,
        "trainingRecords": 24,
        "validationRecords": 12,
        "semanticGroups": 12,
        "validationApprovedForTraining": False,
        "validationApprovedForRuntimeValidationLoss": True,
        "tokenizerPolicy": _tokenizer_policy(),
        "freshModelFromScratch": True,
        "matchedStepZeroEvaluation": True,
        "finalHoldoutOpened": False,
        "limits": _limits(),
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-15 approval does not match the exact candidate and bounded run")
    if _split_sha(rows, "train") != TRAIN_SHA or _split_sha(rows, "validation") != VALIDATION_SHA:
        raise ValueError("P2-15 split rows no longer match the approved hashes")
    return approval


def _write_jsonl(path: Path, values: list[dict]) -> str:
    raw = (
        "\n".join(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for value in values
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _build_dataset(output: Path, rows: list[dict], contracts: dict[str, str]) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    license_dir = output / "licenses"
    license_dir.mkdir()
    notice_path = license_dir / "p2-15-local.txt"
    notice_path.write_text(NOTICE_TEXT, encoding="utf-8", newline="\n")
    notice_sha = sha256_file(notice_path)

    groups = sorted({row["splitGroupId"] for row in rows})
    sources = [
        {
            "id": f"p2-15-source-{group}",
            "groupId": group,
            "rightsReviewStatus": "approved",
            "licenseNoticeFile": "licenses/p2-15-local.txt",
            "licenseNoticeSha256": notice_sha,
        }
        for group in groups
    ]
    source_by_group = {source["groupId"]: source["id"] for source in sources}

    split_records: dict[str, list[dict]] = {"train": [], "validation": []}
    for row in rows:
        text = source_text(row, contracts)
        split_records[row["candidateSplit"]].append(
            {
                "recordId": row["id"],
                "sourceId": source_by_group[row["splitGroupId"]],
                "groupId": row["splitGroupId"],
                "contentSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text": text,
            }
        )

    train_sha = _write_jsonl(output / "train.jsonl", split_records["train"])
    validation_sha = _write_jsonl(output / "validation.jsonl", split_records["validation"])
    manifest = {
        "schemaVersion": 1,
        "pipelineVersion": "p1-14.2",
        "recordFormat": "jsonl; exact approved P2-15 request-to-code record per row",
        "normalization": "canonical LF UTF-8 generated from hash-pinned candidate rows",
        "split": {
            "method": "owner-approved-explicit-semantic-family-split-v1",
            "trainGroups": 8,
            "validationGroups": 4,
        },
        "sources": sources,
        "summary": {
            "records": 36,
            "trainRecords": 24,
            "validationRecords": 12,
            "trainJsonlSha256": train_sha,
            "validationJsonlSha256": validation_sha,
            "jsonlBytes": (output / "train.jsonl").stat().st_size
            + (output / "validation.jsonl").stat().st_size,
            "licenseNoticeBytes": notice_path.stat().st_size,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _token_budgets(
    tokenizer: PlexTokenizer, rows: list[dict], settings: dict
) -> dict:
    contracts = settings["outputContracts"]
    css_limit = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    maximum_prompt = maximum_record = maximum_answer = 0
    records = []
    for row in rows:
        prompt_ids = tokenizer.encode(prompt_text(row, contracts))
        whole_ids = tokenizer.encode(source_text(row, contracts))
        if whole_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(f"P2-15 prompt is not a token-prefix of its training record: {row['id']}")
        answer_tokens = len(whole_ids) - len(prompt_ids) + 1
        record_tokens = len(whole_ids) + 1
        if record_tokens > DEFAULT_CONFIG.context_length:
            raise ValueError(f"P2-15 record exceeds 512-token context: {row['id']}")
        if answer_tokens > css_limit:
            raise ValueError(f"P2-15 answer exceeds CSS generation budget: {row['id']}")
        maximum_prompt = max(maximum_prompt, len(prompt_ids))
        maximum_record = max(maximum_record, record_tokens)
        maximum_answer = max(maximum_answer, answer_tokens)
        records.append(
            {
                "id": row["id"],
                "split": row["candidateSplit"],
                "promptTokens": len(prompt_ids),
                "recordTokensIncludingEos": record_tokens,
                "answerTokensIncludingEos": answer_tokens,
            }
        )
    return {
        "maximumPromptTokens": maximum_prompt,
        "maximumRecordTokensIncludingEos": maximum_record,
        "maximumAnswerTokensIncludingEos": maximum_answer,
        "cssGenerationLimit": css_limit,
        "contextLength": DEFAULT_CONFIG.context_length,
        "records": records,
    }


def prepare(output: Path) -> dict:
    verify_candidate()
    rows = _rows()
    approval = _load_approval(rows)
    if _canonical_sha256(INPUT) != CANDIDATE_JSONL_SHA256:
        raise ValueError("P2-15 candidate JSONL changed after approval")
    if _canonical_sha256(TASK_SET) != P2_14_TASK_SET_SHA256:
        raise ValueError("P2-14 scoring settings changed after P2-15 approval")

    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-15 experiment already exists; choose a fresh directory")
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "approved").mkdir()
        shutil.copyfile(APPROVAL, output / "approved/approval.json")
        shutil.copyfile(INPUT, output / "approved/candidate.jsonl")
        (output / "scoring").mkdir()
        shutil.copyfile(TASK_SET, output / "scoring/p2-14-task-set.json")

        settings = json.loads(TASK_SET.read_text(encoding="utf-8"))
        dataset_manifest = _build_dataset(output / "dataset", rows, settings["outputContracts"])
        tokenizer_result = train_tokenizer(
            output / "dataset",
            output / "tokenizer",
            vocab_size=approval["tokenizerPolicy"]["requestedVocabularySize"],
            min_frequency=approval["tokenizerPolicy"]["minFrequency"],
        )
        tokenizer = PlexTokenizer.load(output / "tokenizer")
        budgets = _token_budgets(tokenizer, rows, settings)
        initialization = initialize_model(
            output / "tokenizer",
            output / "initialization",
            seed=approval["limits"]["seed"],
            artifact_root=ARTIFACT_ROOT,
        )
        bundle = inspect_pilot_bundle(output / "tokenizer")
        if bundle["dataset"]["trainRecords"] != 24 or bundle["dataset"]["validationRecords"] != 12:
            raise ValueError("P2-15 tokenizer bundle split counts changed")
        if dataset_manifest["summary"]["trainJsonlSha256"] != bundle["dataset"]["trainJsonlSha256"]:
            raise ValueError("P2-15 tokenizer was not fitted from the prepared training dataset")

        files = {
            path.relative_to(output).as_posix(): sha256_file(path)
            for path in output.rglob("*")
            if path.is_file()
        }
        plan = {
            "schemaVersion": 1,
            "experiment": EXPERIMENT,
            "approvalStatus": "approved",
            "trainingObjective": OBJECTIVE,
            "samplingPolicy": "complete-record-v1",
            "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
            "trainingRowsSha256": TRAIN_SHA,
            "validationRowsSha256": VALIDATION_SHA,
            "approvalSha256": _canonical_sha256(APPROVAL),
            "developmentTaskSetSha256": P2_14_TASK_SET_SHA256,
            "trainingRecords": 24,
            "validationRecords": 12,
            "semanticGroups": 12,
            "validationUsedForTraining": False,
            "validationUsedForRuntimeValidationLoss": True,
            "tokenizerFitSplit": "train",
            "tokenizerValidationTextUsedForFit": False,
            "tokenizerSha256": tokenizer_result["tokenizerSha256"],
            "actualVocabularySize": tokenizer_result["actualVocabularySize"],
            "freshModelFromScratch": True,
            "seed": 1337,
            "matchedStepZeroEvaluation": True,
            "microBatch": 1,
            "gradientAccumulation": 16,
            "device": "cuda",
            "maximumSteps": 100,
            "maximumMinutes": 10,
            "maximumTotalSteps": 100,
            "maximumTotalMinutes": 10,
            "automaticExtension": False,
            "tokenBudgets": budgets,
            "initializationCheckpointSha256": initialization["checkpointSha256"],
            "initialModelWeightsSha256": initialization["initialModelWeightsSha256"],
            "modelTrained": False,
            "finalHoldoutOpened": False,
            "files": files,
        }
        (output / "experiment.json").write_text(
            json.dumps(plan, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return plan
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def verify_prepared(prepared: Path) -> dict:
    verify_candidate()
    rows = _rows()
    _load_approval(rows)
    prepared = prepared.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))

    fixed = {
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "trainingObjective": OBJECTIVE,
        "samplingPolicy": "complete-record-v1",
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "trainingRowsSha256": TRAIN_SHA,
        "validationRowsSha256": VALIDATION_SHA,
        "approvalSha256": _canonical_sha256(APPROVAL),
        "developmentTaskSetSha256": P2_14_TASK_SET_SHA256,
        "trainingRecords": 24,
        "validationRecords": 12,
        "semanticGroups": 12,
        "validationUsedForTraining": False,
        "validationUsedForRuntimeValidationLoss": True,
        "tokenizerFitSplit": "train",
        "tokenizerValidationTextUsedForFit": False,
        "freshModelFromScratch": True,
        "seed": 1337,
        "matchedStepZeroEvaluation": True,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "maximumTotalSteps": 100,
        "maximumTotalMinutes": 10,
        "automaticExtension": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ValueError("Prepared P2-15 plan differs from owner approval")

    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-15 file changed: {relative}")

    if _canonical_sha256(prepared / "approved/approval.json") != _canonical_sha256(APPROVAL):
        raise ValueError("Prepared P2-15 approval artifact changed")
    if _canonical_sha256(prepared / "approved/candidate.jsonl") != CANDIDATE_JSONL_SHA256:
        raise ValueError("Prepared P2-15 candidate changed")
    if _canonical_sha256(prepared / "scoring/p2-14-task-set.json") != P2_14_TASK_SET_SHA256:
        raise ValueError("Prepared P2-15 scoring settings changed")

    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    if (
        bundle["tokenizer"]["tokenizerSha256"] != plan["tokenizerSha256"]
        or bundle["tokenizer"]["actualVocabularySize"] != plan["actualVocabularySize"]
        or bundle["dataset"]["trainRecords"] != 24
        or bundle["dataset"]["validationRecords"] != 12
    ):
        raise ValueError("Prepared P2-15 tokenizer identity changed")
    settings = json.loads((prepared / "tokenizer/tokenizer-config.json").read_text(encoding="utf-8"))
    if (
        settings.get("fitSplit") != "train"
        or settings.get("trainingJsonlSha256") != bundle["dataset"]["trainJsonlSha256"]
        or settings.get("requestedVocabularySize") != 16384
        or settings.get("minFrequency") != 2
    ):
        raise ValueError("Prepared P2-15 tokenizer fit policy changed")

    init = json.loads((prepared / "initialization/initialization.json").read_text(encoding="utf-8"))
    if (
        init.get("seed") != 1337
        or init.get("pretrainedCheckpointLoaded") is not False
        or init.get("pretrainedModelWeightsLoaded") is not False
        or init.get("tokenizer", {}).get("tokenizerSha256") != plan["tokenizerSha256"]
        or sha256_file(prepared / "initialization/initialization.pt")
        != plan["initializationCheckpointSha256"]
    ):
        raise ValueError("Prepared P2-15 step-zero initialization changed")

    task_settings = json.loads((prepared / "scoring/p2-14-task-set.json").read_text(encoding="utf-8"))
    budgets = _token_budgets(PlexTokenizer.load(prepared / "tokenizer"), rows, task_settings)
    if budgets != plan["tokenBudgets"]:
        raise ValueError("Prepared P2-15 token budgets changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_prepared(args.output) if args.verify_only else prepare(args.output)
        print(
            json.dumps(
                {key: value for key, value in result.items() if key not in {"files", "tokenBudgets"}},
                indent=2,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-15-experiment-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
