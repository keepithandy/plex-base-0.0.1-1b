"""P2-44 deterministic training-bundle packing and zero-update preflight.

This module may pack and inspect the frozen P2-44 curriculum and replay the
future complete-record sampler. It does not create checkpoints, optimizers, or
perform model training.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
from array import array
from collections import Counter
from pathlib import Path
from typing import Any

from .artifacts import path_within_root
from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .structured_plan import render_plan_request_prompt
from .structured_plan_evidence_composition_curriculum import (
    EXPECTED_CANDIDATE_BYTES,
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_MAX_RECORD_TOKENS,
    EXPECTED_TOKENIZER_BUNDLE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    EXPECTED_TRAIN_TOKEN_COUNT,
    EXPECTED_VALIDATION_TOKEN_COUNT,
    _contract as _composition_contract,
    review_evidence_composition_curriculum,
)
from .structured_plan_semantic_binding_training import StructuredPlanCompleteRecordCorpus
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-44"
PIPELINE_VERSION = "p2-44-evidence-first-semantic-composition-bundle-v1"
DEFAULT_PREPARATION_CONTRACT = Path(
    "training/pretraining/p2-44-evidence-first-semantic-composition-preparation-contract.json"
)
DEFAULT_CANDIDATE = Path(
    "training/phase2/drafts/p2-44-evidence-first-semantic-composition-v1.jsonl"
)
DEFAULT_REVIEW = Path(
    "training/phase2/drafts/p2-44-evidence-first-semantic-composition-v1.review.json"
)
DEFAULT_DEVELOPMENT_TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
DEFAULT_SOURCE_BUNDLE = Path("training/artifacts/structured-plan/p2-41-training-bundle")
DEFAULT_OUTPUT_BUNDLE = Path("training/artifacts/structured-plan/p2-44-training-bundle")

TRAIN_RECORDS = 108
VALIDATION_RECORDS = 54
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


def _candidate_rows(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("P2-44 candidate must be a regular JSONL file under 8 MiB")
    raw = path.read_bytes()
    from .structured_plan import canonical_text_sha256

    if (
        canonical_text_sha256(raw) != EXPECTED_CANDIDATE_SHA256
        or len(raw) != EXPECTED_CANDIDATE_BYTES
    ):
        raise ValueError("P2-44 candidate differs from the frozen reviewed candidate")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank P2-44 JSONL line {number}")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"P2-44 line {number} is not an object")
        rows.append(value)
    if len(rows) != TRAIN_RECORDS + VALIDATION_RECORDS:
        raise ValueError("P2-44 candidate row count changed after review")
    return rows


def _render_training_text(row: dict[str, Any]) -> str:
    return render_plan_request_prompt(row["language"], row["request"]) + row["solution"]


def prepare_evidence_composition_bundle(
    *,
    candidate_path: Path = DEFAULT_CANDIDATE,
    review_path: Path = DEFAULT_REVIEW,
    development_task_set_path: Path = DEFAULT_DEVELOPMENT_TASK_SET,
    source_bundle_dir: Path = DEFAULT_SOURCE_BUNDLE,
    output_dir: Path = DEFAULT_OUTPUT_BUNDLE,
    artifact_root: Path = Path("training/artifacts"),
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Pack the frozen P2-44 candidate with the frozen tokenizer, without training."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    _composition_contract(preparation_contract_path)

    review = review_evidence_composition_curriculum(
        candidate_path=candidate_path,
        review_path=review_path,
        development_task_set_path=development_task_set_path,
        contract_path=preparation_contract_path,
        bundle_dir=source_bundle_dir,
    )
    if review.get("status") != "candidate-review-passed":
        raise ValueError("P2-44 candidate review has not passed")
    expected_preflight = {
        "checked": True,
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "bundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
        "maximumRecordTokensIncludingEos": EXPECTED_MAX_RECORD_TOKENS,
        "trainTokenCount": EXPECTED_TRAIN_TOKEN_COUNT,
        "validationTokenCount": EXPECTED_VALIDATION_TOKEN_COUNT,
    }
    if review.get("tokenizerPreflight") != expected_preflight:
        raise ValueError("P2-44 frozen-tokenizer review differs from the frozen result")

    tokenizer, source_identity = _completion_tokenizer(source_bundle_dir)
    if (
        source_identity.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or source_identity.get("bundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
        or tokenizer.vocabulary_size != 16384
    ):
        raise ValueError("P2-44 requires the exact frozen P2-41 tokenizer bundle")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-44 training bundle already exists; choose a fresh output")

    rows = _candidate_rows(candidate_path)
    by_split = {
        split: [row for row in rows if row.get("candidateSplit") == split]
        for split in ("train", "validation")
    }
    if len(by_split["train"]) != TRAIN_RECORDS or len(by_split["validation"]) != VALIDATION_RECORDS:
        raise ValueError("P2-44 candidate split changed after review")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-p2-44-bundle-", dir=output.parent)).resolve()
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
                        raise ValueError(f"P2-44 tokenizer roundtrip failed: {record_id}")
                    packed_ids = ids + [3]
                    if len(packed_ids) > DEFAULT_CONFIG.context_length:
                        raise ValueError(f"P2-44 record exceeds context: {record_id}")
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
                raise ValueError(f"P2-44 {split} packed accounting differs from frozen review")

            overall_maximum = max(overall_maximum, maximum)
            source_summary[f"{split}Records"] = len(index)
            source_summary[f"{split}JsonlSha256"] = sha256_file(jsonl_path)
            source_summary[f"{split}IndexSha256"] = sha256_file(index_path)
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
            raise ValueError("P2-44 packed maximum record length differs from frozen review")

        source_manifest = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "pipelineVersion": PIPELINE_VERSION,
            "recordFormat": "JSONL recordId/text rendered from frozen P2-44 full-plan candidate",
            "normalization": "UTF-8; canonical repository text",
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "candidateBytes": EXPECTED_CANDIDATE_BYTES,
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
            "sourceTokenizerBundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "candidateBytes": EXPECTED_CANDIDATE_BYTES,
            "repackedWithFrozenTokenizer": True,
            "trainingAuthorized": False,
            **split_info,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if size > storage_limit_bytes:
            raise ValueError("P2-44 bundle exceeds remaining artifact storage allocation")
        os.rename(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    inspected = inspect_evidence_composition_bundle(
        output, preparation_contract_path=preparation_contract_path
    )
    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "training-bundle-prepared-zero-update",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(output / "manifest.json"),
        "sourceDatasetManifestSha256": inspected["dataset"]["sourceDatasetManifestSha256"],
        "tokenizerSha256": inspected["tokenizer"]["tokenizerSha256"],
        "trainRecords": inspected["dataset"]["trainRecords"],
        "validationRecords": inspected["dataset"]["validationRecords"],
        "trainTokenCount": inspected["dataset"]["trainTokenCount"],
        "validationTokenCount": inspected["dataset"]["validationTokenCount"],
        "trainJsonlSha256": inspected["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": inspected["dataset"]["validationJsonlSha256"],
        "trainIndexSha256": inspected["dataset"]["trainIndexSha256"],
        "validationIndexSha256": inspected["dataset"]["validationIndexSha256"],
        "maximumRecordTokensIncludingEos": inspected["maximumRecordTokensIncludingEos"],
        "modelTrainingAuthorized": False,
        "checkpointStagingAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }


def inspect_evidence_composition_bundle(
    bundle_dir: Path,
    *,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
) -> dict[str, Any]:
    """Verify P2-44 packed text, tokens, indices, candidate, and tokenizer identity."""
    _composition_contract(preparation_contract_path)
    root = bundle_dir.resolve(strict=True)
    if root.is_symlink():
        raise ValueError("P2-44 bundle may not be a symlink")

    manifest = _json(root / "manifest.json")
    source = _json(root / "source-dataset-manifest.json")
    tokenizer, tokenizer_record = _completion_tokenizer(root)

    if (
        manifest.get("schemaVersion") != 1
        or manifest.get("milestone") != MILESTONE
        or manifest.get("pipelineVersion") != PIPELINE_VERSION
        or manifest.get("codec") != CODEC
        or manifest.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or manifest.get("candidateBytes") != EXPECTED_CANDIDATE_BYTES
        or manifest.get("sourceTokenizerBundleManifestSha256") != EXPECTED_TOKENIZER_BUNDLE_SHA256
        or manifest.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or manifest.get("trainingAuthorized") is not False
        or tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
        or tokenizer.vocabulary_size != 16384
        or source.get("pipelineVersion") != PIPELINE_VERSION
        or source.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
        or source.get("candidateBytes") != EXPECTED_CANDIDATE_BYTES
        or sha256_file(root / "source-dataset-manifest.json")
        != manifest.get("sourceDatasetManifestSha256")
    ):
        raise ValueError("P2-44 packed bundle identity is invalid")

    summary = source.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("P2-44 source dataset summary is missing")

    dataset: dict[str, Any] = {
        "sourceDatasetManifestSha256": manifest["sourceDatasetManifestSha256"],
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
    }
    ids_by_split: dict[str, set[str]] = {}
    overall_maximum = 0

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
            raise ValueError(f"P2-44 {split} split accounting is invalid")

        jsonl_path = root / f"{split}.jsonl"
        token_path = root / f"{split}.tokens.u16le"
        index_path = root / f"{split}.index.json"
        if any(
            path.is_symlink() or not path.is_file()
            for path in (jsonl_path, token_path, index_path)
        ):
            raise ValueError("P2-44 bundle contains missing or linked split files")

        if (
            sha256_file(jsonl_path) != info.get("jsonlSha256")
            or info.get("jsonlSha256") != summary.get(f"{split}JsonlSha256")
            or sha256_file(index_path) != info.get("indexSha256")
            or info.get("indexSha256") != summary.get(f"{split}IndexSha256")
            or sha256_file(token_path) != info.get("sha256")
        ):
            raise ValueError(f"P2-44 {split} split hash differs from manifest")

        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len(entries) != expected_records:
            raise ValueError(f"P2-44 {split} token index is invalid")

        tokens = array("H")
        tokens.frombytes(token_path.read_bytes())
        if sys.byteorder != "little":
            tokens.byteswap()

        lines = list(jsonl_path.open(encoding="utf-8"))
        if len(lines) != expected_records:
            raise ValueError(f"P2-44 {split} JSONL row count changed")

        offset = 0
        ids: set[str] = set()
        maximum = 0
        for line, entry in zip(lines, entries):
            row = json.loads(line)
            record_id = row.get("recordId")
            text = row.get("text")
            if (
                not isinstance(record_id, str)
                or not record_id
                or record_id in ids
                or not isinstance(text, str)
                or not text.startswith(
                    "Convert the repository-style request into one semantic edit plan.\n"
                )
                or "\nJSON:{" not in text
            ):
                raise ValueError("P2-44 packed text shape is invalid")

            expected = tokenizer.encode(text) + [3]
            if (
                entry.get("recordId") != record_id
                or entry.get("startToken") != offset
                or entry.get("tokenCount") != len(expected)
                or list(tokens[offset : offset + len(expected)]) != expected
            ):
                raise ValueError("P2-44 packed text/index/tokens differ")
            maximum = max(maximum, len(expected))
            ids.add(record_id)
            offset += len(expected)

        if offset != len(tokens) or offset != expected_tokens:
            raise ValueError("P2-44 packed token accounting differs")

        ids_by_split[split] = ids
        overall_maximum = max(overall_maximum, maximum)
        dataset[f"{split}JsonlSha256"] = info["jsonlSha256"]
        dataset[f"{split}TokensSha256"] = info["sha256"]
        dataset[f"{split}TokenCount"] = info["tokenCount"]
        dataset[f"{split}Records"] = info["records"]
        dataset[f"{split}IndexSha256"] = info["indexSha256"]

    if ids_by_split["train"] & ids_by_split["validation"]:
        raise ValueError("P2-44 train/validation record identities overlap")
    if overall_maximum != EXPECTED_MAX_RECORD_TOKENS:
        raise ValueError("P2-44 packed maximum record length differs from frozen review")

    return {
        "root": root,
        "manifest": manifest,
        "trainPath": root / "train.tokens.u16le",
        "validationPath": root / "validation.tokens.u16le",
        "tokenizer": tokenizer_record,
        "dataset": dataset,
        "maximumRecordTokensIncludingEos": overall_maximum,
    }


def preflight_evidence_composition_bundle(
    *,
    bundle_dir: Path = DEFAULT_OUTPUT_BUNDLE,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    proposed_seed: int = PROPOSED_SEED,
    proposed_maximum_steps: int = PROPOSED_MAXIMUM_STEPS,
    proposed_micro_batch: int = PROPOSED_MICRO_BATCH,
    proposed_gradient_accumulation: int = PROPOSED_GRADIENT_ACCUMULATION,
) -> dict[str, Any]:
    """Replay future sampling only; perform no optimizer or checkpoint work."""
    if type(proposed_seed) is not int or not 0 <= proposed_seed <= 2**63 - 1:
        raise ValueError("P2-44 proposed seed is invalid")
    if (
        type(proposed_maximum_steps) is not int
        or not 1 <= proposed_maximum_steps <= 1000
        or type(proposed_micro_batch) is not int
        or not 1 <= proposed_micro_batch <= 64
        or type(proposed_gradient_accumulation) is not int
        or not 1 <= proposed_gradient_accumulation <= 256
    ):
        raise ValueError("P2-44 proposed sampler dimensions are invalid")

    bundle = inspect_evidence_composition_bundle(
        bundle_dir, preparation_contract_path=preparation_contract_path
    )
    tokenizer = PlexTokenizer.load(bundle["root"])
    draws = proposed_maximum_steps * proposed_micro_batch * proposed_gradient_accumulation

    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train:
        expected_positions, _ = train.replay_progress(proposed_seed, draws)
        rng = random.Random(proposed_seed)
        selection_counts = Counter(rng.choice(train.starts) for _ in range(draws))
        records_selected = len(selection_counts)
        minimum = min(selection_counts.get(start, 0) for start in train.starts)
        maximum = max(selection_counts.get(start, 0) for start in train.starts)
        sampler = train.sampler_record

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "status": "bundle-preflight-passed-awaiting-separate-stage-decision",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "sourceDatasetManifestSha256": bundle["dataset"]["sourceDatasetManifestSha256"],
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "trainRecords": bundle["dataset"]["trainRecords"],
        "validationRecords": bundle["dataset"]["validationRecords"],
        "trainTokenCount": bundle["dataset"]["trainTokenCount"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "trainIndexSha256": bundle["dataset"]["trainIndexSha256"],
        "validationIndexSha256": bundle["dataset"]["validationIndexSha256"],
        "maximumRecordTokensIncludingEos": bundle["maximumRecordTokensIncludingEos"],
        "sampler": sampler,
        "proposedRun": {
            "seed": proposed_seed,
            "maximumSteps": proposed_maximum_steps,
            "microBatch": proposed_micro_batch,
            "gradientAccumulation": proposed_gradient_accumulation,
            "examples": draws,
            "expectedRealTargetPositions": expected_positions,
            "recordsSelected": records_selected,
            "minimumRecordSelections": minimum,
            "maximumRecordSelections": maximum,
        },
        "proposalOnly": True,
        "modelTrainingAuthorized": False,
        "checkpointStagingAuthorized": False,
        "optimizerCreationAuthorized": False,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
