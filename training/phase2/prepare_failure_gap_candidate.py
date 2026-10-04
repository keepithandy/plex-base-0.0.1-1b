"""Prepare an unapproved P2 candidate informed by the failed development run.

The approved v2 source and final holdout are read only. This script never trains.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path

from prepare_code_pair_candidate import prompt_text
from prepare_curated_request_candidate import Tree
from plex_training.benchmark import _check_task, _inspect_css
from plex_training.dataset import _family_stratified_group_split

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "training/phase2/drafts/p2-02-request-following-v2/candidate.jsonl"
OUTPUT = ROOT / "training/phase2/drafts/p2-02-request-following-v3"
DEV = ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json"
APPROVED_SHA = "9f6ad8eff96298f45880f9bfe831648364e2a7ed11996e7a7d91d5e984eb3d0b"
LANGUAGES = ("html", "css", "javascript")

# The names identify distinct requested operations. No name-only clones are added.
JS_NAMES = {
    "array-copy": ["copyItems", "reverseItems", "withoutFirst", "withoutLast", "takeFirstTwo", "takeLastTwo"],
    "array-lookup": ["hasItem", "firstItemIndex", "lastItemIndex", "startsWithItem", "endsWithItem", "countMatchingItems"],
    "binary": ["addNumbers", "subtractNumbers", "multiplyNumbers", "largerNumber", "smallerNumber", "absoluteGap"],
    "bound": ["capAtLimit", "raiseToLimit", "exceedsLimit", "belowLimit", "equalsLimit", "distanceFromLimit"],
    "classification": ["isWholeNumber", "isPositive", "isNegative", "isZero", "numberSign", "absoluteMagnitude"],
    "conversion": ["secondsToMillis", "millisToSeconds", "wholeMinutes", "metersToUnits", "minutesToUnits", "roundedSeconds"],
    "division": ["quotientTowardZero", "quotientDown", "quotientUp", "javascriptRemainder", "isDivisible", "absoluteRemainder"],
    "object-lookup": ["readProperty", "hasOwnProperty", "listObjectKeys", "listObjectValues", "listObjectEntries", "isPropertyUndefined"],
    "string-build": ["bracketText", "trimOuterSpace", "upperText", "lowerText", "duplicateText", "labelText"],
    "string-slice": ["firstCodeUnits", "skipCodeUnits", "lastCodeUnits", "dropLastCodeUnits", "longerThanCount", "exactCodeUnitCount"],
}

CSS_SELECTORS = {
    "aspect": [".square-thumb", ".wide-thumb", ".framed-thumb", ".avatar-box", ".poster-box", ".compact-thumb"],
    "columns": [".two-column-copy", ".narrow-column-copy", ".three-column-copy", ".ruled-copy", ".full-column-title", ".sequential-copy"],
    "cursor": [".click-target", ".blocked-target", ".drag-handle", ".busy-target", ".editable-copy", ".plain-target"],
    "decoration": [".underlined-link", ".wavy-link", ".tinted-link", ".overline-link", ".struck-label", ".solid-link"],
    "logical-border": [".start-edge", ".end-edge", ".top-edge", ".bottom-edge", ".paired-inline-edge", ".paired-block-edge"],
    "object-fit": [".contained-photo", ".covered-photo", ".stretched-photo", ".bounded-photo", ".scaled-photo", ".unfitted-photo"],
    "outline": [".solid-focus", ".thick-focus", ".spaced-focus", ".unoutlined-focus", ".dotted-focus", ".dashed-focus"],
    "overflow": [".horizontal-scroll", ".vertical-scroll", ".clipped-panel", ".clip-context", ".one-axis-scroll", ".short-scroll"],
    "table": [".automatic-table", ".fixed-table", ".collapsed-table", ".spaced-table", ".below-caption", ".separate-table"],
    "whitespace": [".single-line", ".preserved-wrap", ".tabbed-copy", ".ordinary-copy", ".spaced-copy", ".newline-copy"],
}

# These are newly authored task families. They teach composition and varied
# target names without copying a development request or final-holdout task.
EXTRAS = {
    "html": {
        "navigation": [
            ("Make a footer navigation named Resources with links to Guides and Support.", '<nav aria-label="Resources"><a href="/guides">Guides</a><a href="/support">Support</a></nav>'),
            ("Create a sidebar navigation named Topics containing a list with Art and Music links.", '<nav aria-label="Topics"><ul><li><a href="/art">Art</a></li><li><a href="/music">Music</a></li></ul></nav>'),
            ("Create a navigation named Account with Sign in and Help links, separated by a span containing a vertical bar.", '<nav aria-label="Account"><a href="/signin">Sign in</a><span>|</span><a href="/help">Help</a></nav>'),
            ("Make a footer with a navigation named Legal containing Terms and Privacy links.", '<footer><nav aria-label="Legal"><a href="/terms">Terms</a><a href="/privacy">Privacy</a></nav></footer>'),
            ("Build a list of two section links inside a navigation named Chapters: Start and Finish.", '<nav aria-label="Chapters"><ol><li><a href="#start">Start</a></li><li><a href="#finish">Finish</a></li></ol></nav>'),
            ("Create a header with a brand link named Atlas and navigation named Pages containing a Docs link.", '<header><a href="/">Atlas</a><nav aria-label="Pages"><a href="/docs">Docs</a></nav></header>'),
        ],
        "forms": [
            ("Make a form with a label for a required text input id username and a Save submit button.", '<form><label for="username">Username</label><input id="username" name="username" type="text" required><button type="submit">Save</button></form>'),
            ("Create a labeled textarea id notes in a form with a Send submit button.", '<form><label for="notes">Notes</label><textarea id="notes" name="notes"></textarea><button type="submit">Send</button></form>'),
            ("Make a form with a label for a select id region with North and South options.", '<form><label for="region">Region</label><select id="region" name="region"><option value="north">North</option><option value="south">South</option></select></form>'),
            ("Make a labeled number input id quantity with minimum 1 and a Place order submit button.", '<form><label for="quantity">Quantity</label><input id="quantity" name="quantity" type="number" min="1"><button type="submit">Place order</button></form>'),
            ("Make a form with two radio choices named size, Small and Large, each wrapped in its own label.", '<form><label><input type="radio" name="size" value="small">Small</label><label><input type="radio" name="size" value="large">Large</label></form>'),
            ("Make a form with a labeled password input id passcode and a Reset button that does not submit.", '<form><label for="passcode">Passcode</label><input id="passcode" name="passcode" type="password"><button type="reset">Reset</button></form>'),
        ],
        "content": [
            ("Create a figure with a diagram image diagram.png, descriptive alt text Flow diagram, and caption Process flow.", '<figure><img src="diagram.png" alt="Flow diagram"><figcaption>Process flow</figcaption></figure>'),
            ("Make an article with a heading Shipping update and one paragraph Packages leave tomorrow.", '<article><h2>Shipping update</h2><p>Packages leave tomorrow.</p></article>'),
            ("Create a table with caption Inventory, one header Item and one body cell Lamp.", '<table><caption>Inventory</caption><thead><tr><th scope="col">Item</th></tr></thead><tbody><tr><td>Lamp</td></tr></tbody></table>'),
            ("Build an ordered list with two items, Prepare and Publish, under a heading Workflow.", '<section><h2>Workflow</h2><ol><li>Prepare</li><li>Publish</li></ol></section>'),
            ("Make an image of mountains with a descriptive alt inside a linked figure captioned Trail map.", '<figure><a href="/trails"><img src="mountains.png" alt="Mountain trail"></a><figcaption>Trail map</figcaption></figure>'),
            ("Create an aside with a heading Tip and a paragraph Read the guide first.", '<aside><h3>Tip</h3><p>Read the guide first.</p></aside>'),
        ],
    },
    "css": {
        "layout": [
            ("Make .toolbar a flex row with a 12px gap and centered items.", ".toolbar { display: flex; gap: 12px; align-items: center; }"),
            ("Make .tile-list a three-column grid with 16px gaps.", ".tile-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }"),
            ("Make .badge-row wrap its flex items with an 8px gap.", ".badge-row { display: flex; flex-wrap: wrap; gap: 8px; }"),
            ("Make .sidebar-layout a grid with a 180px sidebar and flexible content, separated by 24px.", ".sidebar-layout { display: grid; grid-template-columns: 180px 1fr; gap: 24px; }"),
            ("Make .actions a flex row that places items at opposite ends and centers them vertically.", ".actions { display: flex; justify-content: space-between; align-items: center; }"),
            ("Make .stack a column flex container with 20px between children.", ".stack { display: flex; flex-direction: column; gap: 20px; }"),
        ],
        "state": [
            ("Give .tab:focus-visible a 3px solid royalblue outline and 3px offset.", ".tab:focus-visible { outline: 3px solid royalblue; outline-offset: 3px; }"),
            ("On .menu-link:hover, underline the text and change color to navy.", ".menu-link:hover { text-decoration: underline; color: navy; }"),
            ("For .send-button:disabled, reduce opacity to 0.4 and show a not-allowed cursor.", ".send-button:disabled { opacity: 0.4; cursor: not-allowed; }"),
            ("For .step-link[aria-current='step'], use font-weight 700 and a 2px solid border below.", ".step-link[aria-current='step'] { font-weight: 700; border-bottom: 2px solid; }"),
            ("For .chip[aria-pressed='true'], use a dark background and white text.", ".chip[aria-pressed='true'] { background: #1e293b; color: white; }"),
            ("For .text-field:invalid, set a crimson border and pale pink background.", ".text-field:invalid { border: 1px solid crimson; background: mistyrose; }"),
        ],
        "sizing": [
            ("Make .reading-pane at most 60ch wide with 16px inline padding.", ".reading-pane { max-width: 60ch; padding-inline: 16px; }"),
            ("Make .hero-photo fill available width, keep auto height, and display as block.", ".hero-photo { max-width: 100%; height: auto; display: block; }"),
            ("Give .video-frame a 16:9 ratio and cap its width at 720px.", ".video-frame { aspect-ratio: 16 / 9; max-width: 720px; }"),
            ("Make .quote-box at least 120px tall and include padding in its box size.", ".quote-box { min-height: 120px; box-sizing: border-box; }"),
            ("Make .scroll-region at most 240px tall with vertical auto scrolling.", ".scroll-region { max-height: 240px; overflow-y: auto; }"),
            ("Make .cover-art 200px wide and 200px tall, cropping its image to cover.", ".cover-art { width: 200px; height: 200px; object-fit: cover; }"),
        ],
    },
    "javascript": {
        "arrays": [
            ("Write keepEven(items) for an array of integers; return a new array of even values.", "function keepEven(items) {\n  return items.filter(item => item % 2 === 0);\n}"),
            ("Write doubleValues(items) for an array of numbers; return a new array with each number doubled.", "function doubleValues(items) {\n  return items.map(item => item * 2);\n}"),
            ("Write firstLong(items) for an array of strings; return the first string longer than five characters.", "function firstLong(items) {\n  return items.find(item => item.length > 5);\n}"),
            ("Write allPositive(items) for an array of numbers; report whether every number exceeds zero.", "function allPositive(items) {\n  return items.every(item => item > 0);\n}"),
            ("Write joinNames(items) for an array of strings; join them with a comma and one space.", "function joinNames(items) {\n  return items.join(', ');\n}"),
            ("Write countEmpty(items) for an array of strings; count the empty strings.", "function countEmpty(items) {\n  return items.filter(item => item === '').length;\n}"),
        ],
        "strings": [
            ("Write startsWithHash(text) for a string; report whether its first character is #.", "function startsWithHash(text) {\n  return text.startsWith('#');\n}"),
            ("Write removeOuterSpace(text) for a string; remove whitespace at both ends.", "function removeOuterSpace(text) {\n  return text.trim();\n}"),
            ("Write dashSpaces(text) for a string; replace every ordinary space with a dash.", "function dashSpaces(text) {\n  return text.replaceAll(' ', '-');\n}"),
            ("Write lastCharacter(text) for a string; return its last UTF-16 code unit or empty string.", "function lastCharacter(text) {\n  return text.slice(-1);\n}"),
            ("Write isBlank(text) for a string; report whether trimming leaves an empty string.", "function isBlank(text) {\n  return text.trim().length === 0;\n}"),
            ("Write lineParts(text) for a string; return an array split at newline characters.", "function lineParts(text) {\n  return text.split('\\n');\n}"),
        ],
        "objects": [
            ("Write hasTitle(item) for an object; report whether it owns a title property.", "function hasTitle(item) {\n  return Object.hasOwn(item, 'title');\n}"),
            ("Write displayLabel(item) for an object with a label property; return that label in square brackets.", "function displayLabel(item) {\n  return '[' + item.label + ']';\n}"),
            ("Write objectFieldCount(item) for an object; return its number of own enumerable string keys.", "function objectFieldCount(item) {\n  return Object.keys(item).length;\n}"),
            ("Write withActive(item) for an object; return a shallow copy with active set to true.", "function withActive(item) {\n  return { ...item, active: true };\n}"),
            ("Write getHeading(item) for an object; return its heading property or the empty string if nullish.", "function getHeading(item) {\n  return item.heading ?? '';\n}"),
            ("Write propertyNames(item) for an object; return its own enumerable string keys sorted alphabetically.", "function propertyNames(item) {\n  return Object.keys(item).sort();\n}"),
        ],
    },
}


def source_rows() -> list[dict]:
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != APPROVED_SHA:
        raise ValueError("Approved v2 candidate bytes changed")
    return [json.loads(line) for line in raw.splitlines()]


def records() -> list[dict]:
    rows = []
    for old in source_rows():
        row = copy.deepcopy(old)
        row["parentRecordId"] = old["id"]
        row["id"] = old["id"].replace("curated-", "gap-", 1)
        row["sourceFamilyId"] = old["sourceFamilyId"].replace("-v2", "-v3")
        row["curationOrigin"] = "p2-02-request-following-v2"
        row["approvalStatus"] = "pending-owner-review"
        language, topic, pattern = row["templateLineage"].split("/")
        index = int(pattern.removeprefix("pattern-")) - 1
        if language == "javascript":
            name = JS_NAMES[topic][index]
            row["request"] = row["request"].replace("transformAlpha", name)
            row["solution"] = row["solution"].replace("transformAlpha", name)
            for check in row["checks"]:
                if check.get("name") == "transformAlpha": check["name"] = name
                if "text" in check: check["text"] = check["text"].replace("transformAlpha", name)
        elif language == "css":
            old_selector = next(iter(row["expectedCssRules"]))
            selector = CSS_SELECTORS[topic][index]
            row["request"] = row["request"].replace(old_selector, selector)
            row["solution"] = row["solution"].replace(old_selector, selector)
            row["expectedCssRules"] = {selector: row["expectedCssRules"][old_selector]}
            for check in row["checks"]:
                check["selector"] = selector
        rows.append(row)

    for language, topics in EXTRAS.items():
        for topic, examples in topics.items():
            for index, (request, solution) in enumerate(examples, 1):
                row = {
                    "schemaVersion": 1,
                    "id": f"gap-{language}-{topic}-{index:02d}",
                    "language": language,
                    "sourceFamilyId": f"plex-request-following-{language}-v3",
                    "splitGroupId": f"{language}-{topic}",
                    "templateLineage": f"{language}/{topic}/pattern-{index}",
                    "provenance": "codex-authored-failure-gap-candidate",
                    "approvalStatus": "pending-owner-review",
                    "request": request + " Return code only.",
                    "solution": solution,
                    "checks": [],
                    "behaviorReviewCases": [],
                    "reviewForbiddenStrings": [],
                    "curationOrigin": "p2-development-failure-audit",
                }
                if language == "html":
                    row["expectedHtmlTree"] = Tree().finish(solution)
                    row["checks"] = [{"kind": "html_element", "tag": tag} for tag in sorted(set(re.findall(r"<([a-z][a-z0-9]*)\b", solution)))]
                elif language == "css":
                    status, rules, detail = _inspect_css(solution)
                    if status != "pass" or len(rules) != 1: raise ValueError(detail or "Expected one rule")
                    row["expectedCssRules"] = rules
                    row["checks"] = [{"kind": "css_declaration", "selector": selector, "property": prop, "value": value} for selector, decls in rules.items() for prop, value in decls.items()]
                else:
                    name = re.match(r"function ([A-Za-z]\w*)\(", solution)
                    if name is None: raise ValueError("Expected a named JS function")
                    row["checks"] = [{"kind": "js_function", "name": name.group(1)}, {"kind": "contains", "text": solution.split("\n", 1)[1].rsplit("\n", 1)[0]}]
                rows.append(row)

    groups = {f"plex-request-following-{language}-v3": {r["splitGroupId"] for r in rows if r["language"] == language} for language in LANGUAGES}
    held = _family_stratified_group_split(groups, 30, 51)
    for row in rows:
        row["candidateSplit"] = "validation" if (row["sourceFamilyId"], row["splitGroupId"]) in held else "train"
    return rows


def validate(rows: list[dict]) -> dict:
    tasks = json.loads(DEV.read_text(encoding="utf-8"))
    if tasks["kind"] != "development": raise ValueError("Only development tasks may inform this candidate")
    if Counter(r["language"] for r in rows) != {language: 78 for language in LANGUAGES}: raise ValueError("Expected 78 records per language")
    normalized = lambda value: " ".join(value.casefold().split())
    dev_requests = {normalized(t["request"]) for t in tasks["tasks"]}
    ids, requests, answers = set(), set(), set()
    js_names, css_selectors = set(), set()
    static_checks = 0
    for row in rows:
        if row["approvalStatus"] != "pending-owner-review": raise ValueError("Candidate claimed approval")
        if row["id"] in ids or normalized(row["request"]) in requests | dev_requests or normalized(row["solution"]) in answers:
            raise ValueError(f"Duplicate id/request/answer: {row['id']}")
        result = _check_task({"id": row["id"], "language": row["language"], "difficulty": "basic", "checks": row["checks"]}, row["solution"], None, 5.0)
        if not result["passed"]: raise ValueError(f"Static answer failure: {row['id']}: {result}")
        static_checks += result["checksPassed"]
        if row["language"] == "html":
            if Tree().finish(row["solution"]) != row["expectedHtmlTree"]: raise ValueError("HTML tree mismatch")
        elif row["language"] == "css":
            status, rules, _ = _inspect_css(row["solution"])
            if status != "pass" or rules != row["expectedCssRules"]: raise ValueError("CSS rule mismatch")
            selector = next(iter(rules))
            if selector in css_selectors: raise ValueError(f"Repeated CSS selector: {selector}")
            css_selectors.add(selector)
        else:
            name = re.match(r"function ([A-Za-z]\w*)\(", row["solution"])
            if name is None or name.group(1) in js_names: raise ValueError("Repeated or missing JS name")
            js_names.add(name.group(1))
        ids.add(row["id"]); requests.add(normalized(row["request"])); answers.add(normalized(row["solution"]))
    groups = {f"plex-request-following-{language}-v3": {r["splitGroupId"] for r in rows if r["language"] == language} for language in LANGUAGES}
    held = _family_stratified_group_split(groups, 30, 51)
    if any(r["candidateSplit"] != ("validation" if (r["sourceFamilyId"], r["splitGroupId"]) in held else "train") for r in rows):
        raise ValueError("Whole-group split mismatch")
    if any(r["candidateSplit"] == "train" for r in rows if r["splitGroupId"] in {group for _, group in held}):
        raise ValueError("Train/validation leakage")
    new_counts = Counter(f"{r['candidateSplit']}/{r['language']}" for r in rows if r["curationOrigin"] == "p2-development-failure-audit")
    if any(new_counts[f"train/{language}"] == 0 or new_counts[f"validation/{language}"] == 0 for language in LANGUAGES):
        raise ValueError("New families need train and validation representation")
    return {
        "schemaVersion": 1, "candidate": "p2-02-request-following-v3", "approvalStatus": "pending-owner-review",
        "records": len(rows), "revisedApprovedRecordCount": 180, "newRecordCount": 54,
        "recordsByLanguage": dict(Counter(r["language"] for r in rows)),
        "recordsBySplit": dict(Counter(r["candidateSplit"] for r in rows)),
        "newRecordsBySplitAndLanguage": dict(new_counts), "splitGroups": sum(map(len, groups.values())),
        "uniqueCssSelectors": len(css_selectors), "uniqueJavascriptFunctionNames": len(js_names),
        "staticSolutionsPassed": len(rows), "staticChecksPassed": static_checks,
        "developmentRequestDuplicates": 0, "sourceV2Sha256": APPROVED_SHA,
        "developmentTaskSetSha256": hashlib.sha256(DEV.read_bytes()).hexdigest(),
        "splitSeed": 51, "validationPercentOfGroups": 30,
        "javascriptBehaviorExecuted": False, "finalHoldoutOpened": False, "modelTrained": False,
        "limitations": ["Static answer checks do not establish behavior or model capability.",
                        "JavaScript examples were syntax-checked but never executed.",
                        "The development failures informed broad skill families; this is not an independent evaluation.",
                        "The candidate needs exact-record owner approval, a build, tokenization, and a new bounded training/evaluation comparison."],
    }


def prepare() -> dict:
    if OUTPUT.exists(): raise FileExistsError("Never overwrite a review candidate")
    rows = records()
    report = validate(rows)
    raw = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
    report["candidateJsonlSha256"] = hashlib.sha256(raw).hexdigest()
    tasks = json.loads(DEV.read_text(encoding="utf-8"))
    stage = OUTPUT.parent / (".request-gap-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        (stage / "candidate.jsonl").write_bytes(raw)
        (stage / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        guide = ["# P2 request-following v3: exact 234-record review\n",
                 "**Pending owner approval. No v3 records are used in training.**\n",
                 "This is a new candidate, not a modification of the approved v2 snapshot. It revises the 180 previous records to give each JavaScript function and CSS selector a distinct meaningful name, and adds 54 examples in nine new groups. The HTML v2 examples keep their existing requested structures; their new ids and split assignments still require approval.\n",
                 f"Canonical JSONL SHA-256: `{report['candidateJsonlSha256']}`.\n",
                 "The source groups are indivisible between training and validation. JavaScript behavior is not executed. Static checks establish the supplied answers' consistency, not Plex capability.\n"]
        catalog = []
        for language in LANGUAGES:
            root = stage / "sources" / language
            root.mkdir(parents=True)
            (root / "NOTICE.md").write_text("Original Codex-authored Plex P2 local-use review candidate. Owner approval pending. No external source text or public license asserted. Excluded from training.\n", encoding="utf-8", newline="\n")
            family = f"plex-request-following-{language}-v3"
            split_groups = sorted({r["splitGroupId"] for r in rows if r["language"] == language})
            catalog.append({"id": family, "groupId": family, "sourceFamilyId": family, "localPath": f"sources/{language}",
                            "origin": "urn:plex:codex-authored:p2-02-request-following-v3", "revision": report["candidateJsonlSha256"],
                            "licenseId": "Local-use-review-pending", "licenseEvidence": "NOTICE.md", "rightsReviewStatus": "pending-owner-review",
                            "rightsReviewedAtUtc": None, "includeExtensions": [".txt"],
                            "splitGroupRules": [{"id": group, "pathPrefixes": [group + "/"]} for group in split_groups]})
            for row in (r for r in rows if r["language"] == language):
                folder = root / row["splitGroupId"]
                folder.mkdir(exist_ok=True)
                (folder / (row["id"] + ".txt")).write_text(prompt_text(row, tasks["outputContracts"]) + "\n" + row["solution"], encoding="utf-8", newline="\n")
                guide.append(f"## {row['id']} — {row['candidateSplit']}\n\nGroup `{row['splitGroupId']}`; origin `{row['curationOrigin']}`.\n\n{row['request']}\n\n```{language}\n{row['solution']}\n```\n")
        (stage / "dataset-sources.candidate.json").write_text(json.dumps({"schemaVersion": 1, "splitStrategy": "family-stratified-groups-v1", "sources": catalog}, indent=2) + "\n", encoding="utf-8", newline="\n")
        (stage / "REVIEW.md").write_text("\n".join(guide), encoding="utf-8", newline="\n")
        os.rename(stage, OUTPUT)
    except Exception:
        if stage.resolve().parent == OUTPUT.parent.resolve() and stage.name.startswith(".request-gap-"):
            shutil.rmtree(stage)
        raise
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
