"""Portable regressions for P2-48 request-grounded bundle preparation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plex_training.request_grounded_coding_bundle import (
    EXPECTED_MAX_RECORD_TOKENS,
    EXPECTED_TRAIN_TOKEN_COUNT,
    EXPECTED_VALIDATION_TOKEN_COUNT,
    prepare_request_grounded_bundle,
    preflight_request_grounded_bundle,
)
from plex_training.request_grounded_coding_curriculum import (
    build_candidate_rows,
    generate_request_grounded_coding_candidate,
    render_request_grounded_change_prompt,
)

TASK_SET = Path("training/phase2/evaluation/p2-31-plan-dev-v1.json")
P247_CONTRACT = Path(
    "training/pretraining/p2-47-request-grounded-coding-preparation-contract.json"
)
P248_CONTRACT = Path(
    "training/pretraining/p2-48-final-transfer-preparation-contract.json"
)
P247_REVIEW_RESULT = Path(
    "training/pretraining/p2-47-request-grounded-coding-review-result.json"
)


class _FakeTokenizer:
    vocabulary_size = 16384

    def __init__(self) -> None:
        rows = build_candidate_rows()
        train = [row for row in rows if row["candidateSplit"] == "train"]
        validation = [row for row in rows if row["candidateSplit"] == "validation"]

        packed_train = [286] + [268] * 8 + [269] * 63
        packed_validation = [272] * 7 + [271] * 29
        self._lengths: dict[str, int] = {}
        self._ids: dict[str, int] = {}
        self._text_by_id: dict[int, str] = {}

        for rows_for_split, packed_counts in (
            (train, packed_train),
            (validation, packed_validation),
        ):
            for row, packed in zip(rows_for_split, packed_counts, strict=True):
                text = (
                    render_request_grounded_change_prompt(
                        row["language"],
                        row["request"],
                    )
                    + row["solution"]
                )
                token_id = 1000 + len(self._ids)
                self._ids[text] = token_id
                self._text_by_id[token_id] = text
                self._lengths[text] = packed - 1

    def encode(self, text: str) -> list[int]:
        return [self._ids[text]] * self._lengths[text]

    def decode(self, ids: list[int]) -> str:
        if not ids:
            return ""
        return self._text_by_id[ids[0]]


class RequestGroundedBundleTests(unittest.TestCase):
    def test_fake_tokenizer_matches_real_review_accounting(self) -> None:
        fake = _FakeTokenizer()
        rows = build_candidate_rows()
        totals = {"train": 0, "validation": 0}
        maximum = 0
        for row in rows:
            text = (
                render_request_grounded_change_prompt(
                    row["language"],
                    row["request"],
                )
                + row["solution"]
            )
            packed = len(fake.encode(text)) + 1
            totals[row["candidateSplit"]] += packed
            maximum = max(maximum, packed)
        self.assertEqual(totals["train"], EXPECTED_TRAIN_TOKEN_COUNT)
        self.assertEqual(totals["validation"], EXPECTED_VALIDATION_TOKEN_COUNT)
        self.assertEqual(maximum, EXPECTED_MAX_RECORD_TOKENS)

    def test_pack_and_sampler_preflight_remain_zero_update(self) -> None:
        fake = _FakeTokenizer()
        identity = {
            "tokenizerSha256":
                "2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697",
            "bundleManifestSha256":
                "46d6e4501d56c45196e604fb78dafaaada49e6c386badaae07ffbd4d6794f5d6",
            "actualVocabularySize": 16384,
        }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = root / "artifacts"
            source = artifacts / "structured-plan" / "p2-44-training-bundle"
            output = artifacts / "request-grounded" / "p2-48-training-bundle"
            candidate = root / "candidate.jsonl"
            review = root / "review.json"
            source.mkdir(parents=True)
            for name in ("tokenizer.json", "tokenizer-config.json", "model-config.json"):
                (source / name).write_text("{}\n", encoding="utf-8")

            generate_request_grounded_coding_candidate(
                candidate_path=candidate,
                review_path=review,
                development_task_set_path=TASK_SET,
                contract_path=P247_CONTRACT,
            )

            with patch(
                "plex_training.request_grounded_coding_curriculum._completion_tokenizer",
                return_value=(fake, identity),
            ), patch(
                "plex_training.request_grounded_coding_bundle._completion_tokenizer",
                return_value=(fake, identity),
            ):
                packed = prepare_request_grounded_bundle(
                    candidate_path=candidate,
                    review_path=review,
                    development_task_set_path=TASK_SET,
                    source_bundle_dir=source,
                    output_dir=output,
                    artifact_root=artifacts,
                    preparation_contract_path=P248_CONTRACT,
                    review_result_path=P247_REVIEW_RESULT,
                )

                self.assertEqual(
                    packed["status"],
                    "training-bundle-prepared-zero-update",
                )
                self.assertEqual(packed["trainRecords"], 72)
                self.assertEqual(packed["validationRecords"], 36)
                self.assertEqual(
                    packed["trainTokenCount"],
                    EXPECTED_TRAIN_TOKEN_COUNT,
                )
                self.assertEqual(
                    packed["validationTokenCount"],
                    EXPECTED_VALIDATION_TOKEN_COUNT,
                )
                self.assertEqual(
                    packed["maximumRecordTokensIncludingEos"],
                    EXPECTED_MAX_RECORD_TOKENS,
                )
                self.assertFalse(packed["checkpointStagingAuthorized"])
                self.assertFalse(packed["optimizerCreationAuthorized"])
                self.assertFalse(packed["modelTrainingAuthorized"])
                self.assertFalse(packed["trainingPerformed"])
                self.assertEqual(packed["researchOptimizerUpdates"], 0)
                self.assertFalse(packed["finalHoldoutOpened"])

                with patch(
                    "plex_training.request_grounded_coding_bundle.PlexTokenizer.load",
                    return_value=fake,
                ):
                    preflight = preflight_request_grounded_bundle(
                        bundle_dir=output,
                        preparation_contract_path=P248_CONTRACT,
                        review_result_path=P247_REVIEW_RESULT,
                    )

        self.assertEqual(
            preflight["status"],
            "bundle-preflight-passed-awaiting-stage-decision",
        )
        self.assertTrue(preflight["proposalOnly"])
        self.assertEqual(preflight["proposedRun"]["examples"], 1600)
        self.assertEqual(preflight["proposedRun"]["recordsSelected"], 72)
        self.assertGreater(preflight["proposedRun"]["minimumRecordSelections"], 0)
        self.assertGreater(
            preflight["proposedRun"]["expectedRealTargetPositions"],
            0,
        )
        self.assertFalse(preflight["checkpointStagingAuthorized"])
        self.assertFalse(preflight["optimizerCreationAuthorized"])
        self.assertFalse(preflight["modelTrainingAuthorized"])
        self.assertFalse(preflight["trainingPerformed"])
        self.assertEqual(preflight["researchOptimizerUpdates"], 0)
        self.assertFalse(preflight["finalHoldoutOpened"])


if __name__ == "__main__":
    unittest.main()
