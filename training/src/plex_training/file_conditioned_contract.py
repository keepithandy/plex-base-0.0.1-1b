"""Deterministic P3-01 single-file request/edit contract and review."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path, PureWindowsPath
from statistics import mean, median
from typing import Any

from .tokenizer import PlexTokenizer, sha256_file
from .path_safety import require_unambiguous_windows_destination

ROOT = Path(__file__).absolute().parents[3]
DEFAULT_CONTRACT = ROOT / "training/pretraining/p3-01-file-request-contract.json"
MILESTONE = "P3-01"
EXPECTED_CANDIDATE_SHA256 = "7f81bd850fa522adeb92f030ac51a91cab7ff3b0145a3bab9af0ca56956d638a"
EXPECTED_CANDIDATE_BYTES = 4264
REPRESENTATION = "plex-file-edit-v1"
EXPECTED_TOKENIZER_SHA256 = "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697"
TOKENIZER_SOURCE_BUNDLE_SHA256 = "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6"
TOKENIZER_BUNDLE_SHA256 = "71fec0882692f5eb1b47b72f4a9f539e53e77882d003649beacd5f341b5a4ea7"
PROMPT_TEMPLATE = (
    "Edit the supplied file to satisfy the request.\n"
    "Language: {language}\n"
    "Request: {request}\n"
    "File:\n"
    "{input_file}\n"
    "Edited file:"
)
FIELDS = {"schemaVersion", "id", "language", "request", "inputFile", "expectedFile", "editKind"}
LANGUAGES = ("html", "css", "javascript")
GENERATOR_VERSION = "p3-01-file-edit-contract-generator-v2"


def _fixture_rows() -> list[dict[str, Any]]:
    examples = [
        ("html", "Change the button text to Save Changes.", "<button>Apply</button>", "<button>Save Changes</button>"),
        ("html", "Change the heading text to Welcome.", "<h1>Hello</h1>", "<h1>Welcome</h1>"),
        ("html", "Change the link destination to /account.", '<a href="/home">Account</a>', '<a href="/account">Account</a>'),
        ("html", "Change the input type to email.", '<input type="text" name="email">', '<input type="email" name="email">'),
        ("html", "Change the image alt text to a blue sky.", '<img src="sky.jpg" alt="Sky">', '<img src="sky.jpg" alt="a blue sky">'),
        ("html", "Change the button label from Send to Submit.", '<button class="primary">Send</button>', '<button class="primary">Submit</button>'),
        ("css", "Change the gap to 16px.", ".card {\n  display: grid;\n  gap: 8px;\n}", ".card {\n  display: grid;\n  gap: 16px;\n}"),
        ("css", "Change the text color to navy.", ".title {\n  color: black;\n}", ".title {\n  color: navy;\n}"),
        ("css", "Change the border radius to 4px.", ".panel {\n  padding: 13px;\n  border-radius: 2px;\n}", ".panel {\n  padding: 13px;\n  border-radius: 4px;\n}"),
        ("css", "Change the display value to flex.", ".toolbar {\n  display: block;\n  gap: 8px;\n}", ".toolbar {\n  display: flex;\n  gap: 8px;\n}"),
        ("css", "Change the top margin to 20px.", ".section {\n  margin-top: 10px;\n  color: navy;\n}", ".section {\n  margin-top: 20px;\n  color: navy;\n}"),
        ("css", "Change the font size to 18px.", ".label {\n  font-weight: bold;\n  font-size: 16px;\n}", ".label {\n  font-weight: bold;\n  font-size: 18px;\n}"),
        ("javascript", "Change the retry limit to 5.", "const retryLimit = 3;", "const retryLimit = 5;"),
        ("javascript", "Change the greeting to Welcome.", 'const greeting = "Hello";', 'const greeting = "Welcome";'),
        ("javascript", "Change the delay to 250 milliseconds.", "const delay = 100;", "const delay = 250;"),
        ("javascript", "Change the button selector to .save-button.", 'const button = document.querySelector(".submit-button");', 'const button = document.querySelector(".save-button");'),
        ("javascript", "Change the default page size to 20.", "function getPageSize(size = 10) {\n  return size;\n}", "function getPageSize(size = 20) {\n  return size;\n}"),
        ("javascript", "Change the success message to Saved.", 'function save() {\n  return "Done";\n}', 'function save() {\n  return "Saved";\n}'),
    ]
    return [
        {"schemaVersion": 1, "id": f"p301-{lang}-{i:02d}", "language": lang,
         "request": request, "inputFile": source, "expectedFile": target, "editKind": "replace"}
        for lang in LANGUAGES for i, (row_lang, request, source, target) in enumerate(
            [entry for entry in examples if entry[0] == lang], start=1
        )
    ]


def _canonical_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )


# Explicit reviewed replacement regions for this small fixture set. These are
# evaluator metadata, never part of the model-facing prompt or completion.
REPLACEMENTS = dict(zip(
    [f"p301-{language}-{index:02d}" for language in LANGUAGES for index in range(1, 7)],
    [("Apply", "Save Changes"), ("Hello", "Welcome"), ("/home", "/account"),
     ('type="text"', 'type="email"'), ('alt="Sky"', 'alt="a blue sky"'),
     ("Send", "Submit"), ("gap: 8px", "gap: 16px"), ("black", "navy"),
     ("border-radius: 2px", "border-radius: 4px"), ("block", "flex"),
     ("margin-top: 10px", "margin-top: 20px"), ("font-size: 16px", "font-size: 18px"),
     ("3", "5"), ("Hello", "Welcome"), ("100", "250"),
     (".submit-button", ".save-button"), ("10", "20"), ("Done", "Saved")],
))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path):
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError("JSON input must be a bounded regular file")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def _check_identity(raw):
    if len(raw) != EXPECTED_CANDIDATE_BYTES or hashlib.sha256(raw).hexdigest() != EXPECTED_CANDIDATE_SHA256:
        raise ValueError("P3-01 frozen candidate identity changed")


def _paths_alias(first: Path, second: Path) -> bool:
    first_resolved = first.resolve(strict=False)
    second_resolved = second.resolve(strict=False)
    if first_resolved == second_resolved:
        return True
    if first.exists() and second.exists():
        try:
            return os.path.samefile(first, second)
        except OSError as exc:
            raise ValueError("P3 path identity could not be verified safely") from exc
    return False


def _require_separate_p3_outputs(
    *,
    outputs: dict[str, Path],
    protected_inputs: dict[str, Path],
) -> None:
    output_items = list(outputs.items())
    if os.name == "nt":
        for _, path in output_items:
            require_unambiguous_windows_destination(PureWindowsPath(path))
            require_unambiguous_windows_destination(PureWindowsPath(path.resolve(strict=False)))
    for index, (first_name, first_path) in enumerate(output_items):
        for second_name, second_path in output_items[index + 1:]:
            if _paths_alias(first_path, second_path):
                raise ValueError(
                    f"P3 output paths must differ: {first_name} aliases {second_name}"
                )
        for input_name, input_path in protected_inputs.items():
            if _paths_alias(first_path, input_path):
                raise ValueError(
                    f"P3 output must not overwrite protected input: "
                    f"{first_name} aliases {input_name}"
                )


def _require_overwritable_p3_output(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError("Existing P3 output must be a regular file, not a link or special path")


def _write_staged_p3_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _publish_p3_pair(
    *,
    candidate_path: Path,
    candidate_bytes: bytes,
    review_path: Path,
    review_bytes: bytes,
    contract_path: Path,
) -> None:
    candidate_stage = candidate_path.with_name(candidate_path.name + ".p3tmp")
    review_stage = review_path.with_name(review_path.name + ".p3tmp")
    candidate_backup = candidate_path.with_name(candidate_path.name + ".p3bak")

    _require_separate_p3_outputs(
        outputs={
            "candidate": candidate_path,
            "review metadata": review_path,
            "candidate staging": candidate_stage,
            "review staging": review_stage,
            "candidate recovery backup": candidate_backup,
        },
        protected_inputs={"contract": contract_path},
    )
    _require_overwritable_p3_output(candidate_path)
    _require_overwritable_p3_output(review_path)
    for internal in (candidate_stage, review_stage, candidate_backup):
        if internal.exists() or internal.is_symlink():
            raise FileExistsError(
                f"Refusing P3 publication with stale transaction artifact: {internal.name}"
            )

    candidate_existed = candidate_path.exists()
    candidate_backup_created = False
    candidate_published = False
    try:
        _write_staged_p3_file(candidate_stage, candidate_bytes)
        _write_staged_p3_file(review_stage, review_bytes)

        try:
            if candidate_existed:
                os.replace(candidate_path, candidate_backup)
                candidate_backup_created = True
            os.replace(candidate_stage, candidate_path)
            candidate_published = True
            os.replace(review_stage, review_path)
        except BaseException:
            try:
                if candidate_backup_created:
                    os.replace(candidate_backup, candidate_path)
                elif candidate_published:
                    candidate_path.unlink(missing_ok=True)
            except BaseException as rollback_exc:
                raise RuntimeError(
                    "P3 paired publication failed and candidate rollback also failed; "
                    f"recovery artifact may remain at {candidate_backup}"
                ) from rollback_exc
            raise

        if candidate_backup_created:
            try:
                candidate_backup.unlink(missing_ok=True)
            except OSError:
                # The published pair is already consistent. A stale backup is
                # intentionally left visible so the next run fails closed.
                pass
    finally:
        candidate_stage.unlink(missing_ok=True)
        review_stage.unlink(missing_ok=True)


def score_file_edit(row, actual):
    """Conservative replacement-region scoring for the frozen fixtures only."""
    if not isinstance(actual, str):
        raise ValueError("Actual output must be text")
    actual = actual.replace("\r\n", "\n").replace("\r", "\n")
    old, new = REPLACEMENTS[row["id"]]
    source = row["inputFile"]
    if source.count(old) != 1 or source.replace(old, new, 1) != row["expectedFile"]:
        raise ValueError("Invalid expected replacement")
    prefix, suffix = source.split(old)
    preserved = (len(actual) >= len(prefix) + len(suffix)
                 and actual.startswith(prefix) and actual.endswith(suffix))
    exact = actual == row["expectedFile"]
    return {"exactMatch": exact, "requestedEditCorrect": exact,
            "unrelatedCodePreserved": preserved, "unnecessaryEdits": not preserved,
            "syntaxCheckability": "known-valid-target" if exact else "not-checked"}


def _validate_rows(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list) or len(rows) != 18:
        raise ValueError("P3-01 candidate must contain exactly 18 fixtures")
    approved = {row["id"]: row for row in _fixture_rows()}
    counts = Counter()
    requests, pairs, ids = set(), set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("P3-01 fixture fields are invalid")
        if type(row["schemaVersion"]) is not int or row["schemaVersion"] != 1 or row["language"] not in LANGUAGES or row["editKind"] != "replace":
            raise ValueError("P3-01 fixture schema, language, or edit kind is invalid")
        for field in ("id", "request", "inputFile", "expectedFile"):
            value = row[field]
            if not isinstance(value, str) or not value or not value.strip() or "\r" in value or "\ufeff" in value:
                raise ValueError(f"P3-01 {field} must be nonempty, trimmed LF text")
        if row["id"] in ids or row["request"] in requests:
            raise ValueError("P3-01 fixture IDs and exact requests must be unique")
        pair = (row["inputFile"], row["expectedFile"])
        if pair in pairs or pair[0] == pair[1]:
            raise ValueError("P3-01 fixture edit pairs must be unique and non-identical")
        if "```" in row["expectedFile"] or row["expectedFile"].lstrip().startswith(("{\"", "{\n")):
            raise ValueError("P3-01 target must be raw edited-file text, without fences or JSON wrapper")
        old, new = REPLACEMENTS.get(row["id"], ("", ""))
        if not old or pair[0].count(old) != 1 or pair[0].replace(old, new, 1) != pair[1]:
            raise ValueError("P3-01 expected output must preserve all text outside one replacement")
        if row != approved.get(row["id"]):
            raise ValueError("P3-01 fixture differs from the reviewed request and supplied file")
        ids.add(row["id"]); requests.add(row["request"]); pairs.add(pair); counts[row["language"]] += 1
    if any(counts[lang] != 6 for lang in LANGUAGES):
        raise ValueError("P3-01 fixture set must contain exactly six fixtures per language")
    return {"fixtures": len(rows), "perLanguage": dict(sorted(counts.items()))}


def build_candidate_rows() -> list[dict[str, Any]]:
    rows = _fixture_rows()
    _validate_rows(rows)
    return rows


def _contract(contract_path):
    contract = _read_json(contract_path)
    required = {"schemaVersion": 1, "kind": "plex-p3-01-file-request-contract-v1",
                "status": "candidate-preparation-authorized", "milestone": MILESTONE, "dataPreparationAuthorized": True, "contractReviewAuthorized": True,
                "tokenizerContextReviewAuthorized": True, "modelTrainingAuthorized": False,
                "checkpointStagingAuthorized": False, "optimizerCreationAuthorized": False,
                "automaticContinuation": False, "trainingPerformed": False,
                "researchOptimizerUpdates": 0, "finalHoldoutOpened": False}
    if any(type(contract.get(key)) is not type(value) or contract.get(key) != value for key, value in required.items()):
        raise ValueError("P3-01 preparation/review contract is invalid")
    if contract.get("candidateIdentity") != {"candidateId": "p3-01-file-edit-contract-v1",
            "fixtures": 18, "perLanguage": dict.fromkeys(LANGUAGES, 6),
            "sha256": EXPECTED_CANDIDATE_SHA256, "bytes": EXPECTED_CANDIDATE_BYTES}:
        raise ValueError("P3-01 contract candidate identity changed")
    if contract.get("representation") != REPRESENTATION or contract.get("schemaVersion") != 1:
        raise ValueError("Invalid P3-01 contract representation")
    if contract.get("tokenizer") != {
        "tokenizerSha256": EXPECTED_TOKENIZER_SHA256,
        "bundleManifestSha256": TOKENIZER_SOURCE_BUNDLE_SHA256, "contextTokens": 512,
    }:
        raise ValueError("Contract tokenizer identity changed")
    return contract


def generate_file_edit_candidate(*, candidate_path: Path, review_path: Path, contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    _require_separate_p3_outputs(
        outputs={"candidate": candidate_path, "review metadata": review_path},
        protected_inputs={"contract": contract_path},
    )
    rows = build_candidate_rows()
    raw = _canonical_bytes(rows)
    _check_identity(raw)
    _contract(contract_path)
    review = {"schemaVersion": 1, "milestone": MILESTONE, "generatorVersion": GENERATOR_VERSION,
              "representation": REPRESENTATION, "candidateSha256": hashlib.sha256(raw).hexdigest(),
              "byteCount": len(raw), "fixtures": len(rows), "modelTrainingAuthorized": False,
              "trainingPerformed": False, "researchOptimizerUpdates": 0, "finalHoldoutOpened": False}
    review_raw = (json.dumps(review, indent=2) + "\n").encode("utf-8")
    _publish_p3_pair(
        candidate_path=candidate_path,
        candidate_bytes=raw,
        review_path=review_path,
        review_bytes=review_raw,
        contract_path=contract_path,
    )
    return {"candidateSha256": review["candidateSha256"], "byteCount": len(raw), "fixtures": len(rows)}


def review_file_edit_candidate(*, candidate_path: Path, review_path: Path, contract_path: Path,
                               tokenizer_bundle: Path | None = None, report_path: Path | None = None) -> dict[str, Any]:
    if report_path is not None:
        protected_inputs = {
            "candidate": candidate_path,
            "review metadata": review_path,
            "contract": contract_path,
        }
        if tokenizer_bundle is not None:
            protected_inputs["tokenizer bundle"] = tokenizer_bundle
            for name in ("manifest.json", "tokenizer-config.json", "tokenizer.json"):
                protected_inputs[f"tokenizer {name}"] = tokenizer_bundle / name
        _require_separate_p3_outputs(
            outputs={"review report": report_path},
            protected_inputs=protected_inputs,
        )
    _contract(contract_path)
    raw = candidate_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("P3-01 candidate must be UTF-8 without BOM and use LF newlines")
    _check_identity(raw)
    parsed = [json.loads(line, object_pairs_hook=_unique_object) for line in raw.decode("utf-8").splitlines() if line]
    summary = _validate_rows(parsed)
    if raw != _canonical_bytes(parsed):
        raise ValueError("P3-01 candidate JSONL serialization is not canonical")
    digest = hashlib.sha256(raw).hexdigest()
    recorded = _read_json(review_path)
    if recorded.get("candidateSha256") != digest or recorded.get("byteCount") != len(raw):
        raise ValueError("P3-01 draft review identity does not match candidate bytes")
    for key, value in {"schemaVersion": 1, "milestone": MILESTONE, "generatorVersion": GENERATOR_VERSION,
                       "representation": REPRESENTATION, "fixtures": 18, "modelTrainingAuthorized": False,
                       "trainingPerformed": False, "researchOptimizerUpdates": 0, "finalHoldoutOpened": False}.items():
        if type(recorded.get(key)) is not type(value) or recorded.get(key) != value:
            raise ValueError("Draft review metadata changed")
    if tokenizer_bundle is None or tokenizer_bundle.is_symlink() or not tokenizer_bundle.is_dir():
        raise ValueError("P3-01 frozen tokenizer bundle is required for context review")
    try:
        for name in ("manifest.json", "tokenizer-config.json", "tokenizer.json"):
            if (tokenizer_bundle / name).is_symlink():
                raise ValueError("Linked tokenizer artifacts are not allowed")
        manifest = _read_json(tokenizer_bundle / "manifest.json")
        if sha256_file(tokenizer_bundle / "manifest.json") != TOKENIZER_BUNDLE_SHA256:
            raise ValueError("Frozen tokenizer bundle manifest changed")
        if manifest.get("sourceTokenizerBundleManifestSha256") != TOKENIZER_SOURCE_BUNDLE_SHA256:
            raise ValueError("Tokenizer source provenance changed")
        tokenizer = PlexTokenizer.load(tokenizer_bundle)
        record = {"tokenizerSha256": sha256_file(tokenizer_bundle / "tokenizer.json"),
                  "bundleManifestSha256": sha256_file(tokenizer_bundle / "manifest.json")}
        if tokenizer.vocabulary_size != 16384:
            raise ValueError("Frozen tokenizer vocabulary changed")
    except PermissionError as exc:
        raise ValueError("P3-01 tokenizer bundle is inaccessible; context review cannot pass") from exc
    if record.get("tokenizerSha256") != EXPECTED_TOKENIZER_SHA256:
        raise ValueError("P3-01 tokenizer identity differs from the frozen P2-48 tokenizer")
    token_counts = []
    for row in parsed:
        prompt = PROMPT_TEMPLATE.format(language=row["language"], request=row["request"], input_file=row["inputFile"])
        target = row["expectedFile"]
        if tokenizer.decode(tokenizer.encode(prompt)) != prompt or tokenizer.decode(tokenizer.encode(target)) != target:
            raise ValueError("P3-01 tokenizer failed exact text roundtrip")
        token_counts.append(len(tokenizer.encode(prompt)) + len(tokenizer.encode(target)) + 1)  # EOS
    if max(token_counts) > 512:
        raise ValueError("P3-01 fixture exceeds the 512-token context")
    result = {"schemaVersion": 1, "milestone": MILESTONE, "status": "candidate-review-passed",
              "representation": REPRESENTATION, "generatorVersion": GENERATOR_VERSION, "promptTemplate": PROMPT_TEMPLATE,
              "targetRule": "Complete edited file text only, followed by EOS; no wrapper or explanation.",
              "candidateSha256": digest, "byteCount": len(raw), **summary,
              "tokenizerPreflight": {"checked": True, "recordEncoding": "encode(prompt) + encode(target) + [EOS=3]", "tokenizerSha256": record["tokenizerSha256"],
                                     "bundleManifestSha256": record["bundleManifestSha256"],
                                     "minimumTokensIncludingEos": min(token_counts),
                                     "maximumTokensIncludingEos": max(token_counts),
                                     "meanTokensIncludingEos": round(mean(token_counts), 3),
                                     "medianTokensIncludingEos": median(token_counts),
                                     "allFit512Tokens": True,
                                     "sourceBundleManifestSha256": TOKENIZER_SOURCE_BUNDLE_SHA256},
              "scoring": {"exactMatch": "UTF-8 text equality after CRLF/CR to LF normalization; preserve all other whitespace.",
                          "preservation": "Frozen replacement prefix and suffix must remain unchanged; no semantic equivalence claim.",
                          "unnecessaryEdits": "Boolean: output fails to preserve the frozen prefix or suffix. Extra content inside the replacement region fails exact correctness.",
                          "syntaxCheckability": "Record per-language syntax check status when a later evaluator provides a cheap checker; exact fixture targets are known-valid."},
              "modelTrainingAuthorized": False, "trainingPerformed": False, "researchOptimizerUpdates": 0,
              "finalHoldoutOpened": False}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result
