"""Portable tests for the P2-35 serialization-stability curriculum."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from plex_training.cli import main
from plex_training.structured_plan_serialization_curriculum import (
    EXPECTED_CANDIDATE_SHA256,
    _contract,
    render_p235_record,
    review_serialization_stability_curriculum,
)


class P235SerializationCurriculumTests(unittest.TestCase):
    def test_committed_candidate_passes_static_review(self) -> None:
        report = review_serialization_stability_curriculum(
            candidate_path=Path(
                "training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl"
            ),
            review_path=Path(
                "training/phase2/drafts/p2-35-serialization-stability-candidate-v1.review.json"
            ),
            development_task_set_path=Path(
                "training/phase2/evaluation/p2-31-plan-dev-v1.json"
            ),
            contract_path=Path(
                "training/pretraining/p2-35-serialization-stability-preparation-contract.json"
            ),
        )
        self.assertEqual(report["status"], "candidate-review-passed")
        self.assertEqual(report["candidateSha256"], EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(report["records"], 144)
        self.assertEqual(report["trainRecords"], 108)
        self.assertEqual(report["validationRecords"], 36)
        self.assertEqual(report["groups"], 24)
        self.assertEqual(report["trainGroups"], 18)
        self.assertEqual(report["validationGroups"], 6)
        self.assertEqual(report["perLevel"], {level: 24 for level in "ABCDEF"})
        self.assertEqual(report["jsonObjectSolutions"], 144)
        self.assertEqual(report["strictFullPlanSolutions"], 48)
        self.assertEqual(report["developmentTargetRoleOverlap"], 0)
        self.assertEqual(report["developmentExactRequestOverlap"], 0)
        self.assertFalse(report["p233ResponsesUsedForTraining"])
        self.assertFalse(report["modelTrainingAuthorized"])
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])
        self.assertFalse(report["tokenizerPreflight"]["checked"])

    def test_preparation_contract_blocks_training(self) -> None:
        value = _contract(
            Path("training/pretraining/p2-35-serialization-stability-preparation-contract.json")
        )
        self.assertTrue(value["dataPreparationAuthorized"])
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertFalse(value["automaticTrainingExtension"])
        self.assertIsNone(value["trainingCommand"])
        self.assertEqual(
            value["baseCheckpoint"]["sha256"],
            "707e46f9e3e87cdd9beec705e2bd55701b37a40e79aad7ab93858fa63f8ebcf4",
        )

    def test_candidate_contains_six_coherent_stages_per_group(self) -> None:
        path = Path("training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        groups: dict[str, list[dict]] = {}
        for row in rows:
            groups.setdefault(row["splitGroupId"], []).append(row)
        self.assertEqual(len(groups), 24)
        for entries in groups.values():
            self.assertEqual({entry["level"] for entry in entries}, set("ABCDEF"))
            self.assertEqual(len(entries), 6)
            self.assertEqual(
                {entry["renderMode"] for entry in entries if entry["level"] == "F"},
                {"structured-plan"},
            )
            self.assertEqual(
                {entry["renderMode"] for entry in entries if entry["level"] != "F"},
                {"micro-json"},
            )

    def test_render_modes_keep_micro_and_production_prompts_distinct(self) -> None:
        path = Path("training/phase2/drafts/p2-35-serialization-stability-candidate-v1.jsonl")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        group = [row for row in rows if row["splitGroupId"] == rows[0]["splitGroupId"]]
        by_level = {row["level"]: row for row in group}
        micro = render_p235_record(by_level["A"])
        production = render_p235_record(by_level["F"])
        self.assertTrue(micro.startswith("Practice exact JSON serialization.\n"))
        self.assertIn("Serialize exactly this flat JSON object", micro)
        self.assertTrue(production.startswith(
            "Convert the repository-style request into one semantic edit plan.\n"
        ))
        self.assertTrue(micro.endswith(by_level["A"]["solution"]))
        self.assertTrue(production.endswith(by_level["F"]["solution"]))

    def test_cli_review_writes_no_training_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "review.json"
            status = main([
                "plan-serialization-review",
                "--report", str(report_path),
            ])
            self.assertEqual(status, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["records"], 144)
            self.assertFalse(report["trainingPerformed"])
            self.assertEqual(report["researchOptimizerUpdates"], 0)


if __name__ == "__main__":
    unittest.main()
