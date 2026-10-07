"""Plex Web dataset build that preserves the verifier's accepted file set."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dataset import build_dataset
from .web_sources import verify_web_sources


def build_web_dataset(
    source_manifest: Path,
    output_dir: Path,
    *,
    validation_percent: int,
    seed: int,
    storage_limit_bytes: int,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Build a Plex Web corpus from exactly the paths accepted by web-source-verify."""
    preflight = verify_web_sources(source_manifest, policy_path)
    if preflight.get("readyForDeterministicBuild") is not True:
        raise ValueError("Plex Web source preflight did not authorize a deterministic build")

    allowed_paths_by_source: dict[str, frozenset[str]] = {}
    for source in preflight["sources"]:
        source_id = source["id"]
        paths = source["acceptedPaths"]
        allowed_paths_by_source[source_id] = frozenset(paths)

    result = build_dataset(
        source_manifest,
        output_dir,
        validation_percent=validation_percent,
        seed=seed,
        storage_limit_bytes=storage_limit_bytes,
        allowed_paths_by_source=allowed_paths_by_source,
    )
    return {
        **result,
        "webPolicy": preflight["policy"],
        "preflightAcceptedFiles": preflight["acceptedFiles"],
        "preflightAcceptedBytes": preflight["acceptedBytes"],
        "preflightSkippedCounts": preflight["skippedCounts"],
        "verifiedPathSetApplied": True,
    }
