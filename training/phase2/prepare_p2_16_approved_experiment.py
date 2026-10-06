"""Prepare the owner-approved P2-16 CSS generalization experiment without training it."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.dataset import build_dataset
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.tokenizer import PlexTokenizer, sha256_file, train_tokenizer

from verify_p2_16_css_generalization_candidate import (
    CANDIDATE,
    CANDIDATE_SHA256,
    P2_01B,
    P2_01B_SHA256,
    P2_14,
    P2_14_SHA256,
    TIER_SHA256,
    TRAIN_SHA256,
    verify as verify_candidate,
)

EXPERIMENT = "p2-16-css-generalization-approved-v1"
ARTIFACT_ROOT = ROOT / "training" / "artifacts"
PHASE2 = ROOT / "training" / "phase2"
APPROVAL = PHASE2 / "approvals/p2-16-css-generalization-candidate-v1.json"

MODEL_SEED = 1337
DATASET_SPLIT_SEED = 1337
DATASET_VALIDATION_PERCENT = 50
EXPECTED_PARAMETERS = 27_566_080
TRAIN_GROUP = "p2-16-train"
EVALUATION_GROUP = "p2-16-evaluation"
P2_16_OUTPUT_CONTRACT = (
    "Return CSS rules only. Do not include HTML, Markdown fences, or explanations."
)
RIGHTS_REVIEWED_AT_UTC = "2026-10-06T01:36:57Z"


def _canonical_text_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _canonical_sha(path: Path) -> str:
    return hashlib.sha256(_canonical_text_bytes(path)).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_rows(path: Path = CANDIDATE) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def p2_16_prompt(row: dict[str, Any]) -> str:
    return (
        "Write a small CSS coding solution.\n"
        f"Request: {row['request']}\n"
        f"Output contract: {P2_16_OUTPUT_CONTRACT}\n"
        "Return code only. Do not include Markdown fences or explanations."
    )


def p2_16_source(row: dict[str, Any]) -> str:
    return p2_16_prompt(row) + "\n" + row["solution"]


def _verify_approval() -> dict[str, Any]:
    verify_candidate()
    if _canonical_sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-16 candidate identity differs from the owner-approved SHA-256")
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    expected = {
        "schemaVersion": 1,
        "candidate": "p2-16-css-generalization-candidate-v1",
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "records": 180,
        "trainingRecords": 120,
        "evaluationRecords": 60,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training",
        "freshInitialization": True,
        "seed": MODEL_SEED,
        "tokenizerFitSplit": "train-only",
        "unchangedArchitecture": True,
        "expectedParameterCount": EXPECTED_PARAMETERS,
        "lossObjective": "ordinary-next-token-over-complete-records",
        "samplingPolicy": "complete-record-v1",
        "microBatch": 1,
        "gradientAccumulation": 16,
        "device": "cuda",
        "matchedStepZeroEvaluation": True,
        "maxUpdates": 100,
        "maxDurationMinutes": 10,
        "automaticExtension": False,
        "p214ExcludedFromTraining": True,
        "p201bExcludedFromTraining": True,
        "finalHoldoutOpened": False,
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-16 owner approval differs from the exact authorized candidate or run policy")
    owner_message = approval.get("ownerMessage")
    if not isinstance(owner_message, str) or CANDIDATE_SHA256 not in owner_message:
        raise ValueError("P2-16 owner approval does not retain the exact authorizing message")
    return approval


def _validation_group_for_seed() -> str:
    groups = {TRAIN_GROUP, EVALUATION_GROUP}
    ranked = sorted(
        groups,
        key=lambda group: hashlib.sha256(
            f"{DATASET_SPLIT_SEED}\0{group}".encode("utf-8")
        ).digest(),
    )
    validation_count = min(
        len(groups) - 1,
        max(1, (len(groups) * DATASET_VALIDATION_PERCENT + 50) // 100),
    )
    selected = ranked[:validation_count]
    if selected != [EVALUATION_GROUP]:
        raise ValueError("Pinned P2-16 dataset split no longer selects only the evaluation group")
    return selected[0]


def _write_source_material(root: Path, rows: list[dict[str, Any]]) -> Path:
    _validation_group_for_seed()
    train_dir = root / "train"
    evaluation_dir = root / "evaluation"
    train_dir.mkdir(parents=True)
    evaluation_dir.mkdir(parents=True)
    notice = (
        "Plex P2-16 original local curriculum.\n"
        "Authored locally for this repository; no external source text is included.\n"
        f"Candidate SHA-256: {CANDIDATE_SHA256}\n"
    )
    (train_dir / "NOTICE.md").write_text(notice, encoding="utf-8", newline="\n")
    (evaluation_dir / "NOTICE.md").write_text(notice, encoding="utf-8", newline="\n")
    for row in rows:
        destination = train_dir if row["candidateSplit"] == "train" else evaluation_dir
        (destination / f"{row['id']}.txt").write_text(
            p2_16_source(row),
            encoding="utf-8",
            newline="\n",
        )
    catalog = {
        "schemaVersion": 1,
        "splitStrategy": "source-groups-v1",
        "sources": [
            {
                "id": "p2-16-train",
                "localPath": "train",
                "origin": "local://plex/p2-16-css-generalization-candidate-v1/train",
                "revision": CANDIDATE_SHA256,
                "licenseId": "Plex-Original-Local",
                "licenseEvidence": "NOTICE.md",
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": RIGHTS_REVIEWED_AT_UTC,
                "groupId": TRAIN_GROUP,
                "includeExtensions": [".txt"],
            },
            {
                "id": "p2-16-evaluation",
                "localPath": "evaluation",
                "origin": "local://plex/p2-16-css-generalization-candidate-v1/evaluation",
                "revision": CANDIDATE_SHA256,
                "licenseId": "Plex-Original-Local",
                "licenseEvidence": "NOTICE.md",
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": RIGHTS_REVIEWED_AT_UTC,
                "groupId": EVALUATION_GROUP,
                "includeExtensions": [".txt"],
            },
        ],
    }
    catalog_path = root / "dataset-sources.approved.json"
    catalog_path.write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return catalog_path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _verify_dataset(dataset: Path, candidate_rows: list[dict[str, Any]]) -> None:
    train = _load_jsonl(dataset / "train.jsonl")
    validation = _load_jsonl(dataset / "validation.jsonl")
    if len(train) != 120 or len(validation) != 60:
        raise ValueError("Prepared P2-16 dataset is not the approved 120/60 partition")
    expected = {row["id"]: row for row in candidate_rows}
    seen: set[str] = set()
    for split_name, rows in (("train", train), ("evaluation", validation)):
        for record in rows:
            candidate_id = Path(record["path"]).stem
            row = expected.get(candidate_id)
            if row is None or candidate_id in seen:
                raise ValueError("Prepared P2-16 dataset has an unknown or duplicate candidate row")
            if row["candidateSplit"] != split_name:
                raise ValueError(f"Prepared P2-16 row crossed its approved split: {candidate_id}")
            if record["text"] != p2_16_source(row):
                raise ValueError(f"Prepared P2-16 text differs from approved candidate: {candidate_id}")
            seen.add(candidate_id)
    if seen != set(expected):
        raise ValueError("Prepared P2-16 dataset omitted approved candidate rows")


def _verify_budgets(tokenizer: PlexTokenizer, rows: list[dict[str, Any]]) -> dict[str, Any]:
    task_settings = json.loads(P2_14.read_text(encoding="utf-8"))
    css_limit = task_settings["inferenceDefaults"]["maxNewTokens"]["css"]
    maximum_prompt = maximum_record = maximum_answer = 0
    records = []
    for row in rows:
        prompt_ids = tokenizer.encode(p2_16_prompt(row))
        whole_ids = tokenizer.encode(p2_16_source(row))
        if whole_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(f"P2-16 prompt is not an exact token prefix: {row['id']}")
        record_tokens = len(whole_ids) + 1
        answer_tokens = len(whole_ids) - len(prompt_ids) + 1
        if record_tokens > 512:
            raise ValueError(f"P2-16 record exceeds the 512-token context: {row['id']}")
        if answer_tokens > css_limit:
            raise ValueError(f"P2-16 answer exceeds the CSS generation budget: {row['id']}")
        maximum_prompt = max(maximum_prompt, len(prompt_ids))
        maximum_record = max(maximum_record, record_tokens)
        maximum_answer = max(maximum_answer, answer_tokens)
        records.append({
            "id": row["id"],
            "candidateSplit": row["candidateSplit"],
            "evaluationTier": row["evaluationTier"],
            "promptTokens": len(prompt_ids),
            "recordTokensIncludingEos": record_tokens,
            "answerTokensIncludingEos": answer_tokens,
        })
    return {
        "maximumPromptTokens": maximum_prompt,
        "maximumRecordTokensIncludingEos": maximum_record,
        "maximumAnswerTokensIncludingEos": maximum_answer,
        "cssGenerationLimit": css_limit,
        "records": records,
    }


def prepare(output: Path) -> dict[str, Any]:
    approval = _verify_approval()
    candidate_rows = _load_rows()
    if len(candidate_rows) != 180:
        raise ValueError("P2-16 approved candidate must contain 180 rows")
    if _canonical_sha(P2_14) != P2_14_SHA256 or _canonical_sha(P2_01B) != P2_01B_SHA256:
        raise ValueError("P2-16 development-set identities changed")

    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-16 experiment exists; choose a fresh output directory")
    output.mkdir(parents=True, exist_ok=False)
    try:
        approved = output / "approved"
        scoring = output / "scoring"
        approved.mkdir()
        scoring.mkdir()
        shutil.copyfile(APPROVAL, approved / "approval.json")
        shutil.copyfile(CANDIDATE, approved / "candidate.jsonl")
        shutil.copyfile(P2_14, scoring / "p2-14-task-set.json")
        shutil.copyfile(P2_01B, scoring / "p2-01b-dev-v1.json")

        source_root = output / "source-material"
        catalog = _write_source_material(source_root, candidate_rows)
        build_dataset(
            catalog,
            output / "dataset",
            validation_percent=DATASET_VALIDATION_PERCENT,
            seed=DATASET_SPLIT_SEED,
            storage_limit_bytes=200 * 1024**3,
        )
        _verify_dataset(output / "dataset", candidate_rows)

        tokenizer_result = train_tokenizer(
            output / "dataset",
            output / "tokenizer",
            vocab_size=16_384,
            min_frequency=2,
        )
        bundle = inspect_pilot_bundle(output / "tokenizer")
        if bundle["dataset"]["trainRecords"] != 120 or bundle["dataset"]["validationRecords"] != 60:
            raise ValueError("P2-16 tokenizer bundle split counts changed")
        tokenizer_settings = json.loads(
            (output / "tokenizer/tokenizer-config.json").read_text(encoding="utf-8")
        )
        if (
            tokenizer_settings.get("fitSplit") != "train"
            or tokenizer_settings.get("trainingJsonlSha256")
            != bundle["dataset"]["trainJsonlSha256"]
        ):
            raise ValueError("P2-16 tokenizer was not fitted on training rows only")

        budgets = _verify_budgets(PlexTokenizer.load(output / "tokenizer"), candidate_rows)
        initialization = initialize_model(
            output / "tokenizer",
            output / "initialization",
            seed=MODEL_SEED,
            artifact_root=ARTIFACT_ROOT,
        )
        if initialization["parameterCount"] != EXPECTED_PARAMETERS:
            raise ValueError("P2-16 initialization changed the approved model architecture")

        files = {
            path.relative_to(output).as_posix(): sha256_file(path)
            for path in output.rglob("*")
            if path.is_file()
        }
        plan = {
            "schemaVersion": 1,
            "experiment": EXPERIMENT,
            "approvalStatus": "approved",
            "candidateJsonlSha256": CANDIDATE_SHA256,
            "trainingRowsSha256": TRAIN_SHA256,
            "tierSha256": TIER_SHA256,
            "trainingRecords": 120,
            "evaluationRecords": 60,
            "evaluationTierCounts": {"A": 24, "B": 12, "C": 12, "D": 12},
            "datasetSplitSeed": DATASET_SPLIT_SEED,
            "datasetValidationPercent": DATASET_VALIDATION_PERCENT,
            "tokenizerFitSplit": "train",
            "tokenizerValidationTextUsedForFit": False,
            "tokenizerSha256": tokenizer_result["tokenizerSha256"],
            "actualVocabularySize": tokenizer_result["actualVocabularySize"],
            "freshModelFromScratch": True,
            "seed": MODEL_SEED,
            "parameterCount": initialization["parameterCount"],
            "matchedStepZeroEvaluation": True,
            "maximumSteps": approval["maxUpdates"],
            "maximumMinutes": approval["maxDurationMinutes"],
            "microBatch": approval["microBatch"],
            "gradientAccumulation": approval["gradientAccumulation"],
            "samplingPolicy": approval["samplingPolicy"],
            "lossObjective": approval["lossObjective"],
            "automaticExtension": False,
            "initializationCheckpointSha256": initialization["checkpointSha256"],
            "initialModelWeightsSha256": initialization["initialModelWeightsSha256"],
            "tokenBudgets": budgets,
            "p214DevelopmentTaskSetSha256": _canonical_sha(P2_14),
            "p201bDevelopmentTaskSetSha256": _canonical_sha(P2_01B),
            "p214ExcludedFromTraining": True,
            "p201bExcludedFromTraining": True,
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


def verify_prepared(prepared: Path) -> dict[str, Any]:
    _verify_approval()
    prepared = prepared.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))
    fixed = {
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "trainingRecords": 120,
        "evaluationRecords": 60,
        "evaluationTierCounts": {"A": 24, "B": 12, "C": 12, "D": 12},
        "datasetSplitSeed": DATASET_SPLIT_SEED,
        "datasetValidationPercent": DATASET_VALIDATION_PERCENT,
        "tokenizerFitSplit": "train",
        "tokenizerValidationTextUsedForFit": False,
        "freshModelFromScratch": True,
        "seed": MODEL_SEED,
        "parameterCount": EXPECTED_PARAMETERS,
        "matchedStepZeroEvaluation": True,
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "samplingPolicy": "complete-record-v1",
        "lossObjective": "ordinary-next-token-over-complete-records",
        "automaticExtension": False,
        "p214ExcludedFromTraining": True,
        "p201bExcludedFromTraining": True,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ValueError("Prepared P2-16 plan differs from the approved experiment")
    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-16 file changed: {relative}")

    candidate_rows = _load_rows(prepared / "approved/candidate.jsonl")
    _verify_dataset(prepared / "dataset", candidate_rows)
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    if (
        bundle["tokenizer"]["tokenizerSha256"] != plan["tokenizerSha256"]
        or bundle["tokenizer"]["actualVocabularySize"] != plan["actualVocabularySize"]
        or bundle["dataset"]["trainRecords"] != 120
        or bundle["dataset"]["validationRecords"] != 60
    ):
        raise ValueError("Prepared P2-16 tokenizer identity changed")
    init = json.loads(
        (prepared / "initialization/initialization.json").read_text(encoding="utf-8")
    )
    if (
        init.get("seed") != MODEL_SEED
        or init.get("parameterCount") != EXPECTED_PARAMETERS
        or init.get("pretrainedCheckpointLoaded") is not False
        or init.get("pretrainedModelWeightsLoaded") is not False
        or sha256_file(prepared / "initialization/initialization.pt")
        != plan["initializationCheckpointSha256"]
    ):
        raise ValueError("Prepared P2-16 initialization changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_prepared(args.output) if args.verify_only else prepare(args.output)
        print(json.dumps(
            {key: value for key, value in result.items() if key not in {"files", "tokenBudgets"}},
            indent=2,
            sort_keys=True,
        ))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-16-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
