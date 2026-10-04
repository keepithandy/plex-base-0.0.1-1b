"""Bound writes beneath Plex's configured local artifact allocation."""

from __future__ import annotations

import os
from pathlib import Path

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
    if not root.exists():
        return 0
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        total += path.stat().st_size
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


def atomic_write_checkpoint(
    checkpoint: dict,
    destination: Path,
    artifact_root: Path,
    *,
    overwrite: bool = False,
) -> int:
    destination = path_within_root(destination, artifact_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"Temporary checkpoint already exists: {temporary.name}")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite checkpoint: {destination.name}")
    enforce_storage_limit(artifact_root, additional_bytes=1)
    try:
        with temporary.open("xb") as stream:
            torch.save(checkpoint, stream)
            stream.flush()
            os.fsync(stream.fileno())
        file_size = temporary.stat().st_size
        enforce_storage_limit(artifact_root)
        os.replace(temporary, destination)
        return file_size
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
