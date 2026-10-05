from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "phase2"))

from prepare_binding_representation_experiment import EXPECTED
from prepare_binding_representation_probe import LEVELS, build, validate
from run_binding_representation_experiment import diagnose


def _level(train_passes: int, eval_passes: int) -> dict:
    return {
        "suppliedConverged": train_passes == 6,
        "scoring": {
            "training": {"representationPass": train_passes},
            "evaluation": {"representationPass": eval_passes},
        },
    }


def test_exact_hashes_match_owner_approval() -> None:
    approval = json.loads((ROOT / "training/phase2/approvals/p2-06-binding-representation-v1.json").read_text())
    assert approval["approvalStatus"] == "approved"
    assert approval["objective"] == "answer-eos-only-complete-record-v1"
    assert approval["freshModelPerLevel"] is True
    assert approval["finalHoldoutOpened"] is False
    for level in LEVELS:
        assert approval["levels"][level]["candidateJsonlSha256"] == EXPECTED[level]["candidate"]
        assert approval["levels"][level]["evaluationJsonlSha256"] == EXPECTED[level]["evaluation"]
        assert approval["levels"][level]["evaluationApprovedForTraining"] is False


def test_probe_ladder_keeps_dual_and_css_splits_identical() -> None:
    levels = build()
    validate(levels)
    assert len(levels["single-copy"]["train"]) == 6
    assert len(levels["single-copy"]["evaluation"]) == 6
    assert [row["bindings"] for row in levels["dual-binding"]["train"]] == [
        row["bindings"] for row in levels["css-composition"]["train"]
    ]
    assert [row["bindings"] for row in levels["dual-binding"]["evaluation"]] == [
        row["bindings"] for row in levels["css-composition"]["evaluation"]
    ]


def test_diagnosis_stops_at_first_failed_capability() -> None:
    assert diagnose({
        "single-copy": _level(6, 5),
        "dual-binding": _level(6, 3),
        "css-composition": _level(6, 3),
    }) == "single-binding-copy-or-wording-transfer-bottleneck"
    assert diagnose({
        "single-copy": _level(6, 6),
        "dual-binding": _level(6, 2),
        "css-composition": _level(6, 3),
    }) == "simultaneous-independent-binding-bottleneck"
    assert diagnose({
        "single-copy": _level(6, 6),
        "dual-binding": _level(6, 3),
        "css-composition": _level(6, 2),
    }) == "code-composition-bottleneck-after-binding-preservation"
    assert diagnose({
        "single-copy": _level(6, 6),
        "dual-binding": _level(6, 3),
        "css-composition": _level(6, 3),
    }).startswith("representation-ladder-passed")


def test_failed_supplied_fit_is_inconclusive() -> None:
    result = diagnose({
        "single-copy": _level(5, 6),
        "dual-binding": _level(6, 3),
        "css-composition": _level(6, 3),
    })
    assert result.startswith("inconclusive-representation-ladder")
