"""Portable regressions for P2-44 bundle packing and zero-update sampler preflight."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.structured_plan import render_plan_request_prompt
from plex_training.structured_plan_evidence_composition_bundle import (
    EXPECTED_TRAIN_TOKEN_COUNT,
    EXPECTED_VALIDATION_TOKEN_COUNT,
    prepare_evidence_composition_bundle,
    preflight_evidence_composition_bundle,
)
from plex_training.structured_plan_evidence_composition_curriculum import (
    build_candidate_rows,
    generate_evidence_composition_candidate,
)

TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
CONTRACT = Path(
    "training/pretraining/p2-44-evidence-first-semantic-composition-preparation-contract.json"
)


class _FakeTokenizer:
    vocabulary_size = 16384

    def __init__(self) -> None:
        rows = build_candidate_rows()
        train = [row for row in rows if row["candidateSplit"] == "train"]
        validation = [row for row in rows if row["candidateSplit"] == "validation"]
        counts: dict[str, int] = {}

        for index, row in enumerate(train):
            packed = 375 if index == 0 else 355 if index <= 27 else 354
            text = render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            counts[text] = packed - 1

        for index, row in enumerate(validation):
            packed = 356 if index < 16 else 355
            text = render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            counts[text] = packed - 1

        self._lengths = counts
        self._ids = {text: 1000 + index for index, text in enumerate(counts)}
        self._text_by_id = {value: key for key, value in self._ids.items()}

        self.train_packed = sum(
            self._lengths[
                render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            ]
            + 1
            for row in train
        )
        self.validation_packed = sum(
            self._lengths[
                render_plan_request_prompt(row["language"], row["request"]) + row["solution"]
            ]
            + 1
            for row in validation
        )

    def encode(self, text: str) -> list[int]:
        token_id = self._ids[text]
        return [token_id] * self._lengths[text]

    def decode(self, ids: list[int]) -> str:
        if not ids:
            return ""
        return self._text_by_id[ids[0]]


class EvidenceCompositionBundleTests(unittest.TestCase):
    def test_fake_tokenizer_fixture_matches_frozen_accounting(self) -> None:
        tokenizer = _FakeTokenizer()
        self.assertEqual(tokenizer.train_packed, EXPECTED_TRAIN_TOKEN_COUNT)
        self.assertEqual(tokenizer.validation_packed, EXPECTED_VALIDATION_TOKEN_COUNT)

    def test_pack_inspect_and_sampler_preflight_remain_zero_update(self) -> None:
        fake = _FakeTokenizer()
        identity = {
            "tokenizerSha256":
                "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
            "bundleManifestSha256":
                "a05e09493778ca772d583a17e01fbd3a5efa84c3897f7865f89ab9679518b22a",
            "actualVocabularySize": 16384,
        }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            source = artifacts / "structured-plan" / "p2-41-training-bundle"
            output = artifacts / "structured-plan" / "p2-44-training-bundle"
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            source.mkdir(parents=True)
            for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
                (source / name).write_text("{}\n", encoding="utf-8")

            generate_evidence_composition_candidate(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=CONTRACT,
            )

            with patch(
                "plex_training.structured_plan_evidence_composition_curriculum._completion_tokenizer",
                return_value=(fake, identity),
            ), patch(
                "plex_training.structured_plan_evidence_composition_bundle._completion_tokenizer",
                return_value=(fake, identity),
            ):
                packed = prepare_evidence_composition_bundle(
                    candidate_path=candidate,
                    review_path=review,
                    development_task_set_path=TASK_SET,
                    source_bundle_dir=source,
                    output_dir=output,
                    artifact_root=artifacts,
                    preparation_contract_path=CONTRACT,
                )

                self.assertEqual(packed["status"], "training-bundle-prepared-zero-update")
                self.assertEqual(packed["trainRecords"], 108)
                self.assertEqual(packed["validationRecords"], 54)
                self.assertEqual(packed["trainTokenCount"], EXPECTED_TRAIN_TOKEN_COUNT)
                self.assertEqual(packed["validationTokenCount"], EXPECTED_VALIDATION_TOKEN_COUNT)
                self.assertEqual(packed["maximumRecordTokensIncludingEos"], 375)
                self.assertFalse(packed["modelTrainingAuthorized"])
                self.assertFalse(packed["checkpointStagingAuthorized"])
                self.assertEqual(packed["researchOptimizerUpdates"], 0)

                with patch(
                    "plex_training.structured_plan_evidence_composition_bundle.PlexTokenizer.load",
                    return_value=fake,
                ):
                    preflight = preflight_evidence_composition_bundle(
                        bundle_dir=output,
                        preparation_contract_path=CONTRACT,
                    )

            self.assertEqual(
                preflight["status"],
                "bundle-preflight-passed-awaiting-separate-stage-decision",
            )
            self.assertEqual(preflight["proposedRun"]["examples"], 1600)
            self.assertEqual(preflight["sampler"]["kind"], "complete-record-v1")
            self.assertEqual(preflight["sampler"]["records"], 108)
            self.assertEqual(preflight["proposedRun"]["recordsSelected"], 108)
            self.assertGreater(preflight["proposedRun"]["minimumRecordSelections"], 0)
            self.assertGreater(
                preflight["proposedRun"]["expectedRealTargetPositions"],
                0,
            )
            self.assertTrue(preflight["proposalOnly"])
            self.assertFalse(preflight["modelTrainingAuthorized"])
            self.assertFalse(preflight["checkpointStagingAuthorized"])
            self.assertFalse(preflight["optimizerCreationAuthorized"])
            self.assertFalse(preflight["trainingPerformed"])
            self.assertEqual(preflight["researchOptimizerUpdates"], 0)
            self.assertFalse(preflight["finalHoldoutOpened"])


if __name__ == "__main__":
    unittest.main()
