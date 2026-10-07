"""Materialize pinned, reviewed Plex Web GitHub sources into the local pretraining cache."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .web_sources import DEFAULT_POLICY, load_source_policy

DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "pretraining" / "p2-26-source-candidates.json"
MAX_REGISTRY_BYTES = 1024 * 1024


def _read_registry(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("Source registry must not be a symbolic link")
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or resolved.stat().st_size > MAX_REGISTRY_BYTES:
        raise ValueError("Source registry must be a regular JSON file no larger than 1 MiB")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Source registry must be valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("Source registry schemaVersion must be 1")
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Source registry must contain sources")
    return value


def _safe_destination(registry_root: Path, local_path: str) -> Path:
    relative = Path(local_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Source localPath must stay beneath the registry directory")
    destination = (registry_root / relative).resolve(strict=False)
    destination.relative_to(registry_root.resolve())
    return destination


def _git(*args: str, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Git is unavailable or timed out while materializing a Plex Web source") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise ValueError(detail)
    return result.stdout.strip()


def _validate_source(item: dict[str, Any], allowed: frozenset[str]) -> None:
    required = (
        "id", "repo", "origin", "revision", "licenseId", "licenseEvidence",
        "localPath", "groupId", "rightsReviewedAtUtc",
    )
    for field in required:
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(f"P2-26 source must provide {field}")
    if item.get("reviewStatus") != "license-file-verified":
        raise ValueError(f"Source {item['id']!r} is not license-file verified")
    if item["licenseId"] not in allowed:
        raise ValueError(f"Source {item['id']!r} license is outside Plex Web policy")
    if not re.fullmatch(r"[a-f0-9]{40}", item["revision"]):
        raise ValueError(f"Source {item['id']!r} revision must be a full Git commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item["repo"]):
        raise ValueError(f"Source {item['id']!r} repo must be owner/name")
    parsed = urlparse(item["origin"])
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password:
        raise ValueError(f"Source {item['id']!r} origin must be a public https://github.com URL")
    if parsed.path.strip("/") != item["repo"]:
        raise ValueError(f"Source {item['id']!r} origin and repo do not match")
    extensions = item.get("includeExtensions")
    if not isinstance(extensions, list) or not extensions or not all(isinstance(v, str) for v in extensions):
        raise ValueError(f"Source {item['id']!r} must list includeExtensions")


def _materialize_one(item: dict[str, Any], registry_root: Path) -> dict[str, Any]:
    destination = _safe_destination(registry_root, item["localPath"])
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not (destination / ".git").is_dir():
            raise ValueError(f"Existing source directory is not a Git checkout: {destination}")
        head = _git("rev-parse", "HEAD", cwd=destination)
        if head != item["revision"]:
            raise ValueError(
                f"Existing source {item['id']!r} is at {head}, expected {item['revision']}"
            )
        return {"id": item["id"], "revision": head, "alreadyVerified": True}

    destination.mkdir()
    try:
        _git("init", cwd=destination)
        _git("remote", "add", "origin", item["origin"], cwd=destination)
        _git("fetch", "--depth", "1", "origin", item["revision"], cwd=destination)
        _git("checkout", "--detach", "FETCH_HEAD", cwd=destination)
        head = _git("rev-parse", "HEAD", cwd=destination)
        if head != item["revision"]:
            raise ValueError(
                f"Materialized source {item['id']!r} resolved to {head}, expected {item['revision']}"
            )
        return {"id": item["id"], "revision": head, "alreadyVerified": False}
    except Exception:
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        raise


def materialize_sources(
    registry_path: Path = DEFAULT_REGISTRY,
    *,
    policy_path: Path = DEFAULT_POLICY,
    manifest_output: Path | None = None,
) -> dict[str, Any]:
    registry = _read_registry(registry_path)
    policy = load_source_policy(policy_path)
    allowed = policy["_allowedSpdxSet"]
    registry_root = registry_path.resolve(strict=True).parent

    sources = registry["sources"]
    ids: set[str] = set()
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Every P2-26 source must be an object")
        _validate_source(item, allowed)
        if item["id"] in ids:
            raise ValueError(f"Duplicate P2-26 source id: {item['id']}")
        ids.add(item["id"])

    results = [_materialize_one(item, registry_root) for item in sources]

    output = manifest_output or registry_root / "sources.p2-26.local.json"
    if output.exists():
        raise FileExistsError(f"P2-26 source manifest already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_sources = []
    for item in sources:
        manifest_sources.append(
            {
                "id": item["id"],
                "localPath": item["localPath"],
                "origin": item["origin"],
                "revision": item["revision"],
                "licenseId": item["licenseId"],
                "licenseEvidence": item["licenseEvidence"],
                "rightsReviewStatus": "approved",
                "rightsReviewedAtUtc": item["rightsReviewedAtUtc"],
                "groupId": item["groupId"],
                "includeExtensions": item["includeExtensions"],
            }
        )
    output.write_text(
        json.dumps({"schemaVersion": 1, "sources": manifest_sources}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "schemaVersion": 1,
        "sources": results,
        "sourceCount": len(results),
        "manifest": str(output),
        "nextCommand": "web-source-verify",
    }
