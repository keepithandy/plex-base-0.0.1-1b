"""Local, deterministic scoring for owner-authored Phase 2 coding tasks.

Generated JavaScript is syntax-checked with ``node --check`` but never executed.
HTML and CSS checks intentionally cover a documented, small static subset.
"""

from __future__ import annotations

import hashlib
import html.parser
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable

LANGUAGES = ("html", "css", "javascript")
ALLOWED_CHECKS = {
    "contains", "html_element", "html_text_contains", "css_declaration",
    "css_stylesheet_exact", "js_function",
}
DEFAULT_RESPONSE_LIMIT_BYTES = 65_536
DEFAULT_NODE_TIMEOUT_SECONDS = 5.0
MAX_TASK_SET_BYTES = 1_048_576
MAX_RESPONSE_FILE_BYTES = 33_554_432
VOID_HTML_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class _HtmlInspector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.text_parts: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self.errors.append(f"duplicate attribute on <{tag}>")
        self.elements.append((tag, dict(attrs)))
        if tag not in VOID_HTML_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self.errors.append(f"duplicate attribute on <{tag}>")
        self.elements.append((tag, dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_HTML_ELEMENTS:
            self.errors.append(f"void element </{tag}> must not have an end tag")
        elif not self.stack:
            self.errors.append(f"unexpected </{tag}>")
        elif self.stack[-1] != tag:
            self.errors.append(f"misnested </{tag}>; expected </{self.stack[-1]}>")
            if tag in self.stack:
                del self.stack[self.stack.index(tag):]
        else:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def close(self) -> None:
        super().close()
        if self.stack:
            self.errors.append(f"unclosed <{self.stack[-1]}>")


def _inspect_html(source: str) -> tuple[str, _HtmlInspector, str | None]:
    inspector = _HtmlInspector()
    try:
        inspector.feed(source)
        inspector.close()
    except (AssertionError, ValueError) as exc:
        return "fail", inspector, f"HTML parse error: {type(exc).__name__}"
    return ("fail", inspector, "; ".join(inspector.errors)) if inspector.errors else ("pass", inspector, None)


def _inspect_css(source: str) -> tuple[str, dict[str, dict[str, str]], str | None]:
    """Parse flat CSS rules used by this task set; nested at-rules are excluded."""
    without_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    if "/*" in without_comments or "*/" in without_comments:
        return "fail", {}, "unterminated CSS comment"
    if without_comments.count("{") != without_comments.count("}"):
        return "fail", {}, "unbalanced CSS braces"
    rules: dict[str, dict[str, str]] = {}
    consumed = [False] * len(without_comments)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", without_comments):
        selector = " ".join(match.group(1).split())
        if not selector or selector.startswith("@"):
            return "fail", {}, "only flat selector rules are supported"
        declarations: dict[str, str] = {}
        for declaration in match.group(2).split(";"):
            declaration = declaration.strip()
            if not declaration:
                continue
            if ":" not in declaration:
                return "fail", {}, f"invalid declaration in {selector}"
            name, value = declaration.split(":", 1)
            name = name.strip().lower()
            value = " ".join(value.strip().split())
            if not re.fullmatch(r"(?:--[\w-]+|[a-zA-Z][\w-]*)", name) or not value:
                return "fail", {}, f"invalid declaration in {selector}"
            if name in declarations:
                return "fail", {}, f"duplicate {name} declaration in {selector}"
            declarations[name] = value
        if selector in rules:
            rules[selector].update(declarations)
        else:
            rules[selector] = declarations
        for index in range(match.start(), match.end()):
            consumed[index] = True
    residue = "".join(char for index, char in enumerate(without_comments) if not consumed[index])
    if residue.strip():
        return "fail", {}, "CSS contains unsupported or malformed syntax"
    return "pass", rules, None


def _node_syntax_status(source: str, node_executable: str | None, timeout: float) -> tuple[str, str | None]:
    node = node_executable or shutil.which("node")
    if not node:
        return "unavailable", "Node.js is not installed or is not on PATH"
    with tempfile.TemporaryDirectory(prefix="plex-p2-eval-") as temporary:
        path = Path(temporary) / "candidate.js"
        path.write_text(source, encoding="utf-8", newline="\n")
        safe_env = {
            name: value for name, value in os.environ.items()
            if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC"}
        }
        try:
            completed = subprocess.run(
                [node, "--check", str(path)],
                cwd=temporary,
                env=safe_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "timeout", f"Node syntax check exceeded {timeout:g} seconds"
        except OSError as exc:
            return "unavailable", f"Node.js could not be started: {type(exc).__name__}"
    if completed.returncode:
        return "fail", f"Node --check rejected the output (exit {completed.returncode})"
    return "pass", None


def _node_version(node_executable: str | None) -> str | None:
    node = node_executable or shutil.which("node")
    if not node:
        return None
    safe_env = {
        name: value for name, value in os.environ.items()
        if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC"}
    }
    try:
        with tempfile.TemporaryDirectory(prefix="plex-node-version-") as temporary:
            completed = subprocess.run(
                [node, "--version"], cwd=temporary, env=safe_env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace",
                timeout=DEFAULT_NODE_TIMEOUT_SECONDS, check=False,
            )
    except (OSError, subprocess.TimeoutExpired):
        return None
    version = completed.stdout.strip()[:80]
    return version if completed.returncode == 0 and re.fullmatch(r"v[0-9]+(?:\.[0-9A-Za-z+-]+)*", version) else None


def _wilson_interval(successes: int, total: int) -> dict[str, float] | None:
    """Return a two-sided 95% Wilson score interval for descriptive reporting."""
    if total <= 0:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return {"low": round(max(0.0, center - margin), 6), "high": round(min(1.0, center + margin), 6)}


def _check_task(task: dict[str, Any], source: str, node_executable: str | None, timeout: float) -> dict[str, Any]:
    language = task["language"]
    checks: list[dict[str, Any]] = []
    parse_status: str
    parse_detail: str | None
    html_info: _HtmlInspector | None = None
    css_rules: dict[str, dict[str, str]] = {}
    if language == "html":
        parse_status, html_info, parse_detail = _inspect_html(source)
    elif language == "css":
        parse_status, css_rules, parse_detail = _inspect_css(source)
    else:
        parse_status, parse_detail = _node_syntax_status(source, node_executable, timeout)

    checks.append({"name": "languageSyntax", "passed": parse_status == "pass", "detail": parse_detail})
    fenced = source.lstrip().startswith("```") or "\n```" in source
    checks.append({"name": "noMarkdownFence", "passed": not fenced})
    for index, assertion in enumerate(task["checks"]):
        kind = assertion["kind"]
        passed = False
        if kind == "contains":
            passed = assertion["text"] in source
        elif kind == "html_element" and html_info is not None:
            tag = assertion["tag"].lower()
            expected_attrs = {name.lower(): value for name, value in assertion.get("attrs", {}).items()}
            matches = [attrs for found_tag, attrs in html_info.elements if found_tag == tag]
            matching_count = sum(
                all((name in attrs) if value is None else (attrs.get(name) == value)
                    for name, value in expected_attrs.items())
                for attrs in matches
            )
            passed = matching_count > 0
            if assertion.get("minimumCount") is not None:
                passed = matching_count >= assertion["minimumCount"]
        elif kind == "html_text_contains" and html_info is not None:
            passed = assertion["text"].casefold() in " ".join("".join(html_info.text_parts).split()).casefold()
        elif kind == "css_declaration":
            selector = " ".join(assertion["selector"].split())
            property_name = assertion["property"].lower()
            expected_value = " ".join(assertion["value"].split())
            passed = css_rules.get(selector, {}).get(property_name) == expected_value
        elif kind == "css_stylesheet_exact":
            expected_rules = {
                " ".join(selector.split()): {
                    name.lower(): " ".join(value.split())
                    for name, value in declarations.items()
                }
                for selector, declarations in assertion["rules"].items()
            }
            passed = css_rules == expected_rules
        elif kind == "js_function" and language == "javascript":
            name = re.escape(assertion["name"])
            passed = bool(re.search(
                rf"(?:\bfunction\s+{name}\s*\(|\b(?:const|let|var)\s+{name}\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>))",
                source,
            ))
        checks.append({"name": f"assertion-{index + 1}-{kind}", "passed": passed})

    available = parse_status != "unavailable"
    passed = available and parse_status == "pass" and all(check["passed"] for check in checks[1:])
    return {
        "taskId": task["id"],
        "language": language,
        "difficulty": task["difficulty"],
        "parseStatus": parse_status,
        "parseDetail": parse_detail,
        "available": available,
        "passed": passed,
        "checksPassed": sum(check["passed"] for check in checks),
        "checksTotal": len(checks),
        "checks": checks,
    }


def validate_task_set(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != 1:
        raise ValueError("Task set must be a schemaVersion 1 JSON object")
    if value.get("kind") not in {"development", "final"} or not isinstance(value.get("setId"), str) or not value["setId"]:
        raise ValueError("Task set must declare setId and kind development or final")
    contracts = value.get("outputContracts")
    if not isinstance(contracts, dict) or any(
        not isinstance(contracts.get(language), str) or not contracts[language].strip()
        for language in LANGUAGES
    ):
        raise ValueError("Task set must provide an output contract for HTML, CSS, and JavaScript")
    defaults = value.get("inferenceDefaults")
    limits = defaults.get("maxNewTokens") if isinstance(defaults, dict) else None
    if (not isinstance(defaults, dict) or defaults.get("promptTemplateVersion") != "plex-coding-task-v1"
            or defaults.get("temperature") != 0.0 or type(defaults.get("seed")) is not int
            or not 0 <= defaults["seed"] <= 2**63 - 1
            or not isinstance(limits, dict)
            or any(type(limits.get(language)) is not int or not 1 <= limits[language] <= 256
                   for language in LANGUAGES)):
        raise ValueError("Task set has invalid deterministic inference defaults")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or not tasks or len(tasks) > 60:
        raise ValueError("Task set must contain between 1 and 60 tasks")
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Each task must be an object")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("Task IDs must be unique nonempty strings")
        seen.add(task_id)
        if task.get("language") not in LANGUAGES or task.get("difficulty") not in {"basic", "edge"}:
            raise ValueError(f"Task {task_id} has an unsupported language or difficulty")
        if not isinstance(task.get("request"), str) or not task["request"].strip():
            raise ValueError(f"Task {task_id} is missing its request")
        if not isinstance(task.get("contract", contracts[task["language"]]), str) or not task.get(
            "contract", contracts[task["language"]]
        ).strip():
            raise ValueError(f"Task {task_id} is missing its output contract")
        provenance = task.get("provenance", value.get("provenance"))
        allowed_provenance = {"owner-authored"} if value["kind"] == "final" else {
            "owner-authored", "codex-authored",
        }
        if provenance not in allowed_provenance:
            raise ValueError(f"Task {task_id} has provenance that is not permitted for this task-set kind")
        assertions = task.get("checks")
        if not isinstance(assertions, list) or not assertions:
            raise ValueError(f"Task {task_id} must have at least one check")
        for assertion in assertions:
            if not isinstance(assertion, dict) or assertion.get("kind") not in ALLOWED_CHECKS:
                raise ValueError(f"Task {task_id} has an unsupported assertion")
            kind = assertion["kind"]
            if ((kind.startswith("html_") and task["language"] != "html")
                    or (kind in {"css_declaration", "css_stylesheet_exact"} and task["language"] != "css")
                    or (kind == "js_function" and task["language"] != "javascript")):
                raise ValueError(f"Task {task_id} uses a check for another language")
            if kind == "contains" and not isinstance(assertion.get("text"), str):
                raise ValueError(f"Task {task_id} contains check needs text")
            if kind == "html_element":
                if not isinstance(assertion.get("tag"), str):
                    raise ValueError(f"Task {task_id} element check needs tag")
                attrs = assertion.get("attrs", {})
                if not isinstance(attrs, dict) or any(
                    not isinstance(name, str) or (value is not None and not isinstance(value, str))
                    for name, value in attrs.items()
                ):
                    raise ValueError(f"Task {task_id} element attributes are invalid")
                if ("minimumCount" in assertion and
                        (type(assertion["minimumCount"]) is not int or assertion["minimumCount"] < 1)):
                    raise ValueError(f"Task {task_id} element minimumCount must be a positive integer")
            if kind == "html_text_contains" and not isinstance(assertion.get("text"), str):
                raise ValueError(f"Task {task_id} text check needs text")
            if kind == "css_declaration" and not all(
                isinstance(assertion.get(key), str) for key in ("selector", "property", "value")
            ):
                raise ValueError(f"Task {task_id} CSS check needs selector, property, and value")
            if kind == "css_stylesheet_exact":
                rules = assertion.get("rules")
                if (not isinstance(rules, dict) or not rules
                        or any(not isinstance(selector, str) or not selector.strip()
                               or not isinstance(declarations, dict) or not declarations
                               or any(not isinstance(name, str) or not name.strip()
                                      or not isinstance(css_value, str) or not css_value.strip()
                                      for name, css_value in declarations.items())
                               for selector, declarations in rules.items())):
                    raise ValueError(f"Task {task_id} exact CSS check needs selector/declaration maps")
                selectors = [" ".join(selector.split()) for selector in rules]
                if len(selectors) != len(set(selectors)):
                    raise ValueError(f"Task {task_id} exact CSS check has duplicate normalized selectors")
            if kind == "js_function" and not isinstance(assertion.get("name"), str):
                raise ValueError(f"Task {task_id} function check needs a name")
    return value


def render_task_prompt(task_set: dict[str, Any], task: dict[str, Any]) -> str:
    """Render the shared, versioned prompt consumed by deterministic dev runs."""
    task_set = validate_task_set(task_set)
    if task not in task_set["tasks"]:
        raise ValueError("Task does not belong to this task set")
    defaults = task_set.get("inferenceDefaults")
    if not isinstance(defaults, dict) or defaults.get("promptTemplateVersion") != "plex-coding-task-v1":
        raise ValueError("Unsupported or missing task prompt template version")
    language_name = {"html": "HTML", "css": "CSS", "javascript": "JavaScript"}[task["language"]]
    contract = task.get("contract", task_set["outputContracts"][task["language"]])
    prompt = (
        f"Write a small {language_name} coding solution.\n"
        f"Request: {task['request']}\n"
        f"Output contract: {contract}\n"
        "Return code only. Do not include Markdown fences or explanations."
    )
    if not prompt or len(prompt.encode("utf-8")) > 4096:
        raise ValueError("Rendered task prompt must be nonempty and no more than 4096 UTF-8 bytes")
    return prompt


def evaluate_task_set(
    task_set: dict[str, Any],
    responses: Iterable[dict[str, Any]],
    *,
    task_set_sha256: str | None = None,
    responses_sha256: str | None = None,
    node_executable: str | None = None,
    node_timeout_seconds: float = DEFAULT_NODE_TIMEOUT_SECONDS,
    response_limit_bytes: int = DEFAULT_RESPONSE_LIMIT_BYTES,
) -> dict[str, Any]:
    task_set = validate_task_set(task_set)
    if (not 0 < node_timeout_seconds <= DEFAULT_NODE_TIMEOUT_SECONDS
            or not 0 < response_limit_bytes <= DEFAULT_RESPONSE_LIMIT_BYTES):
        raise ValueError("Timeout and response-size limits may be lowered but not exceed the safe defaults")
    by_id = {task["id"]: task for task in task_set["tasks"]}
    outputs: dict[str, str] = {}
    truncated_ids: set[str] = set()
    for response in responses:
        if not isinstance(response, dict) or not isinstance(response.get("taskId"), str):
            raise ValueError("Each response must contain a string taskId")
        task_id = response["taskId"]
        if task_id not in by_id:
            raise ValueError(f"Response references unknown task ID: {task_id}")
        if task_id in outputs:
            raise ValueError(f"Duplicate response for task ID: {task_id}")
        if not isinstance(response.get("text"), str):
            raise ValueError(f"Response for {task_id} must contain string text")
        if "truncated" in response and not isinstance(response["truncated"], bool):
            raise ValueError(f"Response truncated flag for {task_id} must be boolean")
        outputs[task_id] = response["text"]
        if response.get("truncated", False):
            truncated_ids.add(task_id)

    javascript_version = _node_version(node_executable) if any(
        task["language"] == "javascript" for task in task_set["tasks"]
    ) else None
    results: list[dict[str, Any]] = []
    for task in task_set["tasks"]:
        source = outputs.get(task["id"], "")
        size = len(source.encode("utf-8"))
        if size > response_limit_bytes:
            results.append({
                "taskId": task["id"], "language": task["language"], "difficulty": task["difficulty"],
                "parseStatus": "fail", "parseDetail": "response exceeds the configured byte limit",
                "available": True, "passed": False, "empty": task["id"] in outputs and not source.strip(),
                "missing": task["id"] not in outputs, "truncated": task["id"] in truncated_ids,
                "overLimit": True,
                "outputBytes": size, "checksPassed": 0, "checksTotal": 1,
                "checks": [{"name": "responseSize", "passed": False}],
            })
            continue
        result = _check_task(task, source, node_executable, node_timeout_seconds)
        result.update({
            "empty": task["id"] in outputs and not source.strip(),
            "missing": task["id"] not in outputs,
            "truncated": task["id"] in truncated_ids,
            "overLimit": False,
            "outputBytes": size,
        })
        if task["id"] in truncated_ids:
            result["checks"].append({"name": "notTruncated", "passed": False})
            result["passed"] = False
            result["checksPassed"] = sum(check["passed"] for check in result["checks"])
            result["checksTotal"] = len(result["checks"])
        if task["id"] not in outputs:
            result["checks"].append({"name": "responsePresent", "passed": False})
            result["checksPassed"] = sum(check["passed"] for check in result["checks"])
            result["checksTotal"] = len(result["checks"])
            result["passed"] = False
        elif not source.strip():
            result["checks"].append({"name": "nonEmpty", "passed": False})
            result["checksPassed"] = sum(check["passed"] for check in result["checks"])
            result["checksTotal"] = len(result["checks"])
            result["passed"] = False
        results.append(result)

    per_language: dict[str, dict[str, Any]] = {}
    for language in LANGUAGES:
        entries = [item for item in results if item["language"] == language]
        passed = sum(item["passed"] for item in entries)
        available = sum(item["available"] for item in entries)
        per_language[language] = {
            "tasks": len(entries), "passed": passed, "passRate": passed / len(entries) if entries else None,
            "evaluable": available, "unavailable": len(entries) - available,
            "passRateWilson95": _wilson_interval(passed, len(entries)),
        }
    all_checks = [check for item in results for check in item["checks"]]
    total = len(results)
    passed_count = sum(item["passed"] for item in results)
    return {
        "schemaVersion": 1,
        "evaluator": "plex-static-task-evaluator-v1",
        "taskSetId": task_set["setId"],
        "taskSetKind": task_set["kind"],
        "taskSetSha256": task_set_sha256,
        "responsesSha256": responses_sha256,
        "scoreMeaning": "Static contract and syntax checks only; JavaScript behavior is not executed.",
        "javascriptParser": {"engine": "Node.js --check", "version": javascript_version},
        "tasks": total,
        "passed": passed_count,
        "passRate": passed_count / total if total else 0.0,
        "passRateWilson95": _wilson_interval(passed_count, total),
        "evaluable": sum(item["available"] for item in results),
        "unavailable": sum(not item["available"] for item in results),
        "perLanguage": per_language,
        "assertionsPassed": sum(check["passed"] for check in all_checks),
        "assertionsTotal": len(all_checks),
        "partialAssertionCount": sum(0 < item["checksPassed"] < item["checksTotal"] for item in results),
        "timeouts": sum(item["parseStatus"] == "timeout" for item in results),
        "emptyOutputs": sum(item.get("empty", False) for item in results),
        "missingOutputs": sum(item.get("missing", False) for item in results),
        "truncatedOutputs": sum(item.get("truncated", False) for item in results),
        "overLimitOutputs": sum(item.get("overLimit", False) for item in results),
        "meanOutputBytes": sum(item.get("outputBytes", 0) for item in results) / total if total else 0.0,
        "results": results,
    }


def evaluate_files(
    task_set_path: Path,
    responses_path: Path,
    *,
    node_timeout_seconds: float = DEFAULT_NODE_TIMEOUT_SECONDS,
    response_limit_bytes: int = DEFAULT_RESPONSE_LIMIT_BYTES,
) -> dict[str, Any]:
    if task_set_path.stat().st_size > MAX_TASK_SET_BYTES:
        raise ValueError("Task set file exceeds the 1 MiB limit")
    task_bytes = task_set_path.read_bytes()
    task_set = validate_task_set(json.loads(task_bytes.decode("utf-8")))
    if responses_path.stat().st_size > MAX_RESPONSE_FILE_BYTES:
        raise ValueError("Response file exceeds the 32 MiB limit")
    response_bytes = responses_path.read_bytes()
    responses: list[dict[str, Any]] = []
    for line_number, line in enumerate(response_bytes.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid response JSON on line {line_number}") from exc
    return evaluate_task_set(
        task_set,
        responses,
        task_set_sha256=hashlib.sha256(task_bytes).hexdigest(),
        responses_sha256=hashlib.sha256(response_bytes).hexdigest(),
        node_timeout_seconds=node_timeout_seconds,
        response_limit_bytes=response_limit_bytes,
    )
