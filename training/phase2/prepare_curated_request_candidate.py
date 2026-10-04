"""Curate an immutable review candidate; no approval, downloads, or training."""
from __future__ import annotations

import copy
import hashlib
import html.parser
import json
import os
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path

import prepare_request_following_candidate as original
from prepare_code_pair_candidate import prompt_text
from plex_training.benchmark import _check_task, _inspect_css, render_task_prompt
from plex_training.dataset import _family_stratified_group_split

OUTPUT = original.OUTPUT.parent / "p2-02-request-following-v2"
LANGUAGES = ("html", "css", "javascript")

# Six different property-name combinations per topic, rather than six values of
# one property. Each extra declaration follows an explicit request requirement.
CSS = {
    "logical-border": [
        ("Add a 2px solid #334155 border on the inline start edge only", "border-inline-start: 2px solid #334155"),
        ("Add a 2px solid #334155 border on the inline end edge only", "border-inline-end: 2px solid #334155"),
        ("Add a 2px dashed #334155 border on the block start edge only", "border-block-start: 2px dashed #334155"),
        ("Add a 2px dashed #334155 border on the block end edge only", "border-block-end: 2px dashed #334155"),
        ("Add a 2px solid #334155 inline start border and remove the inline end border", "border-inline-start: 2px solid #334155; border-inline-end: 0"),
        ("Remove the block start border and add a 2px solid #334155 block end border", "border-block-start: 0; border-block-end: 2px solid #334155"),
    ],
    "aspect": [
        ("Use a preferred square aspect ratio", "aspect-ratio: 1 / 1"),
        ("Use a preferred 16:9 aspect ratio with width 240px", "aspect-ratio: 16 / 9; width: 240px"),
        ("Use a preferred 4:3 aspect ratio and cap width at 100%", "aspect-ratio: 4 / 3; max-width: 100%"),
        ("Use a preferred square aspect ratio with height 120px", "aspect-ratio: 1 / 1; height: 120px"),
        ("Use a preferred 16:9 aspect ratio and include padding inside the border-box size", "aspect-ratio: 16 / 9; box-sizing: border-box"),
        ("Use a preferred 4:3 aspect ratio and a minimum width of 180px", "aspect-ratio: 4 / 3; min-width: 180px"),
    ],
    "outline": [
        ("Use a solid outline style", "outline-style: solid"),
        ("Use a 2px solid #334155 outline", "outline: 2px solid #334155"),
        ("Use a 2px solid #334155 outline offset outward by 4px", "outline: 2px solid #334155; outline-offset: 4px"),
        ("Remove both the outline and any box shadow", "outline: 0; box-shadow: none"),
        ("Use a dotted outline style, 3px width, and -2px offset", "outline-style: dotted; outline-width: 3px; outline-offset: -2px"),
        ("Use a dashed outline style and #334155 outline color", "outline-style: dashed; outline-color: #334155"),
    ],
    "cursor": [
        ("Show a pointer cursor", "cursor: pointer"),
        ("Show a forbidden cursor and opacity 0.5", "cursor: not-allowed; opacity: 0.5"),
        ("Show a grab cursor and prevent text selection", "cursor: grab; user-select: none"),
        ("Show a wait cursor and disable pointer targeting", "cursor: wait; pointer-events: none"),
        ("Show a text cursor and color #334155", "cursor: text; color: #334155"),
        ("Show a default cursor and display as a block", "cursor: default; display: block"),
    ],
    "whitespace": [
        ("Keep text on one unwrapped line", "white-space: nowrap"),
        ("Preserve whitespace while allowing wraps, including breaks anywhere in long tokens", "white-space: pre-wrap; overflow-wrap: anywhere"),
        ("Preserve whitespace and use a tab size of 4", "white-space: pre; tab-size: 4"),
        ("Collapse ordinary whitespace, allow wrapping, and use line-height 1.5", "white-space: normal; line-height: 1.5"),
        ("Preserve spaces with break-spaces and set word-spacing to 2px", "white-space: break-spaces; word-spacing: 2px"),
        ("Preserve newlines but collapse spaces, and indent the first line by 1em", "white-space: pre-line; text-indent: 1em"),
    ],
    "decoration": [
        ("Underline text", "text-decoration-line: underline"),
        ("Use a wavy underline", "text-decoration-line: underline; text-decoration-style: wavy"),
        ("Use an underline colored #334155", "text-decoration-line: underline; text-decoration-color: #334155"),
        ("Use both underline and overline with underline offset 4px", "text-decoration-line: underline overline; text-underline-offset: 4px"),
        ("Use line-through with a thickness of 2px", "text-decoration-line: line-through; text-decoration-thickness: 2px"),
        ("Use a solid underline and disable automatic ink skipping", "text-decoration: underline solid; text-decoration-skip-ink: none"),
    ],
    "overflow": [
        ("Allow automatic horizontal scrolling", "overflow-x: auto"),
        ("Always provide vertical scrolling", "overflow-y: scroll"),
        ("Hide overflow on both axes", "overflow: hidden"),
        ("Clip overflow and create a flow-root formatting context", "overflow: clip; display: flow-root"),
        ("Allow automatic horizontal scrolling and hide vertical overflow", "overflow-x: auto; overflow-y: hidden"),
        ("Allow automatic scrolling on both axes and limit height to 200px", "overflow: auto; max-height: 200px"),
    ],
    "table": [
        ("Use automatic table layout", "table-layout: auto"),
        ("Use fixed table layout and width 100%", "table-layout: fixed; width: 100%"),
        ("Collapse table borders", "border-collapse: collapse"),
        ("Keep borders separate with 8px spacing", "border-collapse: separate; border-spacing: 8px"),
        ("Place the table caption below the table", "caption-side: bottom"),
        ("Hide empty cells and keep borders separate", "empty-cells: hide; border-collapse: separate"),
    ],
    "columns": [
        ("Use two text columns", "column-count: 2"),
        ("Use a preferred column width of 180px", "column-width: 180px"),
        ("Use three columns separated by 24px gaps", "column-count: 3; column-gap: 24px"),
        ("Use two columns with a 1px solid #334155 column rule", "column-count: 2; column-rule: 1px solid #334155"),
        ("Make the element span every column", "column-span: all"),
        ("Fill columns sequentially with column-fill auto and height 300px", "column-fill: auto; height: 300px"),
    ],
    "object-fit": [
        ("Contain the entire image in its existing box", "object-fit: contain"),
        ("Cover the existing box with the image and align it at the right bottom", "object-fit: cover; object-position: right bottom"),
        ("Stretch the image to fill its box and display it as a block", "object-fit: fill; display: block"),
        ("Contain the image and limit its width to 100%", "object-fit: contain; max-width: 100%"),
        ("Use scale-down image fitting and set its width to 160px", "object-fit: scale-down; width: 160px"),
        ("Do not resize the image content for fitting and set its box height to 120px", "object-fit: none; height: 120px"),
    ],
}

JS_REPLACEMENTS = {
    "bound": [
        ("cap value at the upper limit using a conditional expression", "return value > limit ? limit : value;", [4, 10], 4),
        ("raise value to the lower limit using a conditional expression", "return value < limit ? limit : value;", [4, 10], 10),
        None, None, None,
        ("return the absolute distance using a conditional expression", "return value > limit ? value - limit : limit - value;", [4, 10], 6),
    ],
    "conversion": [
        ("convert seconds to milliseconds", "return value * 1000;", [2], 2000),
        ("convert milliseconds to seconds", "return value / 1000;", [2000], 2),
        ("convert nonnegative seconds to completed whole minutes, rounded down", "return Math.floor(value / 60);", [125], 2),
        ("return an object with centimeters and millimeters converted from meters", "return { centimeters: value * 100, millimeters: value * 1000 };", [2], {"centimeters": 200, "millimeters": 2000}),
        ("return an array containing seconds then milliseconds converted from minutes", "return [value * 60, value * 60000];", [2], [120, 120000]),
        ("convert nonnegative milliseconds to seconds rounded up", "return Math.ceil(value / 1000);", [1500], 2),
    ],
    "string-build": [
        ("surround text with square brackets", "return '[' + text + ']';", ["oak"], "[oak]"),
        ("return text with outer whitespace removed", "return text.trim();", [" oak "], "oak"),
        ("return text in uppercase", "return text.toUpperCase();", ["oak"], "OAK"),
        ("return text in lowercase", "return text.toLowerCase();", ["OAK"], "oak"),
        ("return an array containing text twice", "return [text, text];", ["oak"], ["oak", "oak"]),
        ("return an object whose label property contains text", "return { label: text };", ["oak"], {"label": "oak"}),
    ],
}


class Tree(html.parser.HTMLParser):
    """Strict tree for explicit-tag fragments, not a browser conformance checker."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ["root", {}, []]
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        if len(dict(attrs)) != len(attrs): raise ValueError("Duplicate HTML attribute")
        node = [tag, dict(attrs), []]
        self.stack[-1][2].append(node)
        if tag not in {"br", "img", "input", "hr", "wbr"}: self.stack.append(node)

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1][0] != tag: raise ValueError("Misnested HTML")
        self.stack.pop()

    def handle_data(self, data):
        if data.strip(): self.stack[-1][2].append(data)

    def finish(self, text):
        self.feed(text); self.close()
        if len(self.stack) != 1: raise ValueError("Unclosed HTML")
        return self.root


def skeleton(row):
    if row["language"] == "html":
        def shape(node):
            if isinstance(node, str): return "TEXT"
            return [node[0], sorted(node[1]), [shape(c) for c in node[2]]]
        return json.dumps(shape(Tree().finish(row["solution"])), sort_keys=True)
    if row["language"] == "css":
        status, rules, _ = _inspect_css(row["solution"])
        if status != "pass" or len(rules) != 1: raise ValueError("Expected one CSS rule")
        return json.dumps(sorted(next(iter(rules.values()))))
    source = row["solution"]
    signature = re.match(r"function \w+\((.*?)\) \{", source)
    if not signature: raise ValueError("Expected one declared function")
    source = re.sub(r"function \w+", "function FUNC", source)
    for index, argument in enumerate(signature[1].split(",")):
        source = re.sub(r"\b" + re.escape(argument.strip()) + r"\b", f"ARG{index}", source)
    source = re.sub(r"(['\"])(?:\\.|(?!\1).)*\1", "STRING", source)
    source = re.sub(r"\b\d+(?:\.\d+)?\b", "NUMBER", source)
    return " ".join(source.split())


def records():
    rows = [copy.deepcopy(r) for r in original.records() if r["id"].endswith("-1")]
    for row in rows:
        row["id"] = row["id"].removesuffix("-1").replace("rf-", "curated-", 1)
        row["sourceFamilyId"] = row["sourceFamilyId"].replace("-v1", "-v2")
        language, family, pattern = row["templateLineage"].split("/")
        index = int(pattern.removeprefix("pattern-")) - 1
        row["curationOrigin"] = "p2-02-request-following-v1"
        if language == "html":
            instruction, template, tags = original.HTML[family][index]
            if family == "ruby" and index == 1:
                instruction, template, tags = "Put the whole ruby pronunciation annotation inside a paragraph", '<p><ruby>{word}<rt>{reading}</rt></ruby></p>', ["p", "ruby", "rt"]
            values = {"word": "Kyoto", "reading": "Kyo-to", "sentence": "A quiet destination.", "number": 35}
            if family == "abbreviation": values.update(word="I/O", sentence="Input and output")
            row["solution"] = template.format(**values)
            used = set(re.findall(r"\{(\w+)\}", template)) - {"number"}
            labels = {"word": "word", "reading": "reading", "sentence": "sentence"}
            text = "; ".join(f'{labels[key]} "{values[key]}"' for key in ("word", "reading", "sentence") if key in used)
            row["request"] = instruction.format(**values) + (". Use " + text if text else "") + ". Return only the fragment."
            row["checks"] = [c for c in row["checks"] if c["kind"] != "contains"]
            if family == "ruby" and index == 1: row["checks"] = [{"kind": "html_element", "tag": tag} for tag in tags]
            row["expectedHtmlTree"] = Tree().finish(row["solution"])
        elif language == "css":
            instruction, profile = CSS[family][index]
            selector = ".rf-" + family + "-alpha"
            declarations = dict(part.strip().split(": ", 1) for part in profile.split(";"))
            row["request"] = f"For {selector}: {instruction}. Return one rule with only the requested declarations."
            row["solution"] = selector + " {\n" + "\n".join(f"  {key}: {value};" for key, value in declarations.items()) + "\n}"
            row["expectedCssRules"] = {selector: declarations}
            row["checks"] = [{"kind": "css_declaration", "selector": selector, "property": key, "value": value} for key, value in declarations.items()]
        elif family in JS_REPLACEMENTS and JS_REPLACEMENTS[family][index] is not None:
            operation, body, arguments, expected = JS_REPLACEMENTS[family][index]
            parameters, domain, _ = original.JS[family]
            if family == "conversion" and index in {2, 5}: domain = "a nonnegative finite numeric value"
            row["request"] = f"Write transformAlpha({parameters}) for {domain}; {operation}. Return one JavaScript function."
            row["solution"] = f"function transformAlpha({parameters}) {{\n  {body}\n}}"
            row["checks"] = [{"kind": "js_function", "name": "transformAlpha"}, {"kind": "contains", "text": body}]
            row["behaviorReviewCases"] = [{"arguments": arguments, "expected": expected}]
    groups = {f"plex-request-following-{language}-v2": {r["splitGroupId"] for r in rows if r["language"] == language} for language in LANGUAGES}
    held = _family_stratified_group_split(groups, 30, 51)
    for row in rows:
        row["candidateSplit"] = "validation" if (row["sourceFamilyId"], row["splitGroupId"]) in held else "train"
    return rows


def validate(rows, tasks):
    if tasks["kind"] != "development": raise ValueError("Final holdout must remain unopened")
    if any(prompt_text(t, tasks["outputContracts"]) != render_task_prompt(tasks, t) for t in tasks["tasks"]): raise ValueError("Prompt drift")
    normalized = lambda text: " ".join(text.casefold().split())
    known = {normalized(t["request"]) for t in tasks["tasks"]}
    for name in ("p2-02-code-pairs-v2.jsonl", "p2-02-authored-examples-v1.jsonl"):
        known.update(normalized(json.loads(line)["request"]) for line in (OUTPUT.parent / name).read_text(encoding="utf-8").splitlines())
    known.update(normalized(r["request"]) for r in json.loads((OUTPUT.parent / "p2-02-expansion-samples-v1.json").read_text(encoding="utf-8"))["examples"])
    ids, requests, answers, shapes = set(), set(), set(), {}
    checks = 0
    for row in rows:
        if row["approvalStatus"] != "pending-owner-review": raise ValueError("Unapproved curation cannot claim approval")
        if row["id"] in ids or normalized(row["request"]) in requests | known or normalized(row["solution"]) in answers: raise ValueError("Exact duplicate")
        key = row["language"] + "/" + skeleton(row)
        if key in shapes: raise ValueError(f"Literal/name-only structural duplicate: {row['id']} and {shapes[key]}")
        shapes[key] = row["id"]
        result = _check_task({"id": row["id"], "language": row["language"], "difficulty": "basic", "checks": row["checks"]}, row["solution"], None, 5.0)
        if not result["passed"]: raise ValueError(f"Static answer failure: {result}")
        checks += result["checksPassed"]
        if row["language"] == "html":
            if Tree().finish(row["solution"]) != row["expectedHtmlTree"]: raise ValueError("HTML nesting/text/attributes differ from reviewed tree")
            if re.search(r"<rb(?:\s|>)", row["solution"]): raise ValueError("Obsolete ruby base markup")
            checks += 1
        elif row["language"] == "css":
            status, rules, _ = _inspect_css(row["solution"])
            if status != "pass" or rules != row["expectedCssRules"]: raise ValueError("Extra or missing CSS declaration")
            checks += 1
        for forbidden in row["reviewForbiddenStrings"]:
            if forbidden in row["solution"]: raise ValueError("Forbidden output")
            checks += 1
        ids.add(row["id"]); requests.add(normalized(row["request"])); answers.add(normalized(row["solution"]))
    if Counter(r["language"] for r in rows) != {language: 60 for language in LANGUAGES}: raise ValueError("Curated candidate requires sixty per language")
    groups = {f"plex-request-following-{language}-v2": {r["splitGroupId"] for r in rows if r["language"] == language} for language in LANGUAGES}
    held = _family_stratified_group_split(groups, 30, 51)
    if any(r["candidateSplit"] != ("validation" if (r["sourceFamilyId"], r["splitGroupId"]) in held else "train") for r in rows): raise ValueError("Wrong whole-group split")
    topic_counts = Counter("/".join(r["templateLineage"].split("/")[:2]) for r in rows)
    if len(topic_counts) != 30 or set(topic_counts.values()) != {6}: raise ValueError("Each topic requires six distinct profiles")
    return {"schemaVersion": 1, "candidate": "p2-02-request-following-v2", "approvalStatus": "pending-owner-review", "records": len(rows),
            "recordsByLanguage": dict(Counter(r["language"] for r in rows)), "recordsBySplit": dict(Counter(r["candidateSplit"] for r in rows)),
            "recordsBySplitAndLanguage": dict(Counter(f"{r['candidateSplit']}/{r['language']}" for r in rows)), "topicFamilies": 30, "splitGroups": sum(len(g) for g in groups.values()),
            "distinctConservativeSkeletons": len(shapes), "staticSolutionsPassed": len(rows), "staticChecksPassed": checks,
            "splitSeed": 51, "validationPercentOfGroups": 30, "javascriptBehaviorExecuted": False, "finalHoldoutOpened": False, "modelTrained": False,
            "externalSourceTextIncluded": False, "exactDevelopmentOrEarlierApprovedRequestDuplicates": 0,
            "limitations": ["Conservative syntax skeletons measure this screening rule, not independent semantic skills.",
                            "Some wrapper combinations remain related; all topic/template relatives stay grouped.",
                            "Reviewed HTML tree and CSS declaration expectations validate authored structure, not browser behavior.",
                            "JavaScript behavior cases were reviewed by inspection, not executed.",
                            "No fresh candidate tokenizer or measured new-tokenizer budgets yet."]}


def prepare():
    if OUTPUT.exists(): raise FileExistsError("Never overwrite an existing review version")
    tasks = json.loads(original.DEV.read_text(encoding="utf-8"))
    rows = records(); report = validate(rows, tasks)
    raw = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
    report["candidateJsonlSha256"] = hashlib.sha256(raw).hexdigest()
    report["developmentTaskSetSha256"] = hashlib.sha256(original.DEV.read_bytes()).hexdigest()
    staging = OUTPUT.parent / (".curated-request-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        (staging / "candidate.jsonl").write_bytes(raw)
        (staging / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        guide = ["# Curated request-following candidate: all 180 examples\n", "**Pending owner approval for these exact records; not in training.**\n",
                 "The earlier twelve samples are approved separately. This candidate removes 180 rename-only variants, revises weak profiles, and preserves the previous draft. "
                 "There are 60 examples per language, six conservative syntax profiles per topic, and 29 indivisible split groups. "
                 "This is a small instruction-format experiment, not a sufficient scratch-pretraining corpus.\n",
                 f"Canonical JSONL SHA-256: `{report['candidateJsonlSha256']}`.\n",
                 "Expected JavaScript cases are review notes, never executed. HTML tree checks and exact CSS declarations supplement the existing static checks. "
                 "Checks establish supplied-answer consistency, not browser behavior or Plex capability.\n"]
        catalog = []
        for language in LANGUAGES:
            root = staging / "sources" / language
            root.mkdir(parents=True)
            (root / "NOTICE.md").write_text("Original Codex-authored curated examples for exact-record local P2 review. No external text; approval pending; no public license asserted. Excluded from training.\n", encoding="utf-8")
            groups = sorted({r["splitGroupId"] for r in rows if r["language"] == language})
            family = f"plex-request-following-{language}-v2"
            catalog.append({"id": family, "groupId": family, "sourceFamilyId": family, "localPath": f"sources/{language}", "origin": "urn:plex:codex-authored:p2-02-request-following-v2",
                            "revision": report["candidateJsonlSha256"], "licenseId": "Local-use-review-pending", "licenseEvidence": "NOTICE.md", "rightsReviewStatus": "pending-owner-review",
                            "rightsReviewedAtUtc": None, "includeExtensions": [".txt"], "splitGroupRules": [{"id": group, "pathPrefixes": [group + "/"]} for group in groups]})
            for row in (r for r in rows if r["language"] == language):
                folder = root / row["splitGroupId"]; folder.mkdir(exist_ok=True)
                (folder / (row["id"] + ".txt")).write_text(prompt_text(row, tasks["outputContracts"]) + "\n" + row["solution"], encoding="utf-8", newline="\n")
                guide.append(f"## {row['id']} — {row['candidateSplit']}\n\nFamily: `{row['splitGroupId']}`.\n\n{row['request']}\n\n```{language}\n{row['solution']}\n```\n")
                if row["behaviorReviewCases"]: guide.append("Expected cases (not executed): `" + json.dumps(row["behaviorReviewCases"]) + "`\n")
        (staging / "dataset-sources.candidate.json").write_text(json.dumps({"schemaVersion": 1, "splitStrategy": "family-stratified-groups-v1", "sources": catalog}, indent=2) + "\n", encoding="utf-8", newline="\n")
        (staging / "REVIEW.md").write_text("\n".join(guide), encoding="utf-8", newline="\n")
        os.rename(staging, OUTPUT)
    except Exception:
        if staging.resolve().parent == OUTPUT.parent.resolve() and staging.name.startswith(".curated-request-"): shutil.rmtree(staging)
        raise
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
