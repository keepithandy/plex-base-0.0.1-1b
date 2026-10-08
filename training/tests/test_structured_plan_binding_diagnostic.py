"""P2-43 semantic-bundle reuse diagnostic regressions."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from plex_training.structured_plan import canonical_text_sha256
from plex_training.structured_plan_binding_diagnostic import (
    _contract,
    diagnose_semantic_bundle_reuse,
)

TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
P241 = Path("training/phase2/drafts/p2-41-request-conditioned-plan-binding-v1.jsonl")
CONTRACT = Path("training/pretraining/p2-43-semantic-bundle-reuse-contract.json")


class StructuredPlanBindingDiagnosticTests(unittest.TestCase):
    def test_committed_contract_is_read_only_and_pins_p242_endpoint(self) -> None:
        value = _contract(CONTRACT)
        self.assertEqual(value["milestone"], "P2-43")
        self.assertFalse(value["modelTrainingAuthorized"])
        self.assertEqual(
            value["p242Run"]["checkpointSha256"],
            "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc",
        )
        self.assertEqual(
            value["p241Candidate"]["sha256"],
            "20f309181adbd4c86ff0c5a7ad833792d754e3a9102000003922696a237b64ba",
        )
        self.assertTrue(value["protectedEvaluation"]["developmentOnly"])
        self.assertTrue(value["protectedEvaluation"]["noGradientUpdates"])
        self.assertTrue(value["protectedEvaluation"]["noResponseRepair"])
        self.assertTrue(value["protectedEvaluation"]["noCheckpointSelection"])
        self.assertTrue(value["protectedEvaluation"]["finalProjectHoldoutMustRemainClosed"])

    def test_diagnostic_detects_exact_training_bundle_reuse(self) -> None:
        task_set = json.loads(TASK_SET.read_text(encoding="utf-8"))
        first_p241 = json.loads(P241.read_text(encoding="utf-8").splitlines()[0])
        reused_plan_text = first_p241["solution"]

        responses = []
        for index, task in enumerate(task_set["tasks"]):
            expected = task["expectedPlan"]
            if index == 0:
                text = reused_plan_text
            else:
                text = json.dumps(
                    {
                        "schemaVersion": 1,
                        "language": task["language"],
                        "action": expected["action"],
                        "targetKind": expected["targetKind"],
                        "targetRole": expected["targetRole"],
                        "constraints": expected["constraints"],
                        "searchHints": expected["hintKeywords"],
                    },
                    separators=(",", ":"),
                )
            responses.append({"taskId": task["id"], "text": text, "truncated": False})

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            responses_path = root / "responses.jsonl"
            manifest_path = root / "run-manifest.json"
            with responses_path.open("w", encoding="utf-8", newline="\n") as stream:
                for row in responses:
                    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

            responses_sha = hashlib.sha256(responses_path.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "milestone": "P2-42",
                        "trainingPerformed": False,
                        "researchOptimizerUpdates": 0,
                        "finalHoldoutOpened": False,
                        "taskSetSha256": canonical_text_sha256(TASK_SET.read_bytes()),
                        "taskCount": 18,
                        "checkpointSha256":
                            "adec7fa31e40a52caa89aa7bb7150983ce7c4f1c5df899285cec3e3f24bf79cc",
                        "checkpointStep": 100,
                        "tokenizerSha256":
                            "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
                        "tokenizerBundleManifestSha256":
                            "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a",
                        "responsesSha256": responses_sha,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            report = diagnose_semantic_bundle_reuse(
                task_set_path=TASK_SET,
                responses_path=responses_path,
                p241_candidate_path=P241,
                p242_manifest_path=manifest_path,
                contract_path=CONTRACT,
            )

        self.assertEqual(report["summary"]["schemaValid"], 18)
        self.assertEqual(report["summary"]["fieldCorrect"]["targetRole"], 17)
        self.assertEqual(report["summary"]["trainingReuse"]["targetRole"], 1)
        self.assertEqual(report["summary"]["trainingReuse"]["semanticBundle"], 1)
        self.assertEqual(report["summary"]["trainingReuse"]["fullPlan"], 1)
        self.assertEqual(report["summary"]["trainingReuse"]["wrongTargetRoleButSeenInTrain"], 1)
        self.assertEqual(
            report["summary"]["trainingReuse"]["wrongPlanButExactTrainSemanticBundle"], 1
        )
        self.assertEqual(report["summary"]["classifications"]["semantic-pass"], 17)
        self.assertEqual(
            report["summary"]["classifications"]["wrong-plan-exact-train-bundle"], 1
        )
        self.assertFalse(report["trainingPerformed"])
        self.assertEqual(report["researchOptimizerUpdates"], 0)
        self.assertFalse(report["finalHoldoutOpened"])


if __name__ == "__main__":
    unittest.main()
