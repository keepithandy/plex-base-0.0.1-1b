"""Create a pending, original 360-record candidate; never approve or train it.

All related templates remain in one split group. JavaScript is parsed only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))
from plex_training.benchmark import _check_task, render_task_prompt
from plex_training.dataset import _family_stratified_group_split
from prepare_code_pair_candidate import prompt_text

OUTPUT = ROOT / "training/phase2/drafts/p2-02-request-following-v1"
DEV = ROOT / "training/phase2/evaluation/p2-01b-dev-v1.json"

# Each family has six requirement/answer patterns, with two related text/name
# variants per pattern. These are template-authored examples, not 360 independent
# tasks. The full family, including all six patterns, is one indivisible group.
HTML = {
    "ruby": [
        ("Use ruby with an rt reading", '<ruby>{word}<rt>{reading}</rt></ruby>', ["ruby", "rt"]),
        ("Use ruby with rb for the word and rt for its reading", '<ruby><rb>{word}</rb><rt>{reading}</rt></ruby>', ["ruby", "rb", "rt"]),
        ("Use ruby with rt and rp parentheses around the reading", '<ruby>{word}<rp>(</rp><rt>{reading}</rt><rp>)</rp></ruby>', ["ruby", "rp", "rt"]),
        ("Put the word in strong inside ruby, followed by its rt reading", '<ruby><strong>{word}</strong><rt>{reading}</rt></ruby>', ["ruby", "strong", "rt"]),
        ("Put the word in em inside ruby, followed by its rt reading", '<ruby><em>{word}</em><rt>{reading}</rt></ruby>', ["ruby", "em", "rt"]),
        ("Put the whole ruby pronunciation annotation inside a span", '<span><ruby>{word}<rt>{reading}</rt></ruby></span>', ["span", "ruby", "rt"]),
    ],
    "disclosure": [
        ("Make a collapsed details with summary and paragraph", '<details><summary>{word}</summary><p>{sentence}</p></details>', ["details", "summary", "p"]),
        ("Make an expanded details with summary and paragraph", '<details open><summary>{word}</summary><p>{sentence}</p></details>', ["details", "summary", "p"]),
        ("Make a collapsed details with summary and a one-item unordered list", '<details><summary>{word}</summary><ul><li>{sentence}</li></ul></details>', ["details", "summary", "ul", "li"]),
        ("Make an expanded details with summary and a one-item ordered list", '<details open><summary>{word}</summary><ol><li>{sentence}</li></ol></details>', ["details", "summary", "ol", "li"]),
        ("Make a collapsed details with summary and an emphasized body paragraph", '<details><summary>{word}</summary><p><em>{sentence}</em></p></details>', ["details", "summary", "p", "em"]),
        ("Make an expanded details with summary and a strongly emphasized body paragraph", '<details open><summary>{word}</summary><p><strong>{sentence}</strong></p></details>', ["details", "summary", "p", "strong"]),
    ],
    "bidi": [
        ("Isolate the word using bdi", '<bdi>{word}</bdi>', ["bdi"]),
        ("Put a bdi-isolated word inside a paragraph", '<p><bdi>{word}</bdi></p>', ["p", "bdi"]),
        ("Put a bdi-isolated word inside strong", '<strong><bdi>{word}</bdi></strong>', ["strong", "bdi"]),
        ("Put a bdi-isolated word inside em", '<em><bdi>{word}</bdi></em>', ["em", "bdi"]),
        ("Put a bdi-isolated word inside a span with class isolated", '<span class="isolated"><bdi>{word}</bdi></span>', ["span", "bdi"]),
        ("Put a bdi-isolated word inside a one-item unordered list", '<ul><li><bdi>{word}</bdi></li></ul>', ["ul", "li", "bdi"]),
    ],
    "quote": [
        ("Mark the sentence as an inline quotation using q", '<q>{sentence}</q>', ["q"]),
        ("Put an inline q quotation inside a paragraph", '<p><q>{sentence}</q></p>', ["p", "q"]),
        ("Emphasize an inline q quotation using em around q", '<em><q>{sentence}</q></em>', ["em", "q"]),
        ("Put an inline q quotation inside strong", '<strong><q>{sentence}</q></strong>', ["strong", "q"]),
        ("Put an inline q quotation inside a span with class quotation", '<span class="quotation"><q>{sentence}</q></span>', ["span", "q"]),
        ("Put an inline q quotation inside a one-item ordered list", '<ol><li><q>{sentence}</q></li></ol>', ["ol", "li", "q"]),
    ],
    "abbreviation": [
        ("Mark the word as abbr with the sentence as its title", '<abbr title="{sentence}">{word}</abbr>', ["abbr"]),
        ("Put that titled abbreviation inside a paragraph", '<p><abbr title="{sentence}">{word}</abbr></p>', ["p", "abbr"]),
        ("Put that titled abbreviation inside strong", '<strong><abbr title="{sentence}">{word}</abbr></strong>', ["strong", "abbr"]),
        ("Put that titled abbreviation inside em", '<em><abbr title="{sentence}">{word}</abbr></em>', ["em", "abbr"]),
        ("Put that titled abbreviation inside a span with class term", '<span class="term"><abbr title="{sentence}">{word}</abbr></span>', ["span", "abbr"]),
        ("Put that titled abbreviation inside a one-item unordered list", '<ul><li><abbr title="{sentence}">{word}</abbr></li></ul>', ["ul", "li", "abbr"]),
    ],
    "description": [
        ("Use dl with one dt word and one dd sentence", '<dl><dt>{word}</dt><dd>{sentence}</dd></dl>', ["dl", "dt", "dd"]),
        ("Use dl with the dt word inside strong and one dd sentence", '<dl><dt><strong>{word}</strong></dt><dd>{sentence}</dd></dl>', ["dl", "dt", "dd", "strong"]),
        ("Use dl with one dt word and the dd sentence inside em", '<dl><dt>{word}</dt><dd><em>{sentence}</em></dd></dl>', ["dl", "dt", "dd", "em"]),
        ("Use dl with one dt word and the dd sentence inside a paragraph", '<dl><dt>{word}</dt><dd><p>{sentence}</p></dd></dl>', ["dl", "dt", "dd", "p"]),
        ("Wrap a one-term dl in a section; use dt for the word and dd for the sentence", '<section><dl><dt>{word}</dt><dd>{sentence}</dd></dl></section>', ["section", "dl", "dt", "dd"]),
        ("Use dl with a div wrapping its dt word and dd sentence", '<dl><div><dt>{word}</dt><dd>{sentence}</dd></div></dl>', ["dl", "div", "dt", "dd"]),
    ],
    "progress": [
        ("Make determinate progress with value {number} and max 100", '<progress value="{number}" max="100"></progress>', ["progress"]),
        ("Make determinate progress with value {number}, max 100, and the word as fallback text", '<progress value="{number}" max="100">{word}</progress>', ["progress"]),
        ("Make indeterminate progress with the word as fallback text and no value attribute", '<progress>{word}</progress>', ["progress"]),
        ("Wrap determinate progress with value {number} and max 100 in a paragraph", '<p><progress value="{number}" max="100"></progress></p>', ["p", "progress"]),
        ("Put indeterminate progress with the word as fallback text and no value attribute inside a span", '<span><progress>{word}</progress></span>', ["span", "progress"]),
        ("Put determinate progress with value {number} and max 100 inside a div with class tracking", '<div class="tracking"><progress value="{number}" max="100"></progress></div>', ["div", "progress"]),
    ],
    "meter": [
        ("Make a meter with min 0, max 100, and value {number}", '<meter min="0" max="100" value="{number}"></meter>', ["meter"]),
        ("Make a meter with min 0, max 100, value {number}, and the word as fallback text", '<meter min="0" max="100" value="{number}">{word}</meter>', ["meter"]),
        ("Make a meter with min 0, max 100, value {number}, low 20, high 80, and optimum 50", '<meter min="0" max="100" value="{number}" low="20" high="80" optimum="50"></meter>', ["meter"]),
        ("Put a meter with min 0, max 100, and value {number} inside a paragraph", '<p><meter min="0" max="100" value="{number}"></meter></p>', ["p", "meter"]),
        ("Put a meter with min 0, max 100, and value {number} inside a span", '<span><meter min="0" max="100" value="{number}"></meter></span>', ["span", "meter"]),
        ("Put a meter with min 0, max 100, and value {number} inside a div with class reading", '<div class="reading"><meter min="0" max="100" value="{number}"></meter></div>', ["div", "meter"]),
    ],
    "contact": [
        ("Put the word in address as plain contact text", '<address>{word}</address>', ["address"]),
        ("Put the word in a paragraph inside address", '<address><p>{word}</p></address>', ["address", "p"]),
        ("Put the word in strong inside address", '<address><strong>{word}</strong></address>', ["address", "strong"]),
        ("Put the word in a span with class contact inside address", '<address><span class="contact">{word}</span></address>', ["address", "span"]),
        ("Put the word then br then the sentence inside address", '<address>{word}<br>{sentence}</address>', ["address", "br"]),
        ("Put two paragraphs in address: the word then the sentence", '<address><p>{word}</p><p>{sentence}</p></address>', ["address", "p"]),
    ],
    "heading-group": [
        ("Make hgroup containing h1 with the word and p with the sentence", '<hgroup><h1>{word}</h1><p>{sentence}</p></hgroup>', ["hgroup", "h1", "p"]),
        ("Make hgroup containing h2 with the word and p with the sentence", '<hgroup><h2>{word}</h2><p>{sentence}</p></hgroup>', ["hgroup", "h2", "p"]),
        ("Make hgroup containing h3 with the word and p with the sentence", '<hgroup><h3>{word}</h3><p>{sentence}</p></hgroup>', ["hgroup", "h3", "p"]),
        ("Make hgroup containing p with the sentence then h2 with the word", '<hgroup><p>{sentence}</p><h2>{word}</h2></hgroup>', ["hgroup", "h2", "p"]),
        ("Make hgroup containing h2 with the word and p with the sentence inside em", '<hgroup><h2>{word}</h2><p><em>{sentence}</em></p></hgroup>', ["hgroup", "h2", "p", "em"]),
        ("Wrap hgroup in a header; put the word in h2 and the sentence in p", '<header><hgroup><h2>{word}</h2><p>{sentence}</p></hgroup></header>', ["header", "hgroup", "h2", "p"]),
    ],
}

# Each entry is an exact declaration profile: unlike pure value substitution,
# profiles alter requested state, property, or a combination of constraints.
CSS = {
    "logical-border": ["border-inline-start: 2px solid #334155", "border-inline-end: 2px solid #334155", "border-block-start: 2px dashed #334155", "border-block-end: 2px dashed #334155", "border-inline-start: 2px solid #334155; border-inline-end: 0", "border-block-start: 0; border-block-end: 2px solid #334155"],
    "aspect": ["aspect-ratio: 1 / 1", "aspect-ratio: 16 / 9", "aspect-ratio: auto", "aspect-ratio: 1 / 1; width: 120px", "aspect-ratio: 16 / 9; width: 240px", "aspect-ratio: 4 / 3; max-width: 100%"],
    "outline": ["outline-style: solid", "outline-style: dashed", "outline: 2px solid #334155", "outline: 2px solid #334155; outline-offset: 4px", "outline: 0; box-shadow: none", "outline-style: dotted; outline-width: 3px; outline-offset: -2px"],
    "cursor": ["cursor: pointer", "cursor: text", "cursor: wait", "cursor: not-allowed; opacity: 0.5", "cursor: grab; user-select: none", "cursor: default; user-select: text"],
    "whitespace": ["white-space: normal", "white-space: nowrap", "white-space: pre", "white-space: pre-wrap; overflow-wrap: anywhere", "white-space: pre-line; overflow-wrap: break-word", "white-space: break-spaces; tab-size: 4"],
    "decoration": ["text-decoration-line: underline", "text-decoration-line: line-through", "text-decoration-line: none", "text-decoration-line: underline; text-decoration-style: wavy", "text-decoration-line: underline; text-decoration-color: #334155", "text-decoration-line: underline overline; text-underline-offset: 4px"],
    "overflow": ["overflow-x: auto", "overflow-y: scroll", "overflow: hidden", "overflow: clip; display: flow-root", "overflow-x: auto; overflow-y: hidden", "overflow: auto; max-height: 200px"],
    "table": ["table-layout: auto", "table-layout: fixed; width: 100%", "border-collapse: collapse", "border-collapse: separate; border-spacing: 8px", "caption-side: bottom", "empty-cells: hide; border-collapse: separate"],
    "columns": ["column-count: 2", "column-width: 180px", "column-count: 3; column-gap: 24px", "column-count: 2; column-rule: 1px solid #334155", "column-span: all", "column-fill: auto; height: 300px"],
    "object-fit": ["object-fit: contain", "object-fit: cover", "object-fit: fill", "object-fit: none; object-position: center", "object-fit: scale-down; object-position: left top", "object-fit: cover; object-position: right bottom"],
}

# Function domain and operation are explicit. Behavior examples below are human
# review expectations only. Node --check never calls these functions.
JS = {
    "binary": ("a, b", "finite numbers a and b", [
        ("return a plus b", "return a + b;", [3, 4], 7),
        ("return a minus b", "return a - b;", [3, 4], -1),
        ("return the product of a and b", "return a * b;", [3, 4], 12),
        ("return the larger number", "return Math.max(a, b);", [3, 4], 4),
        ("return the smaller number", "return Math.min(a, b);", [3, 4], 3),
        ("return the absolute difference", "return Math.abs(a - b);", [3, 4], 1)]),
    "bound": ("value, limit", "finite numbers value and limit", [
        ("cap value at the upper limit", "return Math.min(value, limit);", [4, 10], 4),
        ("raise value to at least the lower limit", "return Math.max(value, limit);", [4, 10], 10),
        ("report whether value exceeds limit", "return value > limit;", [4, 10], False),
        ("report whether value is below limit", "return value < limit;", [4, 10], True),
        ("report whether value equals limit", "return value === limit;", [4, 10], False),
        ("return the distance between value and limit", "return Math.abs(value - limit);", [4, 10], 6)]),
    "division": ("a, b", "integers a and b with b nonzero and small enough for exact arithmetic", [
        ("return the quotient rounded toward zero", "return Math.trunc(a / b);", [-7, 3], -2),
        ("return the quotient rounded down", "return Math.floor(a / b);", [-7, 3], -3),
        ("return the quotient rounded up", "return Math.ceil(a / b);", [-7, 3], -2),
        ("return the JavaScript remainder", "return a % b;", [-7, 3], -1),
        ("return whether a is divisible by b", "return a % b === 0;", [-7, 3], False),
        ("return the absolute JavaScript remainder", "return Math.abs(a % b);", [-7, 3], 1)]),
    "conversion": ("value", "a finite numeric value", [
        ("convert seconds to milliseconds", "return value * 1000;", [2], 2000),
        ("convert milliseconds to seconds", "return value / 1000;", [2000], 2),
        ("convert minutes to seconds", "return value * 60;", [2], 120),
        ("convert seconds to minutes", "return value / 60;", [120], 2),
        ("convert centimeters to meters", "return value / 100;", [250], 2.5),
        ("convert meters to centimeters", "return value * 100;", [2.5], 250)]),
    "classification": ("value", "a finite numeric value", [
        ("report whether value is an integer", "return Number.isInteger(value);", [2.5], False),
        ("report whether value is positive", "return value > 0;", [-2], False),
        ("report whether value is negative", "return value < 0;", [-2], True),
        ("report whether value is zero", "return value === 0;", [0], True),
        ("return its sign using Math.sign", "return Math.sign(value);", [-2], -1),
        ("return its absolute magnitude", "return Math.abs(value);", [-2], 2)]),
    "array-lookup": ("items, value", "an array items and a value, with primitive elements", [
        ("return whether items includes value", "return items.includes(value);", [[2, 4, 2], 2], True),
        ("return the first index of value or -1", "return items.indexOf(value);", [[2, 4, 2], 2], 0),
        ("return the last index of value or -1", "return items.lastIndexOf(value);", [[2, 4, 2], 2], 2),
        ("return whether value equals the first element, using strict equality", "return items.length > 0 && items[0] === value;", [[2, 4, 2], 2], True),
        ("return whether value equals the last element, using strict equality", "return items.length > 0 && items[items.length - 1] === value;", [[2, 4, 2], 4], False),
        ("count elements strictly equal to value", "return items.filter(item => item === value).length;", [[2, 4, 2], 2], 2)]),
    "array-copy": ("items", "an array items; preserve the original array", [
        ("return a shallow copy", "return items.slice();", [[1, 2, 3]], [1, 2, 3]),
        ("return a reversed shallow copy", "return items.slice().reverse();", [[1, 2, 3]], [3, 2, 1]),
        ("return a copy omitting the first element", "return items.slice(1);", [[1, 2, 3]], [2, 3]),
        ("return a copy omitting the last element", "return items.slice(0, -1);", [[1, 2, 3]], [1, 2]),
        ("return a copy of at most the first two elements", "return items.slice(0, 2);", [[1, 2, 3]], [1, 2]),
        ("return a copy of at most the last two elements", "return items.slice(-2);", [[1, 2, 3]], [2, 3])]),
    "string-slice": ("text, count", "a string text and a nonnegative integer count; count UTF-16 code units", [
        ("return at most the first count code units", "return text.slice(0, count);", ["abcd", 2], "ab"),
        ("remove at most the first count code units", "return text.slice(count);", ["abcd", 2], "cd"),
        ("return at most the last count code units, or empty if count is zero", "return count === 0 ? '' : text.slice(-count);", ["abcd", 0], ""),
        ("remove at most the last count code units, returning text unchanged for zero", "return count === 0 ? text : text.slice(0, -count);", ["abcd", 0], "abcd"),
        ("return whether text has more than count code units", "return text.length > count;", ["abcd", 2], True),
        ("return whether text has exactly count code units", "return text.length === count;", ["abcd", 2], False)]),
    "string-build": ("text", "a string text", [
        ("surround text with square brackets", "return '[' + text + ']';", ["oak"], "[oak]"),
        ("surround text with parentheses", "return '(' + text + ')';", ["oak"], "(oak)"),
        ("prepend a hash character", "return '#' + text;", ["oak"], "#oak"),
        ("append an exclamation mark", "return text + '!';", ["oak"], "oak!"),
        ("concatenate text to itself", "return text + text;", ["oak"], "oakoak"),
        ("put one slash before and after text", "return '/' + text + '/';", ["oak"], "/oak/")]),
    "object-lookup": ("record, key", "a plain object record and a string key; return results without mutation", [
        ("return the property value", "return record[key];", [{"a": 3}, "a"], 3),
        ("report whether record has an own property named key", "return Object.prototype.hasOwnProperty.call(record, key);", [{"a": 3}, "a"], True),
        ("return all own enumerable string keys; key is unused", "return Object.keys(record);", [{"a": 3}, "a"], ["a"]),
        ("return all own enumerable values; key is unused", "return Object.values(record);", [{"a": 3}, "a"], [3]),
        ("return all own enumerable key-value pairs; key is unused", "return Object.entries(record);", [{"a": 3}, "a"], [["a", 3]]),
        ("report whether the property value is undefined", "return record[key] === undefined;", [{}, "a"], True)]),
}


def records() -> list[dict]:
    rows = []
    def add(language, family, pattern, variant, request, answer, checks, cases=None, forbidden=None):
        rows.append({"schemaVersion": 1, "id": f"rf-{language}-{family}-{pattern+1:02}-{variant+1}",
                     "language": language, "sourceFamilyId": f"plex-request-following-{language}-v1",
                     "splitGroupId": f"{language}-{family}", "templateLineage": f"{language}/{family}/pattern-{pattern+1}",
                     "provenance": "codex-authored-template-candidate", "approvalStatus": "pending-owner-review",
                     "request": request, "solution": answer, "checks": checks,
                     "behaviorReviewCases": cases or [], "reviewForbiddenStrings": forbidden or []})
    for family, patterns in HTML.items():
        for i, (instruction, template, tags) in enumerate(patterns):
            for j in range(2):
                values = {"word": ["Kyoto", "Osaka"][j], "reading": ["Kyo-to", "O-sa-ka"][j],
                          "sentence": ["A quiet destination.", "A busy destination."][j], "number": [35, 65][j]}
                if family == "abbreviation":
                    values.update(word=["I/O", "CPU"][j], sentence=["Input and output", "Central processing unit"][j])
                answer = template.format(**values)
                request = (instruction.format(**values) + f'. Use word "{values["word"]}", reading "{values["reading"]}", '
                           f'and sentence "{values["sentence"]}" where requested; omit unused supplied text. Return only the fragment.')
                checks = [{"kind": "html_element", "tag": tag} for tag in tags]
                # Attributes are separately checked; nesting is documented as a manual limitation.
                import re
                for tag, attrs in re.findall(r'<([a-z0-9]+)([^>]*)>', answer):
                    attributes = dict(re.findall(r'([a-z-]+)="([^"]*)"', attrs))
                    if " open" in attrs: attributes["open"] = None
                    if attributes: checks.append({"kind": "html_element", "tag": tag, "attrs": attributes})
                checks.append({"kind": "contains", "text": answer})
                forbidden = []
                if family == "disclosure" and " open" not in answer: forbidden.append(" open")
                if family == "progress" and 'value=' not in answer: forbidden.append('value=')
                add("html", family, i, j, request, answer, checks, forbidden=forbidden)
    for family, profiles in CSS.items():
        for i, profile in enumerate(profiles):
            for j in range(2):
                selector = f".rf-{family}-{'alpha' if j == 0 else 'beta'}"
                declarations = [tuple(part.strip().split(": ", 1)) for part in profile.split(";")]
                request = f"For {selector}, set " + "; ".join(f"{prop} to {value}" for prop, value in declarations) + ". Return one CSS rule with exactly these declarations."
                answer = selector + " {\n" + "\n".join(f"  {prop}: {value};" for prop, value in declarations) + "\n}"
                checks = [{"kind": "css_declaration", "selector": selector, "property": prop, "value": value} for prop, value in declarations]
                add("css", family, i, j, request, answer, checks)
    for family, (arguments, domain, patterns) in JS.items():
        for i, (operation, body, args, expected) in enumerate(patterns):
            for j in range(2):
                name = "transformAlpha" if j == 0 else "transformBeta"
                request = f"Write {name}({arguments}) for {domain}; {operation}. Return one JavaScript function."
                answer = f"function {name}({arguments}) {{\n  {body}\n}}"
                checks = [{"kind": "js_function", "name": name}, {"kind": "contains", "text": body}]
                add("javascript", family, i, j, request, answer, checks, [{"arguments": args, "expected": expected}])
    # Math.min/Math.max/absolute-difference bodies occur in both topics. Keeping
    # renamed functions apart would create template leakage across the split.
    for row in rows:
        if row["language"] == "javascript" and row["splitGroupId"] in {"javascript-binary", "javascript-bound"}:
            row["splitGroupId"] = "javascript-numeric-comparison"
    groups = {f"plex-request-following-{lang}-v1": {r["splitGroupId"] for r in rows if r["language"] == lang}
              for lang in ("html", "css", "javascript")}
    held = _family_stratified_group_split(groups, 30, 51)
    for row in rows:
        row["candidateSplit"] = "validation" if (row["sourceFamilyId"], row["splitGroupId"]) in held else "train"
    return rows


def validate(rows: list[dict], tasks: dict) -> dict:
    if tasks["kind"] != "development": raise ValueError("Final holdout must remain unopened")
    if any(prompt_text(task, tasks["outputContracts"]) != render_task_prompt(tasks, task) for task in tasks["tasks"]):
        raise ValueError("Candidate prompt renderer drift")
    normalize = lambda text: " ".join(text.casefold().split())
    known_requests = {normalize(t["request"]) for t in tasks["tasks"]}
    known_answers = set()
    for name in ("p2-02-code-pairs-v2.jsonl", "p2-02-authored-examples-v1.jsonl"):
        for line in (OUTPUT.parent / name).read_text(encoding="utf-8").splitlines():
            prior = json.loads(line); known_requests.add(normalize(prior["request"])); known_answers.add(normalize(prior["solution"]))
    samples = json.loads((OUTPUT.parent / "p2-02-expansion-samples-v1.json").read_text(encoding="utf-8"))
    known_requests.update(normalize(r["request"]) for r in samples["examples"])
    known_answers.update(normalize(r["solution"]) for r in samples["examples"])
    requests, answers, identifiers = set(), set(), set()
    checks = 0
    js_templates = {}
    for row in rows:
        request, answer = normalize(row["request"]), normalize(row["solution"])
        if request in requests or request in known_requests or answer in answers or answer in known_answers:
            raise ValueError(f"Duplicate request/solution: {row['id']}")
        if row["id"] in identifiers or row["approvalStatus"] != "pending-owner-review": raise ValueError("Invalid draft identity")
        if row["language"] == "javascript":
            match = re.match(r"function \w+\((.*?)\) \{", row["solution"])
            if not match: raise ValueError("Expected a bounded function declaration")
            signature = re.sub(r"function \w+", "function FUNC", row["solution"])
            for index, argument in enumerate(match[1].split(",")):
                signature = re.sub(r"\b" + re.escape(argument.strip()) + r"\b", f"ARG{index}", signature)
            prior_group = js_templates.setdefault(normalize(signature), row["splitGroupId"])
            if prior_group != row["splitGroupId"]: raise ValueError("Renamed JavaScript template crosses split groups")
        result = _check_task({"id": row["id"], "language": row["language"], "difficulty": "basic", "checks": row["checks"]}, row["solution"], None, 5.0)
        if not result["passed"]: raise ValueError(f"Static checks failed: {result}")
        for forbidden in row["reviewForbiddenStrings"]:
            if forbidden in row["solution"]: raise ValueError("Forbidden output")
        checks += result["checksPassed"] + len(row["reviewForbiddenStrings"])
        requests.add(request); answers.add(answer); identifiers.add(row["id"])
    counts = Counter(r["language"] for r in rows)
    splits = Counter(r["candidateSplit"] for r in rows)
    groups = {r["splitGroupId"] for r in rows}
    if counts != {lang: 120 for lang in ("html", "css", "javascript")} or sum(splits.values()) != 360: raise ValueError("Wrong candidate counts")
    language_groups = {f"plex-request-following-{lang}-v1": {r["splitGroupId"] for r in rows if r["language"] == lang}
                       for lang in ("html", "css", "javascript")}
    held = _family_stratified_group_split(language_groups, 30, 51)
    if any(r["candidateSplit"] != ("validation" if (r["sourceFamilyId"], r["splitGroupId"]) in held else "train") for r in rows):
        raise ValueError("Candidate split differs from deterministic whole-group assignment")
    for group in groups:
        members = [r for r in rows if r["splitGroupId"] == group]
        expected = 24 if group == "javascript-numeric-comparison" else 12
        if len(members) != expected or len({r["candidateSplit"] for r in members}) != 1 or len({r["templateLineage"] for r in members}) != expected // 2:
            raise ValueError("Template relatives must stay together")
    return {"schemaVersion": 1, "candidate": "p2-02-request-following-v1", "approvalStatus": "pending-owner-review",
            "records": 360, "recordsByLanguage": dict(counts), "recordsBySplit": dict(splits), "splitGroups": len(groups), "topicFamilies": 30,
            "declaredRequirementProfiles": 180, "variantsPerProfile": 2, "staticSolutionsPassed": 360, "staticChecksPassed": checks,
            "splitSeed": 51, "validationPercentOfGroups": 30, "javascriptBehaviorExecuted": False,
            "finalHoldoutOpened": False, "modelTrained": False, "externalSourceTextIncluded": False,
            "exactRequestOrSolutionDuplicatesWithPriorAuthoredSets": 0,
            "semanticOverlapAbsenceProven": False,
            "recordsBySplitAndLanguage": dict(Counter(f"{r['candidateSplit']}/{r['language']}" for r in rows)),
            "limitations": ["Template-authored; many related variants, not 360 independent tasks.",
                            "Six declared profiles per topic are not necessarily six independent structural patterns; some vary only a value.",
                            "Static checks partly reflect authored answers and do not prove semantics.",
                            "CSS requests explicitly state declarations; no proof of free-form task reasoning.",
                            "HTML nesting/content semantics and JavaScript behavior require review.",
                            "Candidate tokenizer and token budgets have not been measured."]}


def main() -> None:
    if OUTPUT.exists(): raise FileExistsError("Candidate exists; never overwrite its version")
    tasks = json.loads(DEV.read_text(encoding="utf-8"))
    rows = records(); report = validate(rows, tasks)
    raw = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    report["candidateJsonlSha256"] = hashlib.sha256(raw).hexdigest()
    report["developmentTaskSetSha256"] = hashlib.sha256(DEV.read_bytes()).hexdigest()
    OUTPUT.mkdir()
    (OUTPUT / "candidate.jsonl").write_bytes(raw)
    (OUTPUT / "review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    guide = ["# Request-following candidate: all 360 examples\n", "**Pending review: not approved or included in training.**\n",
             "Thirty topic families, six declared requirement profiles per topic, two variants per profile; 29 split groups after merging shared arithmetic/bound templates. All relatives stay together. "
             "The approved twelve samples illustrate the style but are not included or replaced here. "
             "JavaScript behavior cases are expectations, never executed. Static checks are not a correctness proof. Some profiles change values rather than structure: this draft does not yet meet the proposal's six-distinct-patterns target.\n",
             f"Canonical JSONL SHA-256: `{report['candidateJsonlSha256']}`.\n",
             "Training format is the unchanged inference prompt, newline, answer; EOS is appended by the tokenizer after approval.\n"]
    sources = []
    for lang in ("html", "css", "javascript"):
        source_root = OUTPUT / "sources" / lang
        source_root.mkdir(parents=True)
        (source_root / "NOTICE.md").write_text("Original Codex-authored template examples. Pending exact-record local training review; no external text or public license grant. Excluded from training.\n", encoding="utf-8")
        groups = sorted({r["splitGroupId"] for r in rows if r["language"] == lang})
        sources.append({"id": f"plex-request-following-{lang}-v1", "groupId": f"plex-request-following-{lang}-v1",
                        "sourceFamilyId": f"plex-request-following-{lang}-v1", "localPath": f"sources/{lang}",
                        "origin": "urn:plex:codex-authored:p2-02-request-following-v1", "revision": report["candidateJsonlSha256"],
                        "licenseId": "Local-use-review-pending", "licenseEvidence": "NOTICE.md", "rightsReviewStatus": "pending-owner-review",
                        "rightsReviewedAtUtc": None, "includeExtensions": [".txt"],
                        "splitGroupRules": [{"id": group, "pathPrefixes": [group + "/"]} for group in groups]})
        for row in (r for r in rows if r["language"] == lang):
            group_root = source_root / row["splitGroupId"]
            group_root.mkdir(exist_ok=True)
            text = prompt_text(row, tasks["outputContracts"]) + "\n" + row["solution"]
            (group_root / (row["id"] + ".txt")).write_text(text, encoding="utf-8", newline="\n")
            guide.append(f"## {row['id']} — {row['candidateSplit']}\n\nFamily: `{row['splitGroupId']}`; template: `{row['templateLineage']}`.\n\n{row['request']}\n\n```{lang}\n{row['solution']}\n```\n")
            if row["behaviorReviewCases"]: guide.append("Expected cases (not executed): `" + json.dumps(row["behaviorReviewCases"]) + "`\n")
    (OUTPUT / "dataset-sources.candidate.json").write_text(json.dumps({"schemaVersion": 1, "splitStrategy": "family-stratified-groups-v1", "sources": sources}, indent=2) + "\n", encoding="utf-8", newline="\n")
    (OUTPUT / "REVIEW.md").write_text("\n".join(guide), encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
