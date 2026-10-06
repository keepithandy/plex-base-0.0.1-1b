"""Prepare P2-15 from the promoted owner-approved CSS data without changing its split."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.dataset import build_dataset
from plex_training.initialization import initialize_model
from plex_training.pilot import inspect_pilot_bundle
from plex_training.tokenizer import PlexTokenizer, sha256_file, train_tokenizer

from prepare_p2_15_css_edit_candidate import (
    CANDIDATE_JSONL_SHA256,
    INPUT,
    P2_14_TASK_SET_SHA256,
    PHASE2,
    rows as candidate_rows,
)

EXPERIMENT = "p2-15-promoted-css-edit-v1"
ARTIFACT_ROOT = ROOT / "training" / "artifacts"
APPROVAL = PHASE2 / "approvals/p2-15-css-edit-candidate-v1.json"
PROMOTED = PHASE2 / "data/authored/p2-15-css-edit-v1"
SOURCE_MANIFEST = PROMOTED / "dataset-sources.approved.json"
P2_14_TASK_SET = PHASE2 / "drafts/p2-14-css-edit-step200-v1/task-set.json"
P2_01B_TASK_SET = PHASE2 / "evaluation/p2-01b-dev-v1.json"

# The generic source-group splitter needs one deterministic seed. Seed 299 is
# pinned here because, at 30%, the repository's grouped SHA-256 splitter
# reproduces the already-approved semantic partition exactly: 8 training
# families and the 4 validation-only families.
DATASET_SPLIT_SEED = 299
VALIDATION_PERCENT = 30
MODEL_SEED = 1337
EXPECTED_VALIDATION_GROUPS = {
    "css-list-style",
    "css-white-space",
    "css-aspect-ratio",
    "css-outline",
}
P2_15_OUTPUT_CONTRACT = "Return CSS rules only. Do not include HTML, Markdown fences, or explanations."


def p2_15_prompt(row: dict) -> str:
    return (
        f"Write a small CSS coding solution.\n"
        f"Request: {row['request']}\n"
        f"Output contract: {P2_15_OUTPUT_CONTRACT}\n"
        "Return code only. Do not include Markdown fences or explanations."
    )


def p2_15_source(row: dict) -> str:
    return p2_15_prompt(row) + "\n" + row["solution"]


EXPECTED_TRAIN_GROUPS = {
    "css-button-radius",
    "css-callout-border",
    "css-nav-justify",
    "css-card-shadow",
    "css-label-font-style",
    "css-thumbnail-width",
    "css-badge-transform",
    "css-menu-opacity",
}


def _validation_groups_for_seed(groups: set[str], seed: int) -> set[str]:
    ranked = sorted(
        groups,
        key=lambda group: hashlib.sha256(f"{seed}\0{group}".encode("utf-8")).digest(),
    )
    count = min(
        len(groups) - 1,
        max(1, (len(groups) * VALIDATION_PERCENT + 50) // 100),
    )
    return set(ranked[:count])


def _verify_split_seed() -> None:
    all_groups = EXPECTED_TRAIN_GROUPS | EXPECTED_VALIDATION_GROUPS
    selected = _validation_groups_for_seed(all_groups, DATASET_SPLIT_SEED)
    if selected != EXPECTED_VALIDATION_GROUPS:
        raise ValueError(
            "Pinned P2-15 dataset split seed no longer reproduces the approved validation families"
        )


def _canonical_sha(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _verify_owner_approval() -> dict:
    approval = json.loads(APPROVAL.read_text(encoding="utf-8-sig"))
    expected = {
        "schemaVersion": 1,
        "candidate": "p2-15-css-edit-candidate-v1",
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "records": 36,
        "approvalStatus": "approved",
        "approvedBy": "repository-owner",
        "scope": "local-P2-training",
        "maxUpdates": 100,
        "maxDurationMinutes": 10,
        "freshInitialization": True,
        "seed": MODEL_SEED,
        "matchedStepZeroEvaluation": True,
        "finalHoldoutOpened": False,
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise ValueError("P2-15 owner approval no longer matches the exact promoted candidate and bounds")
    if not isinstance(approval.get("ownerMessage"), str) or "continue" not in approval["ownerMessage"].casefold():
        raise ValueError("P2-15 approval no longer retains the owner's authorizing message")
    if hashlib.sha256(INPUT.read_bytes()).hexdigest() != CANDIDATE_JSONL_SHA256:
        raise ValueError("P2-15 candidate JSONL changed after approval")
    if _canonical_sha(P2_14_TASK_SET) != P2_14_TASK_SET_SHA256:
        raise ValueError("P2-14 development task set changed")
    return approval


def _expected_promoted_text(row: dict) -> bytes:
    return p2_15_source(row).encode("utf-8")


def _verify_promoted_sources() -> None:
    promoted_approval = json.loads((PROMOTED / "approval.json").read_text(encoding="utf-8"))
    source_approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    if promoted_approval != source_approval:
        raise ValueError("Promoted P2-15 approval copy differs from the source approval")

    expected_files = set()
    for row in candidate_rows():
        path = PROMOTED / "sources" / row["splitGroupId"] / f"{row['id']}.txt"
        expected_files.add(path.resolve())
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing promoted P2-15 source: {row['id']}")
        candidate_path = (
            PHASE2 / "drafts/p2-15-css-edit-candidate-v1/records"
            / row["candidateSplit"] / row["splitGroupId"] / f"{row['id']}.txt"
        )
        if not candidate_path.is_file() or candidate_path.is_symlink():
            raise ValueError(f"Reviewed P2-15 candidate source is missing: {row['id']}")
        expected = _expected_promoted_text(row)
        if candidate_path.read_bytes() != expected:
            raise ValueError(f"Reviewed P2-15 candidate prompt format drifted: {row['id']}")
        if path.read_bytes() != candidate_path.read_bytes():
            raise ValueError(f"Promoted P2-15 source differs from the approved candidate: {row['id']}")

    actual_files = {
        path.resolve()
        for path in (PROMOTED / "sources").rglob("*.txt")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise ValueError("Promoted P2-15 source file set differs from the 36 approved examples")


def _groups(rows: list[dict]) -> set[str]:
    groups = set()
    for row in rows:
        group = row.get("groupId")
        if not isinstance(group, str):
            raise ValueError("Prepared P2-15 dataset row is missing its group")
        groups.add(group)
    return groups


def _verify_budgets(tokenizer: PlexTokenizer, settings: dict) -> dict:
    maximum_prompt = maximum_record = maximum_answer = 0
    records = []
    css_limit = settings["inferenceDefaults"]["maxNewTokens"]["css"]
    for row in candidate_rows():
        prompt_ids = tokenizer.encode(p2_15_prompt(row))
        whole_ids = tokenizer.encode(p2_15_source(row))
        if whole_ids[: len(prompt_ids)] != prompt_ids:
            raise ValueError(f"Prompt is not an exact token prefix for {row['id']}")
        record_tokens = len(whole_ids) + 1
        answer_tokens = len(whole_ids) - len(prompt_ids) + 1
        if record_tokens > 512:
            raise ValueError(f"P2-15 record exceeds the 512-token model context: {row['id']}")
        if answer_tokens > css_limit:
            raise ValueError(f"P2-15 answer exceeds the CSS generation budget: {row['id']}")
        maximum_prompt = max(maximum_prompt, len(prompt_ids))
        maximum_record = max(maximum_record, record_tokens)
        maximum_answer = max(maximum_answer, answer_tokens)
        records.append({
            "id": row["id"],
            "split": row["candidateSplit"],
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


def prepare(output: Path) -> dict:
    approval = _verify_owner_approval()
    _verify_split_seed()
    task_settings = json.loads(P2_14_TASK_SET.read_text(encoding="utf-8"))
    _verify_promoted_sources()

    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Prepared P2-15 experiment exists; choose a fresh output directory")
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "approved").mkdir()
        shutil.copyfile(APPROVAL, output / "approved/approval.json")
        shutil.copyfile(INPUT, output / "approved/candidate.jsonl")
        shutil.copyfile(SOURCE_MANIFEST, output / "approved/dataset-sources.approved.json")
        (output / "scoring").mkdir()
        shutil.copyfile(P2_14_TASK_SET, output / "scoring/p2-14-task-set.json")
        shutil.copyfile(P2_01B_TASK_SET, output / "scoring/p2-01b-dev-v1.json")

        build_dataset(
            SOURCE_MANIFEST,
            output / "dataset",
            validation_percent=VALIDATION_PERCENT,
            seed=DATASET_SPLIT_SEED,
            storage_limit_bytes=200 * 1024**3,
        )
        train_rows = _load_jsonl(output / "dataset/train.jsonl")
        validation_rows = _load_jsonl(output / "dataset/validation.jsonl")
        if len(train_rows) != 24 or len(validation_rows) != 12:
            raise ValueError("Prepared P2-15 dataset is not the approved 24/12 split")
        if _groups(train_rows) != EXPECTED_TRAIN_GROUPS:
            raise ValueError("Prepared P2-15 training families differ from the approved eight families")
        if _groups(validation_rows) != EXPECTED_VALIDATION_GROUPS:
            raise ValueError("Prepared P2-15 validation families differ from the approved four families")

        tokenizer_result = train_tokenizer(
            output / "dataset",
            output / "tokenizer",
            vocab_size=16_384,
            min_frequency=2,
        )
        bundle = inspect_pilot_bundle(output / "tokenizer")
        if bundle["dataset"]["trainRecords"] != 24 or bundle["dataset"]["validationRecords"] != 12:
            raise ValueError("P2-15 tokenizer bundle split counts changed")
        tokenizer_settings = json.loads(
            (output / "tokenizer/tokenizer-config.json").read_text(encoding="utf-8")
        )
        if (
            tokenizer_settings.get("fitSplit") != "train"
            or tokenizer_settings.get("trainingJsonlSha256") != bundle["dataset"]["trainJsonlSha256"]
        ):
            raise ValueError("P2-15 tokenizer was not fitted on the training split only")

        budgets = _verify_budgets(PlexTokenizer.load(output / "tokenizer"), task_settings)
        initialization = initialize_model(
            output / "tokenizer",
            output / "initialization",
            seed=MODEL_SEED,
            artifact_root=ARTIFACT_ROOT,
        )

        files = {
            path.relative_to(output).as_posix(): sha256_file(path)
            for path in output.rglob("*")
            if path.is_file()
        }
        plan = {
            "schemaVersion": 1,
            "experiment": EXPERIMENT,
            "approvalStatus": "approved",
            "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
            "approvalSha256": _canonical_sha(APPROVAL),
            "sourceCatalogSha256": sha256_file(SOURCE_MANIFEST),
            "trainingRecords": 24,
            "validationRecords": 12,
            "trainingGroups": sorted(EXPECTED_TRAIN_GROUPS),
            "validationGroups": sorted(EXPECTED_VALIDATION_GROUPS),
            "datasetSplitSeed": DATASET_SPLIT_SEED,
            "datasetValidationPercent": VALIDATION_PERCENT,
            "tokenizerFitSplit": "train",
            "tokenizerValidationTextUsedForFit": False,
            "tokenizerSha256": tokenizer_result["tokenizerSha256"],
            "actualVocabularySize": tokenizer_result["actualVocabularySize"],
            "freshModelFromScratch": True,
            "seed": MODEL_SEED,
            "matchedStepZeroEvaluation": True,
            "maximumSteps": approval["maxUpdates"],
            "maximumMinutes": approval["maxDurationMinutes"],
            "microBatch": 1,
            "gradientAccumulation": 16,
            "samplingPolicy": "complete-record-v1",
            "lossObjective": "ordinary-next-token-over-complete-records",
            "automaticExtension": False,
            "initializationCheckpointSha256": initialization["checkpointSha256"],
            "initialModelWeightsSha256": initialization["initialModelWeightsSha256"],
            "tokenBudgets": budgets,
            "p214DevelopmentTaskSetSha256": _canonical_sha(P2_14_TASK_SET),
            "p201bDevelopmentTaskSetSha256": _canonical_sha(P2_01B_TASK_SET),
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
    _verify_owner_approval()
    prepared = prepared.resolve()
    prepared.relative_to(ARTIFACT_ROOT.resolve())
    plan = json.loads((prepared / "experiment.json").read_text(encoding="utf-8"))

    fixed = {
        "experiment": EXPERIMENT,
        "approvalStatus": "approved",
        "candidateJsonlSha256": CANDIDATE_JSONL_SHA256,
        "approvalSha256": _canonical_sha(APPROVAL),
        "sourceCatalogSha256": sha256_file(SOURCE_MANIFEST),
        "trainingRecords": 24,
        "validationRecords": 12,
        "trainingGroups": sorted(EXPECTED_TRAIN_GROUPS),
        "validationGroups": sorted(EXPECTED_VALIDATION_GROUPS),
        "datasetSplitSeed": DATASET_SPLIT_SEED,
        "datasetValidationPercent": VALIDATION_PERCENT,
        "tokenizerFitSplit": "train",
        "tokenizerValidationTextUsedForFit": False,
        "freshModelFromScratch": True,
        "seed": MODEL_SEED,
        "matchedStepZeroEvaluation": True,
        "maximumSteps": 100,
        "maximumMinutes": 10,
        "microBatch": 1,
        "gradientAccumulation": 16,
        "samplingPolicy": "complete-record-v1",
        "lossObjective": "ordinary-next-token-over-complete-records",
        "automaticExtension": False,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ValueError("Prepared P2-15 plan differs from the approved experiment")

    for relative, digest in plan.get("files", {}).items():
        path = prepared / relative
        path.resolve().relative_to(prepared)
        if path.is_symlink() or not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"Prepared P2-15 file changed: {relative}")

    train_rows = _load_jsonl(prepared / "dataset/train.jsonl")
    validation_rows = _load_jsonl(prepared / "dataset/validation.jsonl")
    if _groups(train_rows) != EXPECTED_TRAIN_GROUPS or _groups(validation_rows) != EXPECTED_VALIDATION_GROUPS:
        raise ValueError("Prepared P2-15 semantic split changed")
    bundle = inspect_pilot_bundle(prepared / "tokenizer")
    if (
        bundle["tokenizer"]["tokenizerSha256"] != plan["tokenizerSha256"]
        or bundle["tokenizer"]["actualVocabularySize"] != plan["actualVocabularySize"]
        or bundle["dataset"]["trainRecords"] != 24
        or bundle["dataset"]["validationRecords"] != 12
    ):
        raise ValueError("Prepared P2-15 tokenizer identity changed")
    init = json.loads((prepared / "initialization/initialization.json").read_text(encoding="utf-8"))
    if (
        init.get("seed") != MODEL_SEED
        or init.get("pretrainedCheckpointLoaded") is not False
        or init.get("pretrainedModelWeightsLoaded") is not False
        or sha256_file(prepared / "initialization/initialization.pt")
        != plan["initializationCheckpointSha256"]
    ):
        raise ValueError("Prepared P2-15 initialization changed")
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
        print(f"plex-p2-15-promoted-prepare: {exc}", file=sys.stderr)
        raise SystemExit(2)
