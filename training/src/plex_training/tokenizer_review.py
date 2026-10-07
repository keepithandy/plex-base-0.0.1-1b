"""P2-27 tokenizer review for the frozen Plex Web corpus.

Candidate tokenizers are always fitted by the existing train-only tokenizer pipeline.
This module measures compression/roundtrip behavior; it does not initialize or train
model weights.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .config import DEFAULT_CONFIG
from .tokenizer import PlexTokenizer, sha256_file, train_tokenizer


REVIEW_SAMPLES: tuple[tuple[str, str], ...] = (
    (
        "html",
        '<section class="card" data-state="ready">\n'
        '  <button type="button" aria-label="Save">Save</button>\n'
        '</section>\n',
    ),
    (
        "css",
        '.card[data-state="ready"] {\n'
        '  display: grid;\n'
        '  gap: 1rem;\n'
        '  color: var(--text-color);\n'
        '}\n',
    ),
    (
        "javascript",
        'export function togglePanel(panel, open) {\n'
        '  panel.hidden = !open;\n'
        '  panel.dataset.state = open ? "open" : "closed";\n'
        '}\n',
    ),
    (
        "plex-task-format",
        '{"intent":"replace","language":"CSS","targetKind":"CSS_PROPERTY",'
        '"targetRole":"declaration-value","request":"Increase the card gap to 1rem."}\n',
    ),
    (
        "ordinary-text",
        "Update the existing navigation without changing unrelated behavior.\n",
    ),
)


def _sha256_text(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dataset_split_rows(dataset_dir: Path, split: str) -> Iterable[dict[str, Any]]:
    path = dataset_dir / f"{split}.jsonl"
    with path.open("r", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"Blank line in {split}.jsonl at line {line_number}")
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                raise ValueError(f"Invalid {split}.jsonl row at line {line_number}")
            yield row


def _measure_split(tokenizer: PlexTokenizer, dataset_dir: Path, split: str) -> dict[str, Any]:
    records = 0
    text_bytes = 0
    token_count = 0
    for row in _dataset_split_rows(dataset_dir, split):
        text = row["text"]
        ids = tokenizer.encode(text)
        if tokenizer.decode(ids) != text:
            raise ValueError(f"Tokenizer failed exact roundtrip for {split} record {row.get('recordId')!r}")
        records += 1
        text_bytes += len(text.encode("utf-8"))
        token_count += len(ids)
    if records == 0 or token_count == 0:
        raise ValueError(f"Dataset {split} split must contain encodable text")
    return {
        "records": records,
        "textBytes": text_bytes,
        "textTokens": token_count,
        "bytesPerTextToken": text_bytes / token_count,
        "tokensPerKiB": token_count * 1024 / text_bytes,
        "roundtripRecords": records,
    }


def _measure_samples(tokenizer: PlexTokenizer) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total_bytes = 0
    total_tokens = 0
    for sample_id, text in REVIEW_SAMPLES:
        ids = tokenizer.encode(text)
        if tokenizer.decode(ids) != text:
            raise ValueError(f"Tokenizer failed exact roundtrip for review sample {sample_id!r}")
        byte_count = len(text.encode("utf-8"))
        token_count = len(ids)
        total_bytes += byte_count
        total_tokens += token_count
        rows.append(
            {
                "id": sample_id,
                "bytes": byte_count,
                "tokens": token_count,
                "bytesPerToken": byte_count / token_count,
            }
        )
    return {
        "samples": rows,
        "totalBytes": total_bytes,
        "totalTokens": total_tokens,
        "bytesPerToken": total_bytes / total_tokens,
        "allRoundtripsExact": True,
    }


def _measure_bundle(directory: Path, dataset_dir: Path) -> dict[str, Any]:
    tokenizer = PlexTokenizer.load(directory)
    config_path = directory / "tokenizer-config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "tokenizerSha256": config["tokenizerSha256"],
        "actualVocabularySize": tokenizer.vocabulary_size,
        "train": _measure_split(tokenizer, dataset_dir, "train"),
        "validation": _measure_split(tokenizer, dataset_dir, "validation"),
        "reviewSamples": _measure_samples(tokenizer),
    }


def review_tokenizers(
    dataset_dir: Path,
    output_dir: Path,
    *,
    vocab_sizes: list[int],
    min_frequency: int = 2,
    baseline_tokenizer: Path | None = None,
    storage_limit_bytes: int = 200 * 1024**3,
) -> dict[str, Any]:
    """Fit and measure fresh train-only tokenizer candidates for P2-27."""
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage remains for tokenizer review")
    if not vocab_sizes:
        raise ValueError("At least one tokenizer vocabulary size is required")
    if any(type(value) is not int for value in vocab_sizes):
        raise ValueError("Tokenizer vocabulary sizes must be integers")
    sizes = sorted(set(vocab_sizes))
    if any(value < 260 or value > DEFAULT_CONFIG.vocab_size for value in sizes):
        raise ValueError(
            f"Tokenizer vocabulary sizes must be 260..{DEFAULT_CONFIG.vocab_size}"
        )
    if type(min_frequency) is not int or min_frequency < 1:
        raise ValueError("min-frequency must be a positive integer")

    dataset_dir = dataset_dir.resolve(strict=True)
    output_dir = output_dir.resolve(strict=False)
    if output_dir.exists():
        raise FileExistsError("Tokenizer review output already exists")
    if output_dir == dataset_dir or dataset_dir in output_dir.parents or output_dir in dataset_dir.parents:
        raise ValueError("Tokenizer review output must be separate from the source dataset")

    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Tokenizer review dataset is missing manifest.json")
    dataset_manifest_sha = sha256_file(manifest_path)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent)
    ).resolve()
    staging.relative_to(output_dir.parent.resolve())

    remaining = storage_limit_bytes
    candidates: list[dict[str, Any]] = []
    try:
        candidate_root = staging / "candidates"
        candidate_root.mkdir()
        for vocab_size in sizes:
            relative = Path("candidates") / f"vocab-{vocab_size}"
            candidate_dir = staging / relative
            trained = train_tokenizer(
                dataset_dir,
                candidate_dir,
                vocab_size=vocab_size,
                min_frequency=min_frequency,
                storage_limit_bytes=remaining,
            )
            remaining -= trained["bundleBytes"]
            if remaining <= 0:
                raise ValueError("Tokenizer review exceeded remaining artifact storage")
            measured = _measure_bundle(candidate_dir, dataset_dir)
            candidates.append(
                {
                    "requestedVocabularySize": vocab_size,
                    "bundleDirectory": relative.as_posix(),
                    "bundleBytes": trained["bundleBytes"],
                    **measured,
                }
            )

        baseline: dict[str, Any] | None = None
        if baseline_tokenizer is not None:
            baseline_path = baseline_tokenizer.resolve(strict=True)
            baseline = {
                "directory": str(baseline_path),
                **_measure_bundle(baseline_path, dataset_dir),
            }

        best_validation = max(
            candidates,
            key=lambda row: row["validation"]["bytesPerTextToken"],
        )
        best_samples = max(
            candidates,
            key=lambda row: row["reviewSamples"]["bytesPerToken"],
        )

        report: dict[str, Any] = {
            "schemaVersion": 1,
            "kind": "plex-p2-27-tokenizer-review-v1",
            "datasetDirectory": dataset_dir.name,
            "datasetManifestSha256": dataset_manifest_sha,
            "fitPolicy": "candidate vocabularies are fitted on train.jsonl text only",
            "validationUsedForFitting": False,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "minFrequency": min_frequency,
            "requestedVocabularySizes": sizes,
            "candidateCount": len(candidates),
            "candidates": candidates,
            "baseline": baseline,
            "informationalLeaders": {
                "validationCompressionVocabularySize": best_validation["requestedVocabularySize"],
                "reviewSampleCompressionVocabularySize": best_samples["requestedVocabularySize"],
            },
            "selectionPolicy": {
                "automaticPromotion": False,
                "requirements": [
                    "exact roundtrip on all train and validation records",
                    "exact roundtrip on representative HTML/CSS/JavaScript/Plex-task samples",
                    "fit only the training split",
                    "review compression against vocabulary size before freezing a tokenizer",
                    "do not initialize or train Plex weights during P2-27",
                ],
            },
            "scratchTrainingBoundary": {
                "pretrainedTokenizerLoadedForCandidateFit": False,
                "pretrainedModelWeightsLoaded": False,
                "modelTrainingPerformed": False,
            },
        }

        report_bytes = (
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode("utf-8")
        if len(report_bytes) > remaining:
            raise ValueError("Tokenizer review report exceeds remaining artifact storage")
        (staging / "review.json").write_bytes(report_bytes)
        review_sha = _sha256_text(report_bytes)
        (staging / "review.sha256").write_text(
            review_sha + "  review.json\n",
            encoding="utf-8",
            newline="\n",
        )
        os.rename(staging, output_dir)
        return {
            "directory": output_dir.name,
            "review": "review.json",
            "reviewSha256": review_sha,
            "datasetManifestSha256": dataset_manifest_sha,
            "candidateCount": len(candidates),
            "candidates": [
                {
                    "requestedVocabularySize": row["requestedVocabularySize"],
                    "actualVocabularySize": row["actualVocabularySize"],
                    "tokenizerSha256": row["tokenizerSha256"],
                    "trainBytesPerTextToken": row["train"]["bytesPerTextToken"],
                    "validationBytesPerTextToken": row["validation"]["bytesPerTextToken"],
                    "reviewSampleBytesPerToken": row["reviewSamples"]["bytesPerToken"],
                }
                for row in candidates
            ],
            "informationalLeaders": report["informationalLeaders"],
            "automaticPromotion": False,
            "modelTrainingPerformed": False,
        }
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
