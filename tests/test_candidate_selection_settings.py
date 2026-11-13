"""Regression tests for strict, bounded clip selection settings."""
import pytest

from app.services.candidates import Candidate, select_candidates


@pytest.mark.parametrize("invalid", [True, False, 0, -1, 6, 1.5, "5", None])
def test_rejects_invalid_clip_counts(invalid):
    with pytest.raises(ValueError, match="Invalid candidate selection settings"):
        select_candidates([], max_count=invalid)


@pytest.mark.parametrize("field,value", [
    ("threshold", True), ("threshold", None), ("threshold", "75"),
    ("threshold", float("nan")), ("threshold", float("inf")),
    ("max_overlap_ratio", False), ("max_overlap_ratio", None),
    ("max_overlap_ratio", "0.25"), ("max_overlap_ratio", float("nan")),
])
def test_rejects_invalid_numeric_settings(field, value):
    with pytest.raises(ValueError, match="Invalid candidate selection settings"):
        select_candidates([], **{field: value})


def test_keeps_five_highest_scoring_nonoverlapping_clips():
    candidates = [Candidate(i * 30, (i + 1) * 30, 95 - i) for i in range(8)]
    selected = select_candidates(candidates, threshold=70, max_count=5)
    assert len(selected) == 5
    assert selected == candidates[:5]


def test_overlapping_duplicate_is_filtered():
    selected = select_candidates([
        Candidate(0, 30, 95),
        Candidate(1, 29, 94),
        Candidate(30, 60, 90),
    ])
    assert [(item.start, item.end) for item in selected] == [(0, 30), (30, 60)]
