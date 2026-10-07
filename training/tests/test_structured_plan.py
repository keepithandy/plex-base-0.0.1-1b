"""Portable regression tests for the P2-31 structured coding bridge."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from plex_training.cli import main
from plex_training.structured_plan import (
    evaluate_plan_files,
    evaluate_plan_set,
    parse_plan_response,
    render_plan_prompt,
    validate_plan,
    validate_plan_task_set,
)
from plex_training.structured_plan_run import _contract, generate_structured_plans


def _task_set(kind: str = "development") -> dict:
    tasks = [
        {
            "id": "h1", "language": "html", "difficulty": "basic",
            "request": "Make the primary navigation explicitly labeled Main.",
            "expectedPlan": {
                "action": "modify", "targetKind": "html-element",
                "targetRole": "primary-navigation",
                "constraints": [
                    {"kind": "attribute", "key": "aria-label", "value": "Main"}
                ],
                "hintKeywords": ["navigation", "main"],
            },
        },
        {
            "id": "c1", "language": "css", "difficulty": "basic",
            "request": "Make the card use flex layout.",
            "expectedPlan": {
                "action": "modify", "targetKind": "css-rule",
                "targetRole": "card-layout",
                "constraints": [
                    {"kind": "declaration", "key": "display", "value": "flex"}
                ],
                "hintKeywords": ["card", "layout"],
            },
        },
        {
            "id": "j1", "language": "javascript", "difficulty": "basic",
            "request": "Add a helper that preserves the input array.",
            "expectedPlan": {
                "action": "create", "targetKind": "js-function",
                "targetRole": "copy-items",
                "constraints": [
                    {"kind": "nonmutation", "key": "input-array", "value": "preserve"}
                ],
                "hintKeywords": ["copy", "items"],
            },
        },
    ]
    return {
        "schemaVersion": 1,
        "setId": "unit-p2-31-v1",
        "kind": kind,
        "provenance": "unit-test",
        "purpose": "portable structured-plan tests",
        "planSchemaVersion": "plex-structured-edit-plan-v1",
        "inferenceDefaults": {
            "temperature": 0.0,
            "seed": 1337,
            "maxNewTokens": 256,
            "promptTemplateVersion": "plex-structured-plan-v1",
        },
        "gate": {"minimumPassed": 2, "minimumPerLanguage": 1, "minimumSchemaValid": 2},
        "tasks": tasks,
    }


def _good_responses() -> list[dict]:
    return [
        {"taskId": "h1", "text": json.dumps({
            "schemaVersion": 1, "language": "html", "action": "modify",
            "targetKind": "html-element", "targetRole": "primary-navigation",
            "constraints": [{"kind": "attribute", "key": "aria-label", "value": "Main"}],
            "searchHints": ["primary navigation", "Main label"],
        })},
        {"taskId": "c1", "text": json.dumps({
            "schemaVersion": 1, "language": "css", "action": "modify",
            "targetKind": "css-rule", "targetRole": "card-layout",
            "constraints": [{"kind": "declaration", "key": "display", "value": "flex"}],
            "searchHints": ["card component", "layout"],
        })},
        {"taskId": "j1", "text": json.dumps({
            "schemaVersion": 1, "language": "javascript", "action": "create",
            "targetKind": "js-function", "targetRole": "copy-items",
            "constraints": [{"kind": "nonmutation", "key": "input-array", "value": "preserve"}],
            "searchHints": ["copy helper", "items"],
        })},
    ]


class StructuredPlanSchemaTests(unittest.TestCase):
    def test_known_good_plans_pass_gate(self) -> None:
        report = evaluate_plan_set(_task_set(), _good_responses())
        self.assertEqual(report["passed"], 3)
        self.assertEqual(report["schemaValid"], 3)
        self.assertTrue(report["gatePassed"])
        self.assertEqual(report["perLanguage"]["html"]["passed"], 1)
        self.assertFalse(report["finalHoldoutOpened"])

    def test_schema_is_strict_and_language_target_kind_is_bound(self) -> None:
        good = json.loads(_good_responses()[0]["text"])
        self.assertEqual(validate_plan(good)["targetRole"], "primary-navigation")

        extra = {**good, "filePath": "index.html"}
        with self.assertRaisesRegex(ValueError, "fields"):
            validate_plan(extra)

        wrong_kind = {**good, "targetKind": "css-rule"}
        with self.assertRaisesRegex(ValueError, "targetKind"):
            validate_plan(wrong_kind)

        path_hint = {**good, "searchHints": ["src/index.html"]}
        with self.assertRaisesRegex(ValueError, "file paths"):
            validate_plan(path_hint)

    def test_duplicate_keys_mark_response_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            parse_plan_response(
                '{"schemaVersion":1,"schemaVersion":1,"language":"html","action":"modify",'
                '"targetKind":"html-element","targetRole":"primary-navigation",'
                '"constraints":[{"kind":"attribute","key":"aria-label","value":"Main"}],'
                '"searchHints":["navigation","main"]}'
            )

    def test_markdown_or_malformed_json_is_not_schema_valid(self) -> None:
        responses = _good_responses()
        responses[0] = {"taskId": "h1", "text": "```json\n{}\n```"}
        responses[1] = {"taskId": "c1", "text": "{broken"}
        report = evaluate_plan_set(_task_set(), responses)
        self.assertEqual(report["schemaValid"], 1)
        self.assertFalse(report["gatePassed"])
        self.assertEqual(report["passed"], 1)

    def test_semantic_scoring_requires_exact_constraints_and_hint_coverage(self) -> None:
        responses = _good_responses()
        plan = json.loads(responses[0]["text"])
        plan["constraints"][0]["value"] = "Secondary"
        responses[0]["text"] = json.dumps(plan)
        plan = json.loads(responses[1]["text"])
        plan["searchHints"] = ["card"]
        responses[1]["text"] = json.dumps(plan)
        report = evaluate_plan_set(_task_set(), responses)
        html = report["results"][0]
        css = report["results"][1]
        self.assertFalse(next(c for c in html["checks"] if c["name"] == "constraintsExact")["passed"])
        self.assertFalse(next(c for c in css["checks"] if c["name"] == "hintCoverage")["passed"])
        self.assertEqual(report["passed"], 1)

    def test_truncation_never_passes_even_if_json_is_valid(self) -> None:
        responses = _good_responses()
        responses[0]["truncated"] = True
        report = evaluate_plan_set(_task_set(), responses)
        self.assertFalse(report["results"][0]["passed"])
        self.assertFalse(next(c for c in report["results"][0]["checks"]
                              if c["name"] == "notTruncated")["passed"])

    def test_prompt_assigns_resolution_to_plex_code(self) -> None:
        task_set = validate_plan_task_set(_task_set())
        prompt = render_plan_prompt(task_set, task_set["tasks"][0])
        self.assertIn("Do not write code", prompt)
        self.assertIn("Do not choose a file path, exact selector, or exact repository symbol", prompt)
        self.assertIn("deterministic Plex Code lookup", prompt)
        self.assertTrue(prompt.endswith("JSON:"))


class StructuredPlanFilesAndContractTests(unittest.TestCase):
    def test_shipped_set_is_balanced_hash_pinned_and_gate_is_predeclared(self) -> None:
        path = Path(__file__).parents[1] / "phase2" / "evaluation" / "p2-31-plan-dev-v1.json"
        raw = path.read_bytes()
        value = validate_plan_task_set(json.loads(raw.decode("utf-8")))
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5")
        self.assertEqual(len(value["tasks"]), 18)
        self.assertEqual(Counter(task["language"] for task in value["tasks"]),
                         {"html": 6, "css": 6, "javascript": 6})
        self.assertEqual(value["gate"],
                         {"minimumPassed": 12, "minimumPerLanguage": 3, "minimumSchemaValid": 15})

    def test_committed_contract_is_evaluation_only_and_pins_step100(self) -> None:
        path = Path("training/pretraining/p2-31-structured-bridge-contract.json")
        value = _contract(path)
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(value["checkpoint"]["step"], 100)
        self.assertEqual(
            value["checkpoint"]["sha256"],
            "28064a22f322d6b9cde04c2424f3c257de8c0803245c1db83072ab29c67f6d6e",
        )
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])

    def test_final_kind_generation_is_blocked_before_checkpoint_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_path = root / "final.json"
            task = _task_set("final")
            task_path.write_text(json.dumps(task), encoding="utf-8")
            task_sha = hashlib.sha256(task_path.read_bytes()).hexdigest()
            contract_path = root / "contract.json"
            contract = {
                "schemaVersion": 1,
                "milestone": "P2-31",
                "kind": "plex-p2-31-structured-bridge-contract-v1",
                "status": "evaluation-authorized",
                "modelTrainingAuthorized": False,
                "protectedEvaluation": {
                    "finalProjectHoldoutMustRemainClosed": True,
                    "noGradientUpdates": True,
                },
                "developmentEvaluation": {
                    "taskSetSha256": task_sha,
                    "setId": task["setId"],
                    "tasks": 3,
                    "planSchemaVersion": "plex-structured-edit-plan-v1",
                    "promptTemplateVersion": "plex-structured-plan-v1",
                    "temperature": 0.0,
                    "seed": 1337,
                    "maxNewTokens": 256,
                },
            }
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "development-only"):
                generate_structured_plans(
                    task_set_path=task_path,
                    checkpoint_path=root / "missing.pt",
                    bundle_dir=root / "missing-bundle",
                    output_dir=root / "output",
                    artifact_root=root,
                    contract_path=contract_path,
                )

    def test_file_evaluator_hashes_inputs_and_cli_refuses_report_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_path = root / "tasks.json"
            response_path = root / "responses.jsonl"
            report_path = root / "report.json"
            task_path.write_text(json.dumps(_task_set()), encoding="utf-8")
            response_path.write_text(
                "".join(json.dumps(row) + "\n" for row in _good_responses()),
                encoding="utf-8",
            )
            report = evaluate_plan_files(task_path, response_path)
            self.assertEqual(len(report["taskSetSha256"]), 64)
            self.assertEqual(len(report["responsesSha256"]), 64)
            output = StringIO()
            with redirect_stdout(output):
                status = main([
                    "plan-evaluate", "--task-set", str(task_path),
                    "--responses", str(response_path), "--report", str(report_path),
                ])
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(output.getvalue())["gatePassed"])
            with redirect_stdout(StringIO()):
                status = main([
                    "plan-evaluate", "--task-set", str(task_path),
                    "--responses", str(response_path), "--report", str(report_path),
                ])
            self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
