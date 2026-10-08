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
    canonical_text_sha256,
    evaluate_plan_files,
    evaluate_plan_set,
    parse_plan_response,
    render_plan_prompt,
    validate_plan,
    validate_plan_task_set,
)
from plex_training.structured_plan_run import _contract, generate_structured_plans
from plex_training.structured_plan_diagnostic import (
    _diagnostic_contract,
    diagnose_structured_plan_responses,
)
from plex_training.structured_plan_bridge_diagnostic import diagnose_bridge_errors


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


class StructuredPlanDiagnosticTests(unittest.TestCase):
    def test_diagnostic_classifies_boundary_failures_without_repairing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_path = root / "tasks.json"
            responses_path = root / "responses.jsonl"
            task = _task_set()
            task_path.write_text(json.dumps(task), encoding="utf-8")
            good = json.dumps(json.loads(_good_responses()[0]["text"]))
            rows = [
                {"taskId": "h1", "text": "Answer: " + good, "truncated": False},
                {"taskId": "c1", "text": "{broken", "truncated": False},
                {"taskId": "j1", "text": "plain prose", "truncated": False},
            ]
            responses_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
            report = diagnose_structured_plan_responses(
                task_set_path=task_path,
                responses_path=responses_path,
            )
        self.assertEqual(report["tasksExpected"], 3)
        self.assertEqual(report["responsesPresent"], 3)
        self.assertEqual(report["strictValidPlans"], 0)
        self.assertEqual(report["classifications"]["extra-text-around-valid-plan"], 1)
        self.assertEqual(report["classifications"]["malformed-json-candidate"], 1)
        self.assertEqual(report["classifications"]["no-json-object-start"], 1)
        self.assertEqual(report["signals"]["embeddedStrictPlanValid"], 1)
        self.assertEqual(report["trainingPerformed"], False)
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertEqual(report["finalHoldoutOpened"], False)

    def test_diagnostic_reports_duplicate_outputs_and_missing_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_path = root / "tasks.json"
            responses_path = root / "responses.jsonl"
            task_path.write_text(json.dumps(_task_set()), encoding="utf-8")
            same = "no json"
            responses_path.write_text(
                json.dumps({"taskId": "h1", "text": same, "truncated": False}) + "\n"
                + json.dumps({"taskId": "c1", "text": same, "truncated": False}) + "\n",
                encoding="utf-8",
            )
            report = diagnose_structured_plan_responses(
                task_set_path=task_path,
                responses_path=responses_path,
            )
        self.assertEqual(report["responsesPresent"], 2)
        self.assertEqual(report["missingResponses"], ["j1"])
        self.assertEqual(report["uniqueResponseTexts"], 1)
        self.assertEqual(report["duplicateResponseTexts"], 1)


class StructuredPlanBridgeDiagnosticTests(unittest.TestCase):
    def test_p237_diagnostic_separates_syntax_schema_and_semantic_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task_path = root / "tasks.json"
            responses_path = root / "responses.jsonl"
            contract_path = root / "contract.json"
            task = _task_set()
            task_path.write_text(json.dumps(task), encoding="utf-8")
            good = json.loads(_good_responses()[0]["text"])
            semantic_wrong = {
                **good,
                "targetRole": "other-role",
                "constraints": [{"kind": "attribute", "key": "aria-label", "value": "Wrong"}],
                "searchHints": ["other"],
            }
            rows = [
                {"taskId": "h1", "text": json.dumps(semantic_wrong), "truncated": False},
                {"taskId": "c1", "text": "{broken", "truncated": False},
                {"taskId": "j1", "text": json.dumps({"schemaVersion": 1}), "truncated": False},
            ]
            response_text = "".join(json.dumps(row) + "\n" for row in rows)
            responses_path.write_text(response_text, encoding="utf-8")
            contract_path.write_text(json.dumps({
                "schemaVersion": 1,
                "milestone": "P2-37",
                "kind": "plex-p2-37-bridge-error-decomposition-contract-v1",
                "status": "diagnostic-authorized",
                "modelTrainingAuthorized": False,
                "taskSet": {
                    "sha256": canonical_text_sha256(task_path.read_bytes()),
                    "tasks": 3,
                },
                "responses": {
                    "sha256": hashlib.sha256(responses_path.read_bytes()).hexdigest(),
                },
                "protectedEvaluation": {
                    "noResponseRepair": True,
                    "noRescoring": True,
                    "noGradientUpdates": True,
                    "finalProjectHoldoutMustRemainClosed": True,
                },
            }), encoding="utf-8")
            report = diagnose_bridge_errors(
                task_set_path=task_path,
                responses_path=responses_path,
                contract_path=contract_path,
            )
        self.assertEqual(report["schemaValid"], 1)
        self.assertEqual(report["classifications"]["schema-valid-semantic-mismatch"], 1)
        self.assertEqual(report["classifications"]["invalid-json"], 1)
        self.assertEqual(report["classifications"]["parseable-json-invalid-plan-schema"], 1)
        self.assertEqual(report["schemaValidFieldCorrect"]["language"], 1)
        self.assertEqual(report["schemaValidFieldCorrect"]["action"], 1)
        self.assertEqual(report["schemaValidFieldCorrect"]["targetKind"], 1)
        self.assertEqual(report["schemaValidFieldCorrect"]["targetRole"], 0)
        self.assertEqual(report["schemaValidFieldCorrect"]["constraintsExact"], 0)
        self.assertEqual(report["schemaValidFieldCorrect"]["hintCoverage"], 0)
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])


class StructuredPlanFilesAndContractTests(unittest.TestCase):
    def test_p238_preparation_contract_blocks_training_and_targets_contrastive_full_plans(self) -> None:
        path = Path("training/pretraining/p2-38-semantic-binding-preparation-contract.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value["milestone"], "P2-38")
        self.assertEqual(value["status"], "design-preparation-only")
        self.assertTrue(value["dataPreparationAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertFalse(value["automaticTrainingExtension"])
        self.assertEqual(value["design"]["recordTarget"], 108)
        self.assertEqual(value["design"]["contrastGroups"], 36)
        self.assertEqual(value["design"]["recordsPerGroup"], 3)
        self.assertEqual(value["design"]["trainRecords"], 72)
        self.assertEqual(value["design"]["validationRecords"], 36)
        self.assertEqual(value["design"]["renderMode"], "structured-plan-production-prompt-only")
        self.assertEqual(value["design"]["targetFormat"], "strict-full-plan-only")
        self.assertTrue(value["design"]["uniqueTargetRolePerRecord"])
        self.assertTrue(value["design"]["noMicroJsonStages"])
        self.assertFalse(value["design"]["tokenizerRefit"])
        self.assertTrue(value["protectedEvaluation"]["p231DevelopmentExactRequestsExcluded"])
        self.assertTrue(value["protectedEvaluation"]["p231DevelopmentTargetRolesExcluded"])
        self.assertTrue(value["protectedEvaluation"]["p235TargetRolesExcluded"])
        self.assertTrue(value["protectedEvaluation"]["p236ResponsesExcludedFromTraining"])
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertIsNone(value["trainingCommand"])
        self.assertFalse(value["trainingPerformed"])
        self.assertEqual(value["researchOptimizerUpdates"], 0)

    def test_committed_p237_contract_pins_p236_responses(self) -> None:
        path = Path("training/pretraining/p2-37-bridge-error-decomposition-contract.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value["milestone"], "P2-37")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["taskSet"]["sha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["responses"]["sha256"],
            "7492c8d0158381b979b319a4d3a880c0bbba7d7b4227e300c4c68ff357ae7fbd",
        )
        self.assertTrue(value["protectedEvaluation"]["noResponseRepair"])
        self.assertTrue(value["protectedEvaluation"]["noRescoring"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])

    def test_committed_p240_contract_pins_p239_responses(self) -> None:
        path = Path("training/pretraining/p2-40-bridge-error-decomposition-contract.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value["milestone"], "P2-40")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["taskSet"]["sha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["responses"]["sha256"],
            "e9aca13ac5fed3286ad00294dc6fc87960ea66e7f22a9abd9cce375e0c92a3e6",
        )
        self.assertEqual(value["comparison"]["milestone"], "P2-39")
        self.assertEqual(value["comparison"]["schemaValid"], 5)
        self.assertEqual(value["comparison"]["checksPassed"], 54)
        self.assertTrue(value["protectedEvaluation"]["noResponseRepair"])
        self.assertTrue(value["protectedEvaluation"]["noRescoring"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])

    def test_committed_p234_contract_pins_failed_p233_responses(self) -> None:
        path = Path("training/pretraining/p2-34-output-boundary-contract.json")
        value = _diagnostic_contract(path)
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["taskSet"]["sha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["responses"]["sha256"],
            "ff7d199607030935b39b6b21a924958e43ac1583b9a02de170bab6ebcccf32d6",
        )
        self.assertTrue(value["protectedEvaluation"]["noResponseRepair"])
        self.assertTrue(value["protectedEvaluation"]["noRescoring"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])

    def test_canonical_task_hash_is_identical_for_lf_and_crlf(self) -> None:
        path = Path(__file__).parents[1] / "phase2" / "evaluation" / "p2-31-plan-dev-v1.json"
        lf = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        expected = "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5"
        self.assertEqual(canonical_text_sha256(lf), expected)
        self.assertEqual(canonical_text_sha256(crlf), expected)

    def test_shipped_set_is_balanced_hash_pinned_and_gate_is_predeclared(self) -> None:
        path = Path(__file__).parents[1] / "phase2" / "evaluation" / "p2-31-plan-dev-v1.json"
        raw = path.read_bytes()
        value = validate_plan_task_set(json.loads(raw.decode("utf-8")))
        self.assertEqual(canonical_text_sha256(raw),
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

    def test_p233_contract_reuses_original_gate_and_pins_p232_endpoint(self) -> None:
        path = Path("training/pretraining/p2-33-structured-bridge-contract.json")
        value = _contract(path)
        self.assertEqual(value["milestone"], "P2-33")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["checkpoint"]["sha256"],
            "707e46f9e3e87cdd9beec705e2bd55701b37a40e79aad7ab93858fa63f8ebcf4",
        )
        self.assertEqual(
            value["developmentEvaluation"]["taskSetSha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["developmentEvaluation"]["gate"],
            {"minimumPassed": 12, "minimumPerLanguage": 3, "minimumSchemaValid": 15},
        )
        self.assertEqual(
            value["checkpointProvenance"],
            {
                "stageKind": "plex-structured-plan-stage-transition-v1",
                "stageMilestone": "P2-32",
                "trainingSettingsKind": "p2-32-authorized-structured-plan-training-v1",
            },
        )
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])

    def test_p236_contract_reuses_original_gate_and_pins_p235_endpoint(self) -> None:
        path = Path("training/pretraining/p2-36-structured-bridge-contract.json")
        value = _contract(path)
        self.assertEqual(value["milestone"], "P2-36")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["checkpoint"]["sha256"],
            "1fafce16260ab8910465517c7f571b34dccf7f21ec1ad9d281dad53ab87fbcd0",
        )
        self.assertEqual(
            value["developmentEvaluation"]["taskSetSha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["developmentEvaluation"]["gate"],
            {"minimumPassed": 12, "minimumPerLanguage": 3, "minimumSchemaValid": 15},
        )
        self.assertEqual(
            value["checkpointProvenance"],
            {
                "stageKind": "plex-serialization-stability-stage-transition-v1",
                "stageMilestone": "P2-35",
                "trainingSettingsKind":
                    "p2-35-authorized-serialization-stability-training-v1",
            },
        )
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["p231DevelopmentWasExcludedFromP235Gradients"])
        self.assertTrue(value["protectedEvaluation"]["p233ResponsesWereExcludedFromP235Gradients"])

    def test_p239_contract_reuses_original_gate_and_pins_p238_endpoint(self) -> None:
        path = Path("training/pretraining/p2-39-structured-bridge-contract.json")
        value = _contract(path)
        self.assertEqual(value["milestone"], "P2-39")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["checkpoint"]["sha256"],
            "9117e34433d6faa404117f557a48d12e840355ed5c7580d5b60f8e565564dbf6",
        )
        self.assertEqual(
            value["developmentEvaluation"]["taskSetSha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["developmentEvaluation"]["gate"],
            {"minimumPassed": 12, "minimumPerLanguage": 3, "minimumSchemaValid": 15},
        )
        self.assertEqual(
            value["checkpointProvenance"],
            {
                "stageKind": "plex-semantic-binding-stage-transition-v1",
                "stageMilestone": "P2-38",
                "trainingSettingsKind":
                    "p2-38-authorized-semantic-binding-training-v1",
            },
        )
        self.assertEqual(value["comparisonBaseline"]["milestone"], "P2-36")
        self.assertEqual(value["comparisonBaseline"]["schemaValid"], 5)
        self.assertEqual(value["comparisonBaseline"]["checksPassed"], 56)
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["p231DevelopmentWasExcludedFromP238Gradients"])
        self.assertTrue(value["protectedEvaluation"]["p236ResponsesWereExcludedFromP238Gradients"])

    def test_p242_contract_reuses_original_gate_and_pins_p241_endpoint(self) -> None:
        path = Path("training/pretraining/p2-42-structured-bridge-contract.json")
        value = _contract(path)
        self.assertEqual(value["milestone"], "P2-42")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["checkpoint"]["sha256"],
            "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc",
        )
        self.assertEqual(
            value["developmentEvaluation"]["taskSetSha256"],
            "8e3f30f93abbbd1b96223b26e21f35d362d2b1084857072c4d7d72a014c527f5",
        )
        self.assertEqual(
            value["developmentEvaluation"]["gate"],
            {"minimumPassed": 12, "minimumPerLanguage": 3, "minimumSchemaValid": 15},
        )
        self.assertEqual(
            value["checkpointProvenance"],
            {
                "stageKind": "plex-request-conditioned-plan-binding-stage-transition-v1",
                "stageMilestone": "P2-41",
                "trainingSettingsKind": "p2-41-authorized-request-binding-training-v1",
            },
        )
        self.assertEqual(value["comparisonBaseline"]["milestone"], "P2-39")
        self.assertEqual(value["comparisonBaseline"]["schemaValid"], 5)
        self.assertEqual(value["comparisonBaseline"]["checksPassed"], 54)
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["p231DevelopmentWasExcludedFromP241Gradients"])
        self.assertTrue(value["protectedEvaluation"]["p239ResponsesWereExcludedFromP241Gradients"])

    def test_contract_rejects_unknown_structured_bridge_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "milestone": "P2-99",
                "kind": "made-up",
                "status": "evaluation-authorized",
                "modelTrainingAuthorized": False,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing or does not block training"):
                _contract(path)

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
