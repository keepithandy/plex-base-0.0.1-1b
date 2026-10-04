"""Fit Plex's byte-level BPE locally, exclusively on reviewed training text.

No pretrained tokenizer, model, network client, or PyTorch import is used here.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from array import array
from pathlib import Path
from typing import Any, Iterator

import tokenizers
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

from .config import DEFAULT_CONFIG

CODEC = "plex-byte-bpe-v1"
SPECIAL_TOKENS = ["<|pad|>", "<|unk|>", "<|bos|>", "<|eos|>"]
ROUNDTRIP_SAMPLES = [
    '<main class="panel">\n  <h1>Plex &amp; friends</h1>\n</main>\n',
    '.panel {\n\tcolor: #fff; margin: 0  1rem;\n}\n',
    'function greet(name) {\r\n  return `Hello ${name}!`;\r\n}\r\n',
    'Ordinary text: café, e\u0301, 日本語, Ελληνικά, مرحبا, 🧑🏽‍💻.\n',
    '  leading spaces\t\tand trailing spaces  \n\n',
    'const quote = "\\n\\t\\\""; // <|pad|> <|unk|> <|bos|> <|eos|>\n',
    '',
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Manifest/config exceeds the 1 MiB limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Manifest/config must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def _local_file(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink():
        raise ValueError("Dataset files must not be symbolic links")
    canonical = path.resolve(strict=True)
    canonical.relative_to(root)
    if not canonical.is_file():
        raise ValueError("Expected a regular dataset file")
    return canonical


def _records(path: Path, expected_hash: str, expected_count: int,
             sources: dict[str, str]) -> Iterator[dict[str, Any]]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while line := stream.readline(8 * 1024 * 1024 + 1):
            if len(line) > 8 * 1024 * 1024:
                raise ValueError("JSONL record exceeds the 8 MiB limit")
            digest.update(line)
            row = json.loads(line)
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) for key in
                    ("text", "recordId", "sourceId", "groupId", "contentSha256")):
                raise ValueError("Invalid curated JSONL record")
            raw = row["text"].encode("utf-8")
            if not raw or len(raw) > 1024 * 1024:
                raise ValueError("Source text must be nonempty and at most 1 MiB")
            if hashlib.sha256(raw).hexdigest() != row["contentSha256"]:
                raise ValueError("Record content hash does not match its text")
            if sources.get(row["sourceId"]) != row["groupId"]:
                raise ValueError("Record source/group is not in the approved manifest")
            count += 1
            yield row
    if digest.hexdigest() != expected_hash or count != expected_count or count == 0:
        raise ValueError("Dataset split hash/count does not match its manifest")


class PlexTokenizer:
    """Local tokenizer wrapper; literal control marker text stays ordinary text."""

    def __init__(self, backend: Tokenizer) -> None:
        self.backend = backend
        # Prevent literal '<|eos|>' in source code from becoming a control token.
        self.backend.encode_special_tokens = True
        self.vocabulary_size = backend.get_vocab_size()
        for token_id, spelling in enumerate(SPECIAL_TOKENS):
            if backend.token_to_id(spelling) != token_id:
                raise ValueError("Unexpected Plex special-token IDs")

    @classmethod
    def load(cls, directory: Path) -> "PlexTokenizer":
        settings = _read_json(directory / "tokenizer-config.json")
        if settings.get("codec") != CODEC:
            raise ValueError("Unsupported Plex tokenizer codec")
        if sha256_file(directory / "tokenizer.json") != settings.get("tokenizerSha256"):
            raise ValueError("Tokenizer hash does not match its settings")
        instance = cls(Tokenizer.from_file(str(directory / "tokenizer.json")))
        if instance.vocabulary_size != settings.get("actualVocabularySize"):
            raise ValueError("Tokenizer vocabulary does not match its settings")
        return instance

    def encode(self, text: str) -> list[int]:
        ids = self.backend.encode(text, add_special_tokens=False).ids
        if any(value < len(SPECIAL_TOKENS) or value >= self.vocabulary_size for value in ids):
            raise ValueError("Plain text encoded to an unknown/control/out-of-range token")
        return ids

    def decode(self, ids: list[int]) -> str:
        if any(value < 0 or value >= self.vocabulary_size for value in ids):
            raise ValueError("Token ID is outside the tokenizer vocabulary")
        return self.backend.decode(ids, skip_special_tokens=False)


def train_tokenizer(dataset_dir: Path, output_dir: Path, *, vocab_size: int = 16_384,
                    min_frequency: int = 2, storage_limit_bytes: int = 200 * 1024**3) -> dict[str, Any]:
    """Create a fresh tokenizer bundle; publish only after every check succeeds."""
    if type(vocab_size) is not int or not 260 <= vocab_size <= DEFAULT_CONFIG.vocab_size:
        raise ValueError("vocab-size must be 260..16384 (within the model's capacity)")
    if type(min_frequency) is not int or min_frequency < 1:
        raise ValueError("min-frequency must be a positive integer")
    if storage_limit_bytes <= 0:
        raise ValueError("No artifact storage allocation remains")
    dataset_dir = dataset_dir.resolve(strict=True)
    output_dir = output_dir.resolve(strict=False)
    # Never publish inside the input dataset or replace its parent.
    if output_dir == dataset_dir or dataset_dir in output_dir.parents or output_dir in dataset_dir.parents:
        raise ValueError("Tokenizer output must be separate from the source dataset")
    if output_dir.exists():
        raise FileExistsError("Refusing to overwrite an existing tokenizer bundle")
    manifest_path = _local_file(dataset_dir, "manifest.json")
    source_manifest_hash = sha256_file(manifest_path)
    manifest = _read_json(manifest_path)
    if manifest.get("schemaVersion") != 1 or manifest.get("pipelineVersion") != "p1-14.2":
        raise ValueError("Expected a P1-14.2 curated dataset manifest")
    source_rows = manifest.get("sources")
    if not isinstance(source_rows, list) or not source_rows:
        raise ValueError("Dataset must have approved source provenance")
    sources: dict[str, str] = {}
    notices: dict[str, bytes] = {}
    for source in source_rows:
        if not isinstance(source, dict):
            raise ValueError("Dataset source must be a JSON object")
        if source.get("rightsReviewStatus") != "approved":
            raise ValueError("All sources must have owner-approved rights reviews")
        source_id, group = source.get("id"), source.get("groupId")
        if not isinstance(source_id, str) or not isinstance(group, str) or source_id in sources:
            raise ValueError("Invalid or duplicate source identifiers")
        sources[source_id] = group
        relative = source.get("licenseNoticeFile", "")
        if (not isinstance(relative, str) or not relative.startswith("licenses/")
                or "\\" in relative or len(Path(relative).parts) != 2
                or Path(relative).parts[-1] in (".", "..")):
            raise ValueError("Missing packaged license notice")
        notice_path = _local_file(dataset_dir, relative)
        if notice_path.stat().st_size > 1024 * 1024:
            raise ValueError("License notice exceeds 1 MiB")
        raw = notice_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source.get("licenseNoticeSha256"):
            raise ValueError("Packaged license notice hash mismatch")
        if relative in notices and notices[relative] != raw:
            raise ValueError("Conflicting packaged license notices")
        notices[relative] = raw
    summary = manifest.get("summary", {})
    if not isinstance(summary, dict):
        raise ValueError("Dataset summary must be a JSON object")
    split_paths = {split: _local_file(dataset_dir, split + ".jsonl") for split in ("train", "validation")}

    def records(split: str) -> Iterator[dict[str, Any]]:
        expected_hash = summary.get(split + "JsonlSha256")
        expected_count = summary.get(split + "Records")
        if not isinstance(expected_hash, str) or type(expected_count) is not int:
            raise ValueError("Missing dataset split hash/count")
        return _records(split_paths[split], expected_hash, expected_count, sources)

    # Review both splits before fitting; only their groups/hashes enter this check.
    groups: dict[str, set[str]] = {}
    content_hashes: dict[str, set[str]] = {}
    for split in split_paths:
        groups[split], content_hashes[split] = set(), set()
        record_ids: set[str] = set()
        for row in records(split):
            if row["contentSha256"] in content_hashes[split] or row["recordId"] in record_ids:
                raise ValueError("Duplicate record/content in dataset")
            record_ids.add(row["recordId"])
            groups[split].add(row["groupId"])
            content_hashes[split].add(row["contentSha256"])
    if groups["train"] & groups["validation"] or content_hashes["train"] & content_hashes["validation"]:
        raise ValueError("Training and validation groups/content must be disjoint")

    backend = Tokenizer(models.BPE(unk_token=SPECIAL_TOKENS[1]))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    backend.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=vocab_size, min_frequency=min_frequency,
        special_tokens=SPECIAL_TOKENS, initial_alphabet=sorted(pre_tokenizers.ByteLevel.alphabet()),
        show_progress=False)
    backend.train_from_iterator((row["text"] for row in records("train")), trainer=trainer,
                                length=summary["trainRecords"])
    plex = PlexTokenizer(backend)
    for text in ROUNDTRIP_SAMPLES:
        if plex.decode(plex.encode(text)) != text:
            raise ValueError("Representative tokenizer roundtrip failed")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".plex-tokenizer-", dir=output_dir.parent)).resolve()
    # Bound cleanup now, before any recursive removal can occur on Windows.
    staging.relative_to(output_dir.parent.resolve())
    try:
        used_bytes = 0

        def budget() -> None:
            nonlocal used_bytes
            used_bytes = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
            if used_bytes > storage_limit_bytes:
                raise ValueError("Tokenizer bundle exceeds remaining artifact storage allocation")

        backend.save(str(staging / "tokenizer.json"))
        settings = {
            "schemaVersion": 1, "codec": CODEC, "algorithm": "byte-level BPE",
            "library": "tokenizers", "libraryVersion": tokenizers.__version__,
            "requestedVocabularySize": vocab_size, "actualVocabularySize": plex.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size, "minFrequency": min_frequency,
            "initialAlphabetBytes": 256, "normalization": "none",
            "addPrefixSpace": False, "useRegex": True,
            "specialTokens": dict(zip(SPECIAL_TOKENS, range(4))),
            "literalSpecialTokens": "encoded as ordinary text",
            "recordBoundary": "one manually appended EOS (id 3); no automatic BOS/PAD",
            "fitSplit": "train", "fitField": "text",
            "trainingJsonlSha256": summary["trainJsonlSha256"],
            "tokenizerSha256": sha256_file(staging / "tokenizer.json"),
        }
        _write_json(staging / "tokenizer-config.json", settings)
        _write_json(staging / "model-config.json", DEFAULT_CONFIG.to_dict())
        _write_json(staging / "source-dataset-manifest.json", manifest)
        for relative, raw in notices.items():
            target = staging / relative
            target.resolve().relative_to(staging)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        budget()
        split_info: dict[str, Any] = {}
        for split in split_paths:
            token_path = staging / (split + ".tokens.u16le")
            offsets: list[dict[str, Any]] = []
            token_count = text_bytes = 0
            with token_path.open("xb") as stream:
                for row in records(split):
                    ids = plex.encode(row["text"])
                    if plex.decode(ids) != row["text"]:
                        raise ValueError("Dataset record failed exact encode/decode roundtrip")
                    ids.append(3)
                    packed = array("H", ids)
                    if packed.itemsize != 2:
                        raise RuntimeError("Platform lacks uint16 arrays")
                    if sys.byteorder != "little":
                        packed.byteswap()
                    if used_bytes + len(packed) * 2 > storage_limit_bytes:
                        raise ValueError("Tokenizer corpora exceed remaining artifact storage allocation")
                    stream.write(packed.tobytes())
                    used_bytes += len(packed) * 2
                    offsets.append({"recordId": row["recordId"], "startToken": token_count,
                                    "tokenCount": len(ids)})
                    token_count += len(ids)
                    text_bytes += len(row["text"].encode("utf-8"))
            _write_json(staging / (split + ".index.json"), offsets)
            budget()
            split_info[split] = {"path": token_path.name, "sha256": sha256_file(token_path),
                "records": len(offsets), "tokenCount": token_count, "textBytes": text_bytes,
                "bytesPerTextToken": text_bytes / (token_count - len(offsets)),
                "roundtripRecords": len(offsets), "jsonlSha256": summary[split + "JsonlSha256"]}
        if sha256_file(manifest_path) != source_manifest_hash:
            raise ValueError("Source dataset manifest changed during tokenizer construction")
        _write_json(staging / "manifest.json", {
            "schemaVersion": 1, "codec": CODEC, "storageDtype": "uint16-le",
            "sourceDatasetManifestSha256": source_manifest_hash,
            "tokenizerSha256": settings["tokenizerSha256"],
            "modelConfigSha256": sha256_file(staging / "model-config.json"),
            "actualVocabularySize": plex.vocabulary_size,
            "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
            "representativeRoundtrips": len(ROUNDTRIP_SAMPLES), **split_info,
        })
        budget()
        # Reopen the saved tokenizer, not just the fitted object.
        loaded = PlexTokenizer.load(staging)
        for text in ROUNDTRIP_SAMPLES:
            if loaded.encode(text) != plex.encode(text) or loaded.decode(loaded.encode(text)) != text:
                raise ValueError("Saved tokenizer roundtrip differs from fitted tokenizer")
        os.rename(staging, output_dir)
        return {"codec": CODEC, "actualVocabularySize": plex.vocabulary_size,
                "modelVocabularyCapacity": DEFAULT_CONFIG.vocab_size,
                "tokenizerSha256": settings["tokenizerSha256"],
                "representativeRoundtrips": len(ROUNDTRIP_SAMPLES),
                "train": split_info["train"], "validation": split_info["validation"],
                "bundleBytes": used_bytes}
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
