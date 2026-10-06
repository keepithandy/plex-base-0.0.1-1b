"""Prepare the owner-approved P2-21 reference-binding experiment without training it."""
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

from plex_training.benchmark import render_task_prompt
from plex_training.dataset import build_dataset
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.record_sampling import CompleteRecordTokenCorpus
from plex_training.tokenizer import PlexTokenizer, sha256_file, train_tokenizer

from verify_p2_21_semantic_role_candidate import (
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

EXPERIMENT = "p2-21-semantic-role-generalization-approved-v1"
ARTIFACT_ROOT = ROOT / "training" / "artifacts"
PHASE2 = ROOT / "training" / "phase2"
APPROVAL = PHASE2 / "approvals/p2-21-semantic-role-generalization-candidate-v1.json"

MODEL_SEED = 1337
DATASET_VALIDATION_PERCENT = 50
EXPECTED_PARAMETERS = 27_566_080
TRAIN_GROUP = "p2-21-train"
EVALUATION_GROUP = "p2-21-evaluation"
RIGHTS_REVIEWED_AT_UTC = "2026-10-06T00:00:00+00:00"


def _split_seed() -> int:
    for seed in range(10_000):
        ranked = sorted(
            (TRAIN_GROUP, EVALUATION_GROUP),
            key=lambda group: hashlib.sha256(
                f"{seed}\0{group}".encode("utf-8")
            ).digest(),
        )
        if ranked[0] == EVALUATION_GROUP:
            return seed
    raise RuntimeError("could not choose deterministic P2-21 dataset split seed")


DATASET_SPLIT_SEED = _split_seed()


def _canonical_text_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _canonical_sha(path: Path) -> str:
    return hashlib.sha256(_canonical_text_bytes(path)).hexdigest()


def _load_rows(path: Path = CANDIDATE) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def p2_21_prompt(row: dict[str, Any]) -> str:
    return (
        "Classify the requested semantic edit role.\n"
        f"Request: {row['request']}\n"
        "Output contract: Return only the requested output in the exact requested format.\n"
        "Return code only. Do not include Markdown fences or explanations."
    )


def p2_21_source(row: dict[str, Any]) -> str:
    return p2_21_prompt(row) + "\n" + row["solution"]


def _verify_approval() -> dict[str, Any]:
    verify_candidate()
    if _canonical_sha(CANDIDATE) != CANDIDATE_SHA256:
        raise ValueError("P2-21 candidate identity differs from the owner-approved SHA-256")
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    expected = {
        "schemaVersion": 1,
        "candidate": "p2-21-semantic-role-generalization-candidate-v1",
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "records": 216,
        "trainingRecords": 144,
        "evaluationRecords": 72,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training",
        "freshInitialization": True,
        "seed": MODEL_SEED,
        "tokenizerFitSplit": "train-only",
        "evaluationTextUsedForTokenizerFit": False,
        "evaluationUsedForGradientTraining": False,
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
        raise ValueError(
            "P2-21 owner approval differs from the exact authorized candidate or run policy"
        )
    owner_message = approval.get("ownerMessage")
    if not isinstance(owner_message, str) or CANDIDATE_SHA256 not in owner_message:
        raise ValueError("P2-21 owner approval does not retain the exact authorizing message")
    return approval


def _validation_group_for_seed() -> str:
    ranked = sorted(
        (TRAIN_GROUP, EVALUATION_GROUP),
        key=lambda group: hashlib.sha256(
            f"{DATASET_SPLIT_SEED}\0{group}".encode("utf-8")
        ).digest(),
    )
    if ranked[0] != EVALUATION_GROUP:
        raise ValueError("Pinned P2-21 dataset split no longer selects only evaluation")
    return ranked[0]


def _write_source_material(root: Path, rows: list[dict[str, Any]]) -> Path:
    _validation_group_for_seed()
    train_dir = root / "train"
    evaluation_dir = root / "evaluation"
    train_dir.mkdir(parents=True)
    evaluation_dir.mkdir(parents=True)
    notice = (
        "Plex P2-21 original local semantic-role-generalization curriculum.\n"
        "Authored locally for this repository; no external source text is included.\n"
        f"Candidate SHA-256: {CANDIDATE_SHA256}\n"
    )
    (train_dir / "NOTICE.md").write_text(notice, encoding="utf-8", newline="\n")
    (evaluation_dir / "NOTICE.md").write_text(
        notice, encoding="utf-8", newline="\n"
    )
    for row in rows:
        destination = train_dir if row["candidateSplit"] == "train" else evaluation_dir
        (destination / f"{row['id']}.txt").write_text(
            p2_21_source(row),
            encoding="utf-8",
            newline="\n",
        )
    catalog = {
        "schemaVersion": 1,
        "splitStrategy": "source-groups-v1",
        "sources": [
            {
                "id": "p2-21-train",
                "localPath": "train",
                "origin": "local://plex/p2-21-semantic-role-generalization-candidate-v1/train",
                "revision": CANDIDATE_SHA256,
                "licenseId": "Plex-Original-Local",
                "licenseEvidence": "NOTICE.md",
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": RIGHTS_REVIEWED_AT_UTC,
                "groupId": TRAIN_GROUP,
                "includeExtensions": [".txt"],
            },
            {
                "id": "p2-21-evaluation",
                "localPath": "evaluation",
                "origin": "local://plex/p2-21-semantic-role-generalization-candidate-v1/evaluation",
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
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _verify_dataset(dataset: Path, candidate_rows: list[dict[str, Any]]) -> None:
    train = _load_jsonl(dataset / "train.jsonl")
    validation = _load_jsonl(dataset / "validation.jsonl")
    if len(train) != 144 or len(validation) != 72:
        raise ValueError("Prepared P2-21 dataset is not the approved 144/72 partition")
    expected = {row["id"]: row for row in candidate_rows}
    seen: set[str] = set()
    for split_name, records in (("train", train), ("evaluation", validation)):
        for record in records:
            candidate_id = Path(record["path"]).stem
            row = expected.get(candidate_id)
            if row is None or candidate_id in seen:
                raise ValueError(
                    "Prepared P2-21 dataset has an unknown or duplicate candidate row"
                )
            if row["candidateSplit"] != split_name:
                raise ValueError(
                    f"Prepared P2-21 row crossed its approved split: {candidate_id}"
                )
            if record["text"] != p2_21_source(row):
                raise ValueError(
                    f"Prepared P2-21 text differs from approved candidate: {candidate_id}"
                )
            seen.add(candidate_id)
    if seen != set(expected):
        raise ValueError("Prepared P2-21 dataset omitted approved candidate rows")


def _verify_budgets(
    tokenizer: PlexTokenizer, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    css_settings = json.loads(P2_14.read_text(encoding="utf-8"))
    generation_limit = css_settings["inferenceDefaults"]["maxNewTokens"]["css"]
    maximum_prompt = maximum_record = maximum_answer = 0
    records = []
    for row in rows:
        prompt_ids = tokenizer.encode(p2_21_prompt(row))
        whole_ids = tokenizer.encode(p2_21_source(row))
        if whole_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(f"P2-21 prompt is not an exact token prefix: {row['id']}")
        record_tokens = len(whole_ids) + 1
        answer_tokens = len(whole_ids) - len(prompt_ids) + 1
        if record_tokens > 512:
            raise ValueError(f"P2-21 record exceeds the 512-token context: {row['id']}")
        if answer_tokens > generation_limit:
            raise ValueError(f"P2-21 answer exceeds the generation budget: {row['id']}")
        maximum_prompt = max(maximum_prompt, len(prompt_ids))
        maximum_record = max(maximum_record, record_tokens)
        maximum_answer = max(maximum_answer, answer_tokens)
        records.append({
            "id": row["id"],
            "candidateSplit": row["candidateSplit"],
            "evaluationTier": row["evaluationTier"],
            "level": row["level"],
            "taskKind": row["taskKind"],
            "promptTokens": len(prompt_ids),
            "recordTokensIncludingEos": record_tokens,
            "answerTokensIncludingEos": answer_tokens,
        })
    return {
        "maximumPromptTokens": maximum_prompt,
        "maximumRecordTokensIncludingEos": maximum_record,
        "maximumAnswerTokensIncludingEos": maximum_answer,
        "generationLimit": generation_limit,
        "records": records,
    }


def _verify_complete_record_compatibility(
    output: Path, bundle: dict[str, Any]
) -> dict[str, Any]:
    tokenizer = PlexTokenizer.load(output / "tokenizer")
    with CompleteRecordTokenCorpus(
        bundle["trainPath"],
        dataset_jsonl=output / "dataset/train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as corpus:
        record = corpus.sampler_record
        if (
            record.get("kind") != "complete-record-v1"
            or record.get("records") != 144
            or record.get("trainJsonlSha256")
            != bundle["dataset"]["trainJsonlSha256"]
        ):
            raise ValueError("P2-21 complete-record sampler preflight changed")
        return {
            "kind": record["kind"],
            "records": record["records"],
            "trainJsonlSha256": record["trainJsonlSha256"],
            "indexSha256": record["indexSha256"],
        }


def _verify_development_budgets(tokenizer: PlexTokenizer) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, path in (("P2-14", P2_14), ("P2-01b", P2_01B)):
        task_set = json.loads(path.read_text(encoding="utf-8"))
        maximum = 0
        records = []
        for task in task_set["tasks"]:
            prompt = render_task_prompt(task_set, task)
            count = len(tokenizer.encode(prompt))
            if count >= 512:
                raise ValueError(
                    f"{label} prompt exceeds the 512-token context: {task['id']}"
                )
            maximum = max(maximum, count)
            records.append({"id": task["id"], "promptTokens": count})
        result[label] = {"maximumPromptTokens": maximum, "records": records}
    return result


def prepare(output: Path) -> dict[str, Any]:
    approval = _verify_approval()
    candidate_rows = _load_rows()
    if len(candidate_rows) != 216:
        raise ValueError("P2-21 approved candidate must contain 216 rows")
    if (
        _canonical_sha(P2_14) != P2_14_SHA256
        or _canonical_sha(P2_01B) != P2_01B_SHA256
    ):
        raise ValueError("P2-21 development-set identities changed")

    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError(
            "Prepared P2-21 experiment exists; choose a fresh output directory"
        )
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
        if (
            bundle["dataset"]["trainRecords"] != 144
            or bundle["dataset"]["validationRecords"] != 72
        ):
            raise ValueError("P2-21 tokenizer bundle split counts changed")
        tokenizer_settings = json.loads(
            (output / "tokenizer/tokenizer-config.json").read_text(encoding="utf-8")
        )
        if (
            tokenizer_settings.get("fitSplit") != "train"
            or tokenizer_settings.get("trainingJsonlSha256")
            != bundle["dataset"]["trainJsonlSha256"]
        ):
            raise ValueError("P2-21 tokenizer was not fitted on training rows only")

        tokenizer = PlexTokenizer.load(output / "tokenizer")
        budgets = _verify_budgets(tokenizer, candidate_rows)
        budgets["development"] = _verify_development_budgets(tokenizer)
        sampler_preflight = _verify_complete_record_compatibility(output, bundle)
        initialization = initialize_model(
            output / "tokenizer",
            output / "initialization",
            seed=MODEL_SEED,
            artifact_root=ARTIFACT_ROOT,
        )
        if initialization["parameterCount"] != EXPECTED_PARAMETERS:
            raise ValueError("P2-21 initialization changed the approved architecture")

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
            "trainingRecords": 144,
            "evaluationRecords": 72,
            "trainingLevelCounts": {"A":48,"B":48,"C":48},
            "evaluationTierCounts": {"A":24,"B":24,"C":24},
            "datasetSplitSeed": DATASET_SPLIT_SEED,
            "datasetValidationPercent": DATASET_VALIDATION_PERCENT,
            "tokenizerFitSplit": "train",
            "tokenizerValidationTextUsedForFit": False,
            "evaluationUsedForGradientTraining": False,
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
            "completeRecordSamplerPreflight": sampler_preflight,
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
    plan = json.loads(
        (prepared / "experiment.json").read_text(encoding="utf-8")
    )
    fixed = {
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "candidateJsonlSha256": CANDIDATE_SHA256,
        "trainingRowsSha256": TRAIN_SHA256,
        "tierSha256": TIER_SHA256,
        "trainingRecords": 144,
        "evaluationRecords": 72,
        "trainingLevelCounts": {"A":48,"B":48,"C":48},
        "evaluationTierCounts": {"A":24,"B":24,"C":24},
        "datasetSplitSeed": DATASET_SPLIT_SEED,
        "datasetValidationPercent": DATASET_VALIDATION_PERCENT,
        "tokenizerFitSplit": "train",
        "tokenizerValidationTextUsedForFit": False,
        "evaluationUsedForGradientTraining": False,
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
        raise ValueError("Prepared P2-21 plan differs from the approved experiment")
    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-21 file changed: {relative}")

    candidate_rows = _load_rows(prepared / "approved/candidate.jsonl")
    _verify_dataset(prepared / "dataset", candidate_rows)
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    sampler_preflight = _verify_complete_record_compatibility(prepared, bundle)
    if plan.get("completeRecordSamplerPreflight") != sampler_preflight:
        raise ValueError("Prepared P2-21 complete-record sampler preflight changed")
    if (
        bundle["tokenizer"]["tokenizerSha256"] != plan["tokenizerSha256"]
        or bundle["tokenizer"]["actualVocabularySize"] != plan["actualVocabularySize"]
        or bundle["dataset"]["trainRecords"] != 144
        or bundle["dataset"]["validationRecords"] != 72
    ):
        raise ValueError("Prepared P2-21 tokenizer identity changed")
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
        raise ValueError("Prepared P2-21 initialization changed")
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_prepared(args.output) if args.verify_only else prepare(args.output)
        print(json.dumps(
            {
                key: value
                for key, value in result.items()
                if key not in {"files", "tokenBudgets"}
            },
            indent=2,
            sort_keys=True,
        ))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-21-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
