from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "training/phase2"
if str(PHASE2) not in sys.path:
    sys.path.insert(0, str(PHASE2))

from prepare_counterbalanced_composition import FOLD_HELDOUT, GAPS, SELECTORS, fold_rows
from run_counterbalanced_composition import interpretation


def _matrix():
    return [
        {
            "id": f"cell-{i}-{j}",
            "bindings": {"selector": selector, "gap": gap},
        }
        for i, selector in enumerate(SELECTORS)
        for j, gap in enumerate(GAPS)
    ]


def test_three_folds_hold_out_every_matrix_cell_exactly_once():
    heldout = [pair for pairs in FOLD_HELDOUT.values() for pair in pairs]
    assert len(heldout) == 9
    assert len(set(heldout)) == 9
    assert set(heldout) == {(selector, gap) for selector in SELECTORS for gap in GAPS}


def test_each_fold_is_six_train_three_holdout_and_slot_balanced():
    matrix = _matrix()
    for fold_name in FOLD_HELDOUT:
        train, heldout = fold_rows(matrix, fold_name)
        assert len(train) == 6
        assert len(heldout) == 3
        assert {tuple(row["bindings"][key] for key in ("selector", "gap")) for row in heldout} == set(FOLD_HELDOUT[fold_name])
        for selector in SELECTORS:
            assert sum(row["bindings"]["selector"] == selector for row in train) == 2
        for gap in GAPS:
            assert sum(row["bindings"]["gap"] == gap for row in train) == 2


def test_interpretation_requires_all_supplied_folds_to_converge():
    assert interpretation(2, 9).startswith("inconclusive-counterbalanced-transfer")
    assert interpretation(3, 9).startswith("full-counterbalanced")
    assert interpretation(3, 8).startswith("strong-counterbalanced")
    assert interpretation(3, 5).startswith("partial-counterbalanced")
    assert interpretation(3, 2).startswith("limited-counterbalanced")
    assert interpretation(3, 0).startswith("no-counterbalanced")


def test_owner_approval_pins_bounds_and_fold_local_claim():
    approval = json.loads((PHASE2 / "approvals/p2-05-counterbalanced-composition-v1.json").read_text(encoding="utf-8"))
    assert approval["approvalStatus"] == "approved"
    assert approval["objective"] == "answer-eos-only-complete-record-v1"
    assert approval["matrixRecords"] == 9
    assert approval["trainingRecordsPerFold"] == 6
    assert approval["heldOutRecordsPerFold"] == 3
    assert approval["foldLocalHeldoutOnly"] is True
    assert approval["globalPristineHoldoutClaim"] is False
    assert approval["limits"]["maximumStepsPerFold"] == 100
    assert approval["limits"]["maximumMinutesPerFold"] == 10
    assert approval["limits"]["maximumTotalSteps"] == 300
    assert approval["limits"]["maximumTotalMinutes"] == 30
    assert approval["limits"]["finalHoldoutOpened"] is False
