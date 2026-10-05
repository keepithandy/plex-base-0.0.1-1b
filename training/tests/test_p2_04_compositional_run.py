from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "training/phase2"
sys.path.insert(0, str(PHASE2))

from prepare_compositional_binding_candidate import build  # noqa: E402
from run_compositional_experiment import validate_bounds  # noqa: E402


def test_owner_approval_pins_exact_six_and_three() -> None:
    approval = json.loads(
        (PHASE2 / "approvals/p2-04-compositional-binding-probe-v1.json").read_text(encoding="utf-8")
    )
    assert approval["approvalStatus"] == "approved"
    assert approval["approvedBy"] == "repository-owner"
    assert approval["sourceId"] == "gap-css-layout-01"
    assert approval["candidateJsonlSha256"] == "df7a6b6f8592006c37612b2b179fb9aee278d966914136284d52a63991c8c754"
    assert approval["evaluationJsonlSha256"] == "578c7e376301751e61112b02feb2a9651f9858efc2276b0bf5067de2e5acccff"
    assert approval["records"] == 6
    assert approval["evaluationOnlyRecords"] == 3
    assert approval["evaluationApprovedForTraining"] is False
    assert approval["objective"] == "answer-eos-only-complete-record-v1"
    assert approval["heldOutPairs"] == [
        [".actions", "28px"],
        [".filters", "6px"],
        [".controls", "14px"],
    ]


def test_layout_matrix_is_balanced_and_heldout_pairs_are_unseen() -> None:
    train, heldout, design = build("gap-css-layout-01")
    assert len(train) == 6
    assert len(heldout) == 3
    train_pairs = {(row["bindings"]["selector"], row["bindings"]["gap"]) for row in train}
    heldout_pairs = {(row["bindings"]["selector"], row["bindings"]["gap"]) for row in heldout}
    assert train_pairs.isdisjoint(heldout_pairs)
    assert heldout_pairs == {
        (".actions", "28px"),
        (".filters", "6px"),
        (".controls", "14px"),
    }
    for selector in design["slotAValues"]:
        assert sum(row["bindings"]["selector"] == selector for row in train) == 2
    for gap in design["slotBValues"]:
        assert sum(row["bindings"]["gap"] == gap for row in train) == 2


def test_p2_04_bounds_reject_automatic_extension() -> None:
    validate_bounds(100, 10.0)
    with pytest.raises(ValueError):
        validate_bounds(101, 10.0)
    with pytest.raises(ValueError):
        validate_bounds(100, 10.01)
    with pytest.raises(ValueError):
        validate_bounds(0, 10.0)
