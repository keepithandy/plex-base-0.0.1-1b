"""P2-48 request-grounded coding bundle preparation and zero-update sampler preflight."""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
from array import array
from pathlib import Path
from typing import Any

from .artifacts import path_within_root
from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .request_grounded_coding_curriculum import (
    EXPECTED_BUNDLE_SHA256,
    EXPECTED_CANDIDATE_BYTES,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    render_request_grounded_change_prompt,
    review_request_grounded_coding_curriculum,
)
from .structured_plan import canonical_text_sha256
from .structured_plan_semantic_binding_training import StructuredPlanCompleteRecordCorpus
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-48"
PIPELINE_VERSION = "p2-48-request-grounded-coding-bundle-v1"
CONTRACT_KIND = "plex-p2-48-final-phase2-transfer-preparation-contract-v1"

DEFAULT_PREPARATION_CONTRACT = Path(
    "training/pretraining/p2-48-final-transfer-preparation-contract.json"
)
DEFAULT_CANDIDATE = Path(
    "training/phase2/drafts/p2-47-request-grounded-coding-v1.jsonl"
)
DEFAULT_REVIEW = Path(
    "training/phase2/drafts/p2-47-request-grounded-coding-v1.review.json"
)
DEFAULT_DEVELOPMENT_TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
DEFAULT_SOURCE_BUNDLE = Path("training/artifacts/structured-plan/p2-44-training-bundle")
DEFAULT_OUTPUT_BUNDLE = Path("training/artifacts/request-grounded/p2-48-training-bundle")

TRAIN_RECORDS = 72
VALIDATION_RECORDS = 36
EXPECTED_MAX_RECORD_TOKENS = 286
EXPECTED_TRAIN_TOKEN_COUNT = 19377
EXPECTED_VALIDATION_TOKEN_COUNT = 9763

PROPOSED_SEED = 1337
PROPOSED_MAXIMUM_STEPS = 100
PROPOSED_MICRO_BATCH = 1
PROPOSED_GRADIENT_ACCUMULATION = 16
PROPOSED_EXAMPLES = (
    PROPOSED_MAXIMUM_STEPS * PROPOSED_MICRO_BATCH * PROPOSED_GRADIENT_ACCUMULATION
)


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _contract(path: Path) -> dict[str, Any]:
    value = _json(path)
    if (
        value.get("schemaVersion") != 1
        or value.get("milestone") != MILESTONE
        or value.get("kind") != CONTRACT_KIND
        or value.get("status") != "bundle-preparation-authorized"
        or value.get("dataPreparationAuthorized") is not True
        or value.get("checkpointStagingAuthorized") is not False
        or value.get("modelTrainingAuthorized") is not False
        or value.get("optimizerCreationAuthorized") is not False
        or value.get("automaticContinuation") is not False
        or value.get("trainingPerformed") is not False
        or value.get("researchOptimizerUpdates") != 0
        or value.get("finalHoldoutOpened") is not False
    ):
        raise ValueError("P2-48 preparation contract is invalid or no longer zero-update")

    candidate = value.get("candidate")
    if not isinstance(candidate, dict) or (
        candidate.get("id") != "p2-47-request-grounded-coding-v1"
        or candidate.get("sha256") != EXPECTED_CANDIDATE_SHA256
        or candidate.get("bytes") != EXPECTED_CANDIDATE_BYTES
        or candidate.get("reviewStatus") != "candidate-review-passed"
        or candidate.get("records") != TRAIN_RECORDS + VALIDATION_RECORDS
        or candidate.get("trainRecords") != TRAIN_RECORDS
        or candidate.get("validationRecords") != VALIDATION_RECORDS
        or candidate.get("maximumRecordTokensIncludingEos") != EXPECTED_MAX_RECORD_TOKENS
        or candidate.get("trainTokenCount") != EXPECTED_TRAIN_TOKEN_COUNT
        or candidate.get("validationTokenCount") != EXPECTED_VALIDATION_TOKEN_COUNT
    ):
        raise ValueError("P2-48 candidate contract identity changed")

    source = value.get("source")
    if not isinstance(source, dict) or (
        source.get("milestone") != "P2-44"
        or source.get("checkpointStep") != 100
        or source.get("checkpointSha256")
        != "69c357db13aae930374f013754a4b89c9bc071bd299c34cfa1c1ab362db0842e"
        or source.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or source.get("tokenizerBundleManifestSha256") != EXPECTED_BUNDLE_SHA256
    ):
        raise ValueError("P2-48 source identity changed")

    proposed = value.get("proposedRun")
    if not isinstance(proposed, dict) or proposed != {
        "seed": PROPOSED_SEED,
        "microBatch": PROPOSED_MICRO_BATCH,
        "gradientAccumulation": PROPOSED_GRADIENT_ACCUMULATION,
        "maximumSteps": PROPOSED_MAXIMUM_STEPS,
        "maximumWallTimeSeconds": 600,
        "examplesAt100Steps": PROPOSED_EXAMPLES,
        "validationSteps": [0, 25, 50, 75, 100],
        "checkpointSteps": [25, 50, 75, 100],
        "device": "cuda",
        "resumeAllowed": False,
    }:
        raise ValueError("P2-48 proposed bounded run changed")
    return value


def _review_result(path: Path) -> dict[str, Any]:
    value = _json(path)
    expected = {
        "schemaVersion": 1,
        "milestone": "P2-47",
        "kind": "plex-p2-47-request-grounded-coding-review-result-v1",
        "status": "candidate-review-passed",
        "representation": "plex-request-grounded-change-v1",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "byteCount": EXPECTED_CANDIDATE_BYTES,
        "records": 108,
        "trainRecords": TRAIN_RECORDS,
        "validationRecords": VALIDATION_RECORDS,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f"P2-47 frozen review result changed: {key}")
    preflight = value.get("tokenizerPreflight")
    if preflight != {
        "checked": True,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_SHA256,
        "maximumRecordTokensIncludingEos": EXPECTED_MAX_RECORD_TOKENS,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
    }:
        raise ValueError("P2-47 tokenizer review result changed")
    return value


def _candidate_rows(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-47 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    if (
        canonical_text_sha256(raw) != EXPECTED_CANDIDATE_SHA256
        or len(raw) != EXPECTED_CANDIDATE_BYTES
    ):
        raise ValueError("P2-47 candidate differs from the frozen reviewed candidate")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-47 JSONL line {number}")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"P2-47 line {number} is not an object")
        rows.append(value)
    if len(rows) != TRAIN_RECORDS + VALIDATION_RECORDS:
        raise ValueError("P2-47 candidate row count changed after review")
    return rows


def _render_training_text(row: dict[str, Any]) -> str:
    return (
        render_request_grounded_change_prompt(row["language"], row["request"])
        + row["solution"]
    )


def prepare_request_grounded_bundle(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE,
    review_path: Path = DEFAULT_REVIEW,
    development_task_set_path: Path = DEFAULT_DEVELOPMENT_TASK_SET,
    source_bundle_dir: Path = DEFAULT_SOURCE_BUNDLE,
    output_dir: Path = DEFAULT_OUTPUT_BUNDLE,
    artifact_root: Path = Path("training/artifacts"),
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    review_result_path: Path = Path(
        "training/pretraining/p2-47-request-grounded-coding-review-result.json"
    ),
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Pack the frozen P2-47 candidate with the frozen tokenizer, without training."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    _contract(preparation_contract_path)
    _review_result(review_result_path)

    review = review_request_grounded_coding_curriculum(
        candidate_path=candidate_path,
        review_path=review_path,
        development_task_set_path=development_task_set_path,
        contract_path=Path(
            "training/pretraining/p2-47-request-grounded-coding-preparation-contract.json"
        ),
        bundle_dir=source_bundle_dir,
    )
    if review.get("status") != "candidate-review-passed":
        raise ValueError("P2-47 candidate review has not passed")
    if review.get("tokenizerPreflight") != {
        "checked": True,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "bundleManifestSha256": EXPECTED_BUNDLE_SHA256,
        "maximumRecordTokensIncludingEos": EXPECTED_MAX_RECORD_TOKENS,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
    }:
        raise ValueError("P2-47 live tokenizer review differs from frozen result")

    tokenizer, source_identity = _completion_tokenizer(source_bundle_dir)
    if (
        source_identity.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or source_identity.get("bundleManifestSha256") != EXPECTED_BUNDLE_SHA256
        or tokenizer.vocabulary_size != 16384
    ):
        raise ValueError("P2-48 requires the exact frozen P2-44 tokenizer bundle")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-48 training bundle already exists; choose a fresh output")

    rows = _candidate_rows(candidate_path)
    by_split = {
        split: [row for row in rows if row.get("candidateSplit") == split]
        for split in ("train", "validation")
    }
    if (
        len(by_split["train"]) != TRAIN_RECORDS
        or len(by_split["validation"]) != VALIDATION_RECORDS
    ):
        raise ValueError("P2-47 candidate split changed after review")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=".plex-p2-48-bundle-", dir=output.parent)
    ).resolve()
    try:
        source_root = source_bundle_dir.resolve(strict=True)
        for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
            source = source_root / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Frozen tokenizer source is missing {name}")
            shutil.copyfile(source, staging / name)

        split_info: dict[str, dict[str, Any]] = {}
        source_summary: dict[str, Any] = {}
        overall_maximum = 0

        for split, expected_records, expected_tokens in (
            ("train", TRAIN_RECORDS, EXPECTED_TRAIN_TOKEN_COUNT),
            ("validation", VALIDATION_RECORDS, EXPECTED_VALIDATION_TOKEN_COUNT),
        ):
            jsonl_path = staging / f"{split}.jsonl"
            token_path = staging / f"{split}.tokens.u16le"
            index_path = staging / f"{split}.index.json"
            index: list[dict[str, Any]] = []
            token_count = 0
            maximum = 0

            with jsonl_path.open("x", encoding="utf-8", newline="\n") as text_stream, \
                    token_path.open("xb") as token_stream:
                for row in by_split[split]:
                    record_id = row["id"]
                    text = _render_training_text(row)
                    ids = tokenizer.encode(text)
                    if tokenizer.decode(ids) != text:
                        raise ValueError(f"P2-48 tokenizer roundtrip failed: {record_id}")
                    packed_ids = ids + [3]
                    if len(packed_ids) > DEFAULT_CONFIG.context_length:
                        raise ValueError(f"P2-48 record exceeds context: {record_id}")
                    text_stream.write(
                        json.dumps(
                            {"recordId": record_id, "text": text},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )
                    packed = array("H", packed_ids)
                    if sys.byteorder != "little":
                        packed.byteswap()
                    token_stream.write(packed.tobytes())
                    index.append(
                        {
                            "recordId": record_id,
                            "startToken": token_count,
                            "tokenCount": len(packed_ids),
                        }
                    )
                    token_count += len(packed_ids)
                    maximum = max(maximum, len(packed_ids))

            index_path.write_text(
                json.dumps(index, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            if len(index) != expected_records or token_count != expected_tokens:
                raise ValueError(f"P2-48 {split} packed accounting differs from review")
            overall_maximum = max(overall_maximum, maximum)
            source_summary[f"{split}Records"] = len(index)
            source_summary[f"{split}JsonlSha256"] = sha256_file(jsonl_path)
            split_info[split] = {
                "path": token_path.name,
                "sha256": sha256_file(token_path),
                "records": len(index),
                "tokenCount": token_count,
                "jsonlSha256": sha256_file(jsonl_path),
                "indexSha256": sha256_file(index_path),
                "maximumRecordTokensIncludingEos": maximum,
                "contextLength": DEFAULT_CONFIG.context_length,
                "contextLimitPassed": True,
            }

        if overall_maximum != EXPECTED_MAX_RECORD_TOKENS:
            raise ValueError("P2-48 maximum record length differs from frozen review")

        source_manifest = {
            "schemaVersion": 1,
            "pipelineVersion": PIPELINE_VERSION,
            "recordFormat": (
                "JSONL recordId/text rendered from frozen P2-47 "
                "request-grounded-change candidate"
            ),
            "normalization": "UTF-8; canonical repository text",
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "reviewStatus": review["status"],
            "summary": source_summary,
        }
        source_manifest_path = staging / "source-dataset-manifest.json"
        source_manifest_path.write_text(
            json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        manifest = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "pipelineVersion": PIPELINE_VERSION,
            "codec": CODEC,
            "actualVocabularySize": tokenizer.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "modelConfigSha256": sha256_file(staging / "model-config.json"),
            "sourceDatasetManifestSha256": sha256_file(source_manifest_path),
            "sourceTokenizerBundleManifestSha256": EXPECTED_BUNDLE_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "repackedWithFrozenTokenizer": True,
            **split_info,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        size = sum(
            path.stat().st_size for path in staging.rglob("*") if path.is_file()
        )
        if size > storage_limit_bytes:
            raise ValueError("P2-48 bundle exceeds remaining artifact storage allocation")
        os.rename(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    inspected = inspect_request_grounded_bundle(
        output,
        preparation_contract_path=preparation_contract_path,
        review_result_path=review_result_path,
    )
    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "training-bundle-prepared-zero-update",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(output / "manifest.json"),
        "sourceDatasetManifestSha256": inspected["dataset"][
            "sourceDatasetManifestSha256"
        ],
        "tokenizerSha256": inspected["tokenizer"]["tokenizerSha256"],
        "trainRecords": inspected["dataset"]["trainRecords"],
        "validationRecords": inspected["dataset"]["validationRecords"],
        "trainTokenCount": inspected["dataset"]["trainTokenCount"],
        "validationTokenCount": inspected["dataset"]["validationTokenCount"],
        "maximumRecordTokensIncludingEos": overall_maximum,
        "trainJsonlSha256": inspected["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": inspected["dataset"]["validationJsonlSha256"],
        "trainTokensSha256": inspected["dataset"]["trainTokensSha256"],
        "validationTokensSha256": inspected["dataset"]["validationTokensSha256"],
        "trainIndexSha256": inspected["dataset"]["trainIndexSha256"],
        "validationIndexSha256": inspected["dataset"]["validationIndexSha256"],
        "checkpointStagingAuthorized": False,
        "optimizerCreationAuthorized": False,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }


def inspect_request_grounded_bundle(
    bundle_dir: Path,
    *,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    review_result_path: Path = Path(
        "training/pretraining/p2-47-request-grounded-coding-review-result.json"
    ),
) -> dict[str, Any]:
    """Verify packed P2-48 text, tokens, indices, and frozen tokenizer identity."""
    _contract(preparation_contract_path)
    _review_result(review_result_path)
    root = bundle_dir.resolve(strict=True)
    if root.is_symlink():
        raise ValueError("P2-48 bundle may not be a symlink")

    manifest = _json(root / "manifest.json")
    source = _json(root / "source-dataset-manifest.json")
    tokenizer, tokenizer_record = _completion_tokenizer(root)
    if (
        manifest.get("schemaVersion") != 1
        or manifest.get("milestone") != MILESTONE
        or manifest.get("pipelineVersion") != PIPELINE_VERSION
        or manifest.get("codec") != CODEC
        or manifest.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or manifest.get("sourceTokenizerBundleManifestSha256") != EXPECTED_BUNDLE_SHA256
        or manifest.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer.vocabulary_size != 16384
        or source.get("pipelineVersion") != PIPELINE_VERSION
        or source.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or sha256_file(root / "source-dataset-manifest.json")
        != manifest.get("sourceDatasetManifestSha256")
    ):
        raise ValueError("P2-48 packed bundle identity is invalid")

    summary = source.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("P2-48 source dataset summary is missing")

    dataset: dict[str, Any] = {
        "sourceDatasetManifestSha256": manifest["sourceDatasetManifestSha256"],
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
    }
    ids_by_split: dict[str, set[str]] = {}

    for split, expected_records, expected_tokens in (
        ("train", TRAIN_RECORDS, EXPECTED_TRAIN_TOKEN_COUNT),
        ("validation", VALIDATION_RECORDS, EXPECTED_VALIDATION_TOKEN_COUNT),
    ):
        info = manifest.get(split)
        if (
            not isinstance(info, dict)
            or info.get("records") != expected_records
            or info.get("tokenCount") != expected_tokens
        ):
            raise ValueError(f"P2-48 {split} split accounting is invalid")
        jsonl_path = root / f"{split}.jsonl"
        token_path = root / f"{split}.tokens.u16le"
        index_path = root / f"{split}.index.json"
        if any(
            path.is_symlink() or not path.is_file()
            for path in (jsonl_path, token_path, index_path)
        ):
            raise ValueError("P2-48 bundle contains missing or linked split files")
        if (
            sha256_file(jsonl_path) != info.get("jsonlSha256")
            or info.get("jsonlSha256") != summary.get(f"{split}JsonlSha256")
            or sha256_file(token_path) != info.get("sha256")
            or sha256_file(index_path) != info.get("indexSha256")
        ):
            raise ValueError(f"P2-48 {split} split hash differs from manifest")

        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len(entries) != expected_records:
            raise ValueError(f"P2-48 {split} token index is invalid")

        tokens = array("H")
        tokens.frombytes(token_path.read_bytes())
        if sys.byteorder != "little":
            tokens.byteswap()

        offset = 0
        ids: set[str] = set()
        lines = list(jsonl_path.open(encoding="utf-8"))
        if len(lines) != expected_records:
            raise ValueError(f"P2-48 {split} JSONL row count changed")
        for line, entry in zip(lines, entries, strict=True):
            row = json.loads(line)
            record_id = row.get("recordId")
            text = row.get("text")
            if (
                not isinstance(record_id, str)
                or not record_id
                or record_id in ids
                or not isinstance(text, str)
                or not text.startswith(
                    "Map the coding request to one request-grounded change record.\n"
                )
                or "\nJSON:{" not in text
            ):
                raise ValueError("P2-48 packed text shape is invalid")
            expected = tokenizer.encode(text) + [3]
            if (
                entry.get("recordId") != record_id
                or entry.get("startToken") != offset
                or entry.get("tokenCount") != len(expected)
                or list(tokens[offset : offset + len(expected)]) != expected
            ):
                raise ValueError("P2-48 packed text/index/tokens differ")
            ids.add(record_id)
            offset += len(expected)

        if offset != len(tokens) or offset != expected_tokens:
            raise ValueError("P2-48 packed token accounting differs")
        ids_by_split[split] = ids
        dataset[f"{split}JsonlSha256"] = info["jsonlSha256"]
        dataset[f"{split}TokensSha256"] = info["sha256"]
        dataset[f"{split}TokenCount"] = info["tokenCount"]
        dataset[f"{split}Records"] = info["records"]
        dataset[f"{split}IndexSha256"] = info["indexSha256"]

    if ids_by_split["train"] & ids_by_split["validation"]:
        raise ValueError("P2-48 train/validation record identities overlap")

    return {
        "root": root,
        "manifest": manifest,
        "trainPath": root / "train.tokens.u16le",
        "validationPath": root / "validation.tokens.u16le",
        "tokenizer": tokenizer_record,
        "dataset": dataset,
    }


def preflight_request_grounded_bundle(
    *,
    bundle_dir: Path = DEFAULT_OUTPUT_BUNDLE,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    review_result_path: Path = Path(
        "training/pretraining/p2-47-request-grounded-coding-review-result.json"
    ),
) -> dict[str, Any]:
    """Replay the proposed complete-record sampler without staging or training."""
    contract = _contract(preparation_contract_path)
    bundle = inspect_request_grounded_bundle(
        bundle_dir,
        preparation_contract_path=preparation_contract_path,
        review_result_path=review_result_path,
    )
    tokenizer = PlexTokenizer.load(bundle["root"])
    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
        expected_text_prefix=(
            "Map the coding request to one request-grounded change record.\n"
        ),
    ) as train:
        expected_positions, _ = train.replay_progress(
            PROPOSED_SEED,
            PROPOSED_EXAMPLES,
        )
        rng = random.Random(PROPOSED_SEED)
        selection_counts: dict[int, int] = {start: 0 for start in train.starts}
        for _ in range(PROPOSED_EXAMPLES):
            selection_counts[rng.choice(train.starts)] += 1
        sampler = train.sampler_record

    selected = [count for count in selection_counts.values() if count > 0]
    if len(selected) != TRAIN_RECORDS:
        raise ValueError("P2-48 proposed sampler failed to select every train record")

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "bundle-preflight-passed-awaiting-stage-decision",
        "proposalOnly": True,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "sourceDatasetManifestSha256": bundle["dataset"][
            "sourceDatasetManifestSha256"
        ],
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "trainRecords": TRAIN_RECORDS,
        "validationRecords": VALIDATION_RECORDS,
        "trainTokenCount": bundle["dataset"]["trainTokenCount"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "trainTokensSha256": bundle["dataset"]["trainTokensSha256"],
        "validationTokensSha256": bundle["dataset"]["validationTokensSha256"],
        "trainIndexSha256": bundle["dataset"]["trainIndexSha256"],
        "validationIndexSha256": bundle["dataset"]["validationIndexSha256"],
        "sampler": sampler,
        "proposedRun": {
            "seed": PROPOSED_SEED,
            "maximumSteps": PROPOSED_MAXIMUM_STEPS,
            "microBatch": PROPOSED_MICRO_BATCH,
            "gradientAccumulation": PROPOSED_GRADIENT_ACCUMULATION,
            "examples": PROPOSED_EXAMPLES,
            "recordsSelected": len(selected),
            "minimumRecordSelections": min(selected),
            "maximumRecordSelections": max(selected),
            "expectedRealTargetPositions": expected_positions,
        },
        "sourceCheckpoint": contract["source"],
        "checkpointStagingAuthorized": False,
        "optimizerCreationAuthorized": False,
        "modelTrainingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
