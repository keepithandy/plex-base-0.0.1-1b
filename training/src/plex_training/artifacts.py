"""Bound writes beneath Plex's configured local artifact allocation."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import BinaryIO

import torch

from .data import DEFAULT_STORAGE_LIMIT_BYTES


def path_within_root(path: Path, root: Path) -> Path:
    canonical_root = root.resolve()
    canonical_path = path.resolve(strict=False)
    try:
        canonical_path.relative_to(canonical_root)
    except ValueError as exc:
        raise ValueError("Training outputs must stay under the configured artifact root") from exc
    return canonical_path


def artifact_bytes(root: Path) -> int:
    try:
        root_metadata = root.lstat()
    except FileNotFoundError:
        return 0
    except OSError as exc:
        raise RuntimeError(f"Artifact allocation cannot be verified: {root}") from exc
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise RuntimeError("Artifact allocation root must be a regular directory")
    total = 0
    pending = [root]
    while pending:
        path = pending.pop()
        try:
            metadata = path.lstat()
            if (stat.S_ISLNK(metadata.st_mode)
                    or getattr(metadata, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                raise RuntimeError(f"Artifact allocation cannot include links or reparse points: {path}")
            if stat.S_ISREG(metadata.st_mode):
                total += metadata.st_size
            elif stat.S_ISDIR(metadata.st_mode):
                with os.scandir(path) as entries:
                    pending.extend(Path(entry.path) for entry in entries)
            else:
                raise RuntimeError(f"Artifact allocation cannot include special files: {path}")
        except OSError as exc:
            raise RuntimeError(f"Artifact allocation cannot be verified: {path}") from exc
    return total


def enforce_storage_limit(
    root: Path,
    additional_bytes: int = 0,
    limit_bytes: int = DEFAULT_STORAGE_LIMIT_BYTES,
) -> None:
    if additional_bytes < 0 or limit_bytes <= 0:
        raise ValueError("Storage accounting values must be positive")
    used = artifact_bytes(root)
    if used + additional_bytes > limit_bytes:
        raise RuntimeError(
            f"Plex artifact allocation exceeded: {used + additional_bytes} bytes requested, "
            f"limit is {limit_bytes} bytes"
        )


class _BoundedCheckpointWriter:
    def __init__(
        self,
        stream: BinaryIO,
        *,
        maximum_bytes: int,
        used_before_write: int,
        limit_bytes: int,
    ) -> None:
        self._stream = stream
        self._maximum_bytes = maximum_bytes
        self._used_before_write = used_before_write
        self._limit_bytes = limit_bytes
        self.bytes_written = 0

    def write(self, data: bytes | bytearray | memoryview) -> int:
        amount = memoryview(data).nbytes
        requested = self.bytes_written + amount
        if requested > self._maximum_bytes:
            raise RuntimeError(
                "Plex artifact allocation exceeded during checkpoint serialization: "
                f"{self._used_before_write + requested} bytes requested, "
                f"limit is {self._limit_bytes} bytes"
            )
        written = self._stream.write(data)
        if written is None:
            written = amount
        if written < 0 or written > amount:
            raise OSError("Checkpoint stream returned an invalid write count")
        self.bytes_written += written
        return written

    def flush(self) -> None:
        self._stream.flush()

    def tell(self) -> int:
        return self._stream.tell()


def atomic_write_checkpoint(
    checkpoint: dict,
    destination: Path,
    artifact_root: Path,
    *,
    overwrite: bool = False,
    storage_limit_bytes: int = DEFAULT_STORAGE_LIMIT_BYTES,
) -> int:
    destination = path_within_root(destination, artifact_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Temporary checkpoint already exists: {temporary.name}")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite checkpoint: {destination.name}")
    if storage_limit_bytes <= 0:
        raise ValueError("Storage limit must be positive")
    used_before_write = artifact_bytes(artifact_root)
    available_bytes = storage_limit_bytes - used_before_write
    if available_bytes <= 0:
        raise RuntimeError(
            f"Plex artifact allocation exceeded: {used_before_write + 1} bytes requested, "
            f"limit is {storage_limit_bytes} bytes"
        )
    try:
        with temporary.open("xb") as stream:
            bounded = _BoundedCheckpointWriter(
                stream,
                maximum_bytes=available_bytes,
                used_before_write=used_before_write,
                limit_bytes=storage_limit_bytes,
            )
            torch.save(checkpoint, bounded)
            bounded.flush()
            os.fsync(stream.fileno())
        file_size = temporary.stat().st_size
        if file_size != bounded.bytes_written:
            raise RuntimeError("Checkpoint serialization byte count did not match the temporary file")
        enforce_storage_limit(artifact_root, limit_bytes=storage_limit_bytes)
        os.replace(temporary, destination)
        return file_size
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
