"""Tests for the local static Phase 2 task evaluator."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from plex_training.benchmark import (
    _node_syntax_status,
    _node_version,
    _wilson_interval,
    evaluate_files,
    evaluate_task_set,
    render_task_prompt,
    validate_task_set,
)
from plex_training.cli import main


def _task_set() -> dict:
    return {
        "schemaVersion": 1,
        "setId": "unit-test-v1",
        "kind": "development",
        "provenance": "owner-authored",
        "outputContracts": {"html": "HTML only", "css": "CSS only", "javascript": "JavaScript only"},
        "inferenceDefaults": {
            "temperature": 0.0, "seed": 1337,
            "maxNewTokens": {"html": 192, "css": 128, "javascript": 192},
            "promptTemplateVersion": "plex-coding-task-v1",
        },
        "tasks": [
            {"id": "h1", "language": "html", "difficulty": "basic", "request": "Add a heading.",
             "checks": [{"kind": "html_element", "tag": "h1"},
                        {"kind": "html_text_contains", "text": "Hello"}]},
            {"id": "c1", "language": "css", "difficulty": "basic", "request": "Style the card.",
             "checks": [{"kind": "css_declaration", "selector": ".card", "property": "display", "value": "flex"}]},
            {"id": "j1", "language": "javascript", "difficulty": "basic", "request": "Write add.",
             "checks": [{"kind": "js_function", "name": "add"},
                        {"kind": "contains", "text": "return a + b"}]},
        ],
    }


def _node_ok(*args, **kwargs):
    return subprocess.CompletedProcess(args[0], 0, "", "")


class BenchmarkTests(unittest.TestCase):
    def test_known_good_outputs_pass_static_contracts(self) -> None:
        with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok):
            result = evaluate_task_set(_task_set(), [
                {"taskId": "h1", "text": "<h1>Hello</h1>"},
                {"taskId": "c1", "text": ".card { display: flex; }"},
                {"taskId": "j1", "text": "function add(a, b) { return a + b; }"},
            ], node_executable="node-test")
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["perLanguage"]["javascript"]["passRate"], 1.0)
        self.assertEqual(result["passRateWilson95"]["high"], 1.0)
        self.assertLess(result["passRateWilson95"]["low"], 1.0)

    def test_deliberately_broken_behavior_assertion_fails_task(self) -> None:
        with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok):
            result = evaluate_task_set(_task_set(), [
                {"taskId": "h1", "text": "<h1>Hello</h1>"},
                {"taskId": "c1", "text": ".card { display: block; }"},
                {"taskId": "j1", "text": "function add(a, b) { return a - b; }"},
            ], node_executable="node-test")
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["partialAssertionCount"], 2)

    def test_malformed_html_css_and_javascript_fail_parse(self) -> None:
        with patch("plex_training.benchmark.subprocess.run", return_value=subprocess.CompletedProcess(
            ["node"], 1, "", "SyntaxError"
        )):
            result = evaluate_task_set(_task_set(), [
                {"taskId": "h1", "text": "<div><h1>Hello</div>"},
                {"taskId": "c1", "text": ".card { display: flex;"},
                {"taskId": "j1", "text": "function add( {"},
            ], node_executable="node-test")
        self.assertEqual([item["parseStatus"] for item in result["results"]], ["fail", "fail", "fail"])
        self.assertEqual(result["passed"], 0)

    def test_empty_and_missing_outputs_are_reported(self) -> None:
        with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok):
            result = evaluate_task_set(_task_set(), [
                {"taskId": "h1", "text": "  "},
                {"taskId": "c1", "text": ".card { display: flex; }"},
            ], node_executable="node-test")
        self.assertEqual(result["emptyOutputs"], 1)
        self.assertEqual(result["missingOutputs"], 1)
        html_result = result["results"][0]
        js_result = result["results"][2]
        self.assertFalse(html_result["passed"])
        self.assertIn("responsePresent", {check["name"] for check in js_result["checks"]})

    def test_node_timeout_is_a_failure_and_is_counted(self) -> None:
        timeout = subprocess.TimeoutExpired(["node", "--check"], 0.01)
        with patch("plex_training.benchmark.subprocess.run", side_effect=timeout):
            result = evaluate_task_set(
                _task_set(), [{"taskId": "j1", "text": "function add(a, b) { return a + b; }"}],
                node_executable="node-test", node_timeout_seconds=0.01,
            )
        self.assertEqual(result["timeouts"], 1)
        self.assertFalse(result["results"][2]["passed"])

    def test_missing_node_is_labeled_unavailable(self) -> None:
        with patch("plex_training.benchmark.shutil.which", return_value=None):
            result = evaluate_task_set(
                _task_set(), [{"taskId": "j1", "text": "function add(a, b) { return a + b; }"}]
            )
        self.assertEqual(result["unavailable"], 1)
        self.assertEqual(result["perLanguage"]["javascript"]["evaluable"], 0)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_installed_node_checks_syntax_without_running_the_source(self) -> None:
        version = _node_version(None)
        valid = _node_syntax_status("function add(a, b) { return a + b; }", None, 5.0)
        invalid = _node_syntax_status("function add( {", None, 5.0)
        self.assertRegex(version or "", r"^v\d+(?:\.[0-9A-Za-z+-]+)*$")
        self.assertEqual(valid[0], "pass")
        self.assertEqual(invalid[0], "fail")
        self.assertNotIn("function add", invalid[1] or "")

    def test_output_over_limit_is_rejected_before_parsing(self) -> None:
        result = evaluate_task_set(
            _task_set(), [{"taskId": "h1", "text": "x" * 100}], response_limit_bytes=32
        )
        html_result = result["results"][0]
        self.assertFalse(html_result["truncated"])
        self.assertTrue(html_result["overLimit"])
        self.assertEqual(html_result["parseStatus"], "fail")
        self.assertEqual(result["truncatedOutputs"], 0)
        self.assertEqual(result["overLimitOutputs"], 1)

    def test_limits_cannot_be_raised_above_the_bounded_defaults(self) -> None:
        with self.assertRaisesRegex(ValueError, "may be lowered"):
            evaluate_task_set(_task_set(), [], node_timeout_seconds=5.01)
        with self.assertRaisesRegex(ValueError, "may be lowered"):
            evaluate_task_set(_task_set(), [], response_limit_bytes=65_537)

    def test_wilson_interval_covers_small_sample_boundaries(self) -> None:
        self.assertEqual(_wilson_interval(0, 0), None)
        all_failed = _wilson_interval(0, 10)
        all_passed = _wilson_interval(10, 10)
        self.assertIsNotNone(all_failed)
        self.assertIsNotNone(all_passed)
        self.assertEqual(all_failed["low"], 0.0)
        self.assertGreater(all_failed["high"], 0.0)
        self.assertLess(all_passed["low"], 1.0)
        self.assertEqual(all_passed["high"], 1.0)

    def test_explicit_generation_truncation_is_reported_and_fails(self) -> None:
        result = evaluate_task_set(
            _task_set(), [{"taskId": "h1", "text": "<h1>Hello</h1>", "truncated": True}]
        )
        html_result = result["results"][0]
        self.assertTrue(html_result["truncated"])
        self.assertFalse(html_result["passed"])
        self.assertEqual(result["truncatedOutputs"], 1)

    def test_duplicate_or_unknown_response_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate response"):
            evaluate_task_set(_task_set(), [
                {"taskId": "h1", "text": "<h1>Hello</h1>"},
                {"taskId": "h1", "text": "<h1>Hello</h1>"},
            ])
        with self.assertRaisesRegex(ValueError, "unknown task"):
            evaluate_task_set(_task_set(), [{"taskId": "other", "text": ""}])

    def test_shipped_development_set_has_ten_tasks_per_language(self) -> None:
        path = Path(__file__).parents[1] / "phase2" / "evaluation" / "p2-01b-dev-v1.json"
        value = validate_task_set(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(value["setId"], "p2-01b-dev-v1")
        self.assertEqual(Counter(task["language"] for task in value["tasks"]), {
            "html": 10, "css": 10, "javascript": 10,
        })
        prompt = render_task_prompt(value, value["tasks"][0])
        self.assertIn("small HTML", prompt)
        self.assertIn("Output contract:", prompt)
        self.assertTrue(prompt.endswith("Do not include Markdown fences or explanations."))

    def test_every_development_task_accepts_a_known_good_example(self) -> None:
        path = Path(__file__).parents[1] / "phase2" / "evaluation" / "p2-01b-dev-v1.json"
        task_set = validate_task_set(json.loads(path.read_text(encoding="utf-8")))
        examples = {
            "p2dev-html-01-primary-navigation": '<nav aria-label="Primary"><a href="/">Home</a><a href="/projects">Projects</a></nav>',
            "p2dev-html-02-email-form": '<form><label for="email">Email</label><input id="email" type="email" required><button type="submit">Join</button></form>',
            "p2dev-html-03-article-date": '<article><h2>Notes for the article</h2><time datetime="2026-10-04">October 4</time><p>Text.</p></article>',
            "p2dev-html-04-live-status": '<p id="save-status" role="status">Saved.</p><button aria-describedby="save-status">Save</button>',
            "p2dev-html-05-three-steps": '<ol><li>Open</li><li>Edit</li><li>Save</li></ol>',
            "p2dev-html-06-figure-caption": '<figure><img src="/images/garden.jpg" alt="A garden in spring"><figcaption>Garden</figcaption></figure>',
            "p2dev-html-07-details-summary": '<details><summary>Shipping</summary><p>Delivery details.</p></details>',
            "p2dev-html-08-data-table": '<table><caption>Scores</caption><thead><tr><th scope="col">Name</th><th scope="col">Score</th></tr></thead><tbody><tr><td>Ada</td><td>9</td></tr></tbody></table>',
            "p2dev-html-09-checkbox-fieldset": '<fieldset><legend>Notifications</legend><input id="weekly" type="checkbox"><label for="weekly">Weekly</label></fieldset>',
            "p2dev-html-10-breadcrumbs": '<nav aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><span aria-current="page">Settings</span></li></ol></nav>',
            "p2dev-css-01-card-flex": '.card { display: flex; gap: 1rem; padding: 1rem; }',
            "p2dev-css-02-auto-grid": '.gallery { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: 1rem; }',
            "p2dev-css-03-keyboard-focus": 'button:focus-visible { outline: 3px solid currentColor; outline-offset: 3px; }',
            "p2dev-css-04-fluid-heading": 'h1 { font-size: clamp(1.5rem, 4vw, 2.5rem); }',
            "p2dev-css-05-responsive-image": 'img { max-width: 100%; height: auto; }',
            "p2dev-css-06-button-hover": 'button:hover { background-color: #234; }',
            "p2dev-css-07-visually-hidden": '.visually-hidden { position: absolute; width: 1px; overflow: hidden; }',
            "p2dev-css-08-sticky-header": '.site-header { position: sticky; top: 0; background-color: white; }',
            "p2dev-css-09-expanded-panel": 'button[aria-expanded="true"] + .panel { display: none; }',
            "p2dev-css-10-wrapping-row": '.toolbar { display: flex; flex-wrap: wrap; gap: 0.5rem; }',
            "p2dev-js-01-clamp": 'function clamp(value, minimum, maximum) { return Math.min(maximum, Math.max(minimum, value)); }',
            "p2dev-js-02-count-words": 'function countWords(text) { const trimmed = text.trim(); return trimmed ? trimmed.split(/\\s+/).length : 0; }',
            "p2dev-js-03-unique-by-id": 'function uniqueById(items) { const seen = new Set(); return items.filter(item => !seen.has(item.id) && seen.add(item.id)); }',
            "p2dev-js-04-group-by": 'function groupBy(items, key) { const groups = Object.create(null); for (const item of items) { (groups[item[key]] ??= []).push(item); } return groups; }',
            "p2dev-js-05-format-usd": 'function formatPrice(value) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value); }',
            "p2dev-js-06-email-shape": 'function isValidEmail(value) { return typeof value === "string" && /^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(value); }',
            "p2dev-js-07-initials": 'function getInitials(name) { return typeof name === "string" ? name.trim().split(/\\s+/).map(part => part[0]?.toUpperCase()).filter(Boolean).slice(0, 2).join("") : ""; }',
            "p2dev-js-08-toggle-item": 'function toggleItem(items, targetId) { return items.includes(targetId) ? items.filter(item => item !== targetId) : [...items, targetId]; }',
            "p2dev-js-09-sum-by": 'function sumBy(items, key) { return items.reduce((total, item) => total + (Number.isFinite(item[key]) ? item[key] : 0), 0); }',
            "p2dev-js-10-sort-by-name": 'function sortByName(items) { return items.slice().sort((a, b) => a.name.localeCompare(b.name)); }',
        }
        self.assertEqual(set(examples), {task["id"] for task in task_set["tasks"]})
        with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok):
            report = evaluate_task_set(
                task_set,
                [{"taskId": task_id, "text": text} for task_id, text in examples.items()],
                node_executable="node-test",
            )
        failures = [item["taskId"] for item in report["results"] if not item["passed"]]
        self.assertEqual(failures, [])

    def test_file_evaluation_reports_input_hashes_and_refuses_bad_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / "tasks.json"
            responses = root / "responses.jsonl"
            tasks.write_text(json.dumps(_task_set()), encoding="utf-8")
            responses.write_text(json.dumps({"taskId": "h1", "text": "<h1>Hello</h1>"}) + "\n",
                                 encoding="utf-8")
            with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok):
                report = evaluate_files(tasks, responses)
            self.assertEqual(len(report["taskSetSha256"]), 64)
            self.assertEqual(len(report["responsesSha256"]), 64)
            responses.write_text("{broken\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                evaluate_files(tasks, responses)

    def test_cli_writes_a_hashed_report_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / "tasks.json"
            responses = root / "responses.jsonl"
            report = root / "report.json"
            tasks.write_text(json.dumps(_task_set()), encoding="utf-8")
            responses.write_text(json.dumps({"taskId": "h1", "text": "<h1>Hello</h1>"}) + "\n",
                                 encoding="utf-8")
            output = StringIO()
            with patch("plex_training.benchmark.subprocess.run", side_effect=_node_ok), redirect_stdout(output):
                status = main(["task-evaluate", "--task-set", str(tasks),
                               "--responses", str(responses), "--report", str(report)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["tasks"], 3)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["taskSetId"], "unit-test-v1")
            with redirect_stdout(StringIO()):
                status = main(["task-evaluate", "--task-set", str(tasks),
                               "--responses", str(responses), "--report", str(report)])
            self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
