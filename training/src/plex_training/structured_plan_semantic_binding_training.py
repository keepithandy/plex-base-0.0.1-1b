"""P2-38 semantic-binding bundle, stage, preflight, and locked training path.

Preparation and staging perform zero optimizer updates. The real run is hard-blocked
unless a separate owner-approved authorization contract is committed.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import sys
import tempfile
import time
from array import array
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .artifacts import enforce_storage_limit, path_within_root
from .checkpoint import read_checkpoint, save_checkpoint
from .completion import _completion_tokenizer
from .config import DEFAULT_CONFIG
from .data import TokenCorpus
from .model import parameter_count
from .runner import (
    ADAMW_BETAS,
    ADAMW_EPSILON,
    ADAMW_LEARNING_RATE,
    ADAMW_WEIGHT_DECAY,
    SCHEDULE_KIND,
    _validation_loss,
    seed_everything,
)
from .structured_plan import canonical_text_sha256
from .structured_plan_semantic_binding_curriculum import (
    EXPECTED_CANDIDATE_SHA256,
    EXPECTED_TOKENIZER_BUNDLE_SHA256,
    EXPECTED_TOKENIZER_SHA256,
    render_p238_record,
    review_semantic_binding_curriculum,
)
from .telemetry import environment_report, peak_gpu_memory, reset_peak_gpu_memory, select_device
from .tokenizer import CODEC, PlexTokenizer, sha256_file

MILESTONE = "P2-38"
PREPARATION_KIND = "plex-p2-38-semantic-binding-preparation-contract-v1"
STAGE_KIND = "plex-semantic-binding-stage-transition-v1"
AUTHORIZATION_KIND = "plex-p2-38-first-semantic-binding-run-contract-v1"
AUTHORIZED_STATUS = "owner-approved-first-run"
AUTHORIZED_APPROVER = "keepithandy"
BASE_CHECKPOINT_SHA256 = "1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0"
BASE_CHECKPOINT_STEP = 100
SEED = 1337
MAXIMUM_STEPS = 100
MAXIMUM_WALL_SECONDS = 600
MICRO_BATCH = 1
GRADIENT_ACCUMULATION = 16
GRADIENT_CLIP_NORM = 1.0
VALIDATION_STEPS = (0, 25, 50, 75, 100)
CHECKPOINT_STEPS = (25, 50, 75, 100)
VALIDATION_MAXIMUM_BATCHES = 100
AUTHORIZED_OUTPUT_DIRECTORY = "structured-plan/p2-38-first-run"
DEFAULT_PREPARATION_CONTRACT = Path(
    "training/pretraining/p2-38-semantic-binding-preparation-contract.json"
)
DEFAULT_AUTHORIZATION_CONTRACT = Path(
    "training/pretraining/p2-38-first-run-contract.draft.json"
)


def _json(path: Path, maximum_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum_bytes:
        raise ValueError(f"Missing, linked, or oversized JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"P2-38 contract mismatch: {label}")


def _preparation_contract(path: Path) -> dict[str, Any]:
    contract = _json(path)
    if (contract.get("schemaVersion") != 1
            or contract.get("milestone") != MILESTONE
            or contract.get("kind") != PREPARATION_KIND
            or contract.get("status") != "design-preparation-only"
            or contract.get("dataPreparationAuthorized") is not True
            or contract.get("modelTrainingAuthorized") is not False
            or contract.get("automaticTrainingExtension") is not False):
        raise ValueError("P2-38 preparation contract is invalid or does not block training")
    return contract


def _candidate_rows(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("P2-38 candidate must be a regular JSONL file under 4 MiB")
    raw = path.read_bytes()
    if canonical_text_sha256(raw) != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("P2-38 candidate differs from the reviewed curriculum")
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if line.strip():
            value = json.loads(line.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("P2-38 candidate row must be an object")
            rows.append(value)
    return rows


def _render_training_text(row: dict[str, Any]) -> str:
    return render_p238_record(row)


def prepare_structured_plan_bundle(
    *,
    candidate_path: Path,
    review_path: Path,
    development_task_set_path: Path,
    source_bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Pack reviewed P2-38 records with the frozen tokenizer without training."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    contract = _preparation_contract(preparation_contract_path)
    review = review_semantic_binding_curriculum(
        candidate_path=candidate_path,
        review_path=review_path,
        development_task_set_path=development_task_set_path,
        p235_candidate_path=Path(
            "training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl"
        ),
        contract_path=preparation_contract_path,
        bundle_dir=source_bundle_dir,
    )
    if review["status"] != "candidate-review-passed" or not review["tokenizerPreflight"]["checked"]:
        raise ValueError("P2-38 frozen-tokenizer curriculum preflight has not passed")

    tokenizer, source_tokenizer_record = _completion_tokenizer(source_bundle_dir)
    if (source_tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
            or source_tokenizer_record.get("bundleManifestSha256")
            != EXPECTED_TOKENIZER_BUNDLE_SHA256
            or tokenizer.vocabulary_size != 16384):
        raise ValueError("P2-38 requires the exact frozen tokenizer source bundle")

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-38 packed bundle already exists; choose a fresh output")
    rows = _candidate_rows(candidate_path)
    by_split = {
        split: [row for row in rows if row.get("candidateSplit") == split]
        for split in ("train", "validation")
    }
    if len(by_split["train"]) != 72 or len(by_split["validation"]) != 36:
        raise ValueError("P2-38 candidate split changed after review")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-p2-38-bundle-", dir=output.parent)).resolve()
    try:
        for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
            source = source_bundle_dir.resolve(strict=True) / name
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Frozen tokenizer source is missing {name}")
            shutil.copyfile(source, staging / name)

        split_info: dict[str, dict[str, Any]] = {}
        summary: dict[str, Any] = {}
        for split in ("train", "validation"):
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
                        raise ValueError("P2-38 training text failed exact tokenizer roundtrip")
                    packed_ids = ids + [3]
                    if len(packed_ids) > DEFAULT_CONFIG.context_length + 1:
                        raise ValueError(f"P2-38 record {record_id} exceeds context")
                    text_stream.write(
                        json.dumps(
                            {"recordId": record_id, "text": text},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ) + "\n"
                    )
                    packed = array("H", packed_ids)
                    if sys.byteorder != "little":
                        packed.byteswap()
                    token_stream.write(packed.tobytes())
                    index.append({
                        "recordId": record_id,
                        "startToken": token_count,
                        "tokenCount": len(packed_ids),
                    })
                    token_count += len(packed_ids)
                    maximum = max(maximum, len(packed_ids))
            index_path.write_text(
                json.dumps(index, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            jsonl_sha = sha256_file(jsonl_path)
            summary[f"{split}Records"] = len(index)
            summary[f"{split}JsonlSha256"] = jsonl_sha
            split_info[split] = {
                "path": token_path.name,
                "sha256": sha256_file(token_path),
                "records": len(index),
                "tokenCount": token_count,
                "jsonlSha256": jsonl_sha,
                "maximumRecordTokensIncludingEos": maximum,
                "contextLength": DEFAULT_CONFIG.context_length,
                "contextLimitPassed": True,
            }

        source_manifest = {
            "schemaVersion": 1,
            "pipelineVersion": "p2-38-semantic-binding-v1",
            "recordFormat": "JSONL recordId/text rendered from reviewed P2-38 full-plan semantic-binding candidate",
            "normalization": "UTF-8; repository text files pinned/canonicalized to LF",
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "reviewStatus": review["status"],
            "summary": summary,
        }
        source_manifest_path = staging / "source-dataset-manifest.json"
        source_manifest_path.write_text(
            json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        model_config_sha = sha256_file(staging / "model-config.json")
        manifest = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "codec": CODEC,
            "actualVocabularySize": tokenizer.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
            "modelConfigSha256": model_config_sha,
            "sourceDatasetManifestSha256": sha256_file(source_manifest_path),
            "sourceTokenizerBundleManifestSha256": EXPECTED_TOKENIZER_BUNDLE_SHA256,
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "repackedWithFrozenTokenizer": True,
            **split_info,
        }
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        size = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if size > storage_limit_bytes:
            raise ValueError("P2-38 bundle exceeds remaining artifact storage allocation")
        os.rename(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    inspected = inspect_structured_plan_bundle(output, preparation_contract_path)
    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(output / "manifest.json"),
        "tokenizerSha256": inspected["tokenizer"]["tokenizerSha256"],
        "trainRecords": inspected["dataset"]["trainRecords"],
        "validationRecords": inspected["dataset"]["validationRecords"],
        "trainTokenCount": inspected["dataset"]["trainTokenCount"],
        "validationTokenCount": inspected["dataset"]["validationTokenCount"],
        "maximumRecordTokensIncludingEos": max(
            inspected["manifest"]["train"]["maximumRecordTokensIncludingEos"],
            inspected["manifest"]["validation"]["maximumRecordTokensIncludingEos"],
        ),
    }


def inspect_structured_plan_bundle(
    bundle_dir: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
) -> dict[str, Any]:
    """Verify packed text, tokens, indices, candidate provenance, and tokenizer identity."""
    _preparation_contract(preparation_contract_path)
    root = bundle_dir.resolve(strict=True)
    if root.is_symlink():
        raise ValueError("P2-38 bundle may not be a symlink")
    manifest = _json(root / "manifest.json")
    source = _json(root / "source-dataset-manifest.json")
    tokenizer, tokenizer_record = _completion_tokenizer(root)
    if (manifest.get("schemaVersion") != 1 or manifest.get("milestone") != MILESTONE
            or manifest.get("codec") != CODEC
            or manifest.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
            or manifest.get("sourceTokenizerBundleManifestSha256")
            != EXPECTED_TOKENIZER_BUNDLE_SHA256
            or manifest.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
            or tokenizer_record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
            or tokenizer.vocabulary_size != 16384
            or source.get("pipelineVersion") != "p2-38-semantic-binding-v1"
            or source.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
            or sha256_file(root / "source-dataset-manifest.json")
            != manifest.get("sourceDatasetManifestSha256")):
        raise ValueError("P2-38 packed bundle identity is invalid")

    summary = source.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("P2-38 source dataset summary is missing")
    dataset: dict[str, Any] = {
        "sourceDatasetManifestSha256": manifest["sourceDatasetManifestSha256"],
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
    }
    ids_by_split: dict[str, set[str]] = {}
    for split, expected_records in (("train", 72), ("validation", 36)):
        info = manifest.get(split)
        if not isinstance(info, dict) or info.get("records") != expected_records:
            raise ValueError(f"P2-38 {split} split record count is invalid")
        jsonl_path = root / f"{split}.jsonl"
        token_path = root / f"{split}.tokens.u16le"
        index_path = root / f"{split}.index.json"
        if any(path.is_symlink() or not path.is_file()
               for path in (jsonl_path, token_path, index_path)):
            raise ValueError("P2-38 bundle contains missing or linked split files")
        if (sha256_file(jsonl_path) != info.get("jsonlSha256")
                or info.get("jsonlSha256") != summary.get(f"{split}JsonlSha256")
                or sha256_file(token_path) != info.get("sha256")):
            raise ValueError(f"P2-38 {split} split hash differs from manifest")
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len(entries) != expected_records:
            raise ValueError(f"P2-38 {split} token index is invalid")
        tokens = array("H")
        tokens.frombytes(token_path.read_bytes())
        if sys.byteorder != "little":
            tokens.byteswap()
        offset = 0
        ids: set[str] = set()
        with jsonl_path.open(encoding="utf-8") as stream:
            lines = list(stream)
        if len(lines) != expected_records:
            raise ValueError(f"P2-38 {split} JSONL row count changed")
        for line, entry in zip(lines, entries):
            row = json.loads(line)
            record_id, text = row.get("recordId"), row.get("text")
            if (not isinstance(record_id, str) or not record_id or record_id in ids
                    or not isinstance(text, str) or not text
                    or not text.startswith(
                        "Convert the repository-style request into one semantic edit plan.\n"
                    )
                    or "\nJSON:{" not in text):
                raise ValueError("P2-38 packed text shape is invalid")
            expected = tokenizer.encode(text) + [3]
            if (entry.get("recordId") != record_id
                    or entry.get("startToken") != offset
                    or entry.get("tokenCount") != len(expected)
                    or list(tokens[offset:offset + len(expected)]) != expected):
                raise ValueError("P2-38 packed text/index/tokens differ")
            ids.add(record_id)
            offset += len(expected)
        if offset != len(tokens) or offset != info.get("tokenCount"):
            raise ValueError("P2-38 packed token accounting differs")
        ids_by_split[split] = ids
        dataset[f"{split}JsonlSha256"] = info["jsonlSha256"]
        dataset[f"{split}TokensSha256"] = info["sha256"]
        dataset[f"{split}TokenCount"] = info["tokenCount"]
        dataset[f"{split}Records"] = info["records"]
        dataset[f"{split}IndexSha256"] = sha256_file(index_path)
    if ids_by_split["train"] & ids_by_split["validation"]:
        raise ValueError("P2-38 train/validation record identities overlap")
    return {
        "root": root,
        "manifest": manifest,
        "trainPath": root / "train.tokens.u16le",
        "validationPath": root / "validation.tokens.u16le",
        "tokenizer": tokenizer_record,
        "dataset": dataset,
    }


class StructuredPlanCompleteRecordCorpus(TokenCorpus):
    """Verified complete-record sampling for P2-38's structured-plan text format."""

    def __init__(
        self,
        token_path: Path,
        *,
        dataset_jsonl: Path,
        index_path: Path,
        tokenizer: PlexTokenizer,
        expected_jsonl_sha256: str,
    ) -> None:
        if (dataset_jsonl.is_symlink() or index_path.is_symlink()
                or not dataset_jsonl.is_file() or not index_path.is_file()):
            raise ValueError("P2-38 sampler requires regular JSONL and index files")
        if sha256_file(dataset_jsonl) != expected_jsonl_sha256:
            raise ValueError("P2-38 sampler JSONL differs from reviewed bundle")
        super().__init__(token_path)
        try:
            entries = json.loads(index_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or not entries:
                raise ValueError("P2-38 sampler index is empty")
            starts, lengths, ids = [], [], set()
            offset = 0
            with dataset_jsonl.open(encoding="utf-8") as stream:
                lines = list(stream)
            if len(lines) != len(entries):
                raise ValueError("P2-38 sampler JSONL/index row counts differ")
            for line, entry in zip(lines, entries):
                row = json.loads(line)
                record_id, text = row.get("recordId"), row.get("text")
                if (not isinstance(record_id, str) or record_id in ids
                        or not isinstance(text, str)
                        or not text.startswith(
                            "Convert the repository-style request into one semantic edit plan.\n"
                        )
                        or "\nJSON:{" not in text):
                    raise ValueError("P2-38 sampler record shape is invalid")
                expected = tokenizer.encode(text) + [3]
                if (entry.get("recordId") != record_id
                        or entry.get("startToken") != offset
                        or entry.get("tokenCount") != len(expected)
                        or offset + len(expected) > self.token_count
                        or self._window(offset, len(expected)).tolist() != expected):
                    raise ValueError("P2-38 sampler index differs from packed tokens")
                starts.append(offset)
                lengths.append(len(expected))
                ids.add(record_id)
                offset += len(expected)
            if offset != self.token_count:
                raise ValueError("P2-38 sampler index does not cover packed corpus")
            self.starts = tuple(starts)
            self.lengths = tuple(lengths)
            self._length_by_start = dict(zip(starts, lengths))
            self.maximum_record_tokens = max(lengths)
            self._counts = dict.fromkeys(starts, 0)
            self._real_targets = 0
            self._padding_targets = 0
            self.sampler_record = {
                "kind": "complete-record-v1",
                "selection": "uniform-record-with-replacement",
                "endPolicy": "stop-at-record-eos-v1",
                "records": len(starts),
                "trainJsonlSha256": expected_jsonl_sha256,
                "indexSha256": sha256_file(index_path),
                "paddingPolicy": "right-pad-to-batch-longest-zero-target-weight-v1",
                "tokenAccounting": "nonpadding-next-token-targets-v1",
                "lossReduction": "mean-real-targets-per-microbatch-then-mean-accumulation-v1",
            }
        except Exception:
            self.close()
            raise

    def sample_batch(self, rng: random.Random, batch_size: int, sequence_length: int):
        raise ValueError("P2-38 complete-record sampling requires a padding mask")

    def sample_masked_batch(self, rng: random.Random, batch_size: int, sequence_length: int):
        if (batch_size <= 0 or sequence_length <= 0
                or self.maximum_record_tokens > sequence_length + 1
                or min(self.lengths) < 2):
            raise ValueError("P2-38 complete records must fit the model context")
        starts = [rng.choice(self.starts) for _ in range(batch_size)]
        lengths = [self._length_by_start[start] - 1 for start in starts]
        inputs = torch.zeros((batch_size, max(lengths)), dtype=torch.long)
        targets = torch.zeros_like(inputs)
        weights = torch.zeros_like(inputs, dtype=torch.float32)
        for row, (start, length) in enumerate(zip(starts, lengths)):
            tokens = self._window(start, length + 1)
            inputs[row, :length] = tokens[:-1]
            targets[row, :length] = tokens[1:]
            weights[row, :length] = 1.0
            self._counts[start] += 1
        real = sum(lengths)
        self._real_targets += real
        self._padding_targets += targets.numel() - real
        return inputs, targets, weights

    def replay_progress(self, seed: int, draws: int) -> tuple[int, tuple]:
        if type(draws) is not int or not 0 <= draws <= 1_000_000:
            raise ValueError("P2-38 sampler replay exceeds bounded limit")
        rng = random.Random(seed)
        positions = sum(self._length_by_start[rng.choice(self.starts)] - 1 for _ in range(draws))
        return positions, rng.getstate()

    def sampling_audit(self) -> dict[str, Any]:
        return {
            "examples": sum(self._counts.values()),
            "recordsSelected": sum(count > 0 for count in self._counts.values()),
            "minimumRecordSelections": min(self._counts.values()),
            "maximumRecordSelections": max(self._counts.values()),
            "realTargetPositions": self._real_targets,
            "paddingTargetPositions": self._padding_targets,
        }


def _structured_plan_training_step(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    source: StructuredPlanCompleteRecordCorpus,
    rng: random.Random,
    device: torch.device,
    *,
    micro_batch: int,
    accumulation_steps: int,
    loss_vocabulary_size: int,
) -> tuple[float, int, int]:
    """One P2-38 optimizer update using the verified mask-aware complete-record sampler."""
    optimizer.zero_grad(set_to_none=True)
    total_loss = 0.0
    real_positions = padding_positions = 0
    for _ in range(accumulation_steps):
        inputs, targets, weights = source.sample_masked_batch(
            rng,
            batch_size=micro_batch,
            sequence_length=model.config.context_length,
        )
        positions = int((weights > 0).sum().item())
        real_positions += positions
        padding_positions += targets.numel() - positions
        _, loss = model(
            inputs.to(device),
            targets.to(device),
            loss_vocabulary_size=loss_vocabulary_size,
            target_weights=weights.to(device),
        )
        if loss is None:
            raise RuntimeError("P2-38 model did not produce a training loss")
        (loss / accumulation_steps).backward()
        total_loss += float(loss.detach().item())
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRADIENT_CLIP_NORM)
    optimizer.step()
    return total_loss / accumulation_steps, real_positions, padding_positions


def _clear_aborted_zero_update_output(output: Path) -> bool:
    """Remove only the exact debris shape produced by a pre-update P2-38 abort."""
    if not output.exists():
        return False
    if output.is_symlink() or not output.is_dir():
        raise FileExistsError("P2-38 first-run output exists and is not a recoverable directory")
    allowed = {"checkpoints", "metrics.jsonl"}
    metadata_names = {"desktop.ini", ".DS_Store"}
    entries = {path.name: path for path in output.iterdir()}
    unexpected = set(entries) - allowed - metadata_names
    if unexpected:
        rendered = ", ".join(sorted(unexpected))
        raise FileExistsError(
            f"P2-38 first-run output contains non-recoverable files: {rendered}"
        )
    for name in sorted(set(entries) & metadata_names):
        path = entries[name]
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
            raise FileExistsError(
                f"P2-38 first-run output contains unsafe metadata entry: {name}"
            )
    checkpoints = output / "checkpoints"
    if checkpoints.exists():
        if checkpoints.is_symlink() or not checkpoints.is_dir() or any(checkpoints.iterdir()):
            raise FileExistsError("P2-38 first-run output contains checkpoint state")
    metrics = output / "metrics.jsonl"
    if metrics.exists():
        if metrics.is_symlink() or not metrics.is_file() or metrics.stat().st_size > 1024 * 1024:
            raise FileExistsError("P2-38 first-run metrics are not safely recoverable")
        for line in metrics.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FileExistsError("P2-38 first-run metrics are malformed") from exc
            if not isinstance(event, dict) or event.get("event") != "run_started":
                raise FileExistsError("P2-38 first-run output shows progress beyond zero updates")
    shutil.rmtree(output)
    return True


def create_structured_plan_stage(
    *,
    base_checkpoint: Path,
    bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    preparation_contract_path: Path = DEFAULT_PREPARATION_CONTRACT,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Create a weights-only P2-38 stage from the official P2-35 step-100 endpoint."""
    contract = _preparation_contract(preparation_contract_path)
    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    if output.exists():
        raise FileExistsError("P2-38 stage output already exists")
    if (base_checkpoint.is_symlink() or not base_checkpoint.is_file()
            or sha256_file(base_checkpoint) != BASE_CHECKPOINT_SHA256):
        raise ValueError("P2-38 stage requires the exact official P2-35 step-100 checkpoint")
    bundle = inspect_structured_plan_bundle(bundle_dir, preparation_contract_path)
    model, payload = read_checkpoint(base_checkpoint, torch.device("cpu"))
    if (model.config != DEFAULT_CONFIG or parameter_count(model) != DEFAULT_CONFIG.parameter_count()
            or payload.get("step") != BASE_CHECKPOINT_STEP
            or payload.get("seed") != SEED
            or payload.get("codec") != CODEC
            or not isinstance(payload.get("initializationRecord"), dict)
            or payload["initializationRecord"].get("pretrainedCheckpointLoaded") is not False
            or payload["initializationRecord"].get("pretrainedModelWeightsLoaded") is not False
            or not isinstance(payload.get("stageTransitionRecord"), dict)
            or payload["stageTransitionRecord"].get("milestone") != "P2-35"
            or not isinstance(payload.get("trainingSettings"), dict)
            or payload["trainingSettings"].get("kind") != "p2-35-authorized-serialization-stability-training-v1"):
        raise ValueError("P2-35 endpoint provenance does not satisfy the P2-38 stage contract")
    source_tokenizer = payload.get("tokenizerRecord")
    if (not isinstance(source_tokenizer, dict)
            or source_tokenizer.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256
            or source_tokenizer.get("actualVocabularySize") != 16384):
        raise ValueError("P2-35 endpoint tokenizer identity differs from P2-38")
    if contract.get("baseCheckpoint", {}).get("sha256") != BASE_CHECKPOINT_SHA256:
        raise ValueError("P2-38 preparation contract base checkpoint changed")

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-38 optimizer unexpectedly contains state")
    rng = random.Random(SEED)
    transition = {
        "schemaVersion": 1,
        "kind": STAGE_KIND,
        "milestone": MILESTONE,
        "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
        "baseCheckpointStep": BASE_CHECKPOINT_STEP,
        "baseMilestone": "P2-35",
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "modelWeightsLoadedFromBase": True,
        "baseOptimizerStateReused": False,
        "baseSamplerStateReused": False,
        "baseTrainingStepReusedAsP238Step": False,
        "p238StageStep": 0,
        "modelTrainingPerformed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    checkpoint = output / "stage-checkpoint.pt"
    try:
        save_checkpoint(
            model,
            optimizer,
            step=0,
            seed=SEED,
            codec=CODEC,
            sampling_rng=rng,
            device=torch.device("cpu"),
            destination=checkpoint,
            artifact_root=root,
            initialization_record=payload["initializationRecord"],
            stage_transition_record=transition,
            tokenizer_record=bundle["tokenizer"],
            dataset_record=bundle["dataset"],
            training_settings=None,
            schedule_state=None,
            tokens_processed_total=0,
        )
        saved_model, saved = read_checkpoint(checkpoint, torch.device("cpu"))
        weights_equal = all(
            torch.equal(value, saved_model.state_dict()[name])
            for name, value in model.state_dict().items()
        )
        if (not weights_equal
                or saved.get("optimizerStateDict", {}).get("state") != {}
                or saved.get("step") != 0
                or saved.get("tokensProcessedTotal") != 0
                or saved.get("samplingRngState") != random.Random(SEED).getstate()
                or saved.get("stageTransitionRecord") != transition
                or saved.get("tokenizerRecord") != bundle["tokenizer"]
                or saved.get("datasetRecord") != bundle["dataset"]):
            raise ValueError("Saved P2-38 stage failed weights/state verification")
        report = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "trainingPerformed": False,
            "researchOptimizerUpdates": 0,
            "finalHoldoutOpened": False,
            "baseCheckpointSha256": BASE_CHECKPOINT_SHA256,
            "stageCheckpointSha256": sha256_file(checkpoint),
            "stageCheckpoint": "stage-checkpoint.pt",
            "parameterCount": parameter_count(model),
            "modelWeightsPreserved": weights_equal,
            "modelWeightEqualityMethod": "torch.equal for every model-state tensor after reload",
            "optimizerStateReused": False,
            "samplerStateReset": True,
            "p238StageStep": 0,
            "p238TokensProcessed": 0,
            "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
            "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "stageTransition": transition,
        }
        (output / "stage-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > storage_limit_bytes:
            raise ValueError("P2-38 stage exceeds remaining artifact storage allocation")
        return report
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def _verify_stage(
    stage_checkpoint: Path,
    bundle: dict[str, Any],
) -> tuple[torch.nn.Module, dict[str, Any]]:
    if stage_checkpoint.is_symlink() or not stage_checkpoint.is_file():
        raise ValueError("P2-38 stage checkpoint must be a regular file")
    model, payload = read_checkpoint(stage_checkpoint, torch.device("cpu"))
    if (model.config != DEFAULT_CONFIG
            or payload.get("step") != 0
            or payload.get("tokensProcessedTotal") != 0
            or payload.get("seed") != SEED
            or payload.get("codec") != CODEC
            or payload.get("optimizerStateDict", {}).get("state") != {}
            or payload.get("trainingSettings") is not None
            or payload.get("scheduleState") is not None
            or payload.get("samplingRngState") != random.Random(SEED).getstate()
            or payload.get("tokenizerRecord") != bundle["tokenizer"]
            or payload.get("datasetRecord") != bundle["dataset"]):
        raise ValueError("P2-38 stage checkpoint is not untouched step zero")
    transition = payload.get("stageTransitionRecord")
    if (not isinstance(transition, dict)
            or transition.get("kind") != STAGE_KIND
            or transition.get("milestone") != MILESTONE
            or transition.get("baseCheckpointSha256") != BASE_CHECKPOINT_SHA256
            or transition.get("baseCheckpointStep") != BASE_CHECKPOINT_STEP
            or transition.get("candidateSha256") != EXPECTED_CANDIDATE_SHA256
            or transition.get("modelWeightsLoadedFromBase") is not True
            or transition.get("baseOptimizerStateReused") is not False
            or transition.get("baseSamplerStateReused") is not False
            or transition.get("baseTrainingStepReusedAsP238Step") is not False
            or transition.get("p238StageStep") != 0
            or transition.get("modelTrainingPerformed") is not False):
        raise ValueError("P2-38 stage transition provenance is invalid")
    return model, payload


def _draft_authorization(contract: dict[str, Any]) -> bool:
    return (
        contract.get("schemaVersion") == 1
        and contract.get("milestone") == MILESTONE
        and contract.get("kind") == AUTHORIZATION_KIND
        and contract.get("status") == "draft-awaiting-owner-review"
        and contract.get("modelTrainingAuthorized") is False
        and contract.get("approvedBy") is None
    )


def _validate_authorization(contract: dict[str, Any]) -> None:
    _require_exact(contract.get("schemaVersion"), 1, "schemaVersion")
    _require_exact(contract.get("milestone"), MILESTONE, "milestone")
    _require_exact(contract.get("kind"), AUTHORIZATION_KIND, "kind")
    _require_exact(contract.get("status"), AUTHORIZED_STATUS, "status")
    _require_exact(contract.get("modelTrainingAuthorized"), True, "modelTrainingAuthorized")
    _require_exact(contract.get("approvedBy"), AUTHORIZED_APPROVER, "approvedBy")
    _require_exact(contract.get("outputDirectory"), AUTHORIZED_OUTPUT_DIRECTORY, "outputDirectory")
    execution = contract.get("executionState")
    if not isinstance(execution, dict):
        raise ValueError("P2-38 execution-state gate is missing")
    for key, expected in {
        "trainingExecuted": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }.items():
        _require_exact(execution.get(key), expected, f"executionState.{key}")
    training = contract.get("training")
    if not isinstance(training, dict):
        raise ValueError("P2-38 training authorization is missing")
    expected = {
        "objective": "ordinary-next-token-v1",
        "optimizer": "AdamW",
        "learningRate": ADAMW_LEARNING_RATE,
        "betas": list(ADAMW_BETAS),
        "epsilon": ADAMW_EPSILON,
        "weightDecay": ADAMW_WEIGHT_DECAY,
        "gradientClippingNorm": GRADIENT_CLIP_NORM,
        "schedule": SCHEDULE_KIND,
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "device": "cuda",
        "seed": SEED,
        "contextLength": DEFAULT_CONFIG.context_length,
        "dropout": DEFAULT_CONFIG.dropout,
        "resumeAllowed": False,
        "automaticContinuation": False,
    }
    for key, value in expected.items():
        _require_exact(training.get(key), value, f"training.{key}")
    for key, value in {
        "steps": list(VALIDATION_STEPS),
        "maximumBatches": VALIDATION_MAXIMUM_BATCHES,
        "checkpointSteps": list(CHECKPOINT_STEPS),
        "checkpointSelection":
            "Report fixed step-100 endpoint or early-stop endpoint; do not select the lowest-validation checkpoint",
    }.items():
        _require_exact(contract.get("evaluation", {}).get(key), value, f"evaluation.{key}")
    protected = contract.get("protectedEvaluation")
    if not isinstance(protected, dict):
        raise ValueError("P2-38 protected evaluation contract is missing")
    for key in (
        "validationExcludedFromGradients",
        "p231DevelopmentExcludedFromGradients",
        "p236ResponsesExcludedFromGradients",
        "p201bExcludedFromGradients",
        "finalProjectHoldoutMustRemainClosed",
    ):
        _require_exact(protected.get(key), True, f"protectedEvaluation.{key}")


def preflight_structured_plan_training(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
    require_cuda: bool = True,
) -> dict[str, Any]:
    """Verify stage/data/runtime and return identities; never update weights."""
    _preparation_contract(preparation_contract_path)
    bundle = inspect_structured_plan_bundle(bundle_dir, preparation_contract_path)
    model, payload = _verify_stage(stage_checkpoint, bundle)
    auth = _json(authorization_contract_path)
    draft = _draft_authorization(auth)
    authorized = False
    if not draft:
        _validate_authorization(auth)
        authorized = True

    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    expected_output = path_within_root(root / AUTHORIZED_OUTPUT_DIRECTORY, root)
    if output != expected_output:
        raise ValueError("P2-38 first run must use the locked output directory")
    if output.exists():
        raise FileExistsError("P2-38 first-run output exists; resume/overwrite are forbidden")
    if require_cuda:
        select_device("cuda")

    tokenizer = PlexTokenizer.load(bundle["root"])
    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train:
        expected_positions, _ = train.replay_progress(
            SEED, MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION
        )
        sampler = train.sampler_record

    device = select_device("cuda") if require_cuda else torch.device("cpu")
    model = model.to(device)
    with TokenCorpus(bundle["validationPath"]) as validation:
        baseline_loss = _validation_loss(
            model,
            validation,
            device,
            maximum_batches=VALIDATION_MAXIMUM_BATCHES,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
        )
    del model

    if authorized:
        base = auth.get("baseStage", {})
        data = auth.get("data", {})
        training = auth.get("training", {})
        _require_exact(base.get("checkpointSha256"), sha256_file(stage_checkpoint),
                       "baseStage.checkpointSha256")
        _require_exact(base.get("p238Step"), 0, "baseStage.p238Step")
        expected_data = {
            "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
            "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
            "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
            "trainRecords": 72,
            "validationRecords": 36,
        }
        for key, value in expected_data.items():
            _require_exact(data.get(key), value, f"data.{key}")
        _require_exact(training.get("sampler"), sampler, "training.sampler")
        _require_exact(training.get("expectedRealTargetPositionsAt100Steps"), expected_positions,
                       "training.expectedRealTargetPositionsAt100Steps")
        evaluation = auth["evaluation"]
        if not math.isclose(
            float(evaluation.get("baselineLoss")),
            baseline_loss,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("P2-38 baseline loss differs from authorization")

    return {
        "schemaVersion": 1,
        "milestone": MILESTONE,
        "authorized": authorized,
        "authorizationStatus": auth.get("status"),
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
        "candidateSha256": EXPECTED_CANDIDATE_SHA256,
        "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
        "stageCheckpointSha256": sha256_file(stage_checkpoint),
        "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
        "trainRecords": 72,
        "validationRecords": 36,
        "trainJsonlSha256": bundle["dataset"]["trainJsonlSha256"],
        "validationJsonlSha256": bundle["dataset"]["validationJsonlSha256"],
        "trainIndexSha256": bundle["dataset"]["trainIndexSha256"],
        "validationIndexSha256": bundle["dataset"]["validationIndexSha256"],
        "trainTokenCount": bundle["dataset"]["trainTokenCount"],
        "validationTokenCount": bundle["dataset"]["validationTokenCount"],
        "sampler": sampler,
        "expectedExamplesAt100Steps": MAXIMUM_STEPS * MICRO_BATCH * GRADIENT_ACCUMULATION,
        "expectedRealTargetPositionsAt100Steps": expected_positions,
        "baselineValidationLoss": baseline_loss,
        "baselineValidationBatches": min(
            VALIDATION_MAXIMUM_BATCHES,
            bundle["dataset"]["validationTokenCount"] // DEFAULT_CONFIG.context_length,
        ),
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "device": "cuda" if require_cuda else "cpu",
        "outputWouldBe": str(output.relative_to(root)),
    }


def _training_settings(contract_sha: str, sampler: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "kind": "p2-38-authorized-semantic-binding-training-v1",
        "authorizationContractSha256": contract_sha,
        "objective": "ordinary-next-token-v1",
        "microBatch": MICRO_BATCH,
        "gradientAccumulation": GRADIENT_ACCUMULATION,
        "optimizer": {
            "kind": "AdamW",
            "learningRate": ADAMW_LEARNING_RATE,
            "betas": list(ADAMW_BETAS),
            "epsilon": ADAMW_EPSILON,
            "weightDecay": ADAMW_WEIGHT_DECAY,
        },
        "gradientClippingNorm": GRADIENT_CLIP_NORM,
        "learningRateSchedule": SCHEDULE_KIND,
        "maximumSteps": MAXIMUM_STEPS,
        "maximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
        "resumeAllowed": False,
        "automaticContinuation": False,
        "samplingPolicy": sampler,
    }


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _save_checkpoint(
    *,
    path: Path,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    step: int,
    rng: random.Random,
    device: torch.device,
    artifact_root: Path,
    payload: dict[str, Any],
    bundle: dict[str, Any],
    settings: dict[str, Any],
    tokens_processed: int,
) -> dict[str, Any]:
    saved = save_checkpoint(
        model,
        optimizer,
        step=step,
        seed=SEED,
        codec=CODEC,
        sampling_rng=rng,
        device=device,
        destination=path,
        artifact_root=artifact_root,
        initialization_record=payload["initializationRecord"],
        stage_transition_record=payload["stageTransitionRecord"],
        tokenizer_record=bundle["tokenizer"],
        dataset_record=bundle["dataset"],
        training_settings=settings,
        schedule_state={"kind": SCHEDULE_KIND, "step": step, "learningRate": ADAMW_LEARNING_RATE},
        tokens_processed_total=tokens_processed,
    )
    _, checked = read_checkpoint(path, torch.device("cpu"))
    if (checked.get("step") != step
            or checked.get("tokensProcessedTotal") != tokens_processed
            or checked.get("stageTransitionRecord") != payload["stageTransitionRecord"]
            or checked.get("trainingSettings") != settings
            or checked.get("datasetRecord") != bundle["dataset"]
            or checked.get("tokenizerRecord") != bundle["tokenizer"]):
        raise ValueError("Saved P2-38 checkpoint failed identity verification")
    return {**saved, "sha256": sha256_file(path)}


def run_structured_plan_training(
    *,
    bundle_dir: Path,
    stage_checkpoint: Path,
    authorization_contract_path: Path,
    preparation_contract_path: Path,
    output_dir: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Execute only an explicitly owner-authorized P2-38 first run."""
    auth = _json(authorization_contract_path)
    _validate_authorization(auth)
    root = artifact_root.resolve()
    output = path_within_root(output_dir, root)
    recovered_zero_update_output = _clear_aborted_zero_update_output(output)
    preflight = preflight_structured_plan_training(
        bundle_dir=bundle_dir,
        stage_checkpoint=stage_checkpoint,
        authorization_contract_path=authorization_contract_path,
        preparation_contract_path=preparation_contract_path,
        output_dir=output_dir,
        artifact_root=artifact_root,
        require_cuda=True,
    )
    if not preflight["authorized"]:
        raise ValueError("P2-38 model training is not authorized")
    bundle = inspect_structured_plan_bundle(bundle_dir, preparation_contract_path)
    model, payload = _verify_stage(stage_checkpoint, bundle)
    device = select_device("cuda")
    enforce_storage_limit(root, additional_bytes=2 * 1024**3)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    checkpoints_dir = output / "checkpoints"
    checkpoints_dir.mkdir()
    metrics_path = output / "metrics.jsonl"

    seed_everything(SEED)
    rng = random.Random(SEED)
    model = model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=ADAMW_LEARNING_RATE,
        betas=ADAMW_BETAS,
        weight_decay=ADAMW_WEIGHT_DECAY,
        eps=ADAMW_EPSILON,
    )
    if optimizer.state:
        raise RuntimeError("Fresh P2-38 optimizer unexpectedly contains state")
    tokenizer = PlexTokenizer.load(bundle["root"])
    auth_sha = sha256_file(authorization_contract_path)
    source_sha = sha256_file(stage_checkpoint)

    with StructuredPlanCompleteRecordCorpus(
        bundle["trainPath"],
        dataset_jsonl=bundle["root"] / "train.jsonl",
        index_path=bundle["root"] / "train.index.json",
        tokenizer=tokenizer,
        expected_jsonl_sha256=bundle["dataset"]["trainJsonlSha256"],
    ) as train, TokenCorpus(bundle["validationPath"]) as validation:
        _require_exact(train.sampler_record, auth["training"]["sampler"], "runtime sampler")
        settings = _training_settings(auth_sha, train.sampler_record)
        reset_peak_gpu_memory(device)
        baseline = _validation_loss(
            model,
            validation,
            device,
            maximum_batches=VALIDATION_MAXIMUM_BATCHES,
            loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
        )
        if not math.isclose(
            baseline,
            float(auth["evaluation"]["baselineLoss"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("P2-38 stage-zero baseline changed before training")

        started = time.perf_counter()
        deadline = started + MAXIMUM_WALL_SECONDS
        validations = [{"step": 0, "meanLoss": baseline}]
        losses: list[float] = []
        tokens_seen = 0
        padding_seen = 0
        saved_checkpoints: list[dict[str, Any]] = []
        interrupted = False
        _append_jsonl(metrics_path, {
            "event": "run_started",
            "startedAtUtc": datetime.now(timezone.utc).isoformat(),
            "authorizationContractSha256": auth_sha,
            "stageCheckpointSha256": source_sha,
            "trainingSettings": settings,
            "environment": environment_report(device),
        })
        try:
            while len(losses) < MAXIMUM_STEPS and time.perf_counter() < deadline:
                loss, real_positions, padding_positions = _structured_plan_training_step(
                    model,
                    optimizer,
                    train,
                    rng,
                    device,
                    micro_batch=MICRO_BATCH,
                    accumulation_steps=GRADIENT_ACCUMULATION,
                    loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                )
                step = len(losses) + 1
                losses.append(loss)
                tokens_seen += real_positions
                padding_seen += padding_positions
                _append_jsonl(metrics_path, {
                    "event": "training_progress",
                    "step": step,
                    "loss": loss,
                    "tokensProcessedTotal": tokens_seen,
                    "elapsedSeconds": time.perf_counter() - started,
                })
                if step in VALIDATION_STEPS:
                    value = _validation_loss(
                        model,
                        validation,
                        device,
                        maximum_batches=VALIDATION_MAXIMUM_BATCHES,
                        loss_vocabulary_size=bundle["tokenizer"]["actualVocabularySize"],
                    )
                    validations.append({"step": step, "meanLoss": value})
                    _append_jsonl(metrics_path, {"event": "validation", "step": step, "meanLoss": value})
                if step in CHECKPOINT_STEPS:
                    saved = _save_checkpoint(
                        path=checkpoints_dir / f"step-{step:04d}.pt",
                        model=model,
                        optimizer=optimizer,
                        step=step,
                        rng=rng,
                        device=device,
                        artifact_root=root,
                        payload=payload,
                        bundle=bundle,
                        settings=settings,
                        tokens_processed=tokens_seen,
                    )
                    saved_checkpoints.append(saved)
                    _append_jsonl(metrics_path, {"event": "checkpoint_saved", **saved})
        except KeyboardInterrupt:
            interrupted = True

        completed_steps = len(losses)
        final = next((item for item in saved_checkpoints if item["step"] == completed_steps), None)
        if final is None:
            final = _save_checkpoint(
                path=checkpoints_dir / f"step-{completed_steps:04d}-final.pt",
                model=model,
                optimizer=optimizer,
                step=completed_steps,
                rng=rng,
                device=device,
                artifact_root=root,
                payload=payload,
                bundle=bundle,
                settings=settings,
                tokens_processed=tokens_seen,
            )
            saved_checkpoints.append(final)
        if sha256_file(stage_checkpoint) != source_sha:
            raise ValueError("P2-38 stage source changed during training")
        result = {
            "schemaVersion": 1,
            "milestone": MILESTONE,
            "kind": "p2-38-first-semantic-binding-run-result-v1",
            "trainingPerformed": completed_steps > 0,
            "researchOptimizerUpdates": completed_steps,
            "authorizedMaximumSteps": MAXIMUM_STEPS,
            "authorizedMaximumWallTimeSeconds": MAXIMUM_WALL_SECONDS,
            "automaticContinuation": False,
            "resumeAllowed": False,
            "continuationAuthorized": False,
            "finalHoldoutOpened": False,
            "interrupted": interrupted,
            "elapsedSeconds": time.perf_counter() - started,
            "stageCheckpointSha256": source_sha,
            "authorizationContractSha256": auth_sha,
            "bundleManifestSha256": sha256_file(bundle["root"] / "manifest.json"),
            "candidateSha256": EXPECTED_CANDIDATE_SHA256,
            "tokenizerSha256": bundle["tokenizer"]["tokenizerSha256"],
            "completedSteps": completed_steps,
            "tokensProcessed": tokens_seen,
            "paddingTargetPositions": padding_seen,
            "meanRecentLoss": sum(losses[-20:]) / len(losses[-20:]) if losses else None,
            "validation": validations,
            "samplingAudit": train.sampling_audit(),
            "checkpoints": saved_checkpoints,
            "finalCheckpoint": final,
            "peakGpuMemory": peak_gpu_memory(device),
            "p231DevelopmentEvaluationPending": True,
            "recoveredZeroUpdateOutput": recovered_zero_update_output,
        }

    result_path = output / "run-result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    enforce_storage_limit(root)
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "result": str(result_path.relative_to(root)),
        "metrics": str(metrics_path.relative_to(root)),
    }
