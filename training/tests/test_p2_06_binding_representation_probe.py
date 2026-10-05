from __future__ import annotations

from collections import Counter

import pytest

from prepare_binding_representation_probe import (
    GAPS,
    HELDOUT_PAIRS,
    LEVELS,
    SELECTORS,
    TRAIN_PAIRS,
    build,
    pair,
    validate,
)


def test_p2_06_counts_and_levels() -> None:
    levels = build()
    assert tuple(levels) == LEVELS
    assert len(levels["single-copy"]["train"]) == 6
    assert len(levels["single-copy"]["evaluation"]) == 6
    assert len(levels["dual-binding"]["train"]) == 6
    assert len(levels["dual-binding"]["evaluation"]) == 3
    assert len(levels["css-composition"]["train"]) == 6
    assert len(levels["css-composition"]["evaluation"]) == 3
    validate(levels)


def test_single_copy_uses_same_values_with_different_wording() -> None:
    levels = build()
    train = levels["single-copy"]["train"]
    evaluation = levels["single-copy"]["evaluation"]
    assert {row["bindings"].get("selector") for row in train if "selector" in row["bindings"]} == set(SELECTORS)
    assert {row["bindings"].get("selector") for row in evaluation if "selector" in row["bindings"]} == set(SELECTORS)
    assert {row["bindings"].get("gap") for row in train if "gap" in row["bindings"]} == set(GAPS)
    assert {row["bindings"].get("gap") for row in evaluation if "gap" in row["bindings"]} == set(GAPS)
    assert {row["request"] for row in train}.isdisjoint({row["request"] for row in evaluation})
    assert all(row["contract"] == "Return exactly the requested token and nothing else." for row in train + evaluation)


def test_dual_and_css_share_identical_binding_split() -> None:
    levels = build()
    for split, expected in (("train", set(TRAIN_PAIRS)), ("evaluation", set(HELDOUT_PAIRS))):
        dual = levels["dual-binding"][split]
        css = levels["css-composition"][split]
        assert {pair(row) for row in dual} == expected
        assert {pair(row) for row in css} == expected
        assert [row["bindings"] for row in dual] == [row["bindings"] for row in css]


def test_matrix_is_balanced_and_complete() -> None:
    assert not (set(TRAIN_PAIRS) & set(HELDOUT_PAIRS))
    assert set(TRAIN_PAIRS) | set(HELDOUT_PAIRS) == {
        (selector, gap) for selector in SELECTORS for gap in GAPS
    }
    for rows in (build()["dual-binding"]["train"], build()["css-composition"]["train"]):
        assert Counter(row["bindings"]["selector"] for row in rows) == Counter({value: 2 for value in SELECTORS})
        assert Counter(row["bindings"]["gap"] for row in rows) == Counter({value: 2 for value in GAPS})


def test_training_candidates_are_not_approved() -> None:
    levels = build()
    for level in LEVELS:
        assert all(row["approvalStatus"] == "pending-owner-review" for row in levels[level]["train"])
        assert all(row["approvalStatus"] == "evaluation-only" for row in levels[level]["evaluation"])
        assert all(row["use"] == "evaluation-only-never-train" for row in levels[level]["evaluation"])


def test_validation_rejects_pair_drift() -> None:
    levels = build()
    levels["dual-binding"]["evaluation"][0]["bindings"]["gap"] = "99px"
    with pytest.raises(ValueError):
        validate(levels)
