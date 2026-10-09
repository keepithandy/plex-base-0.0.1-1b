"""Deterministic P3-01 single-file request/edit contract and review."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from .initialization import _tokenizer_metadata
from .tokenizer import PlexTokenizer

MILESTONE = "P3-01"
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
GENERATOR_VERSION = "p3-01-file-edit-contract-generator-v1"


def _fixture_rows() -> list[dict[str, Any]]:
    examples = [
        ("html", "Change the button text to Save Changes.", "<button>Apply</button>", "<button>Store</button>"),
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


def _replacement_signature(before: str, after: str) -> tuple[str, str] | None:
    # Accept one contiguous replacement with identical surrounding content.
    matcher = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'|\b[A-Za-z_$][A-Za-z0-9_$]*\b|\d+(?:\.\d+)?(?:px|ms)?|#[0-9A-Fa-f]+|/[-A-Za-z0-9_./]+|\.[A-Za-z_-][A-Za-z0-9_-]*')
    old_tokens = list(matcher.finditer(before))
    new_tokens = list(matcher.finditer(after))
    matches = [(old, new) for old in old_tokens for new in new_tokens
               if before[:old.start()] == after[:new.start()]
               and before[old.end():] == after[new.end():]
               and before[old.start():old.end()] != after[new.start():new.end()]]
    if len(matches) != 1:
        return None
    old, new = matches[0]
    return before[old.start():old.end()], after[new.start():new.end()]


def _replacement_preserves(before: str, after: str, expected: tuple[str, str]) -> bool:
    old, new = expected
    matcher = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'|\b[A-Za-z_$][A-Za-z0-9_$]*\b|\d+(?:\.\d+)?(?:px|ms)?|#[0-9A-Fa-f]+|/[-A-Za-z0-9_./]+|\.[A-Za-z_-][A-Za-z0-9_-]*')
    return any(before[:left.start()] == after[:right.start()]
               and before[left.end():] == after[right.end():]
               and before[left.start():left.end()] == old
               and after[right.start():right.end()] == new
               for left in matcher.finditer(before) for right in matcher.finditer(after))


def _validate_rows(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list) or len(rows) != 18:
        raise ValueError("P3-01 candidate must contain exactly 18 fixtures")
    counts = Counter()
    requests, pairs, ids = set(), set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("P3-01 fixture fields are invalid")
        if row["schemaVersion"] != 1 or row["language"] not in LANGUAGES or row["editKind"] != "replace":
            raise ValueError("P3-01 fixture schema, language, or edit kind is invalid")
        for field in ("id", "request", "inputFile", "expectedFile"):
            value = row[field]
            if not isinstance(value, str) or not value or value != value.strip() or "\r" in value:
                raise ValueError(f"P3-01 {field} must be nonempty, trimmed LF text")
        if row["id"] in ids or row["request"] in requests:
            raise ValueError("P3-01 fixture IDs and exact requests must be unique")
        pair = (row["inputFile"], row["expectedFile"])
        if pair in pairs or pair[0] == pair[1]:
            raise ValueError("P3-01 fixture edit pairs must be unique and non-identical")
        if "```" in row["expectedFile"] or row["expectedFile"].lstrip().startswith(("{\"", "{\n")):
            raise ValueError("P3-01 target must be raw edited-file text, without fences or JSON wrapper")
        signature = _replacement_signature(*pair)
        if signature is None or not _replacement_preserves(*pair, signature):
            raise ValueError("P3-01 expected output must preserve all text outside one replacement")
        ids.add(row["id"]); requests.add(row["request"]); pairs.add(pair); counts[row["language"]] += 1
    if any(counts[lang] != 6 for lang in LANGUAGES):
        raise ValueError("P3-01 fixture set must contain exactly six fixtures per language")
    return {"fixtures": len(rows), "perLanguage": dict(sorted(counts.items()))}


def build_candidate_rows() -> list[dict[str, Any]]:
    rows = _fixture_rows()
    _validate_rows(rows)
    return rows


def generate_file_edit_candidate(*, candidate_path: Path, review_path: Path) -> dict[str, Any]:
    rows = build_candidate_rows()
    raw = _canonical_bytes(rows)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw)
    review = {"schemaVersion": 1, "milestone": MILESTONE, "generatorVersion": GENERATOR_VERSION,
              "representation": REPRESENTATION, "candidateSha256": hashlib.sha256(raw).hexdigest(),
              "byteCount": len(raw), "fixtures": len(rows), "modelTrainingAuthorized": False,
              "trainingPerformed": False, "researchOptimizerUpdates": 0, "finalHoldoutOpened": False}
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"candidateSha256": review["candidateSha256"], "byteCount": len(raw), "fixtures": len(rows)}


def review_file_edit_candidate(*, candidate_path: Path, review_path: Path, contract_path: Path,
                               tokenizer_bundle: Path | None = None, report_path: Path | None = None) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    required = {"milestone": MILESTONE, "dataPreparationAuthorized": True, "contractReviewAuthorized": True,
                "tokenizerContextReviewAuthorized": True, "modelTrainingAuthorized": False,
                "checkpointStagingAuthorized": False, "optimizerCreationAuthorized": False,
                "automaticContinuation": False, "trainingPerformed": False,
                "researchOptimizerUpdates": 0, "finalHoldoutOpened": False}
    if any(contract.get(key) != value for key, value in required.items()):
        raise ValueError("P3-01 preparation/review contract is invalid")
    raw = candidate_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("P3-01 candidate must be UTF-8 without BOM and use LF newlines")
    parsed = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    summary = _validate_rows(parsed)
    if raw != _canonical_bytes(parsed):
        raise ValueError("P3-01 candidate JSONL serialization is not canonical")
    digest = hashlib.sha256(raw).hexdigest()
    recorded = json.loads(review_path.read_text(encoding="utf-8"))
    if recorded.get("candidateSha256") != digest or recorded.get("byteCount") != len(raw):
        raise ValueError("P3-01 draft review identity does not match candidate bytes")
    if tokenizer_bundle is None or tokenizer_bundle.is_symlink() or not tokenizer_bundle.is_dir():
        raise ValueError("P3-01 frozen tokenizer bundle is required for context review")
    try:
        _, record = _tokenizer_metadata(tokenizer_bundle)
        tokenizer = PlexTokenizer.load(tokenizer_bundle)
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
        token_counts.append(len(tokenizer.encode(prompt + target)) + 1)  # EOS
    if max(token_counts) > 512:
        raise ValueError("P3-01 fixture exceeds the 512-token context")
    result = {"schemaVersion": 1, "milestone": MILESTONE, "status": "candidate-review-passed",
              "representation": REPRESENTATION, "promptTemplate": PROMPT_TEMPLATE,
              "targetRule": "Complete edited file text only, followed by EOS; no wrapper or explanation.",
              "candidateSha256": digest, "byteCount": len(raw), **summary,
              "tokenizerPreflight": {"checked": True, "tokenizerSha256": record["tokenizerSha256"],
                                     "bundleManifestSha256": record["bundleManifestSha256"],
                                     "minimumTokensIncludingEos": min(token_counts),
                                     "maximumTokensIncludingEos": max(token_counts),
                                     "meanTokensIncludingEos": round(mean(token_counts), 3),
                                     "medianTokensIncludingEos": median(token_counts),
                                     "allFit512Tokens": True,
                                     "sourceBundleManifestSha256": TOKENIZER_SOURCE_BUNDLE_SHA256},
              "scoring": {"exactMatch": "UTF-8 text equality after CRLF/CR to LF normalization; preserve all other whitespace.",
                          "preservation": "Compare actual and expected replacement spans; all text outside the single expected span must match input.",
                          "unnecessaryEdits": "Count output changes outside the expected replacement; exact-match success has zero.",
                          "syntaxCheckability": "Record per-language syntax check status when a later evaluator provides a cheap checker; exact fixture targets are known-valid."},
              "modelTrainingAuthorized": False, "trainingPerformed": False, "researchOptimizerUpdates": 0,
              "finalHoldoutOpened": False}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result
