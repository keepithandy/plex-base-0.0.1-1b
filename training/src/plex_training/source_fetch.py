"""Fetch a bounded, pinned GitHub text snapshot; never approve or execute sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

MAX_PLAN_BYTES = 4 * 1024**2
MAX_FILE_BYTES = 1024**2
MAX_DOWNLOAD_BYTES = 20 * 1024**2
DEFAULT_PLAN = Path(__file__).resolve().parents[2] / "dataset-source-lock.json"
ALLOWED_SUFFIXES = {".js", ".mjs", ".cjs", ".html", ".css", ".md"}


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _file_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Snapshot paths must be relative POSIX file paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", "..", ".git"} for part in value.split("/")):
        raise ValueError("Snapshot paths must not escape their source directory")
    if value != "LICENSE" and path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Snapshots accept only selected text files and the root LICENSE")
    return value


def read_plan(plan_path: Path) -> list[dict]:
    if plan_path.is_symlink() or plan_path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError("Source lock must be a regular JSON file no larger than 4 MiB")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or plan.get("schemaVersion") != 1:
        raise ValueError("Source lock schemaVersion must be 1")
    sources = plan.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Source lock must list at least one source")
    ids: set[str] = set()
    total_bytes = 0
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Each locked source must be an object")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", source_id):
            raise ValueError("Source lock contains an invalid id")
        if source_id in ids:
            raise ValueError("Source lock contains duplicate ids")
        ids.add(source_id)
        if not isinstance(source.get("repo"), str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source["repo"]
        ):
            raise ValueError("Source repository must be a GitHub owner/repository")
        if not isinstance(source.get("revision"), str) or not re.fullmatch(r"[a-f0-9]{40}", source["revision"]):
            raise ValueError("Source revision must be a full immutable Git commit SHA")
        files = source.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Each source must list its selected files")
        paths: set[str] = set()
        for file in files:
            if not isinstance(file, dict):
                raise ValueError("Every locked file must be an object")
            path = _file_path(file.get("path"))
            if path.casefold() in paths:
                raise ValueError("Source lock has duplicate or case-colliding paths")
            paths.add(path.casefold())
            size = file.get("bytes")
            if type(size) is not int or not 0 < size <= MAX_FILE_BYTES:
                raise ValueError("Locked files must be nonempty and no larger than 1 MiB")
            if not isinstance(file.get("gitBlobSha1"), str) or not re.fullmatch(r"[a-f0-9]{40}", file["gitBlobSha1"]):
                raise ValueError("Each locked file must have its upstream Git blob SHA-1")
            total_bytes += size
        if "license" not in paths:
            raise ValueError("Every snapshot must retain the root LICENSE")
    if total_bytes > MAX_DOWNLOAD_BYTES:
        raise ValueError("Source download exceeds the 20 MiB text-snapshot limit")
    return sources


def _verify_blob(raw: bytes, file: dict) -> None:
    if len(raw) != file["bytes"] or git_blob_sha1(raw) != file["gitBlobSha1"]:
        raise ValueError(f"Upstream content differs from the source lock: {file['path']}")


def _download_blob(source: dict, file: dict) -> bytes:
    url = f"https://raw.githubusercontent.com/{source['repo']}/{source['revision']}/{quote(file['path'])}"
    request = Request(url, headers={"User-Agent": "Plex-pinned-source-fetch/1"})
    with urlopen(request, timeout=30) as response:
        final_url = urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname != "raw.githubusercontent.com":
            raise ValueError("Source download redirected outside the expected public GitHub host")
        raw = response.read(file["bytes"] + 1)
    _verify_blob(raw, file)
    return raw


def _verify_existing(root: Path, source: dict) -> None:
    expected = {file["path"] for file in source["files"]}
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Existing source snapshot contains a symbolic link")
        path.resolve().relative_to(root)
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != expected:
        raise ValueError("Existing snapshot file selection differs from the source lock")
    for file in source["files"]:
        path = root / file["path"]
        if path.stat().st_size != file["bytes"]:
            raise ValueError(f"Existing snapshot changed: {file['path']}")
        _verify_blob(path.read_bytes(), file)


def fetch_sources(plan_path: Path) -> dict:
    """Download selected pinned blobs beneath the lock file's data/raw directory."""
    sources = read_plan(plan_path)
    plan_path = plan_path.resolve(strict=True)
    base = (plan_path.parent / "data" / "raw").resolve()
    base.relative_to(plan_path.parent)
    base.mkdir(parents=True, exist_ok=True)
    results = []
    for source in sources:
        destination = base / source["id"]
        if destination.is_symlink():
            raise ValueError("Source snapshot directory must not be a symbolic link")
        destination.resolve().relative_to(base)
        existed = destination.exists()
        if existed:
            _verify_existing(destination, source)
        else:
            staging = Path(tempfile.mkdtemp(prefix=f".{source['id']}.fetch-", dir=base))
            try:
                def fetch_one(file: dict) -> None:
                    raw = _download_blob(source, file)
                    path = staging / file["path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)

                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(fetch_one, source["files"]))
                staging.resolve().relative_to(base)
                os.replace(staging, destination)
            finally:
                if staging.exists():
                    staging.resolve().relative_to(base)
                    shutil.rmtree(staging)
        results.append({
            "id": source["id"],
            "revision": source["revision"],
            "files": len(source["files"]),
            "bytes": sum(file["bytes"] for file in source["files"]),
            "alreadyVerified": existed,
        })
    return {"sources": results, "totalBytes": sum(item["bytes"] for item in results)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(fetch_sources(args.plan), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Source fetch: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
