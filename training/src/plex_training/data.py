"""Small streaming corpus format for the local training runner.

P1-13's bootstrap codec maps each UTF-8 source byte to token id 0..255 and
stores ids as little-endian uint16. P1-15 replaces this codec with Plex's
trained tokenizer without loading any external checkpoint.
"""

from __future__ import annotations

import hashlib
import codecs
import json
import mmap
import os
import random
import sys
from array import array
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

BYTE_VOCABULARY_SIZE = 256
TOKEN_FILE_SUFFIX = ".tokens.u16le"
DEFAULT_STORAGE_LIMIT_BYTES = 200 * 1024**3


def resolve_source_files(values: list[str]) -> list[Path]:
    if not values:
        raise ValueError("At least one input text file is required")
    resolved: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_symlink():
            raise ValueError(f"Input must not be a symbolic link: {path.name}")
        try:
            canonical = path.resolve(strict=True)
        except OSError as exc:
            raise ValueError(f"Input file is unavailable: {path}") from exc
        if not canonical.is_file():
            raise ValueError(f"Input must be a regular file: {path}")
        resolved.append(canonical)
    if len(set(resolved)) != len(resolved):
        raise ValueError("The same source file was provided more than once")
    return resolved


def write_byte_corpus(inputs: list[Path], output: Path, storage_limit: int) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing corpus: {output.name}")
    temporary = output.with_name(output.name + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Temporary corpus already exists: {temporary.name}")
    total_bytes = 0
    sources: list[dict[str, Any]] = []
    try:
        with temporary.open("xb") as destination:
            for source_path in inputs:
                digest = hashlib.sha256()
                source_bytes = 0
                utf8_decoder = codecs.getincrementaldecoder("utf-8")("strict")
                with source_path.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        utf8_decoder.decode(chunk, final=False)
                        source_bytes += len(chunk)
                        total_bytes += len(chunk) * 2
                        if total_bytes > storage_limit:
                            raise ValueError("Prepared corpora exceed the configured storage allocation")
                        # Iterate byte values: passing bytes directly is treated as
                        # a native uint16 buffer and would pack adjacent bytes together.
                        token_ids = array("H", iter(chunk))
                        if sys.byteorder != "little":
                            token_ids.byteswap()
                        destination.write(token_ids.tobytes())
                        digest.update(chunk)
                    utf8_decoder.decode(b"", final=True)
                # A newline prevents adjacent files from joining without a token boundary.
                if total_bytes + 2 > storage_limit:
                    raise ValueError("Prepared corpora exceed the configured storage allocation")
                destination.write(b"\n\x00")
                total_bytes += 2
                sources.append({
                    "name": source_path.name,
                    "sourceBytes": source_bytes,
                    "sha256": digest.hexdigest(),
                })
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "path": output.name,
        "codec": "byte-v1",
        "storageDtype": "uint16-le",
        "tokenCount": total_bytes // 2,
        "fileBytes": total_bytes,
        "sources": sources,
    }


def write_dataset_manifest(output_dir: Path, train_info: dict[str, Any], validation_info: dict[str, Any]) -> Path:
    manifest = {
        "schemaVersion": 1,
        "codec": "byte-v1",
        "vocabularySize": BYTE_VOCABULARY_SIZE,
        "tokenStorage": "little-endian uint16; token ids currently 0..255",
        "train": train_info,
        "validation": validation_info,
        "note": "Bootstrap format for runner plumbing only; P1-14/P1-15 provide the curated dataset and trained tokenizer.",
    }
    destination = output_dir / "manifest.json"
    temporary = output_dir / "manifest.json.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError("Refusing to overwrite an existing dataset manifest")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)
    return destination


class TokenCorpus:
    """Read-only memory-mapped uint16-le tokens; batches copy only small windows."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = path.open("rb")
        size = path.stat().st_size
        if size % 2:
            self._file.close()
            raise ValueError("Token corpus size must be even for uint16-le values")
        if size == 0:
            self._file.close()
            raise ValueError("Token corpus is empty")
        if array("H").itemsize != 2:
            self._file.close()
            raise RuntimeError("This Python platform does not provide a 16-bit unsigned short")
        self.token_count = size // 2
        self._mapping = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self) -> None:
        self._mapping.close()
        self._file.close()

    def __enter__(self) -> "TokenCorpus":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _window(self, start: int, length: int) -> Tensor:
        raw = self._mapping[start * 2 : (start + length) * 2]
        values = array("H")
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        return torch.tensor(values, dtype=torch.long)

    def sample_batch(
        self,
        rng: random.Random,
        batch_size: int,
        sequence_length: int,
    ) -> tuple[Tensor, Tensor]:
        maximum_start = self.token_count - sequence_length - 1
        if maximum_start < 0:
            raise ValueError(
                f"Corpus needs at least {sequence_length + 1} tokens; found {self.token_count}"
            )
        starts = [rng.randint(0, maximum_start) for _ in range(batch_size)]
        inputs = torch.stack([self._window(start, sequence_length) for start in starts])
        targets = torch.stack([self._window(start + 1, sequence_length) for start in starts])
        return inputs, targets

    def sequential_batches(self, sequence_length: int, maximum_batches: int) -> list[tuple[Tensor, Tensor]]:
        if self.token_count < sequence_length + 1:
            raise ValueError(
                f"Corpus needs at least {sequence_length + 1} tokens; found {self.token_count}"
            )
        batches: list[tuple[Tensor, Tensor]] = []
        for start in range(0, self.token_count - sequence_length, sequence_length):
            batches.append((self._window(start, sequence_length)[None, :],
                            self._window(start + 1, sequence_length)[None, :]))
            if len(batches) >= maximum_batches:
                break
        return batches


class SyntheticTokenSource:
    """Deterministic in-memory byte pattern used only by the bounded smoke test."""

    _pattern = (
        b"def add(a, b):\n    return a + b\n"
        b"function greet(name) { return `Hello ${name}`; }\n"
        b"<main><h1>Plex</h1></main>\n"
    )

    def __init__(self, token_count: int = 65_536) -> None:
        repeated = (self._pattern * ((token_count // len(self._pattern)) + 1))[:token_count]
        self.tokens = torch.tensor(list(repeated), dtype=torch.long)
        self.token_count = int(self.tokens.numel())

    def sample_batch(
        self,
        rng: random.Random,
        batch_size: int,
        sequence_length: int,
    ) -> tuple[Tensor, Tensor]:
        maximum_start = self.token_count - sequence_length - 1
        if maximum_start < 0:
            raise ValueError("Synthetic token source is shorter than the requested sequence")
        starts = [rng.randint(0, maximum_start) for _ in range(batch_size)]
        inputs = torch.stack([self.tokens[start : start + sequence_length] for start in starts])
        targets = torch.stack([self.tokens[start + 1 : start + sequence_length + 1] for start in starts])
        return inputs, targets
